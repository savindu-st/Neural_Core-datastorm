"""
Robust Overpass API client for OpenStreetMap (OSM) POI scraping.

Provides regional bounding box searches, request retries with exponential backoff,
stable endpoint fallbacks, and connection timeout handling.
"""

import requests
import time
import logging
import pandas as pd
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter"
]

class OverpassClient:
    def __init__(self, retries: int = 3, backoff_factor: float = 2.0, timeout: int = 180):
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'NeuralCoreDataStorm/1.0 (Educational Hackathon Project; contact: agentic@neuralcore.io)',
            'Accept': 'application/json'
        }

    def fetch_pois(self, bbox: tuple, amenities: str, extra_queries: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Queries Overpass API for POIs within a bounding box.
        bbox: (south, west, north, east)
        amenities: regular expression string of amenities (e.g., "school|hospital")
        """
        s, w, n, e = [float(x) for x in bbox]
        
        # Build Overpass QL query
        query = f"""
        [out:json][timeout:{self.timeout}];
        (
          node["amenity"~"{amenities}"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
          way["amenity"~"{amenities}"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
        """
        
        if extra_queries:
            try:
                formatted_extra = extra_queries.format(s=s, w=w, n=n, e=e)
                query += f"\n  {formatted_extra}"
            except Exception as e:
                logger.error(f"Error formatting extra_queries: {e}")
                query += f"\n  {extra_queries}"
            
        query += f"""
        );
        out center;
        """
        
        logger.info(f"Querying OSM POIs in bounding box: {bbox}...")
        
        # Try multiple endpoints in case of rate limits or server downtime
        for endpoint in OVERPASS_ENDPOINTS:
            for attempt in range(self.retries):
                try:
                    logger.info(f"Attempt {attempt + 1}/{self.retries} querying endpoint: {endpoint}...")
                    response = requests.post(endpoint, data={'data': query}, headers=self.headers, timeout=self.timeout)
                    
                    if response.status_code == 429:
                        wait_time = self.backoff_factor ** attempt
                        logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                        
                    response.raise_for_status()
                    data = response.json()
                    logger.info("Successfully fetched OSM data.")
                    return data
                    
                except requests.exceptions.RequestException as err:
                    logger.error(f"Attempt {attempt + 1} failed for endpoint {endpoint}: {err}")
                    wait_time = self.backoff_factor ** attempt
                    time.sleep(wait_time)
                    
            logger.warning(f"Failed all attempts on endpoint: {endpoint}. Trying next fallback...")
            
        logger.error("Failed to query Overpass API from all endpoints and retry attempts.")
        return None

    @staticmethod
    def parse_osm_response(osm_data: Optional[Dict[str, Any]], category_mapper) -> pd.DataFrame:
        """Parses OSM JSON response elements into a pandas DataFrame using a mapper function."""
        if not osm_data or 'elements' not in osm_data:
            return pd.DataFrame()
            
        records = []
        for el in osm_data['elements']:
            lat = el.get('lat') or el.get('center', {}).get('lat')
            lon = el.get('lon') or el.get('center', {}).get('lon')
            tags = el.get('tags', {})
            
            if not lat or not lon:
                continue
                
            category = category_mapper(tags)
            if not category:
                continue
                
            name = tags.get('name', 'Unnamed POI')
            records.append({
                'lat': float(lat),
                'lon': float(lon),
                'category': category,
                'name': name
            })
            
        return pd.DataFrame(records)
