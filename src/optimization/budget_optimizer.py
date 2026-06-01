"""
LKR 5 Million Western Province Trade Marketing Budget Optimizer.

Allocates the fixed LKR 5M promotional budget across eligible Western Province 
outlets using a risk-adjusted ROI greedy knapsack approach, while enforcing:
  - Total budget cap (LKR 5M)
  - Per-outlet min/max spend bounds
  - Distributor fairness floors (3 WP distributors each guaranteed a floor)
  - Minimum confidence and potential gap thresholds

Output: outputs/predictions/quadnova_budget_allocations.csv
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from src.utils.config import load_config
from src.optimization.allocation_constraints import (
    TOTAL_WP_BUDGET_LKR,
    ELIGIBLE_PROVINCE,
    MIN_SPEND_PER_OUTLET_LKR,
    MAX_SPEND_PER_OUTLET_LKR,
    MIN_CONFIDENCE_SCORE,
    MIN_POTENTIAL_GAP_LITERS,
    WP_DISTRIBUTORS,
    DISTRIBUTOR_MIN_ALLOCATION_LKR,
    ROI_WEIGHT,
    POTENTIAL_GAP_WEIGHT,
    SPATIAL_WEIGHT,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _normalize(series: pd.Series) -> pd.Series:
    """Min-Max normalize a Series to [0, 1]."""
    rng = series.max() - series.min()
    return (series - series.min()) / (rng + 1e-9)


def run_budget_optimizer():
    logger.info("=" * 60)
    logger.info("  Western Province LKR 5M Budget Optimizer  ")
    logger.info("=" * 60)

    config      = load_config()
    gold_path   = Path(config["data"]["gold_path"])
    output_path = Path("outputs/predictions")
    output_path.mkdir(parents=True, exist_ok=True)

    roi_file      = gold_path / "roi_table.csv"
    features_file = gold_path / "model_features.csv"
    output_file   = output_path / "quadnova_budget_allocations.csv"

    if not roi_file.exists():
        raise FileNotFoundError("roi_table.csv not found. Run roi_calculator.py first!")
    if not features_file.exists():
        raise FileNotFoundError("model_features.csv not found. Run build_features.py first!")

    df_roi      = pd.read_csv(roi_file)
    df_features = pd.read_csv(features_file)

    # ── 1. Filter Western Province outlets ───────────────────────
    logger.info(f"Filtering eligible outlets in: {ELIGIBLE_PROVINCE} Province...")
    wp_mask = df_roi["Province"].str.strip().str.lower() == ELIGIBLE_PROVINCE.lower()
    df_wp   = df_roi[wp_mask].copy()
    logger.info(f"Western Province outlets found: {len(df_wp)}")

    if len(df_wp) == 0:
        raise ValueError(f"No outlets found for Province='{ELIGIBLE_PROVINCE}'. Check Province column values.")

    # ── 2. Merge spatial features if available ───────────────────
    spatial_file = gold_path / "spatial_features.csv"
    if spatial_file.exists():
        df_spatial = pd.read_csv(spatial_file)[["Outlet_ID", "spatial_opportunity_score"]]
        df_wp = df_wp.merge(df_spatial, on="Outlet_ID", how="left")
        df_wp["spatial_opportunity_score"] = df_wp["spatial_opportunity_score"].fillna(0.0)
    else:
        df_wp["spatial_opportunity_score"] = 0.0

    # ── 3. Eligibility screening ─────────────────────────────────
    logger.info("Applying eligibility screening (confidence + potential gap thresholds)...")
    eligible_mask = (
        (df_wp["confidence_score"]  >= MIN_CONFIDENCE_SCORE) &
        (df_wp["potential_gap"]     >= MIN_POTENTIAL_GAP_LITERS)
    )
    df_eligible = df_wp[eligible_mask].copy()
    logger.info(f"Eligible outlets after screening: {len(df_eligible)}")

    if len(df_eligible) == 0:
        logger.warning("No outlets passed eligibility screening. Relaxing thresholds by 50%...")
        eligible_mask = (
            (df_wp["confidence_score"]  >= MIN_CONFIDENCE_SCORE  * 0.5) &
            (df_wp["potential_gap"]     >= MIN_POTENTIAL_GAP_LITERS * 0.5)
        )
        df_eligible = df_wp[eligible_mask].copy()
        logger.info(f"Eligible outlets after relaxed screening: {len(df_eligible)}")

    # ── 4. Compute composite allocation score ────────────────────
    logger.info("Computing composite allocation priority scores...")
    df_eligible["norm_roi"]     = _normalize(df_eligible["risk_adjusted_roi"])
    df_eligible["norm_gap"]     = _normalize(df_eligible["potential_gap"])
    df_eligible["norm_spatial"] = _normalize(df_eligible["spatial_opportunity_score"])

    df_eligible["allocation_score"] = (
        df_eligible["norm_roi"]     * ROI_WEIGHT          +
        df_eligible["norm_gap"]     * POTENTIAL_GAP_WEIGHT +
        df_eligible["norm_spatial"] * SPATIAL_WEIGHT
    )

    # Sort descending by allocation score
    df_eligible = df_eligible.sort_values("allocation_score", ascending=False).reset_index(drop=True)

    # ── 5. Continuous Proportional Allocation with Bounded Constraints ──
    logger.info("Executing continuous proportional budget allocation using iterative water-filling...")

    # Pre-extract arrays for vectorized operations
    scores = df_eligible["allocation_score"].values
    dist_ids = df_eligible["Distributor_ID"].values

    # Distributor multipliers for floor satisfaction
    dist_multipliers = {d: 1.0 for d in WP_DISTRIBUTORS}

    for iteration in range(25):
        # Pre-compute per-outlet multiplier array
        mults = np.array([dist_multipliers.get(d, 1.0) for d in dist_ids])

        # Global scaling factor search via binary search
        low, high, best_alpha = 0.0, 1e9, 0.0

        for _ in range(100):
            mid = (low + high) / 2.0
            # Vectorized tentative allocations
            vals = mid * mults * scores
            allocs = np.where(
                vals >= MIN_SPEND_PER_OUTLET_LKR,
                np.clip(vals, MIN_SPEND_PER_OUTLET_LKR, MAX_SPEND_PER_OUTLET_LKR),
                0.0,
            )
            if allocs.sum() > TOTAL_WP_BUDGET_LKR:
                high = mid
            else:
                low = mid
                best_alpha = mid

        # Final allocations for this iteration (vectorized)
        vals = best_alpha * mults * scores
        allocs = np.where(
            vals >= MIN_SPEND_PER_OUTLET_LKR,
            np.clip(vals, MIN_SPEND_PER_OUTLET_LKR, MAX_SPEND_PER_OUTLET_LKR),
            0.0,
        )
        df_eligible["temp_alloc"] = allocs

        # Check distributor floor limits
        all_satisfied = True
        for dist in WP_DISTRIBUTORS:
            dist_mask = dist_ids == dist
            dist_sum = allocs[dist_mask].sum()
            if dist_sum < DISTRIBUTOR_MIN_ALLOCATION_LKR:
                all_satisfied = False
                deficit_ratio = DISTRIBUTOR_MIN_ALLOCATION_LKR / (dist_sum + 1e-9)
                dist_multipliers[dist] *= min(1.5, max(1.05, deficit_ratio))

        if all_satisfied:
            logger.info(f"Water-filling allocation converged successfully in {iteration+1} iterations.")
            break
    df_eligible["Trade_Spend_Allocation_LKR"] = df_eligible["temp_alloc"].round(2)
    df_eligible.drop(columns=["temp_alloc"], inplace=True)
    
    # ── 6. Filter Active Outlets and Save Output ───────────────────
    alloc_df = df_eligible[df_eligible["Trade_Spend_Allocation_LKR"] > 0][["Outlet_ID", "Trade_Spend_Allocation_LKR"]].copy()
    
    # Enforce total budget cap strictly down to the cent via scale rounding if necessary
    actual_total = alloc_df["Trade_Spend_Allocation_LKR"].sum()
    if actual_total > TOTAL_WP_BUDGET_LKR:
        scale = TOTAL_WP_BUDGET_LKR / actual_total
        alloc_df["Trade_Spend_Allocation_LKR"] = (alloc_df["Trade_Spend_Allocation_LKR"] * scale).round(2)
        actual_total = alloc_df["Trade_Spend_Allocation_LKR"].sum()
        
    alloc_df.to_csv(output_file, index=False)

    # ── 6. Summary Report ─────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"  Outlets Allocated  : {len(alloc_df)}")
    logger.info(f"  Total Budget Used  : LKR {actual_total:>12,.2f}")
    logger.info(f"  Budget Cap         : LKR {TOTAL_WP_BUDGET_LKR:>12,.0f}")
    logger.info(f"  Utilisation        : {actual_total / TOTAL_WP_BUDGET_LKR * 100:.1f}%")
    logger.info(f"  Avg Spend/Outlet   : LKR {alloc_df['Trade_Spend_Allocation_LKR'].mean():>10,.2f}")
    logger.info(f"  Max Spend/Outlet   : LKR {alloc_df['Trade_Spend_Allocation_LKR'].max():>10,.2f}")

    # Distributor breakdown
    merged_dist = alloc_df.merge(
        df_wp[["Outlet_ID", "Distributor_ID"]], on="Outlet_ID", how="left"
    )
    dist_summary = merged_dist.groupby("Distributor_ID")["Trade_Spend_Allocation_LKR"].agg(
        ["sum", "count"]
    ).rename(columns={"sum": "Total_LKR", "count": "Outlets"})
    logger.info(f"\n  Distributor Breakdown:\n{dist_summary.to_string()}")
    logger.info("=" * 60)
    logger.info(f"  Budget allocations saved to: {output_file}")


if __name__ == "__main__":
    run_budget_optimizer()
