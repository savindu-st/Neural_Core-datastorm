"""
Bronze → Silver data cleaning pipeline.

Reads raw CSV files from the Bronze lakehouse layer, validates and cleans
each dataset, saves rejected records for auditing, and writes cleaned
Parquet files to the Silver layer.

Usage::

    python -m src.data_pipeline.clean
"""

import pandas as pd

from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Callable
import logging

from src.utils.config import load_config

logger = logging.getLogger(__name__)

__all__ = [
    "clean_outlet_master",
    "clean_outlet_coordinates",
    "clean_holiday_list",
    "clean_distributor_seasonality",
    "clean_transactions",
    "CleaningResult",
]


# ---------------------------------------------------------------------------
# Column name constants — single source of truth
# ---------------------------------------------------------------------------
class Columns:
    """Centralized column names to avoid magic strings throughout the pipeline."""

    OUTLET_SIZE = "Outlet_Size"
    OUTLET_TYPE = "Outlet_Type"
    LATITUDE = "Latitude"
    LONGITUDE = "Longitude"
    VOLUME_LITERS = "Volume_Liters"
    TOTAL_BILL_VALUE = "Total_Bill_Value"
    DATE = "Date"
    YEAR = "Year"
    MONTH = "Month"
    SEASONALITY_INDEX = "Seasonality_Index"


class GeoBounds:
    """Geographic boundaries for Sri Lanka coordinate validation."""

    SRI_LANKA_LAT_MIN = 5.5
    SRI_LANKA_LAT_MAX = 10.0
    SRI_LANKA_LON_MIN = 79.0
    SRI_LANKA_LON_MAX = 82.0


# Known typo corrections for Outlet_Type (must be in Title Case
# to match the output of normalize_column).
_OUTLET_TYPE_TYPOS: dict[str, str] = {
    "Grocry": "Grocery",
    "Bakry": "Bakery",
    "Smmt": "SMMT",  # Restore acronym mangled by .str.title()
}



# ---------------------------------------------------------------------------
# Result dataclass — returned by every cleaning function
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class CleaningResult:
    """Summary of a single dataset's cleaning pass.

    Attributes:
        dataset:       Human-readable dataset name.
        rows_in:       Total rows read from Bronze.
        rows_out:      Total rows written to Silver.
        rows_flagged:  Rows flagged as problematic (saved to rejected/).
        rows_dropped:  Rows actually removed from Silver output.
        output_path:   Absolute path to the output Parquet file.
    """

    dataset: str
    rows_in: int
    rows_out: int
    rows_flagged: int
    rows_dropped: int
    output_path: Path


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _read_bronze_csv(bronze_path: Path, filename: str, **kwargs) -> pd.DataFrame:
    """Read a CSV from the Bronze layer with existence validation.

    Raises:
        FileNotFoundError: If the source file does not exist.
    """
    source = bronze_path / filename
    if not source.exists():
        raise FileNotFoundError(f"Bronze file not found: {source}")
    return pd.read_csv(source, **kwargs)


def _require_columns(df: pd.DataFrame, columns: list[str], dataset: str) -> None:
    """Validate that all expected columns are present in the DataFrame.

    Raises:
        ValueError: If the DataFrame has zero rows.
        KeyError: If any required column is missing.
    """
    if len(df) == 0:
        raise ValueError(f"[{dataset}] DataFrame is empty — 0 rows loaded from Bronze")
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(
            f"[{dataset}] Missing required columns: {', '.join(missing)}"
        )


def normalize_column(df: pd.DataFrame, col: str) -> None:
    """Strip whitespace and title-case a string column in-place.

    Modifies *df* in-place; returns nothing.
    """
    if col not in df.columns:
        return

    # Only apply string normalization to object or string dtypes
    # to avoid converting numeric data or mangling native NaNs.
    if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
        df[col] = df[col].str.strip().str.title()


def save_rejected(
    df: pd.DataFrame,
    mask: pd.Series,
    rejected_path: Path,
    filename: str,
) -> int:
    """Save rejected/bad rows to the rejected folder and return the count.

    Files are timestamped so successive pipeline runs never overwrite
    previous audit records.
    """
    rejected_count = int(mask.sum())
    if rejected_count > 0:
        rejected_df = df[mask].copy()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = rejected_path / f"{filename}_rejected_{ts}.csv"
        rejected_df.to_csv(out_file, index=False)
        logger.warning(
            "Saved %d bad records to %s", rejected_count, out_file
        )
    return rejected_count


def _atomic_parquet_write(df: pd.DataFrame, output_file: Path) -> None:
    """Write Parquet atomically: write to .tmp, then rename.

    Prevents partial corruption if the pipeline crashes mid-write.
    """
    tmp_file = output_file.with_suffix(".parquet.tmp")
    df.to_parquet(tmp_file, index=False)
    tmp_file.replace(output_file)


