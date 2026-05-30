"""
Spatial feature engineering and integration.

Normalizes continuous POI decay scores and competitor saturation metrics to 
synthesize a composite Spatial Opportunity Score at the outlet level.
Supports both:
  - lat/lon based distance_decay_features.csv (from distance_decay.py)
  - count-based poi_data.csv fallback (weighted counts as proxy decay scores)
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from src.utils.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# POI category weights for proxy decay score (reflects human footfall relevance)
POI_WEIGHTS = {
    'restaurant_count': 3.0,
    'bus_stop_count':   2.5,
    'school_count':     2.0,
    'hospital_count':   1.5,
    'fuel_count':       1.0,
    'tourism_count':    1.0,
}


def _build_from_decay_features(decay_file, comp_file):
    """Uses pre-computed distance_decay_features.csv and competitor_density_features.csv."""
    logger.info("Using distance-decay feature files (lat/lon mode)...")
    df_decay = pd.read_csv(decay_file)
    df_comp  = pd.read_csv(comp_file)
    spatial_df = df_decay.merge(df_comp, on="Outlet_ID", how="inner")
    poi_col = "total_poi_decay_score"
    if poi_col in spatial_df.columns:
        p_min, p_max = spatial_df[poi_col].min(), spatial_df[poi_col].max()
        spatial_df["normalized_poi_score"] = (spatial_df[poi_col] - p_min) / (p_max - p_min + 1e-6)
    else:
        spatial_df["normalized_poi_score"] = 0.0
    sat_col = "market_saturation_index"
    if sat_col in spatial_df.columns:
        s_min, s_max = spatial_df[sat_col].min(), spatial_df[sat_col].max()
        spatial_df["normalized_saturation"] = (spatial_df[sat_col] - s_min) / (s_max - s_min + 1e-6)
    else:
        spatial_df["normalized_saturation"] = 0.0
    spatial_df["spatial_opportunity_score"] = (
        (spatial_df["normalized_poi_score"] * 0.6) +
        ((1.0 - spatial_df["normalized_saturation"]) * 0.4)
    ) * 100.0
    return spatial_df


def _build_from_count_based(poi_file, comp_file):
    """Fallback: derives proxy decay scores from per-outlet POI counts."""
    logger.info("Using count-based poi_data.csv as proxy for distance-decay scores...")
    df_poi = pd.read_csv(poi_file)
    proxy_score = pd.Series(0.0, index=df_poi.index)
    for col, weight in POI_WEIGHTS.items():
        if col in df_poi.columns:
            proxy_score += df_poi[col].fillna(0) * weight
    df_poi["total_poi_decay_score"]     = proxy_score
    df_poi["bus_stop_decay_score"]      = df_poi.get("bus_stop_count",   pd.Series(0, index=df_poi.index)).fillna(0) * 2.5
    df_poi["school_decay_score"]        = df_poi.get("school_count",     pd.Series(0, index=df_poi.index)).fillna(0) * 2.0
    df_poi["hospital_decay_score"]      = df_poi.get("hospital_count",   pd.Series(0, index=df_poi.index)).fillna(0) * 1.5
    df_poi["restaurant_decay_score"]    = df_poi.get("restaurant_count", pd.Series(0, index=df_poi.index)).fillna(0) * 3.0
    df_poi["fuel_station_decay_score"]  = df_poi.get("fuel_count",       pd.Series(0, index=df_poi.index)).fillna(0) * 1.0
    df_poi["tourist_place_decay_score"] = df_poi.get("tourism_count",    pd.Series(0, index=df_poi.index)).fillna(0) * 1.0
    df_poi["competitor_decay_score"]    = 0.0
    df_poi["market_saturation_index"]   = 0.0
    if comp_file.exists():
        df_comp = pd.read_csv(comp_file)
        logger.info(f"Loaded {len(df_comp)} competitor POIs (global saturation reference only).")
    p_min = df_poi["total_poi_decay_score"].min()
    p_max = df_poi["total_poi_decay_score"].max()
    df_poi["normalized_poi_score"]      = (df_poi["total_poi_decay_score"] - p_min) / (p_max - p_min + 1e-6)
    df_poi["normalized_saturation"]     = 0.0
    df_poi["spatial_opportunity_score"] = (
        (df_poi["normalized_poi_score"] * 0.6) + 0.4
    ) * 100.0
    return df_poi


def calculate_spatial_features():
    logger.info("Starting Spatial Feature Engineering...")
    config = load_config()
    gold_path   = Path(config["data"]["gold_path"])
    gold_path.mkdir(parents=True, exist_ok=True)
    decay_file  = gold_path / "distance_decay_features.csv"
    comp_file   = gold_path / "competitor_density_features.csv"
    poi_file    = gold_path / "poi_data.csv"
    output_file = gold_path / "spatial_features.csv"
    if decay_file.exists() and comp_file.exists():
        spatial_df = _build_from_decay_features(decay_file, comp_file)
    elif poi_file.exists():
        logger.warning("distance_decay_features.csv not found - falling back to count-based proxy mode.")
        spatial_df = _build_from_count_based(poi_file, comp_file)
    else:
        raise FileNotFoundError("No usable POI data found. Run poi_fast_scraper.py first.")
    keep = [
        "Outlet_ID",
        "bus_stop_decay_score", "school_decay_score", "hospital_decay_score",
        "restaurant_decay_score", "fuel_station_decay_score", "tourist_place_decay_score",
        "total_poi_decay_score", "competitor_decay_score",
        "market_saturation_index", "spatial_opportunity_score",
    ]
    save_cols = [c for c in keep if c in spatial_df.columns]
    final_df   = spatial_df[save_cols].copy()
    final_df.to_csv(output_file, index=False)
    logger.info(f"Spatial features saved to: {output_file} ({len(final_df)} rows)")


if __name__ == "__main__":
    calculate_spatial_features()
