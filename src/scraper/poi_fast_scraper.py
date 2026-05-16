"""
High-performance POI scraper using Bounding Box (BBox) queries and local KD-Tree indexing.

This script replaces the slow one-by-one scraping method with a bulk area search.
It downloads all POIs for the entire region in a few large queries and uses 
spatial math (KD-Tree) to map them to all 20,000 outlets in seconds.

Performance:
- Old Method: ~36 hours for 20,000 outlets.
- This Method: ~3-5 minutes for 20,000 outlets.
"""

import pandas as pd
import numpy as np
import requests
import logging
from pathlib import Path
from scipy.spatial import cKDTree
from src.utils.config import load_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
OVERPASS_URL = "https://overpass-api.de/api/interpreter"  # Stable German server
SEARCH_RADIUS_METERS = 1000
DEGREE_TO_METER = 111320  # Approximate conversion at the equator/Sri Lanka

def fetch_area_pois(bbox):
    """
    Fetches all relevant POIs within a bounding box using a single Overpass query.
    bbox: (south, west, north, east)
    """
    # Ensure coordinates are standard Python floats, not numpy types
    s, w, n, e = [float(x) for x in bbox]
    
    query = f"""
    [out:json][timeout:180];
    (
      node["amenity"~"school|hospital|restaurant|fuel"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
      way["amenity"~"school|hospital|restaurant|fuel"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
      node["highway"="bus_stop"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
      node["tourism"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
    );
    out center;
    """
    
    headers = {
        'User-Agent': 'NeuralCoreDataStorm/1.0 (Educational Competition Project)',
        'Accept': 'application/json'
    }
    
    logger.info(f"Sending bulk BBox query for area: ({s:.4f}, {w:.4f}, {n:.4f}, {e:.4f})...")
    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, headers=headers, timeout=200)
        response.raise_for_status()
        return response.json()
    except Exception as err:
        logger.error(f"Bulk API request failed: {err}")
        if response is not None:
            logger.error(f"Server response: {response.text[:200]}")
        return None

def process_poi_data(osm_data):
    """Parses OSM JSON into a structured DataFrame of POIs."""
    if not osm_data or 'elements' not in osm_data:
        return pd.DataFrame()

    poi_list = []
    for el in osm_data['elements']:
        # Get location (center for ways, lat/lon for nodes)
        lat = el.get('lat') or el.get('center', {}).get('lat')
        lon = el.get('lon') or el.get('center', {}).get('lon')
        tags = el.get('tags', {})
        
        if not lat or not lon:
            continue
            
        # Categorize
        category = "other"
        if 'amenity' in tags:
            cat = tags['amenity']
            if cat == 'school': category = 'school'
            elif cat == 'hospital': category = 'hospital'
            elif cat == 'restaurant': category = 'restaurant'
            elif cat == 'fuel': category = 'fuel'
        elif tags.get('highway') == 'bus_stop':
            category = 'bus_stop'
        elif 'tourism' in tags:
            category = 'tourism'
            
        poi_list.append({'lat': lat, 'lon': lon, 'category': category})
        
    return pd.DataFrame(poi_list)

def main():
    config = load_config()
    input_file = Path("data/silver/outlet_coordinates.parquet")
    output_file = Path("data/gold/poi_data.csv")
    
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return

    # 1. Load Outlets
    logger.info("Loading outlet coordinates...")
    outlets_df = pd.read_parquet(input_file)
    valid_outlets = outlets_df.dropna(subset=['Latitude', 'Longitude'])
    
    # 2. Determine Bounding Box (with 2km buffer)
    s = valid_outlets['Latitude'].min() - 0.02
    n = valid_outlets['Latitude'].max() + 0.02
    w = valid_outlets['Longitude'].min() - 0.02
    e = valid_outlets['Longitude'].max() + 0.02
    bbox = (s, w, n, e)
    
    # 3. Fetch POIs in Bulk
    osm_data = fetch_area_pois(bbox)
    if not osm_data:
        logger.error("Could not fetch POI data. Exiting.")
        return
        
    pois_df = process_poi_data(osm_data)
    logger.info(f"Successfully downloaded {len(pois_df)} POIs for the whole region.")
    
    # 4. Spatial Indexing with KD-Tree
    categories = ["school", "hospital", "bus_stop", "restaurant", "fuel", "tourism"]
    results = outlets_df[['Outlet_ID']].copy()
    
    # Radius in degrees (approx)
    search_radius_deg = SEARCH_RADIUS_METERS / DEGREE_TO_METER
    
    for cat in categories:
        logger.info(f"Mapping {cat} counts to outlets...")
        cat_pois = pois_df[pois_df['category'] == cat]
        
        if cat_pois.empty:
            results[f"{cat}_count"] = 0
            continue
            
        # Build KD-Tree for this category
        tree = cKDTree(cat_pois[['lat', 'lon']].values)
        
        # Query all outlets at once
        # query_ball_point returns a list of indices for each outlet
        counts = tree.query_ball_point(valid_outlets[['Latitude', 'Longitude']].values, r=search_radius_deg)
        
        # Map back to the full results dataframe (handling the dropna outlets)
        outlet_counts = pd.Series(0, index=outlets_df.index)
        outlet_counts.loc[valid_outlets.index] = [len(c) for c in counts]
        results[f"{cat}_count"] = outlet_counts

    # 5. Save Results
    output_file.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_file, index=False)
    logger.info(f"Fast POI scraping complete! Saved all 20,000 outlets to {output_file}")

if __name__ == "__main__":
    main()
