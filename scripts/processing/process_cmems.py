"""
OceanEye Data Processing - CMEMS Ocean Currents
Validates, normalizes, computes derived velocity fields, and generates metadata for CMEMS current NetCDF datasets.
"""

import datetime
import logging
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

from common import get_data_dir, setup_logging
from processing.common import (
    compute_missing_stats,
    get_processed_dir,
    save_metadata,
    validate_coordinates,
)


def process_currents(
    event_name: str,
    overwrite: bool = False,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """
    Process CMEMS ocean current data for a specified event.
    """
    if not logger:
        logger = setup_logging("process_cmems")

    raw_dir = get_data_dir("cmems", event_name)
    proc_dir = get_processed_dir("cmems", event_name)

    raw_file = raw_dir / f"{event_name}_currents.nc"
    output_nc = proc_dir / f"{event_name}_currents_processed.nc"
    output_meta = proc_dir / f"{event_name}_currents_metadata.json"

    if not raw_file.exists():
        logger.info("CMEMS currents raw data not found for event '%s' at %s. Skipping.", event_name, raw_file)
        return {
            "source": "cmems_currents",
            "event": event_name,
            "status": "skipped",
            "reason": "raw_input_not_found",
            "raw_file": str(raw_file),
        }

    logger.info("Found raw CMEMS currents data: %s", raw_file)

    # Check if already processed
    if output_nc.exists() and output_meta.exists() and not overwrite:
        logger.info("Processed currents data already exists: %s. Skipping (use --overwrite to re-process).", output_nc)
        return {
            "source": "cmems_currents",
            "event": event_name,
            "status": "skipped_already_exists",
            "output_file": str(output_nc),
            "metadata_file": str(output_meta),
        }

    # Open and inspect NetCDF dataset safely
    try:
        ds = xr.open_dataset(raw_file)
    except Exception as exc:
        logger.error("Failed to open NetCDF file %s: %s", raw_file, exc)
        meta = {
            "event": event_name,
            "source": "cmems_currents",
            "processing_status": "failed_corrupted_netcdf",
            "raw_input_file": str(raw_file),
            "error": str(exc),
            "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        save_metadata(meta, output_meta)
        return {"source": "cmems_currents", "event": event_name, "status": "failed", "error": str(exc)}

    # Inspect coordinates and dimensions
    dims_info = {str(k): int(v) for k, v in ds.sizes.items()}
    coords_list = list(ds.coords.keys())
    data_vars_list = list(ds.data_vars.keys())

    logger.info("Currents dataset dimensions: %s", dims_info)
    logger.info("Currents dataset variables: %s", data_vars_list)

    # Validate coordinate variables
    time_coord = "time" if "time" in ds.coords else None
    lat_coord = "latitude" if "latitude" in ds.coords else ("lat" if "lat" in ds.coords else None)
    lon_coord = "longitude" if "longitude" in ds.coords else ("lon" if "lon" in ds.coords else None)
    depth_coord = "depth" if "depth" in ds.coords else None

    if not lat_coord or not lon_coord or not time_coord:
        err_msg = f"NetCDF missing essential coordinates. Found: {coords_list}"
        logger.error(err_msg)
        meta = {
            "event": event_name,
            "source": "cmems_currents",
            "processing_status": "missing_required_coordinates",
            "raw_input_file": str(raw_file),
            "error": err_msg,
            "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        save_metadata(meta, output_meta)
        return {"source": "cmems_currents", "event": event_name, "status": "failed", "error": err_msg}

    # Spatial coverage
    lats = ds[lat_coord].values
    lons = ds[lon_coord].values
    min_lat, max_lat = float(np.min(lats)), float(np.max(lats))
    min_lon, max_lon = float(np.min(lons)), float(np.max(lons))

    if not validate_coordinates(min_lat, min_lon) or not validate_coordinates(max_lat, max_lon):
        logger.warning("Coordinates out of standard WGS84 range: lat [%f, %f], lon [%f, %f]", min_lat, max_lat, min_lon, max_lon)

    # Temporal coverage
    time_values = ds[time_coord].values
    start_time_iso = str(np.min(time_values))[:19] + "Z"
    end_time_iso = str(np.max(time_values))[:19] + "Z"

    # Create processed dataset copy
    ds_proc = ds.copy(deep=True)

    # Compute derived variables if uo and vo exist
    has_uo_vo = "uo" in ds_proc and "vo" in ds_proc
    stats: dict[str, Any] = {}

    if has_uo_vo:
        uo = ds_proc["uo"]
        vo = ds_proc["vo"]

        # Calculate current velocity magnitude (speed in m/s)
        current_speed = np.sqrt(uo**2 + vo**2)
        current_speed.attrs = {
            "long_name": "Ocean current speed magnitude",
            "standard_name": "sea_water_speed",
            "units": "m s-1",
        }
        ds_proc["current_speed"] = current_speed

        # Calculate flow direction in degrees (0 = East, 90 = North; or oceanographic azimuth)
        direction_rad = np.arctan2(vo, uo)
        direction_deg = (np.degrees(direction_rad) + 360) % 360
        direction_deg.attrs = {
            "long_name": "Ocean current flow direction angle",
            "units": "degrees",
            "description": "Angle of water velocity vector relative to East (counter-clockwise)",
        }
        ds_proc["current_direction"] = direction_deg

        # Extract surface layer (top depth level) for direct accessibility
        if depth_coord and depth_coord in ds_proc.dims:
            ds_proc["uo_surface"] = uo.isel({depth_coord: 0})
            ds_proc["uo_surface"].attrs = {"long_name": "Surface eastward velocity", "units": "m s-1"}
            ds_proc["vo_surface"] = vo.isel({depth_coord: 0})
            ds_proc["vo_surface"].attrs = {"long_name": "Surface northward velocity", "units": "m s-1"}
            ds_proc["current_speed_surface"] = current_speed.isel({depth_coord: 0})
            ds_proc["current_speed_surface"].attrs = {"long_name": "Surface current speed magnitude", "units": "m s-1"}

    # Compute statistical quality metrics
    for var_name in ds_proc.data_vars:
        data_arr = ds_proc[var_name].values
        total_cells = int(data_arr.size)
        nan_cells = int(np.isnan(data_arr).sum())
        valid_cells = total_cells - nan_cells

        var_stats = compute_missing_stats(total_cells, nan_cells)
        if valid_cells > 0:
            valid_vals = data_arr[~np.isnan(data_arr)]
            var_stats.update({
                "min": round(float(np.min(valid_vals)), 4),
                "max": round(float(np.max(valid_vals)), 4),
                "mean": round(float(np.mean(valid_vals)), 4),
                "std": round(float(np.std(valid_vals)), 4),
                "units": str(ds_proc[var_name].attrs.get("units", "unknown")),
            })
        stats[var_name] = var_stats

    # Enrich metadata attributes
    ds_proc.attrs["processing_stage"] = "OceanEye Prompt 3 Standardized Data"
    ds_proc.attrs["processed_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ds_proc.attrs["source_dataset"] = ds.attrs.get("title", "Copernicus Marine Physical Ocean Current")

    # Save standardized NetCDF
    logger.info("Writing standardized currents NetCDF to %s...", output_nc)
    ds_proc.to_netcdf(output_nc)

    # Build standardized metadata
    metadata = {
        "event": event_name,
        "source": "cmems_currents",
        "processing_status": "success",
        "raw_input_file": str(raw_file),
        "processed_output_file": str(output_nc),
        "coordinate_reference_system": "EPSG:4326 (WGS84)",
        "temporal_coverage": {
            "start": start_time_iso,
            "end": end_time_iso,
            "time_steps_count": int(len(time_values)),
        },
        "spatial_coverage": {
            "min_lon": min_lon,
            "max_lon": max_lon,
            "min_lat": min_lat,
            "max_lat": max_lat,
            "lat_points": int(len(lats)),
            "lon_points": int(len(lons)),
        },
        "depth_levels_count": int(len(ds[depth_coord].values)) if depth_coord else 1,
        "surface_depth_m": float(ds[depth_coord].values[0]) if depth_coord else 0.0,
        "dimensions": dims_info,
        "variables": list(ds_proc.data_vars.keys()),
        "variable_statistics": stats,
        "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    save_metadata(metadata, output_meta)
    logger.info("Saved CMEMS currents metadata to %s", output_meta)

    return {
        "source": "cmems_currents",
        "event": event_name,
        "status": "success",
        "output_file": str(output_nc),
        "metadata_file": str(output_meta),
    }
