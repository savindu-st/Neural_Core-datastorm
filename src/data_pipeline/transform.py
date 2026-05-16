"""
Silver → Gold data transformation and merging.

This script merges cleaned datasets from the Silver layer into a single,
consistent master dataset for modeling and feature engineering.

Usage::

    python -m src.data_pipeline.transform
"""

import pandas as pd
import logging
from pathlib import Path
from src.utils.config import load_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

def merge_silver_to_gold():
    """Main transformation logic to merge Silver datasets into Gold."""
    config = load_config()
    silver_path = Path(config["data"]["silver_path"])
    gold_path = Path(config["data"]["gold_path"])
    
    # Ensure Gold directory exists
    gold_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Loading Silver datasets for merging...")
    
    # Required files for the master join
    tx_file = silver_path / "transactions_history.parquet"
    master_file = silver_path / "outlet_master.parquet"
    coord_file = silver_path / "outlet_coordinates.parquet"
    
    if not all([tx_file.exists(), master_file.exists(), coord_file.exists()]):
        logger.error("Required Silver files (transactions, master, or coordinates) are missing.")
        return

    # 1. Start with transactions as the base
    df = pd.read_parquet(tx_file)
    logger.info(f"Base transactions loaded: {len(df)} rows")
    
    # 2. Join Outlet Master
    outlets = pd.read_parquet(master_file)
    df = df.merge(outlets, on="Outlet_ID", how="left")
    logger.info(f"Merged with Outlet Master. Current rows: {len(df)}")
    
    # 3. Join Coordinates
    coords = pd.read_parquet(coord_file)
    df = df.merge(coords, on="Outlet_ID", how="left")
    logger.info(f"Merged with Coordinates. Current rows: {len(df)}")
    
    # 4. Optional: Join Seasonality if available
    season_file = silver_path / "distributor_seasonality_details.parquet"
    if season_file.exists():
        seasonality = pd.read_parquet(season_file)
        # Seasonality is typically at (Distributor, Year, Month) level
        if all(c in df.columns for c in ["Distributor_ID", "Year", "Month"]):
            df = df.merge(seasonality, on=["Distributor_ID", "Year", "Month"], how="left")
            logger.info("Successfully merged Seasonality Index.")
            
    # 5. Optional: Join Holidays
    holiday_file = silver_path / "holiday_list.parquet"
    if holiday_file.exists():
        # This join is more complex (usually daily). 
        # For simplicity in the final dataset, we'll just flag if a month has a major holiday.
        holidays = pd.read_parquet(holiday_file)
        holiday_counts = holidays.groupby(['Year', 'Month']).size().reset_index(name='holiday_count')
        df = df.merge(holiday_counts, on=['Year', 'Month'], how='left')
        df['holiday_count'] = df['holiday_count'].fillna(0)
        logger.info("Successfully merged Holiday counts per month.")

    # 6. Final Save to Gold
    output_file = gold_path / "final_dataset.csv"
    df.to_csv(output_file, index=False)
    logger.info(f"Saved merged master dataset to {output_file} ({len(df)} rows)")

if __name__ == "__main__":
    merge_silver_to_gold()
