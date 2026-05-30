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

    # ── 5. Distributor fairness floors ───────────────────────────
    # Reserve floor budgets for each WP distributor, then distribute the remainder
    logger.info("Reserving distributor fairness floor allocations...")
    dist_floor_total = 0.0
    dist_floor_map   = {}  # distributor -> guaranteed floor spend

    for dist in WP_DISTRIBUTORS:
        dist_outlets = df_eligible[df_eligible["Distributor_ID"] == dist]
        if len(dist_outlets) > 0:
            dist_floor_map[dist]  = DISTRIBUTOR_MIN_ALLOCATION_LKR
            dist_floor_total     += DISTRIBUTOR_MIN_ALLOCATION_LKR

    remaining_budget = TOTAL_WP_BUDGET_LKR - dist_floor_total
    logger.info(f"Total floor reserved: LKR {dist_floor_total:,.0f} | Remaining pool: LKR {remaining_budget:,.0f}")

    # ── 6. Greedy proportional allocation ────────────────────────
    logger.info("Running greedy proportional allocation...")

    allocations    = {}  # Outlet_ID -> LKR spend
    dist_spent     = {d: 0.0 for d in WP_DISTRIBUTORS}
    budget_used    = 0.0

    # Phase A: Guarantee distributor floors by allocating to their top-scored outlets
    for dist in WP_DISTRIBUTORS:
        if dist not in dist_floor_map:
            continue
        floor     = dist_floor_map[dist]
        dist_outs = df_eligible[df_eligible["Distributor_ID"] == dist].copy()
        dist_outs = dist_outs.sort_values("allocation_score", ascending=False)
        floor_left = floor

        for _, row in dist_outs.iterrows():
            if floor_left <= 0:
                break
            oid  = row["Outlet_ID"]
            alloc = min(MAX_SPEND_PER_OUTLET_LKR, floor_left, MIN_SPEND_PER_OUTLET_LKR * 4)
            alloc = max(alloc, MIN_SPEND_PER_OUTLET_LKR)
            if oid not in allocations:
                allocations[oid]     = alloc
                dist_spent[dist]    += alloc
                budget_used         += alloc
                floor_left          -= alloc

    # Phase B: Distribute remaining budget to all eligible outlets proportionally
    remaining_budget = TOTAL_WP_BUDGET_LKR - budget_used
    total_score      = df_eligible["allocation_score"].sum()

    for _, row in df_eligible.iterrows():
        oid = row["Outlet_ID"]
        if remaining_budget <= MIN_SPEND_PER_OUTLET_LKR:
            break

        # Proportional allocation from remaining pool
        prop_alloc = (row["allocation_score"] / (total_score + 1e-9)) * remaining_budget

        # Apply business limits
        alloc = np.clip(prop_alloc, MIN_SPEND_PER_OUTLET_LKR, MAX_SPEND_PER_OUTLET_LKR)
        alloc = min(alloc, remaining_budget)

        if oid not in allocations:
            allocations[oid]  = alloc
            budget_used      += alloc
            remaining_budget -= alloc
        else:
            # Top-up existing floor-allocated outlets proportionally
            headroom = MAX_SPEND_PER_OUTLET_LKR - allocations[oid]
            if headroom > 0:
                topup = min(alloc * 0.5, headroom, remaining_budget)
                allocations[oid]  += topup
                budget_used       += topup
                remaining_budget  -= topup

    # ── 7. Final rounding and budget guard ───────────────────────
    logger.info("Finalising allocations and enforcing total budget cap...")
    alloc_df = pd.DataFrame([
        {"Outlet_ID": oid, "Trade_Spend_Allocation_LKR": round(spend, 2)}
        for oid, spend in allocations.items()
    ])

    # Safety: scale down proportionally if budget exceeded
    actual_total = alloc_df["Trade_Spend_Allocation_LKR"].sum()
    if actual_total > TOTAL_WP_BUDGET_LKR:
        scale = TOTAL_WP_BUDGET_LKR / actual_total
        alloc_df["Trade_Spend_Allocation_LKR"] = (
            alloc_df["Trade_Spend_Allocation_LKR"] * scale
        ).round(2)
        actual_total = alloc_df["Trade_Spend_Allocation_LKR"].sum()

    # ── 8. Save output CSV ────────────────────────────────────────
    alloc_df.to_csv(output_file, index=False)

    # ── 9. Summary Report ─────────────────────────────────────────
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
