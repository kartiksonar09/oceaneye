"""
OceanEye - AIS Vessel Tracking Ingestion Connector
Fetches automatic identification system (AIS) vessel positions from AISHub API.
"""

import argparse
import os
import sys
from pathlib import Path

from common import (
    check_existing_file,
    create_retry_session,
    get_data_dir,
    get_event,
    get_event_bbox,
    setup_logging,
)

AISHUB_API_URL = "https://data.aishub.net/ws.php"


def download_ais(
    event_name: str,
    min_lon: float,
    max_lon: float,
    min_lat: float,
    max_lat: float,
    overwrite: bool = False,
    logger=None,
):
    """
    Fetch AIS vessel data for a given event region using the AISHub API.
    """
    if not logger:
        logger = setup_logging("download_ais")

    aishub_username = os.getenv("AISHUB_USERNAME")
    if not aishub_username:
        logger.error("AISHUB_USERNAME is missing from environment / .env file.")
        print("ERROR: AISHUB_USERNAME is not configured in .env", file=sys.stderr)
        return None

    output_dir = get_data_dir("ais", event_name)
    output_file = output_dir / f"{event_name}_ais.csv"

    print()
    print("=" * 80)
    print("OCEANEYE - AIS VESSEL TRACKING INGESTION")
    print("=" * 80)
    print(f"Event       : {event_name}")
    print(f"Bounding box: lon [{min_lon}, {max_lon}], lat [{min_lat}, {max_lat}]")
    print(f"Output file : {output_file}")
    print("=" * 80)
    print()

    # Safety check: avoid re-downloading if file exists and overwrite is not requested
    if check_existing_file(output_file, overwrite=overwrite, logger=logger):
        print(f"File already exists: {output_file}")
        print("Skipping download. Use --overwrite to re-download.")
        return output_file

    params = {
        "username": aishub_username,
        "format": 1,
        "output": "csv",
        "compress": 0,
        "latmin": min_lat,
        "latmax": max_lat,
        "lonmin": min_lon,
        "lonmax": max_lon,
    }

    logger.info("Connecting to AISHub API for event '%s'...", event_name)
    logger.debug("AISHub parameters: %s", {k: v for k, v in params.items() if k != "username"})

    session = create_retry_session()

    try:
        response = session.get(
            AISHUB_API_URL,
            params=params,
            timeout=60,
        )
        response.raise_for_status()

        data = response.text.strip()

        # Check for AISHub specific error responses
        if "Invalid username or password" in data:
            logger.error("AISHub authentication failed: Invalid username or password.")
            print("\nERROR: AISHub rejected the username. Verify AISHUB_USERNAME in your .env file.", file=sys.stderr)
            return None

        if "ERROR" in data:
            logger.error("AISHub returned error response: %s", data[:200])
            print(f"\nERROR from AISHub API: {data[:200]}", file=sys.stderr)
            return None

        if not data:
            logger.warning("AISHub returned empty data for the specified bounding box.")
            print("\nWARNING: AISHub returned empty data for this region.", file=sys.stderr)
            return None

        # Write output CSV
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(data)

        logger.info("AIS data downloaded successfully.")
        print(f"\nAIS data saved to: {output_file}")
        return output_file

    except Exception as exc:
        logger.exception("Error connecting to AISHub: %s", exc)
        print(f"\nERROR connecting to AISHub: {exc}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Fetch AIS vessel data for an event from AISHub API."
    )

    parser.add_argument(
        "--event",
        default="wakashio",
        help="Event name from config/events.json (default: wakashio)",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files if they already exist",
    )

    parser.add_argument(
        "--min-lon",
        type=float,
        help="Minimum longitude (overrides event bounding box)",
    )

    parser.add_argument(
        "--max-lon",
        type=float,
        help="Maximum longitude (overrides event bounding box)",
    )

    parser.add_argument(
        "--min-lat",
        type=float,
        help="Minimum latitude (overrides event bounding box)",
    )

    parser.add_argument(
        "--max-lat",
        type=float,
        help="Maximum latitude (overrides event bounding box)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logger = setup_logging("download_ais", args.log_level)

    # Validate and load event configuration (exits cleanly on invalid event)
    event_info = get_event(args.event)

    # Determine bounding box
    default_min_lon, default_max_lon, default_min_lat, default_max_lat = get_event_bbox(event_info)
    min_lon = args.min_lon if args.min_lon is not None else default_min_lon
    max_lon = args.max_lon if args.max_lon is not None else default_max_lon
    min_lat = args.min_lat if args.min_lat is not None else default_min_lat
    max_lat = args.max_lat if args.max_lat is not None else default_max_lat

    download_ais(
        event_name=args.event,
        min_lon=min_lon,
        max_lon=max_lon,
        min_lat=min_lat,
        max_lat=max_lat,
        overwrite=args.overwrite,
        logger=logger,
    )


if __name__ == "__main__":
    main()
