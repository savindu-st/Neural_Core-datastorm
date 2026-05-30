"""
Advanced Spatial Distance-Decay Feature Generator.

Estimates the continuous spatial influence of geographic POIs on outlets 
using continuous exponential decay functions: decay_score = sum( exp(-d / factor) ).
Saves output features to data/gold/distance_decay_features.csv.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from scipy.spatial import cKDTree
from src.utils.config import load_config
from src.spatial.distance_utils import haversine_distance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEGREE_TO_METER = 111320.0
MAX_SEARCH_RADIUS_METERS = 5000.0  # Max distance to include a POI in decay sum

# Category configuration: (scraped_category_name, feature_prefix, decay_factor_meters)
CATEGORY_CONFIGS = [
    ("bus_stop", "bus_stop", 400.0),
    ("school", "school", 1000.0),
    ("hospital", "hospital", 2000.0),
    ("restaurant", "restaurant", 800.0),
    ("fuel_station", "fuel_station", 1500.0),
    ("tourist_attraction", "tourist_place", 2000.0)
]

def main():
    logger.info("Starting Distance-Decay Feature Generation...")
    config = load_config()
    
    silver_path = Path(config["data"]["silver_path"])
    gold_path = Path(config["data"]["gold_path"])
    
    master_file = silver_path / "clean_outlet_master.csv"
    poi_file = gold_path / "poi_data.csv"
    output_file = gold_path / "distance_decay_features.csv"
    
    if not master_file.exists() or not poi_file.exists():
        logger.error("Required clean datasets (clean_outlet_master.csv or poi_data.csv) are missing.")
        raise FileNotFoundError("Missing master or POI data for spatial calculations.")
        
    df_outlets = pd.read_csv(master_file)
    df_pois = pd.read_csv(poi_file)
    
    logger.info(f"Loaded {len(df_outlets)} outlets and {len(df_pois)} geographic POIs.")
    
    # Isolate valid coordinates
    valid_outlets = df_outlets.dropna(subset=["Latitude", "Longitude"])
    outlet_coords = valid_outlets[["Latitude", "Longitude"]].values
    
    # Result container
    features = pd.DataFrame(index=df_outlets.index)
    features["Outlet_ID"] = df_outlets["Outlet_ID"]
    
    # Calculate degree query radius
    search_radius_deg = MAX_SEARCH_RADIUS_METERS / DEGREE_TO_METER
    
    # Initialize total score accumulator
    total_decay_score = pd.Series(0.0, index=df_outlets.index)
    
    # Generate features category by category
    for cat_name, feat_prefix, decay_factor in CATEGORY_CONFIGS:
        logger.info(f"Generating features for category: {cat_name} (decay factor: {decay_factor}m)...")
        cat_pois = df_pois[df_pois["category"] == cat_name]
        
        # Initialize default values
        decay_scores = pd.Series(0.0, index=df_outlets.index)
        nearest_dists = pd.Series(np.nan, index=df_outlets.index)
        
        if not cat_pois.empty:
            poi_coords = cat_pois[["lat", "lon"]].values
            
            # 1. Build KD-Tree for this category
            tree = cKDTree(poi_coords)
            
            # 2. Query tree for neighbors within max bounding box degrees
            indices_list = tree.query_ball_point(outlet_coords, r=search_radius_deg)
            
            # 3. Calculate vectorized Haversine distance and exponential decay for each outlet
            outlet_decay = np.zeros(len(valid_outlets))
            outlet_nearest = np.full(len(valid_outlets), np.nan)
            
            for idx, neighbors in enumerate(indices_list):
                if not neighbors:
                    continue
                    
                matched_pois = poi_coords[neighbors]
                # Calculate exact Haversine distances in meters
                dists = haversine_distance(
                    outlet_coords[idx, 0], outlet_coords[idx, 1],
                    matched_pois[:, 0], matched_pois[:, 1]
                )
                
                # Filter by max radius limit
                valid_dists = dists[dists <= MAX_SEARCH_RADIUS_METERS]
                if len(valid_dists) > 0:
                    # Exponential decay score sum
                    decay_terms = np.exp(-valid_dists / decay_factor)
                    outlet_decay[idx] = np.sum(decay_terms)
                    outlet_nearest[idx] = np.min(valid_dists)
            
            decay_scores.loc[valid_outlets.index] = outlet_decay
            nearest_dists.loc[valid_outlets.index] = outlet_nearest
            
        features[f"{feat_prefix}_decay_score"] = decay_scores
        
        # Accumulate total score
        total_decay_score += decay_scores
        
        # Save nearest distance feature for specific categories required by prompt
        if feat_prefix in ["bus_stop", "school", "restaurant"]:
            features[f"nearest_{feat_prefix}_distance"] = nearest_dists
            
    features["total_poi_decay_score"] = total_decay_score
    
    # Save output to Gold
    gold_path.mkdir(parents=True, exist_ok=True)
    features.to_csv(output_file, index=False)
    logger.info(f"Distance-Decay features generated successfully! Output saved to: {output_file}")

if __name__ == "__main__":
    main()
