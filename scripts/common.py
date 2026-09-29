"""
OceanEye Common Utilities
Shared helpers for data ingestion connectors.
"""

import datetime
import json
import logging
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# ---------------------------------------------------------
# Project Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
EVENTS_FILE = CONFIG_DIR / "events.json"
DATA_DIR = PROJECT_ROOT / "data"
ENV_FILE = PROJECT_ROOT / ".env"

# Automatically load .env if present
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------

def setup_logging(logger_name: str = "oceaneye", level_name: str = "INFO") -> logging.Logger:
    """
    Configure consistent structured logging across connectors.
    Format: YYYY-MM-DD HH:MM:SS [LEVEL] name: message
    """
    numeric_level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    logger = logging.getLogger(logger_name)
    logger.setLevel(numeric_level)
    return logger


# ---------------------------------------------------------
# Event Management & Validation
# ---------------------------------------------------------

def load_events() -> dict:
    """
    Load all events from config/events.json.
    Exits cleanly if the file is missing or invalid.
    """
    if not EVENTS_FILE.exists():
        print(f"Error: Events configuration file not found at {EVENTS_FILE}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        print(f"Error: Malformed JSON in {EVENTS_FILE}: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error reading {EVENTS_FILE}: {exc}", file=sys.stderr)
        sys.exit(1)


def validate_event(event_name: str, event_data: dict) -> None:
    """
    Validate that an event configuration contains all required fields
    and that values are within valid ranges.
    Exits cleanly without traceback on validation failure.
    """
    required_fields = ["name", "latitude", "longitude", "start_date", "end_date"]
    missing = [field for field in required_fields if field not in event_data]
    if missing:
        print(
            f"Error: Event '{event_name}' in config/events.json is missing required fields: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate latitude
    lat = event_data["latitude"]
    if not isinstance(lat, (int, float)) or not (-90.0 <= lat <= 90.0):
        print(
            f"Error: Invalid latitude '{lat}' for event '{event_name}'. Must be between -90 and 90.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate longitude
    lon = event_data["longitude"]
    if not isinstance(lon, (int, float)) or not (-180.0 <= lon <= 180.0):
        print(
            f"Error: Invalid longitude '{lon}' for event '{event_name}'. Must be between -180 and 180.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate dates (YYYY-MM-DD)
    for date_field in ["start_date", "end_date"]:
        val = str(event_data[date_field])
        try:
            datetime.date.fromisoformat(val)
        except ValueError:
            print(
                f"Error: Invalid {date_field} '{val}' for event '{event_name}'. Must be YYYY-MM-DD.",
                file=sys.stderr,
            )
            sys.exit(1)

    if str(event_data["start_date"]) > str(event_data["end_date"]):
        print(
            f"Error: start_date '{event_data['start_date']}' is after end_date '{event_data['end_date']}' for event '{event_name}'.",
            file=sys.stderr,
        )
        sys.exit(1)


def get_event(event_name: str) -> dict:
    """
    Retrieve and validate an event from config/events.json.
    Exits with a clear error message if the event is not found.
    """
    events = load_events()
    if event_name not in events:
        print(f"Error: Event '{event_name}' not found in {EVENTS_FILE.name}.", file=sys.stderr)
        print("Available events:", file=sys.stderr)
        for name in sorted(events.keys()):
            print(f"  - {name}", file=sys.stderr)
        sys.exit(1)

    event_data = events[event_name]
    validate_event(event_name, event_data)
    return event_data


def get_event_bbox(event: dict) -> tuple[float, float, float, float]:
    """
    Calculate bounding box (min_lon, max_lon, min_lat, max_lat) for an event.
    Preserves Wakashio project boundaries for exact consistency.
    """
    # Established Wakashio area
    if event.get("name") == "Wakashio Oil Spill" or event.get("latitude") == -20.4 and event.get("longitude") == 57.75:
        return (56.5, 59.0, -21.5, -19.0)

    lat = float(event["latitude"])
    lon = float(event["longitude"])
    radius_km = float(event.get("radius_km", 100))
    deg_delta = radius_km / 111.0

    min_lon = round(lon - deg_delta, 2)
    max_lon = round(lon + deg_delta, 2)
    min_lat = round(lat - deg_delta, 2)
    max_lat = round(lat + deg_delta, 2)

    return (min_lon, max_lon, min_lat, max_lat)


# ---------------------------------------------------------
# Directory & Data Safety Management
# ---------------------------------------------------------

def get_data_dir(connector: str, event_name: str) -> Path:
    """
    Return standardized output directory: data/<connector>/<event_name>
    Creates directory if it does not exist.
    """
    output_dir = DATA_DIR / connector / event_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def check_existing_file(
    file_path: Path,
    overwrite: bool = False,
    logger: logging.Logger | None = None,
) -> bool:
    """
    Check if a target data file already exists.
    If it exists and overwrite is False:
        Logs info, returns True (meaning: skip download).
    If it exists and overwrite is True:
        Logs notice that file will be overwritten, returns False.
    If it does not exist:
        Returns False.
    """
    if file_path.exists():
        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        msg = f"Output file already exists: {file_path} ({size_mb:.2f} MB)"
        if not overwrite:
            if logger:
                logger.info("%s. Skipping download. Use --overwrite to re-download.", msg)
            else:
                print(f"{msg}. Skipping download. Use --overwrite to re-download.")
            return True
        else:
            if logger:
                logger.info("%s. Overwrite requested (--overwrite). Re-downloading...", msg)
            else:
                print(f"{msg}. Overwrite requested (--overwrite). Re-downloading...")
            return False
    return False


# ---------------------------------------------------------
# Network Retry Session
# ---------------------------------------------------------

def create_retry_session(
    retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
) -> requests.Session:
    """
    Create a requests Session with automatic exponential backoff retry logic.
    Max retries: 3.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
