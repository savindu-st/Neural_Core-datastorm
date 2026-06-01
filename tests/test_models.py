"""
Unit tests for src/models/censored_regression.py and src/models/predict.py.

All tests use synthetic in-memory data — no file I/O required.
Run with: pytest tests/test_models.py -v
"""

import numpy as np
import pandas as pd
import pytest
from src.models.censored_regression import TobitModel
from src.models.predict import calculate_confidence_score, segment_outlets


# ────────────────────────────────────────────────────────────────────
# TobitModel Tests
# ────────────────────────────────────────────────────────────────────

class TestTobitModel:
    """Tests for the custom Tobit (Censored) Regression model."""

    def _make_data(self, n=200, seed=42):
        """Generate simple synthetic censored data."""
        rng = np.random.default_rng(seed)
        X = rng.standard_normal((n, 3))
        y_star = X @ np.array([2.0, -1.0, 0.5]) + 5.0 + rng.standard_normal(n)
        # Censor at 75th percentile
        threshold = np.percentile(y_star, 75)
        y = np.minimum(y_star, threshold)
        censored = y >= threshold
        return X, y, censored

    def test_fit_sets_beta_and_sigma(self):
        """After fit(), beta and sigma must be non-None."""
        X, y, censored = self._make_data()
        model = TobitModel()
        model.fit(X, y, censored)
        assert model.beta is not None, "beta should be set after fit()"
        assert model.sigma is not None, "sigma should be set after fit()"

    def test_beta_length_matches_features_plus_intercept(self):
        """beta should have length n_features + 1 (intercept)."""
        X, y, censored = self._make_data()
        model = TobitModel()
        model.fit(X, y, censored)
        assert len(model.beta) == X.shape[1] + 1

    def test_sigma_is_positive(self):
        """sigma must always be strictly positive."""
        X, y, censored = self._make_data()
        model = TobitModel()
        model.fit(X, y, censored)
        assert model.sigma > 0, f"sigma={model.sigma} should be > 0"

    def test_predict_mean_shape(self):
        """predict(method='mean') should return array of shape (n_samples,)."""
        X, y, censored = self._make_data()
        model = TobitModel().fit(X, y, censored)
        preds = model.predict(X, method='mean')
        assert preds.shape == (len(X),)

    def test_predict_quantile_exceeds_mean(self):
        """90th-percentile predictions should be >= mean predictions on average."""
        X, y, censored = self._make_data()
        model = TobitModel().fit(X, y, censored)
        mean_preds = model.predict(X, method='mean')
        q90_preds = model.predict(X, method='quantile', quantile=0.90)
        assert np.mean(q90_preds) > np.mean(mean_preds), (
            "Quantile predictions should exceed mean predictions"
        )

    def test_predict_quantile_uncaps_censored_rows(self):
        """Latent potential should exceed observed for censored rows on average."""
        X, y, censored = self._make_data()
        model = TobitModel().fit(X, y, censored)
        preds = model.predict(X, method='quantile', quantile=0.90)
        # For censored rows, the model should estimate higher-than-observed demand
        avg_potential_censored = preds[censored].mean()
        avg_observed_censored = y[censored].mean()
        assert avg_potential_censored >= avg_observed_censored, (
            "Model should predict >= observed for censored (supply-capped) outlets"
        )

    def test_predict_configurable_quantile(self):
        """Higher quantile parameter should produce higher predictions."""
        X, y, censored = self._make_data()
        model = TobitModel().fit(X, y, censored)
        p50 = model.predict(X, method='quantile', quantile=0.50)
        p90 = model.predict(X, method='quantile', quantile=0.90)
        p99 = model.predict(X, method='quantile', quantile=0.99)
        assert np.mean(p50) < np.mean(p90) < np.mean(p99), (
            "Higher quantile should produce higher predictions"
        )

    def test_unknown_method_falls_back_to_mean(self):
        """predict() with unknown method string should return latent mean."""
        X, y, censored = self._make_data()
        model = TobitModel().fit(X, y, censored)
        preds_default = model.predict(X, method='unknown_method')
        preds_mean = model.predict(X, method='mean')
        np.testing.assert_array_almost_equal(preds_default, preds_mean)