def _cleanup_old_rejected(rejected_path: Path, keep_last: int = 5) -> None:
    """Keep only the N most recent rejected files per dataset prefix."""
    prefixes = {
        f.name.rsplit("_rejected_", 1)[0]
        for f in rejected_path.glob("*_rejected_*.csv")
    }
    for prefix in prefixes:
        files = sorted(rejected_path.glob(f"{prefix}_rejected_*.csv"), reverse=True)
        for old in files[keep_last:]:
            old.unlink()
            logger.info("Cleaned up old rejected file: %s", old.name)


# ---------------------------------------------------------------------------
# Dataset-specific cleaners
# ---------------------------------------------------------------------------
def clean_outlet_master(
    bronze_path: Path, silver_path: Path, rejected_path: Path
) -> CleaningResult:
    """Clean the outlet_master dataset.

    - Rejects rows with missing Outlet_Size (saved for audit).
    - Normalises string columns *first*, then imputes missing Outlet_Size
      as ``'Unknown'`` so Silver retains full row volume.
    - Fixes known typos in Outlet_Type.
    """
    logger.info("Cleaning outlet_master...")
    df = _read_bronze_csv(bronze_path, "outlet_master.csv")
    _require_columns(df, [Columns.OUTLET_SIZE], "outlet_master")
    rows_in = len(df)

    # Identify bad records (missing Outlet_Size)
    bad_mask = df[Columns.OUTLET_SIZE].isna()
    rows_flagged = save_rejected(df, bad_mask, rejected_path, "outlet_master")

    # Normalise existing data first, then fill gaps — ensures the sentinel
    # value is always exactly "Unknown" regardless of normalize_column logic.
    normalize_column(df, Columns.OUTLET_TYPE)
    normalize_column(df, Columns.OUTLET_SIZE)
    df[Columns.OUTLET_SIZE] = df[Columns.OUTLET_SIZE].fillna("Unknown")

    # Fix known typos (values must be Title Case to match normalize_column output)
    if Columns.OUTLET_TYPE in df.columns:
        df[Columns.OUTLET_TYPE] = df[Columns.OUTLET_TYPE].replace(
            _OUTLET_TYPE_TYPOS
        )

    output_file = silver_path / "outlet_master.parquet"
    _atomic_parquet_write(df, output_file)
    logger.info("Saved cleaned outlet_master to %s (Rows: %d)", output_file, len(df))

    return CleaningResult(
        dataset="outlet_master",
        rows_in=rows_in,
        rows_out=len(df),
        rows_flagged=rows_flagged,
        rows_dropped=0,  # Flagged rows are imputed, not removed
        output_path=output_file,
    )


def clean_outlet_coordinates(
    bronze_path: Path, silver_path: Path, rejected_path: Path
) -> CleaningResult:
    """Clean the outlet_coordinates dataset.

    - Coerces lat/lon to numeric.
    - Flags unparseable and out-of-Sri-Lanka-bounds rows as rejected.
    - Nulls out bad coordinate values in Silver so downstream models
      can decide how to handle missingness.
    """
    logger.info("Cleaning outlet_coordinates...")
    df = _read_bronze_csv(bronze_path, "outlet_coordinates.csv")
    _require_columns(df, [Columns.LATITUDE, Columns.LONGITUDE], "outlet_coordinates")
    rows_in = len(df)

    # Convert to numeric to find unparseable values
    lat_num = pd.to_numeric(df[Columns.LATITUDE], errors="coerce")
    lon_num = pd.to_numeric(df[Columns.LONGITUDE], errors="coerce")

    unparseable = lat_num.isna() | lon_num.isna()
    out_of_bounds = (
        (lat_num < GeoBounds.SRI_LANKA_LAT_MIN)
        | (lat_num > GeoBounds.SRI_LANKA_LAT_MAX)
        | (lon_num < GeoBounds.SRI_LANKA_LON_MIN)
        | (lon_num > GeoBounds.SRI_LANKA_LON_MAX)
    )
    bad_mask = unparseable | out_of_bounds
    rows_flagged = save_rejected(df, bad_mask, rejected_path, "outlet_coordinates")

    # Null out bad values so Silver is genuinely clean
    df[Columns.LATITUDE] = lat_num.where(~bad_mask)
    df[Columns.LONGITUDE] = lon_num.where(~bad_mask)

    output_file = silver_path / "outlet_coordinates.parquet"
    _atomic_parquet_write(df, output_file)
    logger.info(
        "Saved cleaned outlet_coordinates to %s (Rows: %d)", output_file, len(df)
    )

    return CleaningResult(
        dataset="outlet_coordinates",
        rows_in=rows_in,
        rows_out=len(df),
        rows_flagged=rows_flagged,
        rows_dropped=0,  # Flagged rows are nulled, not removed
        output_path=output_file,
    )


