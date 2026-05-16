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
INPUT_FILE = "data/silver/outlet_coordinates.parquet"
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
    # Retry logic for network blips and rate limits
    retry = Retry(
        total=5,
        backoff_factor=2,  # Exponential backoff
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_overpass_query(lat, lon, radius):
    """
    Constructs a compact Overpass QL query for specific POIs.
    """
    return (
        f'[out:json][timeout:30];('
        f'node["amenity"~"school|hospital|restaurant|fuel"](around:{radius},{lat},{lon});'
        f'way["amenity"~"school|hospital|restaurant|fuel"](around:{radius},{lat},{lon});'
        f'node["highway"="bus_stop"](around:{radius},{lat},{lon});'
        f'node["tourism"](around:{radius},{lat},{lon});'
        f'way["tourism"](around:{radius},{lat},{lon});'
        f');out tags;'
    )

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
        # Using a slightly longer timeout to handle slow Overpass responses
        response = session.post(OVERPASS_URL, data={'data': query}, timeout=45)
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
    Main execution flow for POI scraping with checkpointing and progressive saving.
    """
    # 1. Setup paths and directories
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}")
        return

    # 2. Checkpointing: Identify already processed outlets
    processed_ids = set()
    file_exists = os.path.exists(OUTPUT_FILE)
    
    if file_exists:
        try:
            existing_df = pd.read_csv(OUTPUT_FILE, usecols=['Outlet_ID'])
            processed_ids = set(existing_df['Outlet_ID'].astype(str).unique())
            logger.info(f"Checkpoint found: {len(processed_ids)} outlets already processed.")
        except Exception as e:
            logger.warning(f"Could not read existing checkpoint file: {e}. Starting fresh.")
            file_exists = False

    # 3. Load input data
    try:
        logger.info(f"Loading input data from {INPUT_FILE}...")
        full_df = pd.read_parquet(INPUT_FILE)
        
        # Filter out already processed outlets
        df_to_process = full_df[~full_df['Outlet_ID'].astype(str).isin(processed_ids)]
        total_remaining = len(df_to_process)
        
        if total_remaining == 0:
            logger.info("All outlets have already been processed. Nothing to do.")
            return
            
        logger.info(f"Starting POI scraping for {total_remaining} remaining locations (Total: {len(full_df)}).")
    except Exception as e:
        logger.error(f"Failed to load input parquet: {e}")
        return

    # 4. Processing Loop
    session = create_requests_session()
    
    for i, (index, row) in enumerate(df_to_process.iterrows(), 1):
        outlet_id = row['Outlet_ID']
        lat = row['Latitude']
        lon = row['Longitude']

        # Basic coordinate validation
        if pd.isna(lat) or pd.isna(lon):
            logger.warning(f"Skipping Outlet {outlet_id} due to missing coordinates.")
            poi_counts = {k: 0 for k in ["school_count", "hospital_count", "bus_stop_count", "restaurant_count", "fuel_count", "tourism_count"]}
        else:
            logger.info(f"[{i}/{total_remaining}] Fetching POIs for Outlet {outlet_id} ({lat}, {lon})...")
            poi_counts = fetch_poi_counts(session, lat, lon)

        # 5. Progressive Saving: Append row by row to CSV
        result_row = {"Outlet_ID": outlet_id}
        result_row.update(poi_counts)
        
        try:
            pd.DataFrame([result_row]).to_csv(
                OUTPUT_FILE, 
                mode='a', 
                index=False, 
                header=not file_exists
            )
            file_exists = True  # After the first row is written, headers are no longer needed
        except Exception as e:
            logger.error(f"Failed to save result for Outlet {outlet_id}: {e}")

        # Rate limiting: Respect Overpass API and avoid IP blocks
        time.sleep(1)

    logger.info(f"POI scraping complete. Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
