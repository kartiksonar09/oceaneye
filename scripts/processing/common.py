"""
OceanEye Processing - Common Utilities
Shared helper functions for data validation, normalization, metadata serialization, and directory management.
"""

import datetime
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

# Import paths from main common module
import sys

# Ensure parent directory (scripts/) is in path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import DATA_DIR, get_data_dir, setup_logging


def get_processed_dir(connector: str, event_name: str) -> Path:
    """
    Get and create the standard processed directory:
    data/<connector>/<event_name>/processed
    """
    raw_dir = get_data_dir(connector, event_name)
    proc_dir = raw_dir / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    return proc_dir


def save_metadata(metadata: dict[str, Any], output_path: Path) -> None:
    """
    Save metadata dictionary to a JSON file formatted with indentation.
    Handles non-serializable types gracefully.
    """
    def _default_serializer(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.ndarray, list)):
            return [int(x) if isinstance(x, np.integer) else float(x) if isinstance(x, np.floating) else str(x) for x in obj]
        elif isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        return str(obj)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=_default_serializer)


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate that latitude is between -90 and 90, and longitude is between -180 and 180.
    """
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        return (-90.0 <= lat_f <= 90.0) and (-180.0 <= lon_f <= 180.0)
    except (ValueError, TypeError):
        return False


def normalize_iso_timestamp(val: Any) -> str | None:
    """
    Normalize various timestamp representations (epoch int/float, string ISO)
    to a standardized UTC ISO-8601 string: YYYY-MM-DDTHH:MM:SSZ
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None

    try:
        # Check if integer / float epoch timestamp
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
            ts_float = float(val)
            # If in milliseconds (e.g. > 1e11)
            if ts_float > 1e11:
                ts_float = ts_float / 1000.0
            dt = datetime.datetime.fromtimestamp(ts_float, tz=datetime.timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Parse string format
        val_str = str(val).strip()
        # Replace space with T
        if " " in val_str and "T" not in val_str:
            val_str = val_str.replace(" ", "T")
        
        # Strip timezone offset if already present and convert to standard UTC
        dt = datetime.datetime.fromisoformat(val_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = dt.astimezone(datetime.timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def compute_missing_stats(total_elements: int, missing_elements: int) -> dict[str, Any]:
    """
    Compute standard missing value metrics.
    """
    pct = (missing_elements / total_elements * 100.0) if total_elements > 0 else 0.0
    return {
        "total_count": int(total_elements),
        "valid_count": int(total_elements - missing_elements),
        "missing_count": int(missing_elements),
        "missing_percentage": round(pct, 2),
    }
