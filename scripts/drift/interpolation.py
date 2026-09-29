"""
OceanEye Environmental Forcing Interpolation Layer
Provides robust spatio-temporal extraction and interpolation of ocean surface
currents (uo, vo) and 10m wind fields (eastward_wind, northward_wind) from CMEMS NetCDF datasets.
"""

import datetime
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

from common import setup_logging


class EnvironmentalForcing:
    """
    Manages spatio-temporal environmental forcing fields.
    Interpolates ocean currents and wind vectors at arbitrary coordinates and timestamps.
    Handles out-of-bounds queries, missing timesteps, and missing variables gracefully.
    """

    def __init__(
        self,
        currents_path: Path | str | None = None,
        wind_path: Path | str | None = None,
        logger: logging.Logger | None = None,
    ):
        self.logger = logger or setup_logging("drift.forcing")
        self.ds_currents: xr.Dataset | None = None
        self.ds_wind: xr.Dataset | None = None

        self.currents_bounds: dict[str, Any] = {}
        self.wind_bounds: dict[str, Any] = {}

        if currents_path:
            self._load_currents(Path(currents_path))
        if wind_path:
            self._load_wind(Path(wind_path))

    def _load_currents(self, path: Path) -> None:
        if not path.exists():
            self.logger.warning("Currents NetCDF dataset not found at: %s", path)
            return
        try:
            self.ds_currents = xr.open_dataset(path)
            # Find coordinate names
            lat_dim = "latitude" if "latitude" in self.ds_currents.coords else "lat"
            lon_dim = "longitude" if "longitude" in self.ds_currents.coords else "lon"
            time_dim = "time" if "time" in self.ds_currents.coords else None

            lats = self.ds_currents[lat_dim].values
            lons = self.ds_currents[lon_dim].values
            times = self.ds_currents[time_dim].values if time_dim else []

            self.currents_bounds = {
                "lat_min": float(np.min(lats)),
                "lat_max": float(np.max(lats)),
                "lon_min": float(np.min(lons)),
                "lon_max": float(np.max(lons)),
                "time_min": pd.to_datetime(np.min(times)) if len(times) else None,
                "time_max": pd.to_datetime(np.max(times)) if len(times) else None,
                "lat_dim": lat_dim,
                "lon_dim": lon_dim,
                "time_dim": time_dim,
            }
            self.logger.info("Loaded currents dataset from %s", path)
        except Exception as exc:
            self.logger.error("Failed to open currents NetCDF dataset %s: %s", path, exc)
            self.ds_currents = None

    def _load_wind(self, path: Path) -> None:
        if not path.exists():
            self.logger.warning("Wind NetCDF dataset not found at: %s", path)
            return
        try:
            self.ds_wind = xr.open_dataset(path)
            lat_dim = "latitude" if "latitude" in self.ds_wind.coords else "lat"
            lon_dim = "longitude" if "longitude" in self.ds_wind.coords else "lon"
            time_dim = "time" if "time" in self.ds_wind.coords else None

            lats = self.ds_wind[lat_dim].values
            lons = self.ds_wind[lon_dim].values
            times = self.ds_wind[time_dim].values if time_dim else []

            self.wind_bounds = {
                "lat_min": float(np.min(lats)),
                "lat_max": float(np.max(lats)),
                "lon_min": float(np.min(lons)),
                "lon_max": float(np.max(lons)),
                "time_min": pd.to_datetime(np.min(times)) if len(times) else None,
                "time_max": pd.to_datetime(np.max(times)) if len(times) else None,
                "lat_dim": lat_dim,
                "lon_dim": lon_dim,
                "time_dim": time_dim,
            }
            self.logger.info("Loaded wind dataset from %s", path)
        except Exception as exc:
            self.logger.error("Failed to open wind NetCDF dataset %s: %s", path, exc)
            self.ds_wind = None

    def is_currents_available(self) -> bool:
        return self.ds_currents is not None

    def is_wind_available(self) -> bool:
        return self.ds_wind is not None

    def get_current_vector(
        self, lat: float, lon: float, timestamp: Any
    ) -> tuple[float, float, bool]:
        """
        Interpolate ocean surface current velocity (u, v) in m/s at (lat, lon, timestamp).
        Returns: (uo, vo, is_valid)
        """
        if not self.ds_currents:
            return 0.0, 0.0, False

        b = self.currents_bounds
        # Check spatial coverage
        if not (b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]):
            return 0.0, 0.0, False

        # Convert timestamp to numpy datetime64
        t_dt = pd.to_datetime(timestamp)
        if t_dt.tzinfo is not None:
            t_dt = t_dt.tz_convert(None)

        # Check temporal coverage
        if b["time_min"] and b["time_max"]:
            if not (b["time_min"] <= t_dt <= b["time_max"]):
                # Use nearest boundary timestamp if within reasonable range (e.g. 2 days)
                pass

        try:
            # Determine surface variable names
            uo_var = "uo_surface" if "uo_surface" in self.ds_currents.data_vars else "uo"
            vo_var = "vo_surface" if "vo_surface" in self.ds_currents.data_vars else "vo"

            interp_dict = {
                b["lat_dim"]: lat,
                b["lon_dim"]: lon,
            }
            if b["time_dim"]:
                interp_dict[b["time_dim"]] = np.datetime64(t_dt)

            # Nearest-neighbor or linear interpolation
            sub_u = self.ds_currents[uo_var].interp(
                **interp_dict, method="linear", kwargs={"fill_value": "extrapolate"}
            )
            sub_v = self.ds_currents[vo_var].interp(
                **interp_dict, method="linear", kwargs={"fill_value": "extrapolate"}
            )

            # Squeeze depth if present
            if "depth" in sub_u.dims:
                sub_u = sub_u.isel(depth=0)
                sub_v = sub_v.isel(depth=0)

            u_val = float(sub_u.values)
            v_val = float(sub_v.values)

            if np.isnan(u_val) or np.isnan(v_val):
                # Fallback to nearest neighbor
                sub_u = self.ds_currents[uo_var].sel(
                    {b["lat_dim"]: lat, b["lon_dim"]: lon}, method="nearest"
                )
                sub_v = self.ds_currents[vo_var].sel(
                    {b["lat_dim"]: lat, b["lon_dim"]: lon}, method="nearest"
                )
                if b["time_dim"]:
                    sub_u = sub_u.sel({b["time_dim"]: np.datetime64(t_dt)}, method="nearest")
                    sub_v = sub_v.sel({b["time_dim"]: np.datetime64(t_dt)}, method="nearest")
                if "depth" in sub_u.dims:
                    sub_u = sub_u.isel(depth=0)
                    sub_v = sub_v.isel(depth=0)
                u_val = float(sub_u.values)
                v_val = float(sub_v.values)

            if np.isnan(u_val) or np.isnan(v_val):
                return 0.0, 0.0, False

            return float(u_val), float(v_val), True
        except Exception as exc:
            self.logger.debug("Currents interpolation error at (%f, %f): %s", lat, lon, exc)
            return 0.0, 0.0, False

    def get_wind_vector(
        self, lat: float, lon: float, timestamp: Any
    ) -> tuple[float, float, bool]:
        """
        Interpolate 10m wind velocity (eastward_wind, northward_wind) in m/s at (lat, lon, timestamp).
        Returns: (wind_u, wind_v, is_valid)
        """
        if not self.ds_wind:
            return 0.0, 0.0, False

        b = self.wind_bounds
        if not (b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]):
            return 0.0, 0.0, False

        t_dt = pd.to_datetime(timestamp)
        if t_dt.tzinfo is not None:
            t_dt = t_dt.tz_convert(None)

        try:
            u_var = "eastward_wind" if "eastward_wind" in self.ds_wind.data_vars else "u10"
            v_var = "northward_wind" if "northward_wind" in self.ds_wind.data_vars else "v10"

            interp_dict = {
                b["lat_dim"]: lat,
                b["lon_dim"]: lon,
            }
            if b["time_dim"]:
                interp_dict[b["time_dim"]] = np.datetime64(t_dt)

            sub_u = self.ds_wind[u_var].interp(
                **interp_dict, method="linear", kwargs={"fill_value": "extrapolate"}
            )
            sub_v = self.ds_wind[v_var].interp(
                **interp_dict, method="linear", kwargs={"fill_value": "extrapolate"}
            )

            u_val = float(sub_u.values)
            v_val = float(sub_v.values)

            if np.isnan(u_val) or np.isnan(v_val):
                # Fallback to nearest
                sub_u = self.ds_wind[u_var].sel(
                    {b["lat_dim"]: lat, b["lon_dim"]: lon}, method="nearest"
                )
                sub_v = self.ds_wind[v_var].sel(
                    {b["lat_dim"]: lat, b["lon_dim"]: lon}, method="nearest"
                )
                if b["time_dim"]:
                    sub_u = sub_u.sel({b["time_dim"]: np.datetime64(t_dt)}, method="nearest")
                    sub_v = sub_v.sel({b["time_dim"]: np.datetime64(t_dt)}, method="nearest")
                u_val = float(sub_u.values)
                v_val = float(sub_v.values)

            if np.isnan(u_val) or np.isnan(v_val):
                return 0.0, 0.0, False

            return float(u_val), float(v_val), True
        except Exception as exc:
            self.logger.debug("Wind interpolation error at (%f, %f): %s", lat, lon, exc)
            return 0.0, 0.0, False

    def get_net_velocity(
        self, lat: float, lon: float, timestamp: Any, windage: float = 0.03
    ) -> dict[str, Any]:
        """
        Compute total Lagrangian drift velocity vector:
        v_particle = v_current + windage * v_wind
        """
        u_curr, v_curr, curr_valid = self.get_current_vector(lat, lon, timestamp)
        u_wind, v_wind, wind_valid = self.get_wind_vector(lat, lon, timestamp)

        u_total = u_curr + (windage * u_wind)
        v_total = v_curr + (windage * v_wind)

        if curr_valid and wind_valid:
            status = "complete"
        elif curr_valid:
            status = "current_only"
        elif wind_valid:
            status = "wind_only"
        else:
            status = "no_forcing_data"

        return {
            "u_total": round(float(u_total), 4),
            "v_total": round(float(v_total), 4),
            "u_current": round(float(u_curr), 4),
            "v_current": round(float(v_curr), 4),
            "current_valid": curr_valid,
            "u_wind": round(float(u_wind), 4),
            "v_wind": round(float(v_wind), 4),
            "wind_valid": wind_valid,
            "windage": windage,
            "forcing_status": status,
        }

    def close(self) -> None:
        """Close opened NetCDF datasets."""
        if self.ds_currents:
            self.ds_currents.close()
            self.ds_currents = None
        if self.ds_wind:
            self.ds_wind.close()
            self.ds_wind = None
