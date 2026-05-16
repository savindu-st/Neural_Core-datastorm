"""
Reusable Data Quality Engine for the Neural Core Data Storm Pipeline.

This module provides parameterizable validation functions used consistently 
across the Bronze -> Silver transition.

As per competition requirement 4.2:
- Reusable
- Parameterizable
- Consistent application
"""

import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def validate_nulls(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Flags records where mandatory fields contain null values."""
    mask = df[columns].isna().any(axis=1)
    return mask

def validate_duplicates(df: pd.DataFrame, subset: list[str]) -> pd.Series:
    """Detects duplicate records based on a configurable primary key."""
    return df.duplicated(subset=subset, keep="first")

def validate_range(df: pd.DataFrame, column: str, min_val: float, max_val: float) -> pd.Series:
    """Asserts that numeric fields fall within an expected min/max boundary."""
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    
    # Coerce to numeric for safety
    vals = pd.to_numeric(df[column], errors='coerce')
    mask = (vals < min_val) | (vals > max_val) | (vals.isna() & df[column].notna())
    return mask

def validate_referential_integrity(df: pd.DataFrame, ref_df: pd.DataFrame, key: str) -> pd.Series:
    """Validates that foreign key values in one dataset exist in a reference dataset."""
    if key not in df.columns or key not in ref_df.columns:
        return pd.Series(False, index=df.index)
        
    valid_keys = ref_df[key].unique()
    mask = ~df[key].isin(valid_keys)
    return mask

def validate_types(df: pd.DataFrame, column: str, expected_type: str) -> pd.Series:
    """Checks if a column conforms to an expected data type."""
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    
    if expected_type == "numeric":
        return pd.to_numeric(df[column], errors='coerce').isna() & df[column].notna()
    elif expected_type == "date":
        return pd.to_datetime(df[column], errors='coerce').isna() & df[column].notna()
    
    return pd.Series(False, index=df.index)
