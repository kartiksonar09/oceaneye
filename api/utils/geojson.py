"""
OceanEye GeoJSON Conversion Helpers.
Ensures strict adherence to RFC 7946 GeoJSON format:
- Coordinates order: [longitude, latitude] (WGS 84)
- Polygons are closed rings where first and last vertices match.
"""

from typing import Any, Sequence
import pandas as pd


def point_to_geojson_feature(
    latitude: float,
    longitude: float,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convert a latitude and longitude into a GeoJSON Point Feature.
    Coordinates order: [longitude, latitude].
    """
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [round(float(longitude), 6), round(float(latitude), 6)],
        },
        "properties": properties or {},
    }


def trajectory_to_linestring_feature(
    trajectory_data: pd.DataFrame | list[dict[str, Any]],
    properties: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Convert trajectory points to a GeoJSON LineString Feature.
    Coordinates order: [longitude, latitude].
    Returns None if fewer than 2 valid coordinate points exist.
    """
    coordinates = []

    if isinstance(trajectory_data, pd.DataFrame):
        if trajectory_data.empty:
            return None
        lat_col = "latitude" if "latitude" in trajectory_data.columns else "lat"
        lon_col = "longitude" if "longitude" in trajectory_data.columns else "lon"

        for _, row in trajectory_data.iterrows():
            lat = float(row[lat_col])
            lon = float(row[lon_col])
            coordinates.append([round(lon, 6), round(lat, 6)])
    elif isinstance(trajectory_data, list):
        if not trajectory_data:
            return None
        for pt in trajectory_data:
            lat = float(pt.get("latitude") if "latitude" in pt else pt.get("lat", 0.0))
            lon = float(pt.get("longitude") if "longitude" in pt else pt.get("lon", 0.0))
            coordinates.append([round(lon, 6), round(lat, 6)])
    else:
        return None

    if len(coordinates) < 2:
        return None

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates,
        },
        "properties": properties or {},
    }


def source_region_to_polygon_feature(
    points_lat_lon: Sequence[Sequence[float]],
    properties: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Convert a list of [latitude, longitude] vertices into a GeoJSON Polygon Feature.
    Coordinates order in GeoJSON: [longitude, latitude].
    Automatically closes the linear ring if the first and last points differ.
    A valid linear ring requires at least 4 positions (3 unique vertices + closed endpoint).
    """
    if not points_lat_lon or len(points_lat_lon) < 3:
        return None

    ring: list[list[float]] = []
    for pt in points_lat_lon:
        lat = float(pt[0])
        lon = float(pt[1])
        ring.append([round(lon, 6), round(lat, 6)])

    # Ensure closed loop
    if ring[0] != ring[-1]:
        ring.append(list(ring[0]))

    if len(ring) < 4:
        return None

    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring],
        },
        "properties": properties or {},
    }
