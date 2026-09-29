"""
OceanEye Vessel Prioritization & Ranking Feature Extraction Layer
Extracts kinematic, spatial-temporal proximity, and oceanographic drift-alignment
features from AIS vessel trajectories relative to candidate oil spill events.
"""

import datetime
from typing import Any
import numpy as np
import pandas as pd


RANKING_FEATURE_NAMES = [
    "min_distance_km",
    "distance_at_spill_time_km",
    "temporal_offset_hours",
    "trajectory_proximity_score",
    "temporal_proximity_score",
    "mean_speed_knots",
    "speed_variance",
    "speed_anomaly_score",
    "heading_deviation_deg",
    "drift_corrected_distance_km",
    "ais_ping_count",
]


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
    earth_radius_km = 6371.0
    return float(earth_radius_km * c)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate initial compass bearing from point 1 to point 2 in degrees (0-360)."""
    lat1_r, lon1_r = np.radians(lat1), np.radians(lon1)
    lat2_r, lon2_r = np.radians(lat2), np.radians(lon2)
    dlon = lon2_r - lon1_r

    y = np.sin(dlon) * np.cos(lat2_r)
    x = np.cos(lat1_r) * np.sin(lat2_r) - np.sin(lat1_r) * np.cos(lat2_r) * np.cos(dlon)
    initial_bearing = np.degrees(np.arctan2(y, x))
    return float((initial_bearing + 360.0) % 360.0)


def extract_vessel_features(
    vessel_points: pd.DataFrame | list[dict[str, Any]],
    spill_lat: float,
    spill_lon: float,
    spill_timestamp: str | datetime.datetime,
    current_u: float = 0.0,
    current_v: float = 0.0,
    wind_u: float = 0.0,
    wind_v: float = 0.0,
) -> dict[str, float]:
    """
    Compute structured kinematic and trajectory features for a vessel relative to a candidate spill.
    Supports trajectory data containing: latitude, longitude, timestamp, speed_knots, course_deg/heading_deg.
    """
    if isinstance(vessel_points, list):
        df = pd.DataFrame(vessel_points)
    else:
        df = vessel_points.copy()

    if df.empty or "latitude" not in df.columns or "longitude" not in df.columns:
        return {feat: 0.0 for feat in RANKING_FEATURE_NAMES}

    # Normalize timestamps
    if "timestamp" in df.columns:
        df["dt"] = pd.to_datetime(df["timestamp"], utc=True)
    else:
        df["dt"] = pd.Timestamp.now(tz="UTC")

    if isinstance(spill_timestamp, str):
        spill_dt = pd.to_datetime(spill_timestamp, utc=True)
    else:
        spill_dt = pd.Timestamp(spill_timestamp).tz_localize("UTC") if spill_timestamp.tzinfo is None else pd.Timestamp(spill_timestamp)

    # 1. Distances and Temporal Offsets
    distances_km = [
        haversine_distance(row["latitude"], row["longitude"], spill_lat, spill_lon)
        for _, row in df.iterrows()
    ]
    min_dist_km = float(min(distances_km))

    time_diffs_hours = [
        abs((row["dt"] - spill_dt).total_seconds()) / 3600.0
        for _, row in df.iterrows()
    ]
    min_time_offset_hours = float(min(time_diffs_hours))

    # Point closest in time
    closest_time_idx = int(np.argmin(time_diffs_hours))
    dist_at_spill_time = float(distances_km[closest_time_idx])

    # 2. Proximity Decay Scores (continuous [0, 1])
    # Trajectory proximity decays with scale factor 20 km
    traj_prox = float(np.exp(-min_dist_km / 20.0))
    # Temporal proximity decays with scale factor 12 hours
    temp_prox = float(np.exp(-min_time_offset_hours / 12.0))

    # 3. Kinematics (Speed & Heading)
    speed_col = "speed_knots" if "speed_knots" in df.columns else ("speed" if "speed" in df.columns else None)
    if speed_col and not df[speed_col].isna().all():
        speeds = df[speed_col].dropna().astype(float).values
        mean_spd = float(np.mean(speeds))
        var_spd = float(np.var(speeds))
        # Sudden speed drop anomaly (e.g. slowing from cruising speed 14 kts to 2 kts)
        min_spd = float(np.min(speeds))
        max_spd = float(np.max(speeds))
        spd_anomaly = float((max_spd - min_spd) / (max_spd + 1e-3))
    else:
        mean_spd = 10.0
        var_spd = 0.0
        spd_anomaly = 0.0

    # 4. Heading / Course Alignment
    course_col = "course_deg" if "course_deg" in df.columns else ("heading_deg" if "heading_deg" in df.columns else None)
    if course_col and not df[course_col].isna().all():
        closest_row = df.iloc[int(np.argmin(distances_km))]
        vessel_course = float(closest_row[course_col])
        bearing_to_spill = calculate_bearing(
            closest_row["latitude"], closest_row["longitude"], spill_lat, spill_lon
        )
        angle_diff = abs((vessel_course - bearing_to_spill + 180.0) % 360.0 - 180.0)
        heading_dev = float(angle_diff)
    else:
        heading_dev = 90.0

    # 5. Oceanographic Drift-Corrected Distance
    # Back-trace spill position based on surface currents (100%) and wind leeway (3%)
    # Net drift velocity vector in m/s: (current + 0.03 * wind)
    net_u_ms = current_u + 0.03 * wind_u
    net_v_ms = current_v + 0.03 * wind_v

    # Elapsed seconds from closest ping to spill detection
    elapsed_sec = (spill_dt - df.iloc[closest_time_idx]["dt"]).total_seconds()
    drift_x_meters = net_u_ms * elapsed_sec
    drift_y_meters = net_v_ms * elapsed_sec

    # Approximate coordinate offset: 1 deg lat ~ 111,000m, 1 deg lon ~ 111,000m * cos(lat)
    d_lat = drift_y_meters / 111000.0
    d_lon = drift_x_meters / (111000.0 * np.cos(np.radians(spill_lat)) + 1e-6)

    backtracked_spill_lat = spill_lat - d_lat
    backtracked_spill_lon = spill_lon - d_lon

    drift_dist_km = haversine_distance(
        df.iloc[closest_time_idx]["latitude"],
        df.iloc[closest_time_idx]["longitude"],
        backtracked_spill_lat,
        backtracked_spill_lon,
    )

    return {
        "min_distance_km": round(min_dist_km, 2),
        "distance_at_spill_time_km": round(dist_at_spill_time, 2),
        "temporal_offset_hours": round(min_time_offset_hours, 2),
        "trajectory_proximity_score": round(traj_prox, 4),
        "temporal_proximity_score": round(temp_prox, 4),
        "mean_speed_knots": round(mean_spd, 2),
        "speed_variance": round(var_spd, 2),
        "speed_anomaly_score": round(spd_anomaly, 4),
        "heading_deviation_deg": round(heading_dev, 1),
        "drift_corrected_distance_km": round(drift_dist_km, 2),
        "ais_ping_count": float(len(df)),
    }
