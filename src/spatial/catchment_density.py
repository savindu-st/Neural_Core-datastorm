"""
Competitor Catchment Density & Saturation Feature Generator.

Quantifies the intensity of competition in each outlet's local market area.
Generates multi-radii counts, competitor distance-decay scores, the normalized 
Market Saturation Index (MSI), and categorical Competition Levels.
Saves outputs to data/gold/competitor_density_features.csv.
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
COMPETITOR_DECAY_FACTOR = 500.0  # meters (represents typical local retail footprint)
MAX_SEARCH_RADIUS_METERS = 3000.0  # max search distance

def main():
    logger.info("Starting Competitor Catchment Density Generation...")
    config = load_config()
    
    silver_path = Path(config["data"]["silver_path"])
    gold_path = Path(config["data"]["gold_path"])
    
    master_file = silver_path / "clean_outlet_master.csv"
    comp_file = gold_path / "competitor_poi_data.csv"
    output_file = gold_path / "competitor_density_features.csv"
    
    if not master_file.exists() or not comp_file.exists():
        logger.error("Required clean datasets (clean_outlet_master.csv or competitor_poi_data.csv) are missing.")
        raise FileNotFoundError("Missing master or competitor POI data for spatial calculations.")
        
    df_outlets = pd.read_csv(master_file)
    df_comps = pd.read_csv(comp_file)
    
    logger.info(f"Loaded {len(df_outlets)} outlets and {len(df_comps)} competitor POIs.")
    
    # Isolate valid coordinates
    valid_outlets = df_outlets.dropna(subset=["Latitude", "Longitude"])
    outlet_coords = valid_outlets[["Latitude", "Longitude"]].values
    
    # Result container
    features = pd.DataFrame(index=df_outlets.index)
    features["Outlet_ID"] = df_outlets["Outlet_ID"]
    
    # Initialize defaults
    comp_250 = pd.Series(0, index=df_outlets.index)
    comp_500 = pd.Series(0, index=df_outlets.index)
    comp_1000 = pd.Series(0, index=df_outlets.index)
    comp_decay = pd.Series(0.0, index=df_outlets.index)
    
    if not df_comps.empty:
        comp_coords = df_comps[["lat", "lon"]].values
        
        # 1. Build KD-Tree for competitors
        tree = cKDTree(comp_coords)
        
        # 2. Query neighbors within max search bounding box degrees
        search_radius_deg = MAX_SEARCH_RADIUS_METERS / DEGREE_TO_METER
        indices_list = tree.query_ball_point(outlet_coords, r=search_radius_deg)
        
        # Arrays for valid records
        out_250 = np.zeros(len(valid_outlets), dtype=int)
        out_500 = np.zeros(len(valid_outlets), dtype=int)
        out_1000 = np.zeros(len(valid_outlets), dtype=int)
        out_decay = np.zeros(len(valid_outlets))
        
        # 3. Calculate distance metrics for each outlet
        for idx, neighbors in enumerate(indices_list):
            if not neighbors:
                continue
                
            matched_comps = comp_coords[neighbors]
            dists = haversine_distance(
                outlet_coords[idx, 0], outlet_coords[idx, 1],
                matched_comps[:, 0], matched_comps[:, 1]
            )
            
            # Counts at various radii
            out_250[idx] = np.sum(dists <= 250.0)
            out_500[idx] = np.sum(dists <= 500.0)
            out_1000[idx] = np.sum(dists <= 1000.0)
            
            # Competitor exponential decay score
            valid_dists = dists[dists <= MAX_SEARCH_RADIUS_METERS]
            if len(valid_dists) > 0:
                out_decay[idx] = np.sum(np.exp(-valid_dists / COMPETITOR_DECAY_FACTOR))
                
        comp_250.loc[valid_outlets.index] = out_250
        comp_500.loc[valid_outlets.index] = out_500
        comp_1000.loc[valid_outlets.index] = out_1000
        comp_decay.loc[valid_outlets.index] = out_decay
        
    features["competitor_count_250m"] = comp_250
    features["competitor_count_500m"] = comp_500
    features["competitor_count_1000m"] = comp_1000
    features["competitor_decay_score"] = comp_decay
    
    # 4. Market Saturation Index (MSI) - comparing to median competitor decay score (Wow Factor)
    median_decay = comp_decay.loc[valid_outlets.index].median()
    if median_decay > 0:
        msi_scores = (comp_decay / median_decay) * 50.0
    else:
        # Fallback to mean or default in case median is zero
        mean_decay = comp_decay.loc[valid_outlets.index].mean()
        msi_scores = (comp_decay / mean_decay) * 50.0 if mean_decay > 0 else comp_decay * 50.0
        
    # Cap MSI score at 100
    msi_scores = msi_scores.clip(upper=100.0)
    features["market_saturation_index"] = msi_scores
    
    # 5. Competition Level Classification
    comp_levels = pd.Series("Low Competition", index=df_outlets.index)
    
    # Define thresholds:
    # Low: MSI < 25.0
    # High: MSI >= 75.0
    # Medium: 25.0 <= MSI < 75.0
    comp_levels.loc[msi_scores >= 25.0] = "Medium Competition"
    comp_levels.loc[msi_scores >= 75.0] = "High Competition"
    
    features["competition_level"] = comp_levels
    
    # Write to Gold
    gold_path.mkdir(parents=True, exist_ok=True)
    features.to_csv(output_file, index=False)
    logger.info(f"Competitor density features successfully written to: {output_file}")
    logger.info(f"Competition level distribution:\n{features['competition_level'].value_counts()}")

if __name__ == "__main__":
    main()
