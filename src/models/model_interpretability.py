"""
Model interpretability and XAI driver extraction.

Extracts feature coefficients from the trained Tobit model, creates importance 
plots, and computes top positive and negative driver signals for each outlet.
"""

import pandas as pd
import numpy as np
import joblib
import logging
from pathlib import Path
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_interpretability_report():
    logger.info("Starting Model Interpretability Stage...")
    config = load_config()
    
    gold_path = Path(config["data"]["gold_path"])
    model_path = Path("models")
    charts_path = Path("outputs/charts")
    charts_path.mkdir(parents=True, exist_ok=True)
    
    features_file = gold_path / "model_features.csv"
    model_file = model_path / "potential_model.pkl"
    cols_file = model_path / "feature_columns.pkl"
    
    output_imp_file = model_path / "feature_importance.csv"
    output_chart_file = charts_path / "feature_importance_chart.png"
    output_driver_file = gold_path / "model_driver_table.csv"
    
    if not features_file.exists() or not model_file.exists() or not cols_file.exists():
        logger.error("Required model files or model_features.csv missing. Cannot extract drivers.")
        raise FileNotFoundError("Ensure model is trained and gold features exist first!")
        
    # Load model and columns
    model = joblib.load(model_file)
    feature_cols = joblib.load(cols_file)
    
    # Load features
    df = pd.read_csv(features_file)
    
    # 1. Feature Importance Coefficients
    logger.info("Extracting model coefficients as feature importance...")
    if hasattr(model, 'beta') and model.beta is not None:
        # model.beta[0] is the intercept; beta[1:] are feature coefficients
        coefficients = model.beta[1:]
        
        importance_df = pd.DataFrame({
            'Feature': feature_cols,
            'Coefficient': coefficients
        })
        importance_df['Importance_Abs'] = importance_df['Coefficient'].abs()
        importance_df = importance_df.sort_values('Importance_Abs', ascending=False)
        
        # Save feature importance CSV
        importance_df.to_csv(output_imp_file, index=False)
        logger.info(f"Saved feature importances to: {output_imp_file}")
        
        # Plot Feature Importance Chart
        logger.info("Generating feature importance bar chart...")
        plt.figure(figsize=(10, 6))
        
        # Sort values chronologically for horizontal bar plot
        plot_df = importance_df.sort_values('Importance_Abs', ascending=True)
        colors = ['#3b82f6' if c >= 0 else '#ef4444' for c in plot_df['Coefficient']]
        
        plt.barh(plot_df['Feature'], plot_df['Coefficient'], color=colors)
        plt.axvline(0, color='grey', linestyle='--', linewidth=0.8)
        plt.title('Tobit Model Feature Coefficients (Blue: Positive, Red: Negative)', fontsize=12, fontweight='bold')
        plt.xlabel('Coefficient Value')
        plt.ylabel('Feature Name')
        plt.tight_layout()
        plt.savefig(output_chart_file, dpi=300)
        plt.close()
        logger.info(f"Saved feature importance chart to: {output_chart_file}")
        
        # 2. Extract Top Positive and Negative Drivers for each outlet
        logger.info("Calculating individual feature contribution drivers for each outlet...")
        
        # Extract features matrix
        X = df[feature_cols].values
        
        # Compute element-wise product of feature values and coefficients
        # Shape of X: (n_samples, n_features). Coefficients shape: (n_features,)
        contributions = X * coefficients # Shape: (n_samples, n_features)
        
        top_pos_drivers = []
        top_pos_vals = []
        top_neg_drivers = []
        top_neg_vals = []
        
        for i in range(len(df)):
            row_contribs = contributions[i]
            
            # Find index of max positive and max negative contribution
            pos_idx = np.argmax(row_contribs)
            neg_idx = np.argmin(row_contribs)
            
            # Map index back to feature name
            top_pos_drivers.append(feature_cols[pos_idx])
            top_pos_vals.append(row_contribs[pos_idx])
            
            top_neg_drivers.append(feature_cols[neg_idx])
            top_neg_vals.append(row_contribs[neg_idx])
            
        # Compile driver table
        driver_df = pd.DataFrame({
            'Outlet_ID': df['Outlet_ID'],
            'top_positive_driver': top_pos_drivers,
            'positive_driver_value': top_pos_vals,
            'top_negative_driver': top_neg_drivers,
            'negative_driver_value': top_neg_vals
        })
        
        # Save output to Gold
        driver_df.to_csv(output_driver_file, index=False)
        logger.info(f"Outlet drivers calculated and saved successfully to: {output_driver_file}")
    else:
        logger.error("Tobit Model coefficients (beta) not found in the serialized model object.")

def load_config(config_path="config/params.yaml"):
    """Local config helper since model_interpretability is run as main."""
    import yaml
    project_root = Path(__file__).resolve().parents[2]
    path = project_root / config_path
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config

if __name__ == "__main__":
    generate_interpretability_report()
