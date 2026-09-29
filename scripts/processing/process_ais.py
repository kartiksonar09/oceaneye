"""
OceanEye Data Processing - AIS Vessel Tracking
Validates, cleans, normalizes, and extracts metadata from raw AIS CSV datasets.
"""

import datetime
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from common import check_existing_file, get_data_dir, setup_logging
from processing.common import (
    compute_missing_stats,
    get_processed_dir,
    normalize_iso_timestamp,
    save_metadata,
    validate_coordinates,
)

COLUMN_MAP = {
    "mmsi": "mmsi",
    "time": "timestamp",
    "timestamp": "timestamp",
    "datetime": "timestamp",
    "time_utc": "timestamp",
    "latitude": "latitude",
    "lat": "latitude",
    "longitude": "longitude",
    "lon": "longitude",
    "long": "longitude",
    "sog": "speed_knots",
    "speed": "speed_knots",
    "speed_knots": "speed_knots",
    "cog": "course_deg",
    "course": "course_deg",
    "course_deg": "course_deg",
    "heading": "heading_deg",
    "hdg": "heading_deg",
    "heading_deg": "heading_deg",
    "navstat": "nav_status",
    "status": "nav_status",
    "nav_status": "nav_status",
    "name": "vessel_name",
    "vessel_name": "vessel_name",
    "shipname": "vessel_name",
    "imo": "imo",
    "imo_number": "imo",
    "callsign": "callsign",
    "type": "vessel_type",
    "shiptype": "vessel_type",
    "draught": "draught",
    "dest": "destination",
    "destination": "destination",
    "eta": "eta",
}


