"""
Post-prediction mathematical calibration.

Loads the trained Tobit model, predicts latent demand, and applies distributor 
seasonality, observed sales floors, and dynamic ceilings to output realistic 
maximum monthly potentials.
"""

import pandas as pd
import numpy as np
import joblib
import logging
from pathlib import Path
from src.utils.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calibrate_predictions():
    logger.info("Starting Prediction Calibration Stage...")
    config = load_config()
    
    gold_path = Path(config["data"]["gold_path"])
    model_path = Path("models")
    
    features_file = gold_path / "model_features.csv"
    model_file = model_path / "potential_model.pkl"
    cols_file = model_path / "feature_columns.pkl"
    output_file = gold_path / "calibrated_potential.csv"
    
    if not features_file.exists() or not model_file.exists() or not cols_file.exists():
        logger.error("Model files or model_features.csv missing. Cannot calibrate predictions.")
        raise FileNotFoundError("Ensure model is trained and gold features exist first!")
        
    # Load model and columns
    model = joblib.load(model_file)
    feature_cols = joblib.load(cols_file)
    
    # Load features
    df = pd.read_csv(features_file)
    logger.info(f"Loaded {len(df)} records for prediction.")
    
    # Extract prediction matrix
    X = df[feature_cols].values
    
    # 1. Generate Uncapped Latent Predictions using the 90th percentile quantile
    logger.info("Predicting uncapped latent demand from Tobit regression...")
    predictions = model.predict(X, method='quantile')
    
    # 2. Apply January Distributor Seasonality Adjustment
    logger.info("Applying distributor January seasonality scaling...")
    calibrated = predictions * df['distributor_january_seasonality']
    
    # 3. Apply Observed Sales Floor (Cannot predict less than what has been historically achieved)
    logger.info("Applying observed sales floor constraints...")
    calibrated = np.maximum(calibrated, df['historical_max_sales'])
    calibrated = np.maximum(calibrated, df['last_month_sales'])
    
    # 4. Apply Dynamic Potential Ceiling
    # The ceiling expands for outlets with strong growth and active geographic foot traffic
    logger.info("Applying dynamic potential ceilings...")
    dynamic_multiplier = 1.05 + np.clip(df['poi_score'] / 50.0, 0, 0.15) + np.clip(df['growth_rate'], 0, 0.1)
    potential_ceiling = df['historical_max_sales'] * dynamic_multiplier
    
    calibrated = np.minimum(calibrated, potential_ceiling)
    
    # Final check to prevent any absolute negative values
    calibrated = np.maximum(calibrated, 0.0)
    
    # Round predictions to 2 decimal places
    calibrated = np.round(calibrated, 2)
    
    # Compile output calibrated dataset
    df_calibrated = pd.DataFrame({
        'Outlet_ID': df['Outlet_ID'],
        'Maximum_Monthly_Liters': calibrated
    })
    
    # Save output to Gold
    df_calibrated.to_csv(output_file, index=False)
    logger.info(f"Prediction calibration completed successfully! Saved to: {output_file}")
    logger.info(f"Calibrated potential stats - Mean: {df_calibrated['Maximum_Monthly_Liters'].mean():.2f}, Max: {df_calibrated['Maximum_Monthly_Liters'].max():.2f}")

if __name__ == "__main__":
    calibrate_predictions()