# ────────────────────────────────────────────────────────────────────
# calculate_confidence_score Tests
# ────────────────────────────────────────────────────────────────────

class TestConfidenceScore:
    """Tests for the BI confidence scoring function in predict.py."""

    def _make_df(self, inactive=0, sales_std=10.0, avg_sales=100.0, poi_score=5.0, n=10):
        return pd.DataFrame({
            'inactive_days': [inactive] * n,
            'sales_std': [sales_std] * n,
            'monthly_avg_sales': [avg_sales] * n,
            'poi_score': [poi_score] * n,
        })

    def test_score_is_in_range_0_to_100(self):
        """Confidence score must be between 0 and 100."""
        df = self._make_df()
        scores = calculate_confidence_score(df)
        assert (scores >= 0).all() and (scores <= 100).all(), (
            "Confidence scores must be in [0, 100]"
        )

    def test_lower_inactivity_gives_higher_score(self):
        """An active outlet (inactive_days=0) should score higher than a dormant one."""
        df_active = self._make_df(inactive=0)
        df_dormant = self._make_df(inactive=200)
        assert calculate_confidence_score(df_active).mean() > calculate_confidence_score(df_dormant).mean()

    def test_higher_poi_increases_score(self):
        """Higher POI score should result in higher confidence."""
        df_low = self._make_df(poi_score=0.0)
        df_high = self._make_df(poi_score=20.0)
        assert calculate_confidence_score(df_high).mean() > calculate_confidence_score(df_low).mean()


# ────────────────────────────────────────────────────────────────────
# segment_outlets Tests
# ────────────────────────────────────────────────────────────────────

class TestSegmentOutlets:
    """Tests for the vectorized segment_outlets() in predict.py."""

    def _base_df(self, n=5) -> pd.DataFrame:
        return pd.DataFrame({
            'poi_score': [0.0] * n,
            'growth_rate': [0.0] * n,
            'market_saturation_index': [5.0] * n,
            'monthly_avg_sales': [100.0] * n,
            'inactive_days': [0] * n,
        })

    def test_returns_three_series(self):
        """segment_outlets should return exactly 3 Series."""
        df = self._base_df()
        result = segment_outlets(df)
        assert len(result) == 3, "Should return (segments, recommendations, risk_flags)"
        for s in result:
            assert isinstance(s, pd.Series)

    def test_high_potential_segment(self):
        """Outlet with high POI and growth_rate > 0.1 should be 'High Potential Growth'."""
        df = self._base_df(n=1)
        df['poi_score'] = 15.0
        df['growth_rate'] = 0.2
        segs, recs, risks = segment_outlets(df)
        assert segs.iloc[0] == "High Potential Growth"
        assert risks.iloc[0] == "Low"

    def test_dormant_segment(self):
        """Outlet with inactive_days > 60 should be 'At-Risk / Dormant'."""
        df = self._base_df(n=1)
        df['inactive_days'] = 90
        segs, _, risks = segment_outlets(df)
        assert segs.iloc[0] == "At-Risk / Dormant"
        assert risks.iloc[0] == "High"

    def test_stable_core_is_default(self):
        """Outlet matching no special condition should be 'Stable Core Retailer'."""
        df = self._base_df(n=1)
        segs, recs, risks = segment_outlets(df)
        assert segs.iloc[0] == "Stable Core Retailer"
        assert risks.iloc[0] == "Low"

    def test_output_length_matches_input(self):
        """Output Series length must equal the number of rows in input df."""
        df = self._base_df(n=50)
        segs, recs, risks = segment_outlets(df)
        for s in (segs, recs, risks):
            assert len(s) == 50
