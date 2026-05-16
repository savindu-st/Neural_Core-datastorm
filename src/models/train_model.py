"""
Trains the latent potential model using the engineered features.

This script loads the Gold-layer features, defines the censoring indicators,
and trains a Censored Regression model to estimate Maximum Monthly Liters.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import logging
from src.utils.config import load_config
from src.models.censored_regression import TobitModel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def train_potential_model():
    """Main training pipeline."""
    config = load_config()
    gold_path = Path(config["data"]["gold_path"])
    model_path = Path("models")
    model_path.mkdir(exist_ok=True)
    
    # 1. Load Features
    feature_file = gold_path / "model_features.csv"
    if not feature_file.exists():
        logger.error(f"Features file not found at {feature_file}")
        return
    
    df = pd.read_csv(feature_file)
    logger.info(f"Loaded {len(df)} records for training.")

    # 2. Define Features and Target
    # Target is the last observed monthly sales (Volume_Liters)
    # But wait, in build_features we aggregated to last_month_sales.
    y = df['last_month_sales'].values
    
    # Censoring Indicator: is_censored (1 if sales are likely capped, 0 otherwise)
    censored_mask = df['is_censored'].values == 1
    
    # Feature columns for regression
    feature_cols = [
        'monthly_avg_sales', 
        'historical_max_sales', 
        'sales_std', 
        'growth_rate', 
        'inactive_days',
        'avg_order_frequency',
        'Seasonality_Index'
    ]
    
    # Add POI and Causal features if available
    if 'poi_score' in df.columns:
        feature_cols.append('poi_score')
    if 'outlet_density' in df.columns:
        feature_cols.append('outlet_density')
    if 'market_saturation_index' in df.columns:
        feature_cols.append('market_saturation_index')
    if 'temporal_stability_score' in df.columns:
        feature_cols.append('temporal_stability_score')
        
    X = df[feature_cols].values
    
    # 3. Fit Tobit Model
    logger.info("Fitting Tobit Regression model (MLE)...")
    model = TobitModel()
    model.fit(X, y, censored_mask)
    
    logger.info(f"Model fitted. Estimated Sigma: {model.sigma:.4f}")
    
    # 4. Save Model and Explainability Data
    joblib.dump(model, model_path / "potential_model.pkl")
    joblib.dump(feature_cols, model_path / "feature_columns.pkl")
    
    # Generate Feature Importance for the Report (Explainability Layer)
    if hasattr(model, 'beta') and model.beta is not None:
        # Exclude intercept (beta[0])
        importance = pd.DataFrame({
            'Feature': feature_cols,
            'Coefficient': model.beta[1:]
        })
        importance['Importance_Abs'] = importance['Coefficient'].abs()
        importance = importance.sort_values('Importance_Abs', ascending=False)
        importance_file = model_path / "feature_importance.csv"
        importance.to_csv(importance_file, index=False)
        logger.info(f"Feature importance saved for explainability: {importance_file}")
    
    logger.info(f"Model and feature list saved to {model_path}")

if __name__ == "__main__":
    train_potential_model()
