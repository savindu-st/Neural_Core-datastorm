"""
Bronze -> Silver Data Cleaning & Anomaly Correction Pipeline.

Reads standardized loaded CSV files from the Silver drop-zone, runs data quality 
validation routines via dq_checks, quarantines bad records systematically via 
RejectedStore, applies automated coordinate swap-back correction, calculates 
Coordinate Quality Scores, and outputs cleaned Parquet and CSV files.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
from src.utils.config import load_config
import src.data_pipeline.dq_checks as dq_checks
from src.data_pipeline.rejected_store import RejectedStore

logger = logging.getLogger(__name__)

# Geographic constants
SRI_LANKA_LAT_MIN, SRI_LANKA_LAT_MAX = 5.5, 10.0
SRI_LANKA_LON_MIN, SRI_LANKA_LON_MAX = 79.0, 82.0

class DataCleaner:
    def __init__(self):
        self.config = load_config()
        self.silver_path = Path(self.config["data"]["silver_path"])
        self.rejected_path = Path(self.config["data"].get("rejected_path", "data/rejected"))
        self.evidence_path = Path("outputs/evidence")
        
        self.silver_path.mkdir(parents=True, exist_ok=True)
        self.rejected_path.mkdir(parents=True, exist_ok=True)
        self.evidence_path.mkdir(parents=True, exist_ok=True)
        
        self.rejected_store = RejectedStore(self.rejected_path)
        
        # Ingestion metrics list for evidence summary CSV
        self.dq_results_summary = []

    def clean_outlets(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Cleans both outlet master and outlet coordinates.
        Applies coordinate swap-back corrections, computes coordinate quality scores,
        quarantines invalid records, and merges them.
        """
        logger.info("Cleaning outlet datasets...")
        
        # Load raw loaded silver files
        master_file = self.silver_path / "raw_outlet_master_loaded.csv"
        coords_file = self.silver_path / "raw_outlet_coordinates_loaded.csv"
        
        if not master_file.exists() or not coords_file.exists():
            raise FileNotFoundError("Missing raw loaded outlet datasets in Silver layer.")
            
        df_master = pd.read_csv(master_file)
        df_coords = pd.read_csv(coords_file)
        
        logger.info(f"Loaded {len(df_master)} master rows and {len(df_coords)} coordinate rows.")
        
        # --- 1. Clean Coordinates ---
        # Find invalid and swapped coordinates
        bad_coords_mask, swapped_mask = dq_checks.run_coordinate_checks(df_coords)
        
        # Record metrics
        swapped_count = int(swapped_mask.sum())
        invalid_count = int(bad_coords_mask.sum())
        logger.info(f"Geospatial Audit: {swapped_count} swapped coordinates detected, {invalid_count} invalid coordinates detected.")
        
        # Store bad coordinate rows in rejected coordinates
        self.rejected_store.store_rejected(df_coords, bad_coords_mask, "outlet_coordinates", "Geospatial Out-of-Bounds/Format")
        
        # Initialize coordinate quality score
        coord_quality = pd.Series(0.0, index=df_coords.index)
        
        # Swapped Correction (Wow Factor)
        if swapped_count > 0:
            logger.info("Applying automated coordinate swap-back correction...")
            # Perform vectorized swap
            lats = df_coords.loc[swapped_mask, "Latitude"].copy()
            lons = df_coords.loc[swapped_mask, "Longitude"].copy()
            df_coords.loc[swapped_mask, "Latitude"] = lons
            df_coords.loc[swapped_mask, "Longitude"] = lats
            coord_quality.loc[swapped_mask] = 0.5
            
        # Clean standard coordinates
        clean_mask = ~bad_coords_mask & ~swapped_mask
        coord_quality.loc[clean_mask] = 1.0
        
        # Add Coordinate Quality Score to coordinates dataframe
        df_coords["coordinate_quality_score"] = coord_quality
        
        # Null out bad coordinates so they don't break spatial indexes
        df_coords.loc[bad_coords_mask, "Latitude"] = np.nan
        df_coords.loc[bad_coords_mask, "Longitude"] = np.nan
        
        # Keep clean coordinates in silver coordinates output
        df_coords_cleaned = df_coords.copy()
        
        # Save coordinates Parquet
        coord_parquet = self.silver_path / "outlet_coordinates.parquet"
        df_coords_cleaned.to_parquet(coord_parquet, index=False)
        
        self.dq_results_summary.append({
            "dataset": "outlet_coordinates",
            "rows_in": len(df_coords),
            "rows_out": len(df_coords_cleaned),
            "rows_flagged": invalid_count,
            "rows_dropped": 0,
            "percentage_flagged": (invalid_count / len(df_coords) * 100) if len(df_coords) > 0 else 0
        })
        
        # --- 2. Clean Outlet Master ---
        bad_master_mask = dq_checks.run_outlet_master_checks(df_master)
        master_dropped = int(bad_master_mask.sum())
        
        # Store bad master records
        self.rejected_store.store_rejected(df_master, bad_master_mask, "outlet_master", "Mandatory Field Null (Outlet_Size)")
        
        # Filter clean master records
        df_master_cleaned = df_master[~bad_master_mask].copy()
        
        # Standardize strings
        df_master_cleaned["Outlet_Size"] = df_master_cleaned["Outlet_Size"].str.strip().str.title()
        df_master_cleaned["Outlet_Type"] = df_master_cleaned["Outlet_Type"].str.strip().str.title()
        
        # Typos correction
        typo_map = {"Grocry": "Grocery", "Bakry": "Bakery", "Smmt": "SMMT"}
        df_master_cleaned["Outlet_Type"] = df_master_cleaned["Outlet_Type"].replace(typo_map)
        df_master_cleaned["Outlet_Size"] = df_master_cleaned["Outlet_Size"].fillna("Unknown")
        
        # Join Master with Coordinates
        df_master_merged = df_master_cleaned.merge(df_coords_cleaned, on="Outlet_ID", how="left")
        
        # Save Parquet and clean CSV for Member 1 outputs
        master_parquet = self.silver_path / "outlet_master.parquet"
        df_master_merged.to_parquet(master_parquet, index=False)
        
        master_csv = self.silver_path / "clean_outlet_master.csv"
        df_master_merged.to_csv(master_csv, index=False)
        
        self.dq_results_summary.append({
            "dataset": "outlet_master",
            "rows_in": len(df_master),
            "rows_out": len(df_master_merged),
            "rows_flagged": master_dropped,
            "rows_dropped": master_dropped,
            "percentage_flagged": (master_dropped / len(df_master) * 100) if len(df_master) > 0 else 0
        })
        
        logger.info(f"Saved merged outlet master to Parquet and CSV. Quality distribution: {coord_quality.value_counts().to_dict()}")
        
        return df_master_merged, df_coords_cleaned

    def clean_transactions(self, df_master_cleaned: pd.DataFrame):
        """Cleans transactions_history dataset, enforces referential integrity, and writes outputs."""
        logger.info("Cleaning transactions dataset...")
        
        tx_file = self.silver_path / "raw_transactions_loaded.csv"
        if not tx_file.exists():
            raise FileNotFoundError("Missing raw loaded transactions dataset in Silver layer.")
            
        # Large file loaded cleanly with pyarrow
        df = pd.read_csv(tx_file)
        
        # Run detailed checks
        bad_mask, flags = dq_checks.run_transaction_checks(df, df_master_cleaned)
        
        # Store rejections systematically by reason
        for flag_name, mask in flags.items():
            count = int(mask.sum())
            if count > 0:
                self.rejected_store.store_rejected(df, mask, "transactions", f"Transaction Validation: {flag_name}")
                
        dropped_count = int(bad_mask.sum())
        logger.info(f"Transactions Audit: Flags mapped. Dropping {dropped_count} anomalous rows.")
        
        # Filter clean records
        df_cleaned = df[~bad_mask].copy()
        
        # Save Parquet & CSV for Member 1 outputs
        tx_parquet = self.silver_path / "transactions_history.parquet"
        df_cleaned.to_parquet(tx_parquet, index=False)
        
        tx_csv = self.silver_path / "clean_transactions.csv"
        df_cleaned.to_csv(tx_csv, index=False)
        
        self.dq_results_summary.append({
            "dataset": "transactions_history",
            "rows_in": len(df),
            "rows_out": len(df_cleaned),
            "rows_flagged": dropped_count,
            "rows_dropped": dropped_count,
            "percentage_flagged": (dropped_count / len(df) * 100) if len(df) > 0 else 0
        })
        
        logger.info(f"Saved cleaned transactions to Parquet and CSV ({len(df_cleaned)} rows out).")

    def clean_holidays(self):
        """Cleans holiday list dataset."""
        logger.info("Cleaning holiday list...")
        holiday_file = self.silver_path / "raw_holidays_loaded.csv"
        if not holiday_file.exists():
            return
            
        df = pd.read_csv(holiday_file)
        bad_mask = dq_checks.run_holiday_checks(df)
        dropped = int(bad_mask.sum())
        
        if dropped > 0:
            self.rejected_store.store_rejected(df, bad_mask, "holiday_list", "Holiday Date Casing/Format Error")
            
        df_cleaned = df[~bad_mask].copy()
        df_cleaned["Date"] = pd.to_datetime(df_cleaned["Date"], errors='coerce')
        df_cleaned["Year"] = df_cleaned["Date"].dt.year
        df_cleaned["Month"] = df_cleaned["Date"].dt.month
        
        output_file = self.silver_path / "holiday_list.parquet"
        df_cleaned.to_parquet(output_file, index=False)
        
        self.dq_results_summary.append({
            "dataset": "holiday_list",
            "rows_in": len(df),
            "rows_out": len(df_cleaned),
            "rows_flagged": dropped,
            "rows_dropped": dropped,
            "percentage_flagged": (dropped / len(df) * 100) if len(df) > 0 else 0
        })

    def clean_seasonality(self):
        """Cleans distributor seasonality dataset."""
        logger.info("Cleaning seasonality details...")
        season_file = self.silver_path / "raw_seasonality_loaded.csv"
        if not season_file.exists():
            return
            
        df = pd.read_csv(season_file)
        bad_mask = dq_checks.run_seasonality_checks(df)
        dropped = int(bad_mask.sum())
        
        if dropped > 0:
            self.rejected_store.store_rejected(df, bad_mask, "distributor_seasonality", "Seasonality Index Null/Range Error")
            
        df_cleaned = df[~bad_mask].copy()
        
        output_file = self.silver_path / "distributor_seasonality_details.parquet"
        df_cleaned.to_parquet(output_file, index=False)
        
        self.dq_results_summary.append({
            "dataset": "distributor_seasonality_details",
            "rows_in": len(df),
            "rows_out": len(df_cleaned),
            "rows_flagged": dropped,
            "rows_dropped": dropped,
            "percentage_flagged": (dropped / len(df) * 100) if len(df) > 0 else 0
        })

    def run_pipeline(self):
        """Runs the entire Bronze -> Silver cleaning pipeline orchestration."""
        logger.info("Starting Bronze -> Silver Cleaning Pipeline Run...")
        
        # Clear previous rejections
        self.rejected_store.clear_store()
        
        # 1. Outlets & Geospatial (Coordinates + Master)
        df_master_cleaned, df_coords_cleaned = self.clean_outlets()
        
        # 2. Seasonality & Holidays
        self.clean_seasonality()
        self.clean_holidays()
        
        # 3. Transactions (dependant on Master for referential integrity)
        self.clean_transactions(df_master_cleaned)
        
        # 4. Save centralized evidence report
        dq_checks.save_evidence_summary(self.dq_results_summary, self.evidence_path / "data_quality_summary.csv")
        
        logger.info("Bronze -> Silver Cleaning Pipeline Run finished successfully!")

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    cleaner = DataCleaner()
    cleaner.run_pipeline()

if __name__ == "__main__":
    main()
