"""
Unit tests for src/data_pipeline/dq_checks.py and src/optimization/budget_optimizer.py.

All tests use synthetic in-memory data — no file I/O required.
Run with: pytest tests/test_pipeline.py -v
"""

import pandas as pd
import numpy as np
import pytest
from src.data_pipeline.dq_checks import (
    run_coordinate_checks,
    run_outlet_master_checks,
    run_transaction_checks,
    run_seasonality_checks,
)
from src.optimization.budget_optimizer import _normalize


# ────────────────────────────────────────────────────────────────────
# Helper builders
# ────────────────────────────────────────────────────────────────────

def _coords_df(**overrides) -> pd.DataFrame:
    """Build a single-row coordinate DataFrame with valid Sri Lanka defaults."""
    row = {"Outlet_ID": "OUT001", "Latitude": 6.9271, "Longitude": 79.8612}
    row.update(overrides)
    return pd.DataFrame([row])


def _master_df(**overrides) -> pd.DataFrame:
    """Build a single-row outlet master DataFrame with valid defaults."""
    row = {"Outlet_ID": "OUT001", "Outlet_Size": "Large", "Outlet_Type": "Grocery"}
    row.update(overrides)
    return pd.DataFrame([row])


def _tx_df(**overrides) -> pd.DataFrame:
    """Build a single-row transaction DataFrame with valid defaults."""
    row = {
        "Outlet_ID": "OUT001",
        "Volume_Liters": 100.0,
        "Total_Bill_Value": 15000.0,
        "Year": 2025,
        "Month": 11,
    }
    row.update(overrides)
    return pd.DataFrame([row])


# ────────────────────────────────────────────────────────────────────
# run_coordinate_checks Tests
# ────────────────────────────────────────────────────────────────────

class TestCoordinateChecks:
    """Tests for geospatial coordinate validation in dq_checks.py."""

    def test_valid_coordinates_pass(self):
        """Valid Sri Lanka coordinates should produce no bad/swapped flags."""
        df = _coords_df()
        bad, swapped = run_coordinate_checks(df)
        assert not bad.any(), "Valid coords should not be flagged as bad"
        assert not swapped.any(), "Valid coords should not be flagged as swapped"

    def test_out_of_bounds_latitude(self):
        """Latitude outside Sri Lanka bounds should be flagged as bad."""
        df = _coords_df(Latitude=50.0, Longitude=79.8)  # Europe-level lat
        bad, swapped = run_coordinate_checks(df)
        assert bad.any(), "Out-of-bounds lat should be flagged as bad"

    def test_swapped_coordinates_detected(self):
        """Swapped lat/lon (lon in lat field, lat in lon field) should be flagged."""
        # Swap: put longitude value in Latitude field and vice versa
        df = _coords_df(Latitude=79.8612, Longitude=6.9271)
        bad, swapped = run_coordinate_checks(df)
        assert swapped.any(), "Swapped coordinates should be detected"
        assert not bad.any(), "Swapped-but-fixable coords should not be marked bad"

    def test_null_coordinates_flagged_as_bad(self):
        """Null/NaN coordinates should be flagged as bad."""
        df = _coords_df(Latitude=np.nan, Longitude=np.nan)
        bad, _ = run_coordinate_checks(df)
        assert bad.any(), "NaN coordinates should be flagged as bad"

    def test_zero_zero_coordinates_flagged(self):
        """(0.0, 0.0) coordinates (null island) should be flagged as bad."""
        df = _coords_df(Latitude=0.0, Longitude=0.0)
        bad, _ = run_coordinate_checks(df)
        assert bad.any(), "(0, 0) should be flagged as bad"

    def test_multiple_rows_mixed(self):
        """Mixed valid/invalid rows should produce correct per-row flags."""
        df = pd.DataFrame([
            {"Outlet_ID": "A", "Latitude": 6.93, "Longitude": 79.86},   # valid
            {"Outlet_ID": "B", "Latitude": 50.0, "Longitude": 79.86},   # bad lat
            {"Outlet_ID": "C", "Latitude": 79.86, "Longitude": 6.93},   # swapped
        ])
        bad, swapped = run_coordinate_checks(df)
        assert not bad.iloc[0] and not swapped.iloc[0], "Row A should be clean"
        assert bad.iloc[1], "Row B should be bad"
        assert swapped.iloc[2], "Row C should be swapped"


