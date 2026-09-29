"""
OceanEye Geospatial & Trajectory Utilities
Provides robust, vectorized geodesic calculations, coordinate projections,
trajectory proximity metrics, and bounding geometry tools.
"""

from typing import Any
import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0
METERS_PER_DEGREE_LAT = 111139.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees).
    """
    lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
    lat2_r, lon2_r = np.radians(lat2), np.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arcsin(np.clip(np.sqrt(a), 0.0, 1.0))
    return float(EARTH_RADIUS_KM * c)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate initial compass bearing in degrees (0 - 360) from point 1 to point 2.
    0 = North, 90 = East, 180 = South, 270 = West.
    """
    lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
    lat2_r, lon2_r = np.radians(lat2), np.radians(lon2)
    dlon = lon2_r - lon1_r

    y = np.sin(dlon) * np.cos(lat2_r)
    x = np.cos(lat1_r) * np.sin(lat2_r) - np.sin(lat1_r) * np.cos(lat2_r) * np.cos(dlon)
    initial_bearing = np.degrees(np.arctan2(y, x))
    return float((initial_bearing + 360.0) % 360.0)


def displacement_to_latlon(
    lat: float, lon: float, dx_meters: float, dy_meters: float
) -> tuple[float, float]:
    """
    Project a local Cartesian displacement (dx = eastward, dy = northward in meters)
    to new geographic coordinates (latitude, longitude) in degrees.
    """
    delta_lat = dy_meters / METERS_PER_DEGREE_LAT
    cos_lat = np.cos(np.radians(lat))
    # Prevent divide-by-zero near poles
    meters_per_lon = METERS_PER_DEGREE_LAT * max(cos_lat, 1e-6)
    delta_lon = dx_meters / meters_per_lon

    new_lat = float(np.clip(lat + delta_lat, -90.0, 90.0))
    new_lon = float(((lon + delta_lon + 180.0) % 360.0) - 180.0)
    return new_lat, new_lon


def latlon_to_displacement(
    lat_origin: float, lon_origin: float, lat: float, lon: float
) -> tuple[float, float]:
    """
    Calculate Cartesian displacement (dx = eastward, dy = northward in meters)
    of (lat, lon) relative to (lat_origin, lon_origin).
    """
    dy = (lat - lat_origin) * METERS_PER_DEGREE_LAT
    cos_lat = np.cos(np.radians((lat_origin + lat) / 2.0))
    dx = (lon - lon_origin) * METERS_PER_DEGREE_LAT * cos_lat
    return float(dx), float(dy)


def point_to_trajectory_distance(
    lat: float, lon: float, trajectory_df: pd.DataFrame
) -> dict[str, Any]:
    """
    Calculate minimum distance from a geographic point to a trajectory.
    Returns:
      - min_distance_km: float
      - closest_index: int
      - closest_timestamp: str | None
      - closest_latitude: float
      - closest_longitude: float
    """
    if trajectory_df.empty or "latitude" not in trajectory_df.columns or "longitude" not in trajectory_df.columns:
        return {
            "min_distance_km": float("inf"),
            "closest_index": -1,
            "closest_timestamp": None,
            "closest_latitude": lat,
            "closest_longitude": lon,
        }

    lats = trajectory_df["latitude"].values
    lons = trajectory_df["longitude"].values

    distances = [
        haversine_distance(lat, lon, pt_lat, pt_lon)
        for pt_lat, pt_lon in zip(lats, lons)
    ]
    min_idx = int(np.argmin(distances))
    min_dist = float(distances[min_idx])

    closest_time = (
        str(trajectory_df["timestamp"].iloc[min_idx])
        if "timestamp" in trajectory_df.columns
        else None
    )

    return {
        "min_distance_km": round(min_dist, 3),
        "closest_index": min_idx,
        "closest_timestamp": closest_time,
        "closest_latitude": float(lats[min_idx]),
        "closest_longitude": float(lons[min_idx]),
    }


def calculate_trajectory_length(trajectory_df: pd.DataFrame) -> float:
    """Calculate cumulative path distance along a trajectory in kilometers."""
    if len(trajectory_df) < 2 or "latitude" not in trajectory_df.columns or "longitude" not in trajectory_df.columns:
        return 0.0

    lats = trajectory_df["latitude"].values
    lons = trajectory_df["longitude"].values

    total_km = 0.0
    for i in range(len(lats) - 1):
        total_km += haversine_distance(lats[i], lons[i], lats[i + 1], lons[i + 1])
    return float(round(total_km, 3))


def compute_bounding_box(coords: list[tuple[float, float]]) -> dict[str, float]:
    """Calculate bounding box from coordinate pairs [(lat, lon), ...]."""
    if not coords:
        return {"min_lat": 0.0, "max_lat": 0.0, "min_lon": 0.0, "max_lon": 0.0}

    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return {
        "min_lat": round(float(min(lats)), 5),
        "max_lat": round(float(max(lats)), 5),
        "min_lon": round(float(min(lons)), 5),
        "max_lon": round(float(max(lons)), 5),
    }


def compute_convex_hull(points: list[list[float]] | list[tuple[float, float]] | np.ndarray) -> list[list[float]]:
    """
    Compute 2D convex hull of points [(lat, lon), ...] using Andrew's Monotone Chain algorithm.
    Returns polygon vertices in counter-clockwise order.
    """
    pts = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(pts) <= 2:
        return [[p[0], p[1]] for p in pts]

    def cross_product(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    # Lower hull
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross_product(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    # Upper hull
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross_product(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # Concatenate lower and upper hulls, omitting last point of each list
    hull = lower[:-1] + upper[:-1]
    return [[p[0], p[1]] for p in hull]
