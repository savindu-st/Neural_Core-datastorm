"""
Trade spend ROI calculation engine.

Calculates potential volume lifts, expected incremental sales gains from promotional 
spends (using outlet-size scaling efficiencies), baseline ROIs, and risk-adjusted 
ROI scores to prepare outlets for budget optimization.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from src.utils.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_trade_spend_roi():
    logger.info("Starting Spend ROI Calculation Stage...")
    config = load_config()
    
    gold_path = Path(config["data"]["gold_path"])
    
    features_file = gold_path / "model_features.csv"
    potential_file = gold_path / "calibrated_potential.csv"
    output_file = gold_path / "roi_table.csv"
    
    if not features_file.exists() or not potential_file.exists():
        logger.error("Required model features or predictions missing. Cannot calculate ROI.")
        raise FileNotFoundError("Ensure predictions are calibrated and gold features exist first!")
        
    df_features = pd.read_csv(features_file)
    df_potential = pd.read_csv(potential_file)
    
    # Merge datasets
    df = df_features.merge(df_potential, on="Outlet_ID", how="inner")
    
    # 1. Potential Gap
    logger.info("Calculating beverage sales potential gaps...")
    df['potential_gap'] = np.maximum(df['Maximum_Monthly_Liters'] - df['monthly_avg_sales'], 0.0)
    
    # 2. Expected Incremental Liters
    # We model trade spend efficiency based on Outlet_Size.
    # Large outlets have superior cooler capacities and storage, so promotional spend 
    # yields higher gap capture efficiency (e.g. 20%). Medium capture 15%, Small capture 10%.
    logger.info("Modeling promotional conversion efficiencies based on outlet profiles...")
    
    capture_efficiency = []
    for _, row in df.iterrows():
        size = str(row.get('Outlet_Size', 'Unknown')).strip().lower()
        if 'large' in size:
            eff = 0.20
        elif 'medium' in size:
            eff = 0.15
        else: # Small / Unknown
            eff = 0.10
        capture_efficiency.append(eff)
        
    df['capture_efficiency'] = capture_efficiency
    
    # Expected incremental liters captured from standard LKR 10,000 baseline promotional spend
    df['expected_incremental_liters'] = df['potential_gap'] * df['capture_efficiency']
    
    # 3. Expected ROI per LKR (Incremental Liters per LKR spent on LKR 10,000 baseline)
    logger.info("Calculating incremental ROI per LKR spent...")
    baseline_spend = 10000.0
    df['expected_roi_per_lkr'] = df['expected_incremental_liters'] / baseline_spend
    
    # 4. Risk-Adjusted ROI (Adjusted by prediction confidence score)
    # Ensure confidence score exists, calculate if missing
    if 'confidence_score' not in df.columns:
        recency_score = np.clip(100 - (df['inactive_days'] / 2), 0, 100) * 0.4
        cv = df['sales_std'] / (df['monthly_avg_sales'] + 1e-6)
        stability_score = np.clip(100 - (cv * 20), 0, 100) * 0.3
        poi_signal = np.clip(df['poi_score'] * 5, 0, 100) * 0.3
        df['confidence_score'] = recency_score + stability_score + poi_signal
        
    logger.info("Applying data confidence risk adjustments...")
    df['risk_adjusted_roi'] = df['expected_roi_per_lkr'] * (df['confidence_score'] / 100.0)
    
    # Compile output ROI table
    roi_table = df[[
        'Outlet_ID',
        'Province',
        'Distributor_ID',
        'monthly_avg_sales',
        'Maximum_Monthly_Liters',
        'potential_gap',
        'confidence_score',
        'expected_incremental_liters',
        'expected_roi_per_lkr',
        'risk_adjusted_roi'
    ]].copy()
    
    # Save output to Gold
    roi_table.to_csv(output_file, index=False)
    logger.info(f"Spend ROI calculations completed successfully! Saved to: {output_file} ({len(roi_table)} outlets)")
    logger.info(f"Average Potential Gap: {roi_table['potential_gap'].mean():.2f} Liters, Average Risk-Adjusted ROI: {roi_table['risk_adjusted_roi'].mean():.6f}")

if __name__ == "__main__":
    calculate_trade_spend_roi()
