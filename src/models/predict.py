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

def generate_predictions():
    """Main prediction pipeline."""
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
    
    # Predicting the 'potential' (latent mean Xb)
    # Using 'quantile' with 0.90 to estimate the upper ceiling of potential
    predictions = model.predict(X, method='quantile')
    
    # Post-processing: Potential must be at least as high as historical max
    # and cannot be negative.
    df['Maximum_Monthly_Liters'] = np.maximum(predictions, df['historical_max_sales'])
    df['Maximum_Monthly_Liters'] = np.maximum(df['Maximum_Monthly_Liters'], 0)
    
    # 4. Save Final CSV
    submission = df[['Outlet_ID', 'Maximum_Monthly_Liters']].copy()
    
    # Competition requirement: teamname_predictions.csv
    # Using 'neural_core' as placeholder team name
    out_file = output_path / "neural_core_predictions.csv"
    submission.to_csv(out_file, index=False)
    
    logger.info(f"Final predictions saved to {out_file}")
    logger.info(f"Total Outlets: {len(submission)}")
    logger.info(f"Average Potential: {submission['Maximum_Monthly_Liters'].mean():.2f}")

if __name__ == "__main__":
    generate_predictions()
