"""
Geospatial spatial calculations utility.

Provides high-performance vectorized NumPy functions for Haversine distance,
nearest POI lookup, and fixed-radius count queries.
"""

import numpy as np
import pandas as pd
from typing import Tuple

def haversine_distance(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """
    Computes vectorized Haversine distance in meters between two sets of lat/lon coordinates.
    Input coordinates are arrays or single values in decimal degrees.
    """
    # Earth radius in meters
    R = 6371000.0
    
    # Convert decimal degrees to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0)**2
    c = 2.0 * np.arcsin(np.minimum(1.0, np.sqrt(a)))
    
    return R * c

def calculate_nearest_distance(outlet_coords: np.ndarray, poi_coords: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculates the exact distance to the nearest POI and its index in the POI array.
    Uses high-speed broadcasting for moderate array sizes, or SciPy KDTree if available.
    """
    # Fallback to SciPy KDTree if available for massive speedup
    try:
        from scipy.spatial import cKDTree
        # Scale degrees slightly for lat/lon search inside Tree
        tree = cKDTree(poi_coords)
        # Tree queries yield nearest points in Euclidean space
        dists, indices = tree.query(outlet_coords, k=1)
        
        # Calculate standard Haversine distance on these nearest neighbors
        nearest_pois = poi_coords[indices]
        haversine_dists = haversine_distance(
            outlet_coords[:, 0], outlet_coords[:, 1],
            nearest_pois[:, 0], nearest_pois[:, 1]
        )
        return haversine_dists, indices
        
    except ImportError:
        # Vectorized broadcast fallback
        num_outlets = len(outlet_coords)
        distances = np.zeros(num_outlets)
        indices = np.zeros(num_outlets, dtype=int)
        
        for i, (lat, lon) in enumerate(outlet_coords):
            # Compute distance to all POIs
            dists = haversine_distance(lat, lon, poi_coords[:, 0], poi_coords[:, 1])
            min_idx = np.argmin(dists)
            distances[i] = dists[min_idx]
            indices[i] = min_idx
            
        return distances, indices

def calculate_radius_count(outlet_coords: np.ndarray, poi_coords: np.ndarray, radius_m: float) -> np.ndarray:
    """Counts the number of POIs falling within a given radius in meters for each outlet."""
    try:
        from scipy.spatial import cKDTree
        # BBox degree conversion approximation (1 degree = ~111.3km)
        deg_radius = radius_m / 111320.0
        
        tree = cKDTree(poi_coords)
        counts = tree.query_ball_point(outlet_coords, r=deg_radius)
        
        # We need to filter by exact Haversine distance within the ball query subset
        exact_counts = np.zeros(len(outlet_coords), dtype=int)
        for i, indices in enumerate(counts):
            if not indices:
                continue
            matched_pois = poi_coords[indices]
            dists = haversine_distance(
                outlet_coords[i, 0], outlet_coords[i, 1],
                matched_pois[:, 0], matched_pois[:, 1]
            )
            exact_counts[i] = np.sum(dists <= radius_m)
            
        return exact_counts
        
    except ImportError:
        # Fallback broadcast loop
        counts = np.zeros(len(outlet_coords), dtype=int)
        for i, (lat, lon) in enumerate(outlet_coords):
            dists = haversine_distance(lat, lon, poi_coords[:, 0], poi_coords[:, 1])
            counts[i] = np.sum(dists <= radius_m)
        return counts
