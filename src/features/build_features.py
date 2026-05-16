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

def load_master_gold_data(gold_path: Path) -> pd.DataFrame:
    """Loads the merged master dataset using memory-efficient types."""
    path = gold_path / "final_dataset.csv"
    if not path.exists():
        raise FileNotFoundError(f"Gold master dataset not found at {path}. Run transform.py first.")
    
    # Only load columns we need to save RAM
    cols = ['Outlet_ID', 'Year', 'Month', 'Volume_Liters', 'Total_Bill_Value', 'Distributor_ID', 'Latitude', 'Longitude']
    
    # Use smaller data types to save 50% RAM
    dtypes = {
        'Year': 'int16',
        'Month': 'int8',
        'Volume_Liters': 'float32',
        'Total_Bill_Value': 'float32',
        'Distributor_ID': 'category'
    }
    
    df = pd.read_csv(path, usecols=cols, dtype=dtypes)
    logger.info(f"Loaded Gold master dataset ({len(df)} rows) using optimized types.")
    return df

def build_features():
    """Main feature engineering pipeline."""
    config = load_config()
    silver_path = Path(config["data"]["silver_path"])
    gold_path = Path(config["data"]["gold_path"])
    external_path = Path(config["data"].get("external_path", "data/external"))
    
    gold_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Data from Gold (Memory Efficient)
    try:
        tx = load_master_gold_data(gold_path) # Load directly into 'tx'
    except FileNotFoundError as e:
        logger.error(e)
        return
    
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
        'avg_order_frequency',
        'Distributor_ID'
    ]
    
    # Calculate Temporal Stability Score (1 - CV, capped at 1)
    # High stability (near 1) = Consistent demand. Low stability = Volatile.
    cv = outlet_features['sales_std'] / (outlet_features['monthly_avg_sales'] + 1e-6)
    outlet_features['temporal_stability_score'] = np.clip(1 - (cv / 2), 0, 1)
    
    outlet_features = outlet_features.reset_index()
    
    # Growth Rate (Simple: last month vs average)
    outlet_features['growth_rate'] = (outlet_features['last_month_sales'] / outlet_features['monthly_avg_sales']) - 1
    
    # Inactive Days (Recency)
    # Ensure Date is datetime for calculation
    tx['Date'] = pd.to_datetime(tx['Date'])
    max_date = tx['Date'].max()
    
    recency = tx.groupby('Outlet_ID')['Date'].max().reset_index()
    recency.columns = ['Outlet_ID', 'Last_Date']
    recency['inactive_days'] = (max_date - recency['Last_Date']).dt.days
    
    outlet_features = outlet_features.merge(recency[['Outlet_ID', 'inactive_days']], on='Outlet_ID', how='left')

    # IMPORTANT: Wipe the massive transaction data from RAM to prevent crashing!
    del tx
    import gc
    gc.collect()
    logger.info("Transaction memory released.")

    # 3. Metadata (Already present in merged Gold dataset)
    # No extra merge needed

    # 4. Seasonality Score (Already merged in Gold, but ensuring Month 1)
    if 'Seasonality_Index' not in outlet_features.columns:
        logger.warning("Seasonality_Index missing from gold dataset.")
        outlet_features['Seasonality_Index'] = 1.0

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
        
        # 5b. Competition Density (The "Winning" Causal Signal)
        logger.info("Calculating competitive pressure (Outlet Density)...")
        # Optimization: Use the 20k Silver Coordinates file directly to save memory!
        coord_path = Path("data/silver/outlet_coordinates.parquet")
        if coord_path.exists():
            coords_df = pd.read_parquet(coord_path).dropna(subset=['Latitude', 'Longitude'])
            from scipy.spatial import cKDTree
            tree = cKDTree(coords_df[['Latitude', 'Longitude']].values)
            density = tree.query_ball_point(coords_df[['Latitude', 'Longitude']].values, r=0.009)
            
            density_map = pd.DataFrame({
                'Outlet_ID': coords_df['Outlet_ID'],
                'outlet_density': [len(d) - 1 for d in density]
            })
            
            # Merge density into poi_data to calculate saturation
            poi_data = poi_data.merge(density_map, on='Outlet_ID', how='left')
            poi_data['market_saturation_index'] = poi_data['poi_score'] / (1 + poi_data['outlet_density'].fillna(0))
        else:
            logger.warning("Silver coordinates missing. Skipping density features.")
        
        if 'Outlet_ID' in poi_data.columns:
            cols_to_merge = ['Outlet_ID', 'poi_score', 'outlet_density', 'market_saturation_index']
            outlet_features = outlet_features.merge(
                poi_data[[c for c in cols_to_merge if c in poi_data.columns]], 
                on='Outlet_ID', 
                how='left'
            )
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
    # Fill NaNs only in numeric columns to avoid issues with categorical columns (like Distributor_ID)
    numeric_cols = outlet_features.select_dtypes(include=[np.number]).columns
    outlet_features[numeric_cols] = outlet_features[numeric_cols].fillna(0)
    
    # Save to Gold
    output_file = gold_path / "model_features.csv"
    outlet_features.to_csv(output_file, index=False)
    logger.info(f"Successfully saved {len(outlet_features)} features to {output_file}")

if __name__ == "__main__":
    build_features()