def clean_holiday_list(
    bronze_path: Path, silver_path: Path, rejected_path: Path
) -> CleaningResult:
    """Clean the holiday_list dataset.

    - Attempts ISO8601 parse first for speed; falls back to pandas
      inference if the majority of rows fail to parse.
    - Rejects rows with unparseable dates.
    - Derives Year and Month helper columns.
    """
    logger.info("Cleaning holiday_list...")
    df = _read_bronze_csv(bronze_path, "holiday_list.csv")
    _require_columns(df, [Columns.DATE], "holiday_list")
    rows_in = len(df)

    # Try ISO8601 first (faster), fall back to inference if >50% fail
    parsed_dates = pd.to_datetime(
        df[Columns.DATE], format="ISO8601", errors="coerce"
    )
    if parsed_dates.isna().mean() > 0.5:
        logger.warning(
            "ISO8601 parse rejected >50%% of dates — falling back to inferred format"
        )
        parsed_dates = pd.to_datetime(df[Columns.DATE], errors="coerce")

    # Identify bad records (unparseable dates)
    bad_mask = parsed_dates.isna()
    rows_flagged = save_rejected(df, bad_mask, rejected_path, "holiday_list")

    # Remove rows with unparseable dates from Silver — NaT values
    # would produce NaN Year/Month and break downstream joins.
    rows_dropped = int(bad_mask.sum())
    df = df[~bad_mask].copy()
    parsed_dates = parsed_dates[~bad_mask]

    df[Columns.DATE] = parsed_dates
    df[Columns.YEAR] = df[Columns.DATE].dt.year
    df[Columns.MONTH] = df[Columns.DATE].dt.month

    output_file = silver_path / "holiday_list.parquet"
    _atomic_parquet_write(df, output_file)
    logger.info("Saved cleaned holiday_list to %s (Rows: %d)", output_file, len(df))

    return CleaningResult(
        dataset="holiday_list",
        rows_in=rows_in,
        rows_out=len(df),
        rows_flagged=rows_flagged,
        rows_dropped=rows_dropped,
        output_path=output_file,
    )


def clean_distributor_seasonality(
    bronze_path: Path, silver_path: Path, rejected_path: Path
) -> CleaningResult:
    """Clean the distributor_seasonality_details dataset.

    - Rejects rows with any null values.
    - Standardises Seasonality_Index only if it is a string column.
    """
    logger.info("Cleaning distributor_seasonality_details...")
    df = _read_bronze_csv(bronze_path, "distributor_seasonality_details.csv")
    _require_columns(df, [Columns.SEASONALITY_INDEX], "distributor_seasonality")
    rows_in = len(df)

    bad_mask = df.isna().any(axis=1)
    rows_flagged = save_rejected(
        df, bad_mask, rejected_path, "distributor_seasonality"
    )

    # Drop rows with any null from Silver output
    rows_dropped = int(bad_mask.sum())
    df = df[~bad_mask]

    # Standardize string categories only when the column is string-typed
    if Columns.SEASONALITY_INDEX in df.columns:
        if pd.api.types.is_string_dtype(df[Columns.SEASONALITY_INDEX]):
            normalize_column(df, Columns.SEASONALITY_INDEX)

    output_file = silver_path / "distributor_seasonality_details.parquet"
    _atomic_parquet_write(df, output_file)
    logger.info(
        "Saved cleaned distributor_seasonality_details to %s (Rows: %d)",
        output_file,
        len(df),
    )

    return CleaningResult(
        dataset="distributor_seasonality_details",
        rows_in=rows_in,
        rows_out=len(df),
        rows_flagged=rows_flagged,
        rows_dropped=rows_dropped,
        output_path=output_file,
    )


