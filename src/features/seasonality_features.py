"""
Seasonality-based feature engineering.

Processes seasonality datasets and holiday calendars to engineer January 2026 
seasonality indexes and holiday counts at the outlet level.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from src.utils.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_seasonality_features():
    logger.info("Starting Seasonality Feature Engineering...")
    config = load_config()
    
    silver_path = Path(config["data"]["silver_path"])
    gold_path = Path(config["data"]["gold_path"])
    gold_path.mkdir(parents=True, exist_ok=True)
    
    master_file = silver_path / "clean_outlet_master.csv"
    season_file = silver_path / "distributor_seasonality_details.parquet"
    holiday_file = silver_path / "holiday_list.parquet"
    output_file = gold_path / "seasonality_features.csv"
    
    if not master_file.exists():
        raise FileNotFoundError(f"Missing outlet master file: {master_file}")
        
    # Read master data
    df_outlets = pd.read_csv(master_file, dtype={"Outlet_ID": "str"})
    
    # Dynamically resolve Distributor_ID from transaction data if not in master
    tx_file = silver_path / "clean_transactions.csv"
    if tx_file.exists():
        logger.info("Resolving Distributor_ID mappings from clean transactions...")
        df_tx = pd.read_csv(tx_file, usecols=["Outlet_ID", "Distributor_ID"], dtype=str)
        dist_map = df_tx.drop_duplicates(subset=["Outlet_ID"]).set_index("Outlet_ID")["Distributor_ID"].to_dict()
        df_outlets["Distributor_ID"] = df_outlets["Outlet_ID"].map(dist_map)
    else:
        df_outlets["Distributor_ID"] = "Unknown"
        
    df_outlets["Distributor_ID"] = df_outlets["Distributor_ID"].fillna("Unknown")
    
    # Map Province from Distributor_ID
    def get_province(dist_id):
        dist_str = str(dist_id)
        if '_W_' in dist_str: return 'Western'
        if '_C_' in dist_str: return 'Central'
        if '_NW_' in dist_str: return 'North-Western'
        if '_S_' in dist_str: return 'Southern'
        return 'Other'
        
    df_outlets['Province'] = df_outlets['Distributor_ID'].apply(get_province)
    
    # 1. Process Distributor Seasonality
    logger.info("Processing distributor seasonality indexes...")
    if season_file.exists():
        df_season = pd.read_parquet(season_file)
        
        # Translate categorical string to numeric value
        season_map = {
            'Favorable': 1.2,
            'Moderate': 1.0,
            'Un-Favorable': 0.8
        }
        df_season['Seasonality_Index_Num'] = df_season['Seasonality_Index'].map(season_map).fillna(1.0)
        
        # We need the January (Month = 1) seasonality index
        # Let's filter for Month = 1
        df_jan_season = df_season[df_season['Month'] == 1].copy()
        
        if not df_jan_season.empty:
            # If multiple years are present, average the January index over years to get a robust prediction
            dist_jan_map = df_jan_season.groupby('Distributor_ID')['Seasonality_Index_Num'].mean().to_dict()
        else:
            # Fallback if no January index (unexpected)
            dist_jan_map = {}
    else:
        logger.warning(f"Distributor seasonality file not found at: {season_file}. Defaulting to 1.0.")
        dist_jan_map = {}
        
    # Map the January seasonality index to each outlet based on its Distributor_ID
    df_outlets['distributor_january_seasonality'] = df_outlets['Distributor_ID'].map(dist_jan_map).fillna(1.0)
    
    # 2. Process January 2026 Holidays
    logger.info("Processing holiday calendar counts...")
    if holiday_file.exists():
        df_holidays = pd.read_parquet(holiday_file)
        
        # Count holidays in January 2026
        jan_2026_holidays = df_holidays[(df_holidays['Year'] == 2026) & (df_holidays['Month'] == 1)]
        holiday_count = len(jan_2026_holidays)
        
        # Fallback: if no 2026 holidays are loaded, calculate the average of January holidays in historical years
        if holiday_count == 0:
            hist_jan_holidays = df_holidays[df_holidays['Month'] == 1]
            if not hist_jan_holidays.empty:
                holiday_count = hist_jan_holidays.groupby('Year').size().mean()
            else:
                holiday_count = 0
    else:
        logger.warning(f"Holidays calendar not found at: {holiday_file}. Defaulting to 0.")
        holiday_count = 0
        
    df_outlets['holiday_count_jan2026'] = float(holiday_count)
    
    # 3. Process Province Seasonality Index
    # Average distributor seasonality index for January within each Province
    logger.info("Calculating province-level seasonality averages...")
    prov_season = df_outlets.groupby('Province')['distributor_january_seasonality'].transform('mean')
    df_outlets['province_seasonality_index'] = prov_season.fillna(1.0)
    
    # Compile features DataFrame
    seasonality_features = df_outlets[[
        'Outlet_ID',
        'distributor_january_seasonality',
        'holiday_count_jan2026',
        'province_seasonality_index'
    ]].copy()
    
    # Save output to Gold
    seasonality_features.to_csv(output_file, index=False)
    logger.info(f"Seasonality features successfully written to: {output_file} ({len(seasonality_features)} rows)")

if __name__ == "__main__":
    calculate_seasonality_features()
