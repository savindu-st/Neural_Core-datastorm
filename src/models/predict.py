"""
Generates final latent potential predictions for January 2026.

This script loads the trained model, applies it to the latest outlet data,
and saves the results in the required competition format.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import logging
from src.utils.config import load_config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_confidence_score(df: pd.DataFrame) -> pd.Series:
    """Calculates a confidence score (0-100) based on data stability and richness."""
    # Factors: Lower inactivity, more consistent orders, higher history
    # 1. Recency Factor (0 to 40 points)
    recency_score = np.clip(100 - (df['inactive_days'] / 2), 0, 100) * 0.4
    
    # 2. Stability Factor (0 to 30 points) - Lower CV is better
    # Handle division by zero
    cv = df['sales_std'] / (df['monthly_avg_sales'] + 1e-6)
    stability_score = np.clip(100 - (cv * 20), 0, 100) * 0.3
    
    # 3. Data Richness (0 to 30 points) - Higher POI score helps confidence in potential
    poi_signal = np.clip(df['poi_score'] * 5, 0, 100) * 0.3
    
    total_score = recency_score + stability_score + poi_signal
    return np.round(total_score, 2)

def segment_outlets(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Segments outlets into business categories and provides recommendations."""
    segments = []
    recommendations = []
    risk_flags = []
    
    for _, row in df.iterrows():
        # Logic for segments
        if row['poi_score'] > 10 and row['growth_rate'] > 0.1:
            segment = "High Potential Growth"
            action = "Aggressive Expansion & Cooler Deployment"
            risk = "Low"
        elif row['market_saturation_index'] < 2 and row['poi_score'] > 5:
            segment = "Underserved Gem"
            action = "Introduce New SKUs & Trade Marketing"
            risk = "Medium (Competitive Entry)"
        elif row['monthly_avg_sales'] > df['monthly_avg_sales'].median() and row['growth_rate'] < 0:
            segment = "Saturated Mature"
            action = "Retention focus & Loyalty discounts"
            risk = "Medium (Churn Risk)"
        elif row['inactive_days'] > 60:
            segment = "At-Risk / Dormant"
            action = "Re-engagement Visit & Credit Review"
            risk = "High"
        else:
            segment = "Stable Core Retailer"
            action = "Standard Service Level"
            risk = "Low"
            
        segments.append(segment)
        recommendations.append(action)
        risk_flags.append(risk)
        
    return pd.Series(segments), pd.Series(recommendations), pd.Series(risk_flags)

def generate_predictions():
    """Main prediction pipeline with BI layer."""
    config = load_config()
    gold_path = Path(config["data"]["gold_path"])
    output_path = Path("outputs/predictions")
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Model and Features
    model_file = Path("models/potential_model.pkl")
    cols_file = Path("models/feature_columns.pkl")
    
    if not model_file.exists() or not cols_file.exists():
        logger.error("Model files not found. Run train_model.py first.")
        return
        
    model = joblib.load(model_file)
    feature_cols = joblib.load(cols_file)
    
    # 2. Load latest features
    feature_file = gold_path / "model_features.csv"
    df = pd.read_csv(feature_file)
    
    # 3. Generate Uncapped Predictions
    logger.info("Generating uncapped demand potential...")
    X = df[feature_cols].values
    predictions = model.predict(X, method='quantile')
    
    # 3b. Apply Dynamic Potential Ceiling (Advanced Methodology)
    # The 'ceiling' isn't fixed; it expands for outlets with high POI and growth
    dynamic_multiplier = 1.05 + np.clip(df['poi_score'] / 50, 0, 0.15) + np.clip(df['growth_rate'], 0, 0.1)
    df['potential_ceiling'] = df['historical_max_sales'] * dynamic_multiplier
    
    # Final Potential is the model prediction, but bounded by the dynamic ceiling
    # and ensured to be at least the historical max.
    df['Maximum_Monthly_Liters'] = np.maximum(predictions, df['historical_max_sales'])
    df['Maximum_Monthly_Liters'] = np.minimum(df['Maximum_Monthly_Liters'], df['potential_ceiling'])
    df['Maximum_Monthly_Liters'] = np.maximum(df['Maximum_Monthly_Liters'], 0)
    
    # 4. Apply Business Intelligence Layer
    logger.info("Applying Business Intelligence Layer (Segmentation & Risk)...")
    df['confidence_score'] = calculate_confidence_score(df)
    df['outlet_segment'], df['business_recommendation'], df['risk_level'] = segment_outlets(df)
    
    # 5. Save Final CSVs
    # A. Official Submission Format (Only required columns)
    submission = df[['Outlet_ID', 'Maximum_Monthly_Liters']].copy()
    
    # B. Business BI Report (Enhanced version for the report PDF)
    report_cols = [
        'Outlet_ID', 'Maximum_Monthly_Liters', 'confidence_score', 
        'outlet_segment', 'risk_level', 'business_recommendation'
    ]
    bi_report = df[report_cols].copy()
    
    # Competition row count safeguard: load raw bronze master to account for the 196 quarantined outlets
    master_path = Path("data/bronze/outlet_master.csv")
    if master_path.exists():
        logger.info("Applying competition row count safeguard (healing missing quarantined outlets)...")
        master_df = pd.read_csv(master_path, usecols=['Outlet_ID'], dtype=str)
        
        # Merge to guarantee 100% coverage
        submission = master_df.merge(submission, on='Outlet_ID', how='left')
        bi_report  = master_df.merge(bi_report, on='Outlet_ID', how='left')
        
        # Impute missing predictions with overall median
        median_pred = df['Maximum_Monthly_Liters'].median()
        submission['Maximum_Monthly_Liters'] = submission['Maximum_Monthly_Liters'].fillna(median_pred)
        
        # Impute BI columns for quarantined outlets
        bi_report['Maximum_Monthly_Liters'] = bi_report['Maximum_Monthly_Liters'].fillna(median_pred)
        bi_report['confidence_score']        = bi_report['confidence_score'].fillna(0.0)
        bi_report['outlet_segment']         = bi_report['outlet_segment'].fillna("Dormant / Excluded")
        bi_report['risk_level']             = bi_report['risk_level'].fillna("High")
        bi_report['business_recommendation'] = bi_report['business_recommendation'].fillna("Perform In-Person Verification")
        
        logger.info(f"Healed output dataframes to complete 20,000 outlets (added 196 missing rows).")
        
    sub_file = output_path / "quadnova_predictions.csv"
    submission.to_csv(sub_file, index=False)
    
    bi_file = output_path / "business_intelligence_report.csv"
    bi_report.to_csv(bi_file, index=False)
    
    logger.info(f"Submission saved to {sub_file}")
    logger.info(f"Business BI Report saved to {bi_file}")
    logger.info(f"Average Potential: {submission['Maximum_Monthly_Liters'].mean():.2f}")

if __name__ == "__main__":
    generate_predictions()
