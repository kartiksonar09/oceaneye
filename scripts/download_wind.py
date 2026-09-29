"""
OceanEye - CMEMS Wind Data Ingestion Connector
Downloads Copernicus Marine historical global hourly wind observation data.
"""

import argparse
import sys
from pathlib import Path

import copernicusmarine

from common import (
    check_existing_file,
    get_data_dir,
    get_event,
    get_event_bbox,
    setup_logging,
)
from download_cmems import DEFAULT_CREDENTIALS_FILE, load_cmems_credentials

# ---------------------------------------------------------
# Dataset Configuration
# ---------------------------------------------------------

DATASET_ID = "cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H"


def download_wind(
    event_name: str,
    start_date: str,
    end_date: str,
    minimum_longitude: float,
    maximum_longitude: float,
    minimum_latitude: float,
    maximum_latitude: float,
    credentials_file: Path | str | None = None,
    overwrite: bool = False,
    logger=None,
):
    """
    Download CMEMS historical wind data for a given event and bounding box.
    """
    if not logger:
        logger = setup_logging("download_wind")

    output_dir = get_data_dir("cmems", event_name)
    output_file = output_dir / f"{event_name}_wind.nc"

    print()
    print("=" * 80)
    print("OCEANEYE - CMEMS WIND DATA INGESTION")
    print("=" * 80)
    print(f"Event       : {event_name}")
    print(f"Dataset     : {DATASET_ID}")
    print(f"Dates       : {start_date} -> {end_date}")
    print(
        f"Bounding box: {minimum_longitude}, {minimum_latitude} "
        f"to {maximum_longitude}, {maximum_latitude}"
    )
    print(f"Output file : {output_file}")
    print("=" * 80)
    print()

    # Safety check: avoid re-downloading if file exists and overwrite is not requested
    if check_existing_file(output_file, overwrite=overwrite, logger=logger):
        print(f"File already exists: {output_file}")
        print("Skipping download. Use --overwrite to re-download.")
        return output_file

    # Load credentials (reusing shared CMEMS credential resolver)
    cred_path, username, _ = load_cmems_credentials(credentials_file)

    logger.info("Initiating CMEMS historical wind download via copernicusmarine API...")
    logger.debug(
        "Request parameters: dataset=%s, variables=['eastward_wind', 'northward_wind'], "
        "start=%s, end=%s, lon=[%f, %f], lat=[%f, %f], credentials_file=%s",
        DATASET_ID,
        start_date,
        end_date,
        minimum_longitude,
        maximum_longitude,
        minimum_latitude,
        maximum_latitude,
        cred_path,
    )

    try:
        copernicusmarine.subset(
            dataset_id=DATASET_ID,
            variables=["eastward_wind", "northward_wind"],
            minimum_longitude=minimum_longitude,
            maximum_longitude=maximum_longitude,
            minimum_latitude=minimum_latitude,
            maximum_latitude=maximum_latitude,
            start_datetime=start_date,
            end_datetime=end_date,
            output_directory=str(output_dir),
            output_filename=output_file.name,
            overwrite=True,
            credentials_file=str(cred_path) if cred_path else None,
        )

        print()
        logger.info("CMEMS wind data downloaded successfully.")
        print(f"Saved to: {output_file}")
        return output_file

    except Exception as exc:
        logger.exception("Failed to download CMEMS wind data: %s", exc)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Download CMEMS historical wind data for an event."
    )

    parser.add_argument(
        "--event",
        default="wakashio",
        help="Event name from config/events.json (default: wakashio)",
    )

    parser.add_argument(
        "--credentials-file",
        default=str(DEFAULT_CREDENTIALS_FILE) if DEFAULT_CREDENTIALS_FILE.exists() else None,
        help=(
            "Explicit path to Copernicus Marine credentials file "
            f"(default: {DEFAULT_CREDENTIALS_FILE})"
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files if they already exist",
    )

    parser.add_argument(
        "--start",
        help="Start date YYYY-MM-DD (overrides event start date)",
    )

    parser.add_argument(
        "--end",
        help="End date YYYY-MM-DD (overrides event end date)",
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
    logger = setup_logging("download_wind", args.log_level)

    # Validate and load event configuration (exits cleanly on invalid event)
    event_info = get_event(args.event)

    # Determine dates
    start_date = args.start or event_info["start_date"]
    end_date = args.end or event_info["end_date"]

    # Determine bounding box
    default_min_lon, default_max_lon, default_min_lat, default_max_lat = get_event_bbox(event_info)
    min_lon = args.min_lon if args.min_lon is not None else default_min_lon
    max_lon = args.max_lon if args.max_lon is not None else default_max_lon
    min_lat = args.min_lat if args.min_lat is not None else default_min_lat
    max_lat = args.max_lat if args.max_lat is not None else default_max_lat

    download_wind(
        event_name=args.event,
        start_date=start_date,
        end_date=end_date,
        minimum_longitude=min_lon,
        maximum_longitude=max_lon,
        minimum_latitude=min_lat,
        maximum_latitude=max_lat,
        credentials_file=args.credentials_file,
        overwrite=args.overwrite,
        logger=logger,
    )


if __name__ == "__main__":
    main()
