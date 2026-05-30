"""
Outlet opportunity segmentation module.

Segments outlets into descriptive operational categories (Underserved Gems, 
Mature Stars, Competitive Fighters, Low Priority, and At-Risk Outlets) based 
on potential gap, competition saturation, sales volatility, and confidence.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from src.utils.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def segment_outlets_pipeline():
    logger.info("Starting Outlet Opportunity Segmentation...")
    config = load_config()
    
    gold_path = Path(config["data"]["gold_path"])
    
    features_file = gold_path / "model_features.csv"
    potential_file = gold_path / "calibrated_potential.csv"
    output_file = gold_path / "outlet_segments.csv"
    
    if not features_file.exists() or not potential_file.exists():
        logger.warning("Required feature or prediction files not found. Skipping segmentation.")
        raise FileNotFoundError("Missing model_features.csv or calibrated_potential.csv. Ensure predictions are generated first!")
        
    df_features = pd.read_csv(features_file)
    df_potential = pd.read_csv(potential_file)
    
    # Merge datasets
    df = df_features.merge(df_potential, on="Outlet_ID", how="inner")
    
    # Ensure standard confidence score exists, calculate if missing
    if 'confidence_score' not in df.columns:
        # Lower inactive days, lower volatility, higher POI count leads to higher confidence
        recency_score = np.clip(100 - (df['inactive_days'] / 2), 0, 100) * 0.4
        cv = df['sales_std'] / (df['monthly_avg_sales'] + 1e-6)
        stability_score = np.clip(100 - (cv * 20), 0, 100) * 0.3
        poi_signal = np.clip(df['poi_score'] * 5, 0, 100) * 0.3
        df['confidence_score'] = recency_score + stability_score + poi_signal
        
    # Calculate potential gap
    df['potential_gap'] = df['Maximum_Monthly_Liters'] - df['monthly_avg_sales']
    
    # Establish dynamic median thresholds for classification
    median_gap = df['potential_gap'].median()
    median_potential = df['Maximum_Monthly_Liters'].median()
    median_sales = df['monthly_avg_sales'].median()
    
    segments = []
    recommendations = []
    
    for idx, row in df.iterrows():
        # Extracted variables for logic checks
        gap = row['potential_gap']
        potential = row['Maximum_Monthly_Liters']
        current_sales = row['monthly_avg_sales']
        msi = row['market_saturation_index']
        confidence = row['confidence_score']
        
        # Volatility check: CV (std / mean)
        cv_val = row['sales_std'] / (current_sales + 1e-6)
        
        # Segmentation Rules:
        if gap > median_gap and msi < 25.0 and confidence >= 60.0:
            # High gap, low competition, high data confidence -> Underserved Gem
            seg = "Underserved Gems"
            rec = "Deploy Coolers & Expand SKU Portfolio"
        elif potential > median_potential and current_sales > median_sales and confidence >= 60.0:
            # High potential, high current sales, high confidence -> Mature Star
            seg = "Mature Stars"
            rec = "Loyalty Discounts & Priority Service Levels"
        elif potential > median_potential and msi >= 60.0:
            # High potential but high competitive saturation -> Competitive Fighter
            seg = "Competitive Fighters"
            rec = "Defensive Trade Spend & Brand Merchandising"
        elif confidence < 40.0 or (cv_val > 1.2 and msi >= 60.0):
            # Low data confidence or high volatility under competitive pressure -> At-Risk
            seg = "At-Risk Outlets"
            rec = "In-Person Field Visit & Credit Limit Audit"
        elif gap <= 100.0:
            # Low potential gap -> Low Priority
            seg = "Low Priority"
            rec = "Maintain Standard Support Levels"
        else:
            # Stable baseline outlets
            seg = "Stable Core Retailers"
            rec = "Standard Promotional Offers"
            
        segments.append(seg)
        recommendations.append(rec)
        
    df_segments = pd.DataFrame({
        'Outlet_ID': df['Outlet_ID'],
        'potential_gap': df['potential_gap'],
        'confidence_score': df['confidence_score'],
        'outlet_segment': segments,
        'business_recommendation': recommendations
    })
    
    # Save output to Gold
    df_segments.to_csv(output_file, index=False)
    logger.info(f"Outlet segmentation completed successfully! Saved to: {output_file}")
    logger.info(f"Segment Distribution:\n{df_segments['outlet_segment'].value_counts()}")

if __name__ == "__main__":
    segment_outlets_pipeline()