# ────────────────────────────────────────────────────────────────────
# run_outlet_master_checks Tests
# ────────────────────────────────────────────────────────────────────

class TestOutletMasterChecks:
    """Tests for outlet master validation in dq_checks.py."""

    def test_valid_master_row_passes(self):
        """A complete, non-duplicate master row should produce no flags."""
        df = _master_df()
        mask = run_outlet_master_checks(df)
        assert not mask.any(), "Valid master row should not be flagged"

    def test_null_outlet_size_flagged(self):
        """A row with null Outlet_Size should be flagged."""
        df = _master_df(Outlet_Size=None)
        mask = run_outlet_master_checks(df)
        assert mask.any(), "Null Outlet_Size should be flagged"

    def test_duplicate_outlet_id_flagged(self):
        """Duplicate Outlet_IDs should be flagged."""
        df = pd.DataFrame([
            {"Outlet_ID": "OUT001", "Outlet_Size": "Large", "Outlet_Type": "Grocery"},
            {"Outlet_ID": "OUT001", "Outlet_Size": "Small", "Outlet_Type": "Bakery"},
        ])
        mask = run_outlet_master_checks(df)
        assert mask.any(), "Duplicate Outlet_ID should be flagged"


# ────────────────────────────────────────────────────────────────────
# run_transaction_checks Tests
# ────────────────────────────────────────────────────────────────────

class TestTransactionChecks:
    """Tests for transaction validation in dq_checks.py."""

    def test_valid_transaction_passes(self):
        """A fully valid transaction row should produce no flags."""
        df = _tx_df()
        bad, flags = run_transaction_checks(df)
        assert not bad.any(), f"Valid transaction should not be flagged, got flags: {flags}"

    def test_negative_volume_flagged(self):
        """Negative Volume_Liters should be flagged."""
        df = _tx_df(Volume_Liters=-10.0)
        bad, _ = run_transaction_checks(df)
        assert bad.any(), "Negative volume should be flagged"

    def test_null_outlet_id_flagged(self):
        """Null Outlet_ID should be flagged."""
        df = _tx_df(Outlet_ID=None)
        bad, _ = run_transaction_checks(df)
        assert bad.any(), "Null Outlet_ID should be flagged"

    def test_invalid_month_flagged(self):
        """Month=13 is invalid and should be flagged."""
        df = _tx_df(Month=13)
        bad, _ = run_transaction_checks(df)
        assert bad.any(), "Month=13 should be flagged"

    def test_referential_integrity_orphan_flagged(self):
        """Transaction for Outlet_ID not in master should be flagged."""
        tx = _tx_df(Outlet_ID="UNKNOWN_OUTLET")
        master = _master_df(Outlet_ID="OUT001")
        bad, flags = run_transaction_checks(tx, clean_master_df=master)
        assert flags["referential_orphan"].any(), "Orphan outlet should be flagged"


# ────────────────────────────────────────────────────────────────────
# _normalize Tests (Budget Optimizer)
# ────────────────────────────────────────────────────────────────────

class TestNormalize:
    """Tests for the _normalize() helper in budget_optimizer.py."""

    def test_output_range_is_zero_to_one(self):
        """Normalized values must be in [0, 1]."""
        s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        norm = _normalize(s)
        assert norm.min() >= 0.0 and norm.max() <= 1.0

    def test_min_maps_to_zero(self):
        """The minimum input value should map to 0."""
        s = pd.Series([5.0, 10.0, 15.0])
        norm = _normalize(s)
        assert norm.iloc[0] == pytest.approx(0.0)

    def test_max_maps_to_one(self):
        """The maximum input value should map to approximately 1."""
        s = pd.Series([5.0, 10.0, 15.0])
        norm = _normalize(s)
        assert norm.iloc[-1] == pytest.approx(1.0, abs=1e-6)

    def test_constant_series_does_not_raise(self):
        """A constant-valued series should not raise ZeroDivisionError."""
        s = pd.Series([7.0, 7.0, 7.0])
        norm = _normalize(s)
        assert (norm == 0.0).all(), "Constant series should normalize to all zeros"
