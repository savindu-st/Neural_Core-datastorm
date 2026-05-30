"""
Ingestion stage of the data pipeline.

Loads raw CSV files from the Bronze layer (data/bronze/), standardizes their 
column names, validates the presence of required columns, and saves them
into the Silver layer drop-zone as raw_*_loaded.csv.
"""

import pandas as pd
import logging
from pathlib import Path
from src.utils.config import load_config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Column name standardization mapping
COLUMN_MAPPING = {
    "outlet_id": "Outlet_ID",
    "outlet_size": "Outlet_Size",
    "cooler_count": "Cooler_Count",
    "outlet_type": "Outlet_Type",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "year": "Year",
    "month": "Month",
    "distributor_id": "Distributor_ID",
    "sku_id": "SKU_ID",
    "volume_liters": "Volume_Liters",
    "total_bill_value": "Total_Bill_Value",
    "date": "Date",
    "seasonality_index": "Seasonality_Index"
}

# Required columns for validation
REQUIRED_COLUMNS = {
    "transactions_history_final.csv": ["Outlet_ID", "Year", "Month", "Distributor_ID", "SKU_ID", "Volume_Liters", "Total_Bill_Value"],
    "outlet_master.csv": ["Outlet_ID", "Outlet_Size", "Outlet_Type"],
    "outlet_coordinates.csv": ["Outlet_ID", "Latitude", "Longitude"],
    "distributor_seasonality_details.csv": ["Distributor_ID", "Year", "Month", "Seasonality_Index"],
    "holiday_list.csv": ["Date"]
}

def standardize_and_validate(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    """
    Standardizes column names by stripping whitespace and matching standard keys.
    Validates that required columns exist in the DataFrame.
    """
    # 1. Strip whitespace from column names and standardize casing
    standardized_cols = []
    for col in df.columns:
        stripped = col.strip()
        lower = stripped.lower()
        if lower in COLUMN_MAPPING:
            standardized_cols.append(COLUMN_MAPPING[lower])
        else:
            # Fallback to stripped title casing if not in mapping
            standardized_cols.append(stripped)
    df.columns = standardized_cols
    
    # 2. Validate required columns
    required = REQUIRED_COLUMNS.get(filename, [])
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"[{filename}] Missing required columns: {missing}. Found columns: {list(df.columns)}")
        
    return df

def ingest_dataset(bronze_dir: Path, silver_dir: Path, filename: str, output_name: str):
    """Ingests a single raw CSV file from bronze into silver layer."""
    source_file = bronze_dir / filename
    dest_file = silver_dir / output_name
    
    if not source_file.exists():
        logger.error(f"Source raw file '{source_file}' not found.")
        raise FileNotFoundError(f"Missing mandatory raw dataset: {filename}")
        
    logger.info(f"Ingesting '{filename}'...")
    
    # Use chunksize or low_memory=False for very large files like transactions
    if filename == "transactions_history_final.csv":
        # Load with optimized types to save memory
        df = pd.read_csv(source_file, dtype={"Outlet_ID": "str", "Distributor_ID": "str", "SKU_ID": "str"})
    else:
        df = pd.read_csv(source_file)
        
    logger.info(f"Loaded {len(df)} rows from {filename}")
    
    # Standardize column headers and validate columns
    df = standardize_and_validate(df, filename)
    
    # Write as standardized loaded raw CSV to silver layer
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest_file, index=False)
    logger.info(f"Standardized and saved: {filename} -> {dest_file}")

def main():
    logger.info("Starting Bronze -> Silver Raw Ingestion Pipeline...")
    config = load_config()
    
    bronze_dir = Path(config["data"]["bronze_path"])
    silver_dir = Path(config["data"]["silver_path"])
    
    # Mapping of source filename to destination filename
    ingestion_jobs = [
        ("transactions_history_final.csv", "raw_transactions_loaded.csv"),
        ("outlet_master.csv", "raw_outlet_master_loaded.csv"),
        ("outlet_coordinates.csv", "raw_outlet_coordinates_loaded.csv"),
        ("distributor_seasonality_details.csv", "raw_seasonality_loaded.csv"),
        ("holiday_list.csv", "raw_holidays_loaded.csv")
    ]
    
    for filename, output_name in ingestion_jobs:
        try:
            ingest_dataset(bronze_dir, silver_dir, filename, output_name)
        except Exception as e:
            logger.error(f"Ingestion failed for {filename}: {e}")
            raise e
            
    logger.info("Bronze -> Silver Raw Ingestion completed successfully!")

if __name__ == "__main__":
    main()