def clean_transactions(
    bronze_path: Path, silver_path: Path, rejected_path: Path
) -> CleaningResult:
    """Clean the transactions_history_final dataset.

    - Flags non-positive Volume_Liters / negative Total_Bill_Value.
    - Flags out-of-range Year/Month values.
    - Flags exact duplicate rows.
    - Removes all flagged rows from Silver output.
    """
    logger.info("Cleaning transactions_history_final (this may take a minute)...")

    # Use PyArrow engine for a massive speed boost and lower memory footprint.
    # It naturally handles type inference much better than the C engine.
    df = _read_bronze_csv(
        bronze_path, "transactions_history_final.csv", engine="pyarrow", dtype_backend="pyarrow"
    )
    rows_in = len(df)
    logger.info("Loaded %d rows from transactions file.", rows_in)

    # Identify bad records: non-positive volume, negatives, bad dates, duplicates
    bad_mask = pd.Series(False, index=df.index)
    if Columns.VOLUME_LITERS in df.columns:
        bad_mask = bad_mask | (df[Columns.VOLUME_LITERS] <= 0)
    if Columns.TOTAL_BILL_VALUE in df.columns:
        bad_mask = bad_mask | (df[Columns.TOTAL_BILL_VALUE] < 0)

    # Validate Year/Month ranges
    if Columns.YEAR in df.columns and Columns.MONTH in df.columns:
        invalid_period = (
            (df[Columns.YEAR] < 2023) | (df[Columns.YEAR] > 2026)
            | (df[Columns.MONTH] < 1) | (df[Columns.MONTH] > 12)
        )
        bad_mask = bad_mask | invalid_period

    is_duplicate = df.duplicated(keep="first")
    bad_mask = bad_mask | is_duplicate

    rows_flagged = save_rejected(
        df, bad_mask, rejected_path, "transactions_history"
    )

    # Remove flagged rows (negatives + exact duplicates) from Silver.
    # Negatives distort the latent demand ceiling; duplicates without
    # a unique-ID column cannot be distinguished from true duplication.
    rows_dropped = int(bad_mask.sum())
    df = df[~bad_mask]

    output_file = silver_path / "transactions_history.parquet"
    _atomic_parquet_write(df, output_file)
    logger.info("Saved cleaned transactions to %s (Rows: %d)", output_file, len(df))

    return CleaningResult(
        dataset="transactions_history",
        rows_in=rows_in,
        rows_out=len(df),
        rows_flagged=rows_flagged,
        rows_dropped=rows_dropped,
        output_path=output_file,
    )


# ---------------------------------------------------------------------------
# Type alias for pipeline steps
# ---------------------------------------------------------------------------
CleanerFn = Callable[[Path, Path, Path], CleaningResult]


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the full Bronze → Silver cleaning pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # Load paths from centralised config
    config = load_config()
    bronze_path = Path(config["data"]["bronze_path"])
    silver_path = Path(config["data"]["silver_path"])
    rejected_path = Path(config["data"].get("rejected_path", "data/rejected"))

    # Ensure output directories exist
    silver_path.mkdir(parents=True, exist_ok=True)
    rejected_path.mkdir(parents=True, exist_ok=True)

    # Ordered cleaning steps
    steps: list[tuple[str, CleanerFn]] = [
        ("outlet_master", clean_outlet_master),
        ("outlet_coordinates", clean_outlet_coordinates),
        ("holiday_list", clean_holiday_list),
        ("distributor_seasonality", clean_distributor_seasonality),
        ("transactions", clean_transactions),
    ]

    results: list[CleaningResult] = []
    failed: list[str] = []

    for name, func in steps:
        try:
            result = func(bronze_path, silver_path, rejected_path)
            results.append(result)
        except Exception as e:
            logger.error("Failed cleaning %s: %s", name, e, exc_info=True)
            failed.append(name)

    # ---- Summary report ----
    if results:
        logger.info("=" * 72)
        logger.info("CLEANING SUMMARY")
        logger.info("-" * 72)
        logger.info(
            "  %-35s %8s %8s %8s %8s %7s",
            "DATASET", "IN", "OUT", "FLAGGED", "DROPPED", "FLAG%",
        )
        logger.info("-" * 72)
        for r in results:
            flag_pct = (r.rows_flagged / r.rows_in * 100) if r.rows_in > 0 else 0.0
            logger.info(
                "  %-35s %8d %8d %8d %8d %6.1f%%",
                r.dataset, r.rows_in, r.rows_out, r.rows_flagged, r.rows_dropped, flag_pct,
            )
            if flag_pct > 10:
                logger.warning(
                    "  ⚠️  %s: %.1f%% rows flagged — investigate data source!",
                    r.dataset, flag_pct,
                )
        logger.info("-" * 72)
        total_in = sum(r.rows_in for r in results)
        total_out = sum(r.rows_out for r in results)
        total_flagged = sum(r.rows_flagged for r in results)
        total_dropped = sum(r.rows_dropped for r in results)
        total_flag_pct = (total_flagged / total_in * 100) if total_in > 0 else 0.0
        logger.info(
            "  %-35s %8d %8d %8d %8d %6.1f%%",
            "TOTAL", total_in, total_out, total_flagged, total_dropped, total_flag_pct,
        )
        logger.info("=" * 72)

    if failed:
        raise RuntimeError(
            f"Bronze → Silver cleaning failed for: {', '.join(failed)}"
        )

    # Clean up old rejected files (keep last 5 per dataset)
    _cleanup_old_rejected(rejected_path)

    logger.info("All Bronze → Silver data cleaning completed successfully.")


if __name__ == "__main__":
    main()
