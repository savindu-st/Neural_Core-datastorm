import os
import time
import logging
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"
RADIUS = 1000  # meters
INPUT_FILE = "data/silver/outlet_master_cleaned.csv"
OUTPUT_FILE = "data/gold/poi_data.csv"

def create_requests_session():
    """
    Creates a requests session with retry logic and standard User-Agent.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    })
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_overpass_query(lat, lon, radius):
    """
    Constructs a compact Overpass QL query.
    """
    return f'[out:json][timeout:25];(node["amenity"~"school|hospital|restaurant|fuel"](around:{radius},{lat},{lon});way["amenity"~"school|hospital|restaurant|fuel"](around:{radius},{lat},{lon});node["highway"="bus_stop"](around:{radius},{lat},{lon});node["tourism"](around:{radius},{lat},{lon});way["tourism"](around:{radius},{lat},{lon}););out tags;'

def fetch_poi_counts(session, lat, lon, radius=RADIUS):
    """
    Fetches POI data from Overpass API and returns counts for specific categories.
    """
    query = get_overpass_query(lat, lon, radius)
    counts = {
        "school_count": 0,
        "hospital_count": 0,
        "bus_stop_count": 0,
        "restaurant_count": 0,
        "fuel_count": 0,
        "tourism_count": 0
    }

    try:
        response = session.post(OVERPASS_URL, data={'data': query}, timeout=30)
        response.raise_for_status()
        data = response.json()

        for element in data.get('elements', []):
            tags = element.get('tags', {})
            
            # Amenity based counts
            amenity = tags.get('amenity')
            if amenity == 'school':
                counts['school_count'] += 1
            elif amenity == 'hospital':
                counts['hospital_count'] += 1
            elif amenity == 'restaurant':
                counts['restaurant_count'] += 1
            elif amenity == 'fuel':
                counts['fuel_count'] += 1
            
            # Highway based counts
            if tags.get('highway') == 'bus_stop':
                counts['bus_stop_count'] += 1
            
            # Tourism based counts
            if 'tourism' in tags:
                counts['tourism_count'] += 1

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for location ({lat}, {lon}): {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing location ({lat}, {lon}): {e}")

    return counts

def main():
    """
    Main execution flow for POI scraping.
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}. Please ensure it exists in the silver layer.")
        return

    try:
        # Load input data
        logger.info(f"Loading input data from {INPUT_FILE}...")
        df = pd.read_csv(INPUT_FILE)

        # Validate columns
        required_cols = ['Outlet_ID', 'Latitude', 'Longitude']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"Input CSV must contain columns: {required_cols}")
            return

        session = create_requests_session()
        results = []

        logger.info(f"Starting POI scraping for {len(df)} locations...")

        for index, row in df.iterrows():
            outlet_id = row['Outlet_ID']
            lat = row['Latitude']
            lon = row['Longitude']

            # Basic coordinate validation
            if pd.isna(lat) or pd.isna(lon):
                logger.warning(f"Skipping Outlet {outlet_id} due to missing coordinates.")
                results.append({"Outlet_ID": outlet_id, "school_count": 0, "hospital_count": 0, 
                                "bus_stop_count": 0, "restaurant_count": 0, "fuel_count": 0, "tourism_count": 0})
                continue

            logger.info(f"[{index+1}/{len(df)}] Fetching POIs for Outlet {outlet_id}...")
            
            # Fetch counts
            poi_counts = fetch_poi_counts(session, lat, lon)
            
            # Combine ID with results
            row_data = {"Outlet_ID": outlet_id}
            row_data.update(poi_counts)
            results.append(row_data)

            # Rate limiting: Respect Overpass API and avoid IP blocks
            time.sleep(1)

        # Create results DataFrame and save to Gold layer
        results_df = pd.DataFrame(results)
        results_df.to_csv(OUTPUT_FILE, index=False)
        logger.info(f"POI data successfully aggregated and saved to {OUTPUT_FILE}")

    except Exception as e:
        logger.error(f"Critical failure in main execution loop: {e}")

if __name__ == "__main__":
    main()
