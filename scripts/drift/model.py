"""
OceanEye Lagrangian Oil-Spill Drift Model
Simulates forward dispersion trajectories and backward source-localization trajectories
using Euler numerical integration over interpolated ocean currents and wind leeway.
"""

import datetime
import logging
from typing import Any

import numpy as np
import pandas as pd

from common import setup_logging
from drift.geo import displacement_to_latlon, haversine_distance
from drift.interpolation import EnvironmentalForcing


def simulate_forward_drift(
    start_lat: float,
    start_lon: float,
    start_time: Any,
    duration_hours: float = 24.0,
    timestep_seconds: int = 1800,
    forcing: EnvironmentalForcing | None = None,
    windage: float = 0.03,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """
    Simulate forward oil spill trajectory (dispersion forecasting).
    Time advances forward by +timestep_seconds at each step.
    Equation: x(t + dt) = x(t) + [v_curr(t) + windage * v_wind(t)] * dt
    """
    if logger is None:
        logger = setup_logging("drift.model.forward")

    cur_time = pd.to_datetime(start_time, utc=True)
    total_steps = int(max(1, round((duration_hours * 3600.0) / timestep_seconds)))

    cur_lat = float(start_lat)
    cur_lon = float(start_lon)
    cum_dist_km = 0.0

    records = []

    for step in range(total_steps + 1):
        if forcing:
            f_data = forcing.get_net_velocity(cur_lat, cur_lon, cur_time, windage=windage)
        else:
            # Fallback zero velocity if forcing is omitted
            f_data = {
                "u_total": 0.0,
                "v_total": 0.0,
                "u_current": 0.0,
                "v_current": 0.0,
                "u_wind": 0.0,
                "v_wind": 0.0,
                "current_valid": False,
                "wind_valid": False,
                "forcing_status": "no_forcing",
            }

        u_tot = f_data["u_total"]
        v_tot = f_data["v_total"]
        speed_ms = float(np.sqrt(u_tot**2 + v_tot**2))

        records.append({
            "step": step,
            "timestamp": cur_time.isoformat(),
            "latitude": round(cur_lat, 6),
            "longitude": round(cur_lon, 6),
            "u_current": f_data["u_current"],
            "v_current": f_data["v_current"],
            "u_wind": f_data["u_wind"],
            "v_wind": f_data["v_wind"],
            "u_total": u_tot,
            "v_total": v_tot,
            "drift_speed_ms": round(speed_ms, 3),
            "cumulative_distance_km": round(cum_dist_km, 3),
            "forcing_status": f_data["forcing_status"],
        })

        if step < total_steps:
            # Forward step displacement in meters
            dx = u_tot * timestep_seconds
            dy = v_tot * timestep_seconds

            next_lat, next_lon = displacement_to_latlon(cur_lat, cur_lon, dx, dy)
            step_km = haversine_distance(cur_lat, cur_lon, next_lat, next_lon)
            cum_dist_km += step_km

            cur_lat = next_lat
            cur_lon = next_lon
            cur_time += pd.Timedelta(seconds=timestep_seconds)

    df_out = pd.DataFrame(records)
    logger.info(
        "Forward trajectory complete: %d steps, %.2f km total path over %.1f hours",
        len(df_out), cum_dist_km, duration_hours
    )
    return df_out


def simulate_backward_drift(
    start_lat: float,
    start_lon: float,
    start_time: Any,
    duration_hours: float = 48.0,
    timestep_seconds: int = 1800,
    forcing: EnvironmentalForcing | None = None,
    windage: float = 0.03,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """
    Simulate backward oil spill trajectory (source localization).
    Time steps backward by -timestep_seconds to trace where the slick originated.
    Equation: x(t - dt) = x(t) - [v_curr(t) + windage * v_wind(t)] * dt
    """
    if logger is None:
        logger = setup_logging("drift.model.backward")

    cur_time = pd.to_datetime(start_time, utc=True)
    total_steps = int(max(1, round((duration_hours * 3600.0) / timestep_seconds)))

    cur_lat = float(start_lat)
    cur_lon = float(start_lon)
    cum_dist_km = 0.0

    records = []

    for step in range(total_steps + 1):
        if forcing:
            f_data = forcing.get_net_velocity(cur_lat, cur_lon, cur_time, windage=windage)
        else:
            f_data = {
                "u_total": 0.0,
                "v_total": 0.0,
                "u_current": 0.0,
                "v_current": 0.0,
                "u_wind": 0.0,
                "v_wind": 0.0,
                "current_valid": False,
                "wind_valid": False,
                "forcing_status": "no_forcing",
            }

        u_tot = f_data["u_total"]
        v_tot = f_data["v_total"]
        speed_ms = float(np.sqrt(u_tot**2 + v_tot**2))

        records.append({
            "step": step,
            "timestamp": cur_time.isoformat(),
            "latitude": round(cur_lat, 6),
            "longitude": round(cur_lon, 6),
            "u_current": f_data["u_current"],
            "v_current": f_data["v_current"],
            "u_wind": f_data["u_wind"],
            "v_wind": f_data["v_wind"],
            "u_total": u_tot,
            "v_total": v_tot,
            "drift_speed_ms": round(speed_ms, 3),
            "cumulative_distance_km": round(cum_dist_km, 3),
            "forcing_status": f_data["forcing_status"],
        })

        if step < total_steps:
            # Backward displacement: negate velocity vector
            dx = -u_tot * timestep_seconds
            dy = -v_tot * timestep_seconds

            next_lat, next_lon = displacement_to_latlon(cur_lat, cur_lon, dx, dy)
            step_km = haversine_distance(cur_lat, cur_lon, next_lat, next_lon)
            cum_dist_km += step_km

            cur_lat = next_lat
            cur_lon = next_lon
            cur_time -= pd.Timedelta(seconds=timestep_seconds)

    df_out = pd.DataFrame(records)
    logger.info(
        "Backward trajectory complete: %d steps, %.2f km backtrack over %.1f hours",
        len(df_out), cum_dist_km, duration_hours
    )
    return df_out


def calculate_trajectory_summary(
    trajectory_df: pd.DataFrame, mode: str = "forward"
) -> dict[str, Any]:
    """Compile high-level statistical summary for a trajectory."""
    if trajectory_df.empty:
        return {}

    start_row = trajectory_df.iloc[0]
    end_row = trajectory_df.iloc[-1]

    net_disp_km = haversine_distance(
        start_row["latitude"], start_row["longitude"],
        end_row["latitude"], end_row["longitude"]
    )
    cum_dist_km = float(end_row.get("cumulative_distance_km", 0.0))
    speeds = trajectory_df["drift_speed_ms"].values

    return {
        "mode": mode,
        "start_time": start_row["timestamp"],
        "end_time": end_row["timestamp"],
        "start_latitude": start_row["latitude"],
        "start_longitude": start_row["longitude"],
        "terminal_latitude": end_row["latitude"],
        "terminal_longitude": end_row["longitude"],
        "total_steps": len(trajectory_df),
        "cumulative_path_km": cum_dist_km,
        "net_displacement_km": round(net_disp_km, 3),
        "mean_drift_speed_ms": round(float(np.mean(speeds)), 3),
        "max_drift_speed_ms": round(float(np.max(speeds)), 3),
    }
