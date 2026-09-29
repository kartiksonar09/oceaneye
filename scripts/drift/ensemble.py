"""
OceanEye Particle Ensemble & Source Region Density Estimation
Implements Monte Carlo backward drift ensembles to determine the spatial bounds,
dispersion radius, and density distribution of the estimated possible spill source region.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

from common import setup_logging
from drift.geo import (
    compute_bounding_box,
    compute_convex_hull,
    displacement_to_latlon,
    haversine_distance,
)
from drift.interpolation import EnvironmentalForcing
from drift.model import simulate_backward_drift


def simulate_particle_ensemble(
    start_lat: float,
    start_lon: float,
    start_time: Any,
    duration_hours: float = 48.0,
    timestep_seconds: int = 1800,
    forcing: EnvironmentalForcing | None = None,
    num_particles: int = 25,
    windage_mean: float = 0.03,
    windage_std: float = 0.005,
    pos_noise_meters: float = 300.0,
    seed: int = 42,
    logger: logging.Logger | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Execute a Monte Carlo ensemble of backward particle trajectories to estimate
    the spatial probability density and geometry of the possible source region.
    """
    if logger is None:
        logger = setup_logging("drift.ensemble")

    rng = np.random.RandomState(seed)
    all_particle_records = []
    terminal_points = []

    logger.info(
        "Initiating backward drift ensemble: %d particles, duration: %.1f hrs, base windage: %.3f",
        num_particles, duration_hours, windage_mean
    )

    for p_idx in range(num_particles):
        # 1. Perturb initial position with bivariate Gaussian noise (simulates slick finite extent)
        dx_0 = float(rng.normal(0.0, pos_noise_meters))
        dy_0 = float(rng.normal(0.0, pos_noise_meters))
        p_lat, p_lon = displacement_to_latlon(start_lat, start_lon, dx_0, dy_0)

        # 2. Perturb windage coefficient (simulates oil weathering, emulsification, and thickness variance)
        p_windage = float(np.clip(rng.normal(windage_mean, windage_std), 0.01, 0.06))

        # 3. Simulate backward trajectory
        traj_df = simulate_backward_drift(
            start_lat=p_lat,
            start_lon=p_lon,
            start_time=start_time,
            duration_hours=duration_hours,
            timestep_seconds=timestep_seconds,
            forcing=forcing,
            windage=p_windage,
            logger=None,
        )

        traj_df["particle_id"] = p_idx
        traj_df["windage"] = round(p_windage, 4)
        all_particle_records.append(traj_df)

        terminal_row = traj_df.iloc[-1]
        terminal_points.append({
            "particle_id": p_idx,
            "latitude": float(terminal_row["latitude"]),
            "longitude": float(terminal_row["longitude"]),
            "timestamp": terminal_row["timestamp"],
            "windage": round(p_windage, 4),
            "distance_from_detection_km": round(
                haversine_distance(start_lat, start_lon, terminal_row["latitude"], terminal_row["longitude"]), 3
            ),
        })

    ensemble_df = pd.concat(all_particle_records, ignore_index=True)

    # 4. Compute Source Region Geometry and Statistical Density
    term_lats = np.array([p["latitude"] for p in terminal_points])
    term_lons = np.array([p["longitude"] for p in terminal_points])

    centroid_lat = float(np.mean(term_lats))
    centroid_lon = float(np.mean(term_lons))

    distances_to_centroid = [
        haversine_distance(centroid_lat, centroid_lon, p["latitude"], p["longitude"])
        for p in terminal_points
    ]
    radius_95_km = float(np.percentile(distances_to_centroid, 95))
    radius_max_km = float(np.max(distances_to_centroid))

    # Bounding box
    coords_list = list(zip(term_lats, term_lons))
    bbox = compute_bounding_box(coords_list)

    # Convex hull polygon
    hull_polygon = compute_convex_hull(coords_list)

    # Estimated release timestamp (start_time minus duration)
    detection_dt = pd.to_datetime(start_time, utc=True)
    estimated_release_dt = detection_dt - pd.Timedelta(hours=duration_hours)

    source_region_meta = {
        "region_type": "estimated_possible_source_region",
        "detection_point": {
            "latitude": round(start_lat, 6),
            "longitude": round(start_lon, 6),
            "timestamp": detection_dt.isoformat(),
        },
        "estimated_release_timestamp": estimated_release_dt.isoformat(),
        "backtrack_duration_hours": duration_hours,
        "ensemble_size": num_particles,
        "centroid": {
            "latitude": round(centroid_lat, 6),
            "longitude": round(centroid_lon, 6),
        },
        "bounding_box": bbox,
        "dispersion_radius_95_km": round(radius_95_km, 3),
        "dispersion_radius_max_km": round(radius_max_km, 3),
        "polygon_convex_hull": hull_polygon,
        "terminal_endpoints": terminal_points,
        "scientific_notice": (
            "NOTICE: This is an estimated possible source region derived from Lagrangian ensemble "
            "back-projection. It indicates a statistical search zone for investigative vessel "
            "correlation and does NOT represent a confirmed spill origin or verified legal attribution."
        ),
    }

    logger.info(
        "Source region computed: centroid (%.4f, %.4f), 95%% radius: %.2f km across %d particles",
        centroid_lat, centroid_lon, radius_95_km, num_particles
    )
    return ensemble_df, source_region_meta
