"""
Enriches Silver-layer data with feature engineering for latent demand modeling.

This script merges cleaned datasets from the Silver layer, calculates outlet-level
behavioral features, joins external POI signals, and produces a Gold-layer 
model-ready dataset.

Usage::

    python -m src.features.build_features
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from src.utils.config import load_config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_silver_data(silver_path: Path) -> dict[str, pd.DataFrame]:
    """Loads all cleaned parquet files from the Silver layer."""
    data = {}
    files = {
        "transactions": "transactions_history.parquet",
        "outlets": "outlet_master.parquet",
        "coordinates": "outlet_coordinates.parquet",
        "seasonality": "distributor_seasonality_details.parquet",
        "holidays": "holiday_list.parquet"
    }
    
    for key, filename in files.items():
        path = silver_path / filename
        if path.exists():
            data[key] = pd.read_parquet(path)
            logger.info(f"Loaded {filename} ({len(data[key])} rows)")
        else:
            logger.warning(f"Silver file {filename} not found at {path}")
    
    return data

def build_features():
    """Main feature engineering pipeline."""
    config = load_config()
    silver_path = Path(config["data"]["silver_path"])
    gold_path = Path(config["data"]["gold_path"])
    external_path = Path(config["data"].get("external_path", "data/external"))
    
    gold_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Data
    data = load_silver_data(silver_path)
    if "transactions" not in data:
        logger.error("Transactions data missing. Cannot build features.")
        return

    tx = data["transactions"]
    outlets = data.get("outlets")
    
    # 2. Aggregated Behavioral Features (Outlet Level)
    logger.info("Calculating behavioral features...")
    
    # Synthesize Date if missing (using Year and Month)
    if 'Date' not in tx.columns and 'Year' in tx.columns and 'Month' in tx.columns:
        logger.info("Synthesizing Date from Year and Month...")
        tx['Date'] = pd.to_datetime(tx[['Year', 'Month']].assign(Day=1))

    # Group by Outlet and Year-Month to get monthly snapshots
    # We include Distributor_ID to join seasonality later
    monthly_tx = tx.groupby(['Outlet_ID', 'Year', 'Month']).agg({
        'Volume_Liters': 'sum',
        'Total_Bill_Value': 'sum',
        'Outlet_ID': 'count',
        'Distributor_ID': 'first' 
    }).rename(columns={'Outlet_ID': 'order_frequency'}).reset_index()

    # Features:
    # monthly_avg_sales, historical_max_sales, sales_std
    outlet_features = monthly_tx.groupby('Outlet_ID').agg({
        'Volume_Liters': ['mean', 'max', 'std', 'last'],
        'order_frequency': 'mean',
        'Distributor_ID': 'first'
    })
    
    outlet_features.columns = [
        'monthly_avg_sales', 
        'historical_max_sales', 
        'sales_std', 
        'last_month_sales',
        'avg_order_frequency'
    ]
    outlet_features = outlet_features.reset_index()
    
    # Growth Rate (Simple: last month vs average)
    outlet_features['growth_rate'] = (outlet_features['last_month_sales'] / outlet_features['monthly_avg_sales']) - 1
    
    # Inactive Days (Recency)
    # Assuming the "current" date is the max date in the transactions
    max_date = pd.to_datetime(tx['Date']).max()
    recency = tx.groupby('Outlet_ID')['Date'].max().reset_index()
    recency['inactive_days'] = (max_date - pd.to_datetime(recency['Date'])).dt.days
    
    outlet_features = outlet_features.merge(recency[['Outlet_ID', 'inactive_days']], on='Outlet_ID', how='left')

    # 3. Merge Metadata (Outlet Type, Size, Province, Coordinates)
    if outlets is not None:
        logger.info("Merging outlet metadata...")
        outlet_features = outlet_features.merge(outlets, on='Outlet_ID', how='left')

    if "coordinates" in data:
        logger.info("Merging coordinates...")
        outlet_features = outlet_features.merge(data["coordinates"], on='Outlet_ID', how='left')

    # 4. Seasonality Score
    if "seasonality" in data:
        logger.info("Merging seasonality scores...")
        # Seasonality is usually by Distributor or Province and Month
        # Assuming we need Jan 2026 seasonality (Month 1)
        jan_seasonality = data["seasonality"][data["seasonality"]["Month"] == 1].copy()
        # Merge by Distributor_ID if available in outlets
        if 'Distributor_ID' in outlet_features.columns and 'Distributor_ID' in jan_seasonality.columns:
            outlet_features = outlet_features.merge(
                jan_seasonality[['Distributor_ID', 'Seasonality_Index']], 
                on='Distributor_ID', 
                how='left'
            )

    # 5. POI Score (External Data from Ryan's scraper)
    poi_path = gold_path / "poi_data.csv"
    if poi_path.exists():
        logger.info("Merging POI scores...")
        poi_data = pd.read_csv(poi_path)
        
        # Calculate a weighted POI score if counts exist
        count_cols = [c for c in poi_data.columns if 'count' in c]
        if count_cols:
            # Simple weighted score: schools and hospitals might be more important
            weights = {
                'school_count': 2.0,
                'hospital_count': 2.0,
                'bus_stop_count': 1.5,
                'restaurant_count': 1.0,
                'fuel_count': 1.0,
                'tourism_count': 1.5
            }
            poi_data['poi_score'] = sum(poi_data[c] * weights.get(c, 1.0) for c in count_cols)
        
        if 'Outlet_ID' in poi_data.columns:
            outlet_features = outlet_features.merge(poi_data[['Outlet_ID', 'poi_score']], on='Outlet_ID', how='left')
        else:
            logger.warning("POI data found but missing Outlet_ID column.")
    else:
        logger.info("POI data not found. Skipping POI features.")
        outlet_features['poi_score'] = 0.0 # Placeholder

    # 6. Censoring Indicator
    # A crucial part for latent demand: Is the observed max limited by supply?
    # Logic: If last month's sales is near the historical max, it might be censored.
    outlet_features['is_censored'] = (outlet_features['last_month_sales'] >= 0.95 * outlet_features['historical_max_sales']).astype(int)

    # Final Cleanup
    outlet_features = outlet_features.fillna(0)
    
    # Save to Gold
    output_file = gold_path / "model_features.csv"
    outlet_features.to_csv(output_file, index=False)
    logger.info(f"Successfully saved {len(outlet_features)} features to {output_file}")

if __name__ == "__main__":
    build_features()
