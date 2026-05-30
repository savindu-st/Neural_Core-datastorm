"""
High-performance POI scraper using OverpassClient.

Extracts all relevant geographic POIs (bus stops, schools, hospitals, fuel stations, 
restaurants, and tourist attractions) for the outlet region in bulk.
Saves the clean list of POIs to data/gold/poi_data.csv.
"""

import pandas as pd
import logging
from pathlib import Path
from src.utils.config import load_config
from src.scraper.overpass_client import OverpassClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Category mapper for Overpass tags
def get_poi_category(tags: dict) -> str:
    if 'amenity' in tags:
        cat = tags['amenity']
        if cat == 'school': return 'school'
        elif cat == 'hospital': return 'hospital'
        elif cat == 'restaurant': return 'restaurant'
        elif cat == 'fuel': return 'fuel_station'
    if tags.get('highway') == 'bus_stop':
        return 'bus_stop'
    if 'tourism' in tags:
        return 'tourist_attraction'
    return ''

def main():
    logger.info("Starting POI Scraper Pipeline...")
    config = load_config()
    
    input_file = Path(config["data"]["silver_path"]) / "clean_outlet_master.csv"
    output_file = Path(config["data"]["gold_path"]) / "poi_data.csv"
    
    if not input_file.exists():
        logger.error(f"Silver cleaned master dataset not found: {input_file}")
        raise FileNotFoundError(f"Missing master dataset: {input_file}")
        
    df_outlets = pd.read_csv(input_file)
    
    # Drop rows without valid coordinates for bbox calculation
    valid_coords = df_outlets.dropna(subset=["Latitude", "Longitude"])
    if len(valid_coords) == 0:
        logger.error("No valid outlet coordinates found for scraping.")
        return
        
    # Calculate bounding box (with 2km padding)
    lat_min = valid_coords["Latitude"].min() - 0.02
    lat_max = valid_coords["Latitude"].max() + 0.02
    lon_min = valid_coords["Longitude"].min() - 0.02
    lon_max = valid_coords["Longitude"].max() + 0.02
    bbox = (lat_min, lon_min, lat_max, lon_max)
    
    logger.info(f"Calculated Bounding Box: {bbox}")
    
    client = OverpassClient()
    
    # Fetch amenities and extra queries
    amenities = "school|hospital|restaurant|fuel"
    extra_queries = """
      node["highway"="bus_stop"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
      node["tourism"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
    """
    
    # Run fetch
    raw_data = client.fetch_pois(bbox, amenities, extra_queries)
    if not raw_data:
        logger.error("Failed to query POIs from OSM.")
        return
        
    # Parse POIs into DataFrame
    df_pois = client.parse_osm_response(raw_data, get_poi_category)
    logger.info(f"Successfully scraped {len(df_pois)} POIs for category lists.")
    
    # Save the list of POIs in Gold Layer
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_pois.to_csv(output_file, index=False)
    logger.info(f"POI data successfully written to: {output_file}")

if __name__ == "__main__":
    main()
