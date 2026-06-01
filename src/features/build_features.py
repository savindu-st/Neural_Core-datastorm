"""
Final feature dataset assembler.

Orchestrates all modular feature engineering stages (sales, seasonality, 
and spatial features), merges them, computes compatibility metrics, 
and generates gold model_features.csv.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import gc
from src.utils.config import load_config
from src.features.sales_features import calculate_sales_features
from src.features.seasonality_features import calculate_seasonality_features
from src.features.spatial_features import calculate_spatial_features

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
    logger.info("=== Starting Master Feature Engineering Pipeline ===")
    config = load_config()
    silver_path = Path(config["data"]["silver_path"])
    gold_path = Path(config["data"]["gold_path"])
    gold_path.mkdir(parents=True, exist_ok=True)
    
    # --- Step 1: Execute Modular Feature Creators ---
    logger.info("Running modular feature script: sales_features...")
    calculate_sales_features()
    
    logger.info("Running modular feature script: seasonality_features...")
    calculate_seasonality_features()
    
    logger.info("Running modular feature script: spatial_features...")
    try:
        calculate_spatial_features()
        spatial_success = True
    except Exception as e:
        logger.warning(f"Spatial features calculation skipped or failed: {e}")
        spatial_success = False

    # --- Step 2: Extract Recency & Compatibility Indicators from Transactions ---
    logger.info("Processing transaction history for recency, stability, and growth indicators...")
    try:
        tx = load_master_gold_data(gold_path)
    except FileNotFoundError:
        # Fallback to silver Parquet if final_dataset not yet built
        tx_parquet = silver_path / "transactions_history.parquet"
        if tx_parquet.exists():
            tx = pd.read_parquet(tx_parquet)
        else:
            raise FileNotFoundError("No transaction source dataset found to aggregate!")
            
    if 'Date' not in tx.columns and 'Year' in tx.columns and 'Month' in tx.columns:
        tx['Date'] = pd.to_datetime(tx[['Year', 'Month']].assign(Day=1))
    
    # Calculate monthly snaps and find the last month's sales
    monthly_tx = tx.groupby(['Outlet_ID', 'Year', 'Month']).agg({
        'Volume_Liters': 'sum'
    }).reset_index()
    
    last_sales = monthly_tx.groupby('Outlet_ID')['Volume_Liters'].last().reset_index()
    last_sales.columns = ['Outlet_ID', 'last_month_sales']
    
    # Calculate Inactive Days (Recency)
    tx['Date'] = pd.to_datetime(tx['Date'])
    max_date = tx['Date'].max()
    recency = tx.groupby('Outlet_ID')['Date'].max().reset_index()
    recency.columns = ['Outlet_ID', 'Last_Date']
    recency['inactive_days'] = (max_date - recency['Last_Date']).dt.days
    
    # Release massive memory
    del tx
    gc.collect()
    logger.info("Transaction detail memory released.")
    
    # --- Step 3: Load and Merge Modular Gold Features ---
    logger.info("Merging clean outlet master and modular features...")
    
    # A. Clean Master
    master_file = silver_path / "clean_outlet_master.csv"
    if not master_file.exists():
        raise FileNotFoundError(f"Missing master file: {master_file}")
    df_master = pd.read_csv(master_file, dtype={"Outlet_ID": "str"})
    
    # Resolve Distributor_ID and Province from clean transactions dynamically
    tx_file = silver_path / "clean_transactions.csv"
    if tx_file.exists():
        logger.info("Resolving Distributor_ID mappings from clean transactions...")
        df_tx = pd.read_csv(tx_file, usecols=["Outlet_ID", "Distributor_ID"], dtype=str)
        dist_map = df_tx.drop_duplicates(subset=["Outlet_ID"]).set_index("Outlet_ID")["Distributor_ID"].to_dict()
        df_master["Distributor_ID"] = df_master["Outlet_ID"].map(dist_map)
    else:
        df_master["Distributor_ID"] = "Unknown"
        
    df_master["Distributor_ID"] = df_master["Distributor_ID"].fillna("Unknown")
    
    # Map Province from Distributor_ID using config-driven mapping
    _config = load_config()
    _province_map = _config.get("province_mapping", {
        "_W_": "Western", "_C_": "Central", "_NW_": "North-Western",
        "_S_": "Southern", "_N_": "Northern", "_E_": "Eastern",
        "_NC_": "North-Central", "_Sab_": "Sabaragamuwa", "_U_": "Uva",
    })

    def get_province(dist_id: str) -> str:
        """Map a Distributor_ID to a province using config-defined token prefixes."""
        for token, province in _province_map.items():
            if token in str(dist_id):
                return province
        return "Other"

    df_master['Province'] = df_master['Distributor_ID'].apply(get_province)
    
    # B. Sales Features
    sales_file = gold_path / "sales_features.csv"
    df_sales = pd.read_csv(sales_file, dtype={"Outlet_ID": "str"})
    
    # C. Seasonality Features
    season_file = gold_path / "seasonality_features.csv"
    df_season = pd.read_csv(season_file, dtype={"Outlet_ID": "str"})
    
    # Start merging
    merged = df_master.merge(df_sales, on="Outlet_ID", how="left")
    merged = merged.merge(df_season, on="Outlet_ID", how="left")
    merged = merged.merge(last_sales, on="Outlet_ID", how="left")
    merged = merged.merge(recency[['Outlet_ID', 'inactive_days']], on="Outlet_ID", how="left")
    
    # D. Spatial Features
    spatial_file = gold_path / "spatial_features.csv"
    if spatial_success and spatial_file.exists():
        logger.info("Merging advanced POI and competitor density features...")
        df_spatial = pd.read_csv(spatial_file, dtype={"Outlet_ID": "str"})
        merged = merged.merge(df_spatial, on="Outlet_ID", how="left")
        
        # Mapping compatibility fields for existing models
        merged['poi_score'] = merged['total_poi_decay_score']
        merged['competitor_density'] = merged['competitor_decay_score']
        
        # Calculate competitive pressure (outlet density) via SciPy KD-Tree
        coord_path = Path("data/silver/outlet_coordinates.parquet")
        if coord_path.exists():
            coords_df = pd.read_parquet(coord_path).dropna(subset=['Latitude', 'Longitude'])
            from scipy.spatial import cKDTree
            tree = cKDTree(coords_df[['Latitude', 'Longitude']].values)
            # Find outlets within ~1km grid
            density = tree.query_ball_point(coords_df[['Latitude', 'Longitude']].values, r=0.009)
            density_map = pd.DataFrame({
                'Outlet_ID': coords_df['Outlet_ID'],
                'outlet_density': [len(d) - 1 for d in density]
            })
            merged = merged.merge(density_map, on='Outlet_ID', how='left')
        else:
            merged['outlet_density'] = 0.0
    else:
        logger.warning("Spatial features not found or skipped. Setting spatial columns to default 0.0.")
        merged['poi_score'] = 0.0
        merged['competitor_density'] = 0.0
        merged['market_saturation_index'] = 0.0
        merged['spatial_opportunity_score'] = 0.0
        merged['outlet_density'] = 0.0
        merged['bus_stop_decay_score'] = 0.0
        merged['school_decay_score'] = 0.0
        merged['hospital_decay_score'] = 0.0
        merged['restaurant_decay_score'] = 0.0
        merged['fuel_station_decay_score'] = 0.0
        merged['tourist_place_decay_score'] = 0.0
        merged['total_poi_decay_score'] = 0.0
        
    # --- Step 4: Construct Compatibility & Model Columns ---
    logger.info("Structuring backward-compatibility fields for train_model.py...")
    
    # Model variables mapping
    merged['monthly_avg_sales'] = merged['avg_monthly_liters']
    merged['historical_max_sales'] = merged['max_monthly_liters']
    merged['sales_std'] = merged['std_monthly_liters']
    merged['avg_order_frequency'] = merged['purchase_frequency']
    merged['Seasonality_Index'] = merged['distributor_january_seasonality']
    
    # Temporal Stability Score (1 - CV, capped at [0,1])
    merged['temporal_stability_score'] = np.clip(1 - (merged['sales_volatility'] / 2.0), 0, 1)
    
    # Growth Rate: last month vs monthly average
    merged['growth_rate'] = (merged['last_month_sales'] / (merged['monthly_avg_sales'] + 1e-6)) - 1.0
    
    # Censoring indicator
    merged['is_censored'] = (merged['last_month_sales'] >= 0.95 * merged['historical_max_sales']).astype(int)
    
    # Clean up any missing numbers in numerical fields
    numeric_cols = merged.select_dtypes(include=[np.number]).columns
    merged[numeric_cols] = merged[numeric_cols].fillna(0.0)
    
    # --- Step 5: Save Output to Gold ---
    output_file = gold_path / "model_features.csv"
    merged.to_csv(output_file, index=False)
    logger.info(f"Master feature compilation finished successfully! Saved {len(merged)} records to: {output_file}")
    logger.info("=== Master Feature Engineering Completed ===")

if __name__ == "__main__":
    build_features()