def process_ais(
    event_name: str,
    overwrite: bool = False,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """
    Process raw AIS data for an event.
    Returns a dictionary summarizing the processing results and status.
    """
    if not logger:
        logger = setup_logging("process_ais")

    raw_dir = get_data_dir("ais", event_name)
    proc_dir = get_processed_dir("ais", event_name)

    output_csv = proc_dir / f"{event_name}_ais_processed.csv"
    output_meta = proc_dir / f"{event_name}_ais_metadata.json"

    # Locate potential raw input files in order of preference
    candidate_inputs = [
        raw_dir / f"{event_name}_ais.csv",
        raw_dir / "ais_sample.csv",
    ]
    # Also find any other .csv in raw_dir
    candidate_inputs.extend([f for f in raw_dir.glob("*.csv") if "processed" not in str(f) and f not in candidate_inputs])

    raw_file = None
    for candidate in candidate_inputs:
        if candidate.exists() and candidate.is_file():
            raw_file = candidate
            break

    if not raw_file:
        logger.info("AIS raw data not found for event '%s' at %s. Skipping.", event_name, raw_dir)
        return {
            "source": "ais",
            "event": event_name,
            "status": "skipped",
            "reason": "raw_input_not_found",
            "raw_dir": str(raw_dir),
        }

    logger.info("Found raw AIS data for event '%s': %s", event_name, raw_file)

    # Check if already processed
    if output_csv.exists() and output_meta.exists() and not overwrite:
        logger.info("Processed AIS data already exists: %s. Skipping (use --overwrite to re-process).", output_csv)
        return {
            "source": "ais",
            "event": event_name,
            "status": "skipped_already_exists",
            "output_file": str(output_csv),
            "metadata_file": str(output_meta),
        }

    # Inspect raw file content
    try:
        content_sample = raw_file.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as exc:
        logger.error("Failed to read raw AIS file %s: %s", raw_file, exc)
        meta = {
            "event": event_name,
            "source": "ais",
            "processing_status": "failed",
            "error": f"Failed to read file: {exc}",
            "raw_input_file": str(raw_file),
            "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        save_metadata(meta, output_meta)
        return {"source": "ais", "event": event_name, "status": "failed", "error": str(exc)}

    # Check for known API error responses or empty content
    if not content_sample:
        logger.warning("Raw AIS file %s is empty.", raw_file)
        meta = {
            "event": event_name,
            "source": "ais",
            "processing_status": "empty_raw_file",
            "raw_input_file": str(raw_file),
            "record_count": 0,
            "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "warning": "Raw AIS file is empty.",
        }
        save_metadata(meta, output_meta)
        return {"source": "ais", "event": event_name, "status": "empty_raw_file", "metadata_file": str(output_meta)}

    if "Invalid username or password" in content_sample or "ERROR" in content_sample.splitlines()[0]:
        logger.warning("Raw AIS file %s contains API error message: '%s'", raw_file, content_sample.splitlines()[0])
        meta = {
            "event": event_name,
            "source": "ais",
            "processing_status": "invalid_raw_data",
            "raw_input_file": str(raw_file),
            "raw_file_content_snippet": content_sample[:200],
            "record_count": 0,
            "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "warning": "Raw file contains an upstream API error response instead of vessel records.",
        }
        save_metadata(meta, output_meta)
        return {"source": "ais", "event": event_name, "status": "invalid_raw_data", "metadata_file": str(output_meta)}

    # Parse CSV with pandas
    try:
        df = pd.read_csv(raw_file)
    except Exception as exc:
        logger.error("Could not parse %s as CSV: %s", raw_file, exc)
        meta = {
            "event": event_name,
            "source": "ais",
            "processing_status": "parse_error",
            "raw_input_file": str(raw_file),
            "error": str(exc),
            "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        save_metadata(meta, output_meta)
        return {"source": "ais", "event": event_name, "status": "parse_error", "error": str(exc)}

    raw_record_count = len(df)
    logger.info("Read %d raw records from %s", raw_record_count, raw_file)

    if raw_record_count == 0:
        meta = {
            "event": event_name,
            "source": "ais",
            "processing_status": "no_records",
            "raw_input_file": str(raw_file),
            "input_record_count": 0,
            "output_record_count": 0,
            "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        save_metadata(meta, output_meta)
        return {"source": "ais", "event": event_name, "status": "no_records", "metadata_file": str(output_meta)}

    # Normalize column names
    normalized_cols = {}
    for col in df.columns:
        col_clean = str(col).strip().lower()
        normalized_cols[col] = COLUMN_MAP.get(col_clean, col_clean)
    df = df.rename(columns=normalized_cols)

    # Validate coordinate columns
    lat_col = "latitude" if "latitude" in df.columns else None
    lon_col = "longitude" if "longitude" in df.columns else None

    invalid_coord_count = 0
    if lat_col and lon_col:
        valid_mask = df.apply(lambda r: validate_coordinates(r[lat_col], r[lon_col]), axis=1)
        invalid_coord_count = int((~valid_mask).sum())
        if invalid_coord_count > 0:
            logger.warning("Filtered out %d records with invalid coordinates.", invalid_coord_count)
            df = df[valid_mask].copy()

    # Normalize timestamps to ISO 8601 UTC
    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].apply(normalize_iso_timestamp)

    # Detect & remove exact duplicates
    duplicate_count = int(df.duplicated().sum())
    if duplicate_count > 0:
        logger.info("Found and removed %d exact duplicate records.", duplicate_count)
        df = df.drop_duplicates().copy()

    # Missing value statistics
    missing_stats = {}
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        missing_stats[col] = compute_missing_stats(len(df), missing_count)

    # Temporal coverage
    temporal_coverage = {}
    if "timestamp" in df.columns and not df["timestamp"].isna().all():
        valid_times = df["timestamp"].dropna()
        if not valid_times.empty:
            temporal_coverage = {
                "start": str(valid_times.min()),
                "end": str(valid_times.max()),
            }

    # Spatial coverage
    spatial_coverage = {}
    if lat_col and lon_col and not df.empty:
        spatial_coverage = {
            "min_lon": float(df[lon_col].min()),
            "max_lon": float(df[lon_col].max()),
            "min_lat": float(df[lat_col].min()),
            "max_lat": float(df[lat_col].max()),
        }

    # Save standardized CSV
    df.to_csv(output_csv, index=False)
    logger.info("Saved %d standardized AIS records to %s", len(df), output_csv)

    # Build standardized metadata
    metadata = {
        "event": event_name,
        "source": "ais",
        "processing_status": "success",
        "raw_input_file": str(raw_file),
        "processed_output_file": str(output_csv),
        "coordinate_reference_system": "EPSG:4326 (WGS84)",
        "input_record_count": int(raw_record_count),
        "output_record_count": int(len(df)),
        "duplicate_count": int(duplicate_count),
        "invalid_coordinate_count": int(invalid_coord_count),
        "columns": list(df.columns),
        "missing_value_statistics": missing_stats,
        "temporal_coverage": temporal_coverage,
        "spatial_coverage": spatial_coverage,
        "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    save_metadata(metadata, output_meta)
    logger.info("Saved AIS metadata to %s", output_meta)

    return {
        "source": "ais",
        "event": event_name,
        "status": "success",
        "input_records": raw_record_count,
        "output_records": len(df),
        "output_file": str(output_csv),
        "metadata_file": str(output_meta),
    }
