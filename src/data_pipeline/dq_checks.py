"""
Modular and reusable data quality validation wrapper.

Invokes parameterizable validations across each ingested raw dataset 
to flag and isolate problematic records before cleaning.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import src.utils.dq_engine as dq

logger = logging.getLogger(__name__)

def run_outlet_master_checks(df: pd.DataFrame) -> pd.Series:
    """Checks for outlet_master nulls or duplicates."""
    # 1. Null validation on mandatory fields (Outlet_Size, Outlet_Type)
    null_mask = dq.validate_nulls(df, ["Outlet_Size"])
    
    # 2. Duplicate validation on primary key (Outlet_ID)
    dup_mask = dq.validate_duplicates(df, subset=["Outlet_ID"])
    
    return null_mask | dup_mask

def run_coordinate_checks(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Validates geospatial coordinates.
    Returns:
      bad_mask: coordinates that are completely invalid/unrecoverable (or out of bounds and NOT swapped)
      swapped_mask: coordinates that are valid but SWAPPED (can be corrected)
    """
    # Range check boundaries for Sri Lanka
    lat_min, lat_max = 5.5, 10.0
    lon_min, lon_max = 79.0, 82.0
    
    # Check if coords are numeric
    unparseable = dq.validate_types(df, "Latitude", "numeric") | dq.validate_types(df, "Longitude", "numeric")
    
    # Safe numeric conversion for bounds checking
    lats = pd.to_numeric(df["Latitude"], errors='coerce')
    lons = pd.to_numeric(df["Longitude"], errors='coerce')
    
    # Swapped detection (Latitude is in longitude bounds, and Longitude is in latitude bounds)
    swapped_mask = (lats.between(lon_min, lon_max)) & (lons.between(lat_min, lat_max))
    
    # Correct bounds check (standard orientation)
    correct_bounds = (lats.between(lat_min, lat_max)) & (lons.between(lon_min, lon_max))
    
    # Missing/null coordinates or 0.0/0.0 coordinates
    missing_mask = df["Latitude"].isna() | df["Longitude"].isna() | (lats == 0.0) | (lons == 0.0)
    
    # A record is "bad" if it is unparseable, missing, or out of bounds (and NOT swapped)
    out_of_bounds = ~correct_bounds & ~swapped_mask & ~missing_mask
    bad_mask = unparseable | missing_mask | out_of_bounds
    
    return bad_mask, swapped_mask

def run_transaction_checks(df: pd.DataFrame, clean_master_df: pd.DataFrame = None) -> tuple[pd.Series, dict]:
    """
    Validates transactions.
    Returns a bad records mask and a dictionary of detailed flag masks for audit.
    """
    # 1. Null check on mandatory columns
    null_mask = dq.validate_nulls(df, ["Outlet_ID", "Volume_Liters", "Total_Bill_Value", "Year", "Month"])
    
    # 2. Value range validations
    neg_vol = dq.validate_range(df, "Volume_Liters", 0.0001, 1000000)
    neg_val = dq.validate_range(df, "Total_Bill_Value", 0.0, 10000000)
    
    # 3. Date bounds (Month in 1..12, Year in 2023..2026)
    invalid_period = dq.validate_range(df, "Year", 2023, 2026) | dq.validate_range(df, "Month", 1, 12)
    
    # 4. Outlier detection using IQR (Interquartile Range)
    outlier_mask = pd.Series(False, index=df.index)
    if "Volume_Liters" in df.columns and len(df) > 0:
        vols = pd.to_numeric(df["Volume_Liters"], errors='coerce')
        Q1 = vols.quantile(0.25)
        Q3 = vols.quantile(0.75)
        IQR = Q3 - Q1
        # System anomalous ghost entries (Volume > Q3 + 10 * IQR)
        outlier_mask = vols > (Q3 + 10 * IQR)
        
    # 5. Duplicate validation on full row
    dup_mask = dq.validate_duplicates(df, subset=list(df.columns))
    
    # 6. Referential integrity check
    orphan_mask = pd.Series(False, index=df.index)
    if clean_master_df is not None:
        orphan_mask = dq.validate_referential_integrity(df, clean_master_df, "Outlet_ID")
        
    bad_mask = null_mask | neg_vol | neg_val | invalid_period | outlier_mask | dup_mask | orphan_mask
    
    detailed_flags = {
        "null_values": null_mask,
        "negative_volume": neg_vol,
        "negative_bill": neg_val,
        "invalid_date": invalid_period,
        "statistical_outlier": outlier_mask,
        "duplicate": dup_mask,
        "referential_orphan": orphan_mask
    }
    
    return bad_mask, detailed_flags

def run_seasonality_checks(df: pd.DataFrame) -> pd.Series:
    """Validates distributor seasonality details."""
    null_mask = df.isna().any(axis=1)
    invalid_month = dq.validate_range(df, "Month", 1, 12)
    return null_mask | invalid_month

def run_holiday_checks(df: pd.DataFrame) -> pd.Series:
    """Validates holiday list dates."""
    unparseable_date = dq.validate_types(df, "Date", "date")
    return unparseable_date

def save_evidence_summary(results: list[dict], output_path: Path):
    """Saves data quality validation aggregates to evidence directory."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df = pd.DataFrame(results)
    summary_df.to_csv(output_path, index=False)
    logger.info(f"Saved Data Quality Evidence Summary to: {output_path}")
