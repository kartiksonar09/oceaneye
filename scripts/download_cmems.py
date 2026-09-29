"""
OceanEye - CMEMS Ocean Current Ingestion Connector
Downloads Copernicus Marine physical ocean analysis and forecast data.
"""

import argparse
import base64
import configparser
import os
import sys
from pathlib import Path

import copernicusmarine

from common import (
    PROJECT_ROOT,
    check_existing_file,
    get_data_dir,
    get_event,
    get_event_bbox,
    setup_logging,
)

# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

DEFAULT_CREDENTIALS_FILE = (
    Path.home() / ".copernicusmarine" / ".copernicusmarine-credentials"
)

CURRENT_DATASET = "cmems_mod_glo_phy_my_0.083deg_P1D-m"


# ---------------------------------------------------------
# Credentials Management
# ---------------------------------------------------------

def load_cmems_credentials(credentials_file=None):
    """
    Load credentials from the given credentials_file or the default
    ~/.copernicusmarine/.copernicusmarine-credentials file.

    Supports both base64-encoded Copernicus Marine files and standard INI files.
    Falls back to environment variables (COPERNICUSMARINE_SERVICE_USERNAME / CMEMS_USERNAME)
    if not found in the file.

    Returns:
        tuple: (Path to existing credentials file or None, username or None, password or None)
    """
    logger = setup_logging("download_cmems")
    cred_path = (
        Path(credentials_file).expanduser().resolve()
        if credentials_file
        else DEFAULT_CREDENTIALS_FILE
    )

    username = None
    password = None

    if cred_path.exists():
        logger.info("Reading credentials from file: %s", cred_path)
        try:
            raw_content = cred_path.read_text().strip()
            try:
                decoded = base64.standard_b64decode(raw_content).decode("utf-8")
            except Exception:
                decoded = raw_content

            config = configparser.RawConfigParser()
            config.read_string(decoded)
            if config.has_section("credentials"):
                username = config.get("credentials", "username", fallback=None)
                password = config.get("credentials", "password", fallback=None)
        except Exception as exc:
            logger.warning("Failed to parse credentials file %s: %s", cred_path, exc)
    else:
        if credentials_file:
            logger.error("Explicit credentials file not found: %s", cred_path)
            raise FileNotFoundError(f"Credentials file not found: {cred_path}")
        logger.info("Default credentials file not found at %s. Checking environment...", cred_path)

    # Fallback to environment variables
    if not username or not password:
        env_user = os.getenv("COPERNICUSMARINE_SERVICE_USERNAME") or os.getenv("CMEMS_USERNAME")
        env_pass = os.getenv("COPERNICUSMARINE_SERVICE_PASSWORD") or os.getenv("CMEMS_PASSWORD")
        if env_user and env_pass:
            logger.info("Loaded Copernicus Marine credentials from environment variables.")
            username = env_user
            password = env_pass

    if username:
        logger.info("Copernicus Marine user: '%s'", username)
    else:
        logger.warning("No Copernicus Marine credentials found in file or environment.")

    return (cred_path if cred_path.exists() else None, username, password)


def diagnose_cas_failure(username: str | None, password: str | None, logger=None):
    """
    Directly query the Copernicus Marine CAS token endpoint to give explicit diagnostic
    feedback when authentication fails.
    """
    if not logger:
        logger = setup_logging("download_cmems")

    if not username or not password:
        logger.error("Authentication check skipped: Username or password is empty.")
        return

    import requests

    token_url = "https://auth.marine.copernicus.eu/realms/MIS/protocol/openid-connect/token"
    payload = {
        "client_id": "toolbox",
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": "openid profile email",
    }

    try:
        resp = requests.post(token_url, data=payload, timeout=15)
        if resp.status_code == 200:
            logger.info("Direct CAS token endpoint test succeeded (HTTP 200).")
        elif resp.status_code in (400, 401):
            try:
                err_data = resp.json()
                desc = err_data.get("error_description", err_data.get("error", "Unknown auth error"))
            except Exception:
                desc = resp.text[:200]
            logger.error("CAS Authentication Server rejected credentials (HTTP %d): %s", resp.status_code, desc)
        else:
            logger.error(
                "CAS Authentication Server returned unexpected status HTTP %d: %s",
                resp.status_code,
                resp.text[:200],
            )
    except Exception as exc:
        logger.error("Unable to connect to CAS Authentication Server: %s", exc)


# ---------------------------------------------------------
# CMEMS Currents Ingestion
# ---------------------------------------------------------

def download_currents(
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
    Download CMEMS ocean current data for a specified event and region.
    """
    if not logger:
        logger = setup_logging("download_cmems")

    output_dir = get_data_dir("cmems", event_name)
    output_file = output_dir / f"{event_name}_currents.nc"

    print()
    print("=" * 80)
    print("OCEANEYE - CMEMS CURRENT DATA INGESTION")
    print("=" * 80)
    print(f"Event       : {event_name}")
    print(f"Dataset     : {CURRENT_DATASET}")
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

    # Load and validate credentials
    cred_path, username, password = load_cmems_credentials(credentials_file)

    logger.info("Initiating CMEMS current data download via copernicusmarine API...")
    logger.debug(
        "Request parameters: dataset=%s, variables=['uo', 'vo'], start=%sT00:00:00, end=%sT23:59:59, "
        "lon=[%f, %f], lat=[%f, %f], credentials_file=%s",
        CURRENT_DATASET,
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
            dataset_id=CURRENT_DATASET,
            variables=["uo", "vo"],
            minimum_longitude=minimum_longitude,
            maximum_longitude=maximum_longitude,
            minimum_latitude=minimum_latitude,
            maximum_latitude=maximum_latitude,
            start_datetime=f"{start_date}T00:00:00",
            end_datetime=f"{end_date}T23:59:59",
            output_filename=output_file.name,
            output_directory=str(output_dir),
            overwrite=True,
            credentials_file=str(cred_path) if cred_path else None,
        )

        print()
        logger.info("CMEMS current download completed successfully.")
        print(f"Saved to: {output_file}")
        return output_file

    except copernicusmarine.core_functions.credentials_utils.CouldNotConnectToAuthenticationSystem:
        logger.error("Authentication failed: CouldNotConnectToAuthenticationSystem")
        print("\n" + "!" * 80)
        print("AUTHENTICATION ERROR: Could not authenticate with Copernicus Marine Service.")
        print("!" * 80)
        diagnose_cas_failure(username, password, logger=logger)
        print("\nTroubleshooting Steps:")
        print(f"1. Check the credentials file: {cred_path or DEFAULT_CREDENTIALS_FILE}")
        print("2. Re-authenticate using the official Copernicus Marine CLI command:")
        print("   copernicusmarine login --force-overwrite")
        print("3. Or verify/update CMEMS_USERNAME and CMEMS_PASSWORD in your .env file.")
        print("!" * 80 + "\n")
        raise

    except Exception as exc:
        logger.exception("Unexpected error during CMEMS download: %s", exc)
        raise


# ---------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Download CMEMS ocean current data for an event using Copernicus Marine API."
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
    logger = setup_logging("download_cmems", args.log_level)

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

    download_currents(
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
