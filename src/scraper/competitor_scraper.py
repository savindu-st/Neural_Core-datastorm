"""
Competitor Location Scraper.

Extracts retail competitor outlets (shops, convenience stores, groceries, supermarkets, 
pharmacies, and eateries) from OpenStreetMap (OSM) for competitor catchment analysis.
Saves the clean list of competitor POIs to data/gold/competitor_poi_data.csv.
"""

import pandas as pd
import logging
from pathlib import Path
from src.utils.config import load_config
from src.scraper.overpass_client import OverpassClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Category mapper for competitors
def get_competitor_category(tags: dict) -> str:
    # 1. Shops / Retail
    if 'shop' in tags:
        shop = tags['shop']
        if shop == 'convenience': return 'convenience_store'
        elif shop == 'supermarket': return 'supermarket'
        elif shop in ['grocery', 'general']: return 'grocery'
        elif shop in ['pharmacy', 'chemist']: return 'pharmacy'
        elif shop in ['mall', 'department_store']: return 'supermarket'
        else: return 'retail_shop'
        
    # 2. Amenities (Eateries)
    if 'amenity' in tags:
        amenity = tags['amenity']
        if amenity in ['restaurant', 'cafe', 'fast_food', 'food_court']:
            return 'eatery'
        elif amenity == 'pharmacy':
            return 'pharmacy'
            
    return ''

def main():
    logger.info("Starting Competitor Scraper Pipeline...")
    config = load_config()
    
    input_file = Path(config["data"]["silver_path"]) / "clean_outlet_master.csv"
    output_file = Path(config["data"]["gold_path"]) / "competitor_poi_data.csv"
    
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
    
    # Fetch shops and eateries
    amenities = "restaurant|cafe|fast_food|pharmacy"
    extra_queries = """
      node["shop"~"convenience|supermarket|grocery|general|pharmacy|retail"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
      way["shop"~"convenience|supermarket|grocery|general|pharmacy|retail"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
    """
    
    # Run fetch
    raw_data = client.fetch_pois(bbox, amenities, extra_queries)
    if not raw_data:
        logger.error("Failed to query competitors from OSM.")
        return
        
    # Parse into competitor DataFrame
    df_comps = client.parse_osm_response(raw_data, get_competitor_category)
    logger.info(f"Successfully scraped {len(df_comps)} competitor POIs.")
    
    # Save the list of competitors in Gold Layer
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_comps.to_csv(output_file, index=False)
    logger.info(f"Competitor data successfully written to: {output_file}")

if __name__ == "__main__":
    main()
