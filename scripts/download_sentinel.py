"""
OceanEye - Sentinel-1 SAR Imagery Ingestion Connector
Searches and downloads Sentinel-1 IW GRD products from Copernicus Data Space Ecosystem (CDSE).
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
    setup_logging,
)

# ---------------------------------------------------------
# CDSE API endpoints
# ---------------------------------------------------------

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)

CATALOGUE_URL = (
    "https://catalogue.dataspace.copernicus.eu"
    "/odata/v1/Products"
)

DOWNLOAD_URL = (
    "https://download.dataspace.copernicus.eu"
    "/odata/v1/Products"
)


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

def get_access_token(session=None, logger=None):
    """Get a CDSE access token using credentials from .env."""
    if not logger:
        logger = setup_logging("download_sentinel")

    email = os.getenv("CDSE_EMAIL")
    password = os.getenv("CDSE_PASSWORD")

    if not email or not password:
        logger.error("Missing CDSE credentials in .env (CDSE_EMAIL, CDSE_PASSWORD).")
        raise RuntimeError("CDSE_EMAIL and CDSE_PASSWORD must be configured in .env")

    data = {
        "client_id": "cdse-public",
        "username": email,
        "password": password,
        "grant_type": "password",
    }

    logger.info("Requesting CDSE access token...")

    http = session or create_retry_session()

    response = http.post(
        TOKEN_URL,
        data=data,
        timeout=60,
    )

    if response.status_code != 200:
        logger.error("CDSE authentication failed with HTTP %d: %s", response.status_code, response.text[:500])
        raise RuntimeError(
            f"CDSE authentication failed: "
            f"{response.status_code}\n"
            f"{response.text[:500]}"
        )

    result = response.json()
    token = result.get("access_token")

    if not token:
        logger.error("CDSE response did not contain an access token.")
        raise RuntimeError("CDSE response did not contain an access token.")

    logger.info("CDSE authentication successful.")
    return token


# ---------------------------------------------------------
# Sentinel-1 search
# ---------------------------------------------------------

def search_sentinel(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    top: int = 10,
    session=None,
    logger=None,
):
    """
    Search Sentinel-1 IW GRD products around an event.

    The point is:
        longitude latitude

    because OData expects:
        POINT(longitude latitude)
    """
    if not logger:
        logger = setup_logging("download_sentinel")

    filters = (
        "Collection/Name eq 'SENTINEL-1' "
        "and OData.CSC.Intersects("
        "area=geography'SRID=4326;"
        f"POINT({longitude} {latitude})'"
        ") "
        "and ContentDate/Start gt "
        f"{start_date}T00:00:00.000Z "
        "and ContentDate/Start lt "
        f"{end_date}T23:59:59.999Z "
        "and Attributes/OData.CSC.StringAttribute/any("
        "att:att/Name eq 'productType' "
        "and att/OData.CSC.StringAttribute/Value eq 'IW_GRDH_1S'"
        ")"
    )

    params = {
        "$filter": filters,
        "$orderby": "ContentDate/Start asc",
        "$top": top,
    }

    print()
    print("=" * 80)
    print("OCEANEYE - SENTINEL-1 PRODUCT SEARCH")
    print("=" * 80)
    print(f"Location : {latitude}, {longitude}")
    print(f"Dates    : {start_date} -> {end_date}")
    print("Product  : IW_GRDH_1S")
    print("=" * 80)
    print()

    logger.info("Searching Sentinel-1 products via CDSE catalogue API...")
    http = session or create_retry_session()

    response = http.get(
        CATALOGUE_URL,
        params=params,
        timeout=60,
    )

    if response.status_code != 200:
        logger.error("Sentinel-1 search failed with HTTP %d: %s", response.status_code, response.text[:1000])
        raise RuntimeError(
            f"Sentinel-1 search failed: "
            f"{response.status_code}\n"
            f"{response.text[:1000]}"
        )

    products = response.json().get("value", [])
    logger.info("Found %d Sentinel-1 product(s).", len(products))
    return products


# ---------------------------------------------------------
# Print search results
# ---------------------------------------------------------

def print_products(products):
    """Display useful information about search results."""
    if not products:
        print("No Sentinel-1 products found.")
        return

    print("=" * 80)
    print(f"FOUND {len(products)} SENTINEL-1 PRODUCT(S)")
    print("=" * 80)

    for index, product in enumerate(products, start=1):
        product_id = product.get("Id")
        name = product.get("Name")
        size = product.get("ContentLength")
        online = product.get("Online")
        start = product.get("ContentDate", {}).get("Start")

        if size:
            size_gb = size / (1024 ** 3)
            size_text = f"{size_gb:.2f} GB"
        else:
            size_text = "unknown"

        print()
        print(f"[{index}]")
        print(f"ID      : {product_id}")
        print(f"Name    : {name}")
        print(f"Date    : {start}")
        print(f"Size    : {size_text}")
        print(f"Online  : {online}")

    print()
    print("=" * 80)


# ---------------------------------------------------------
# Download
# ---------------------------------------------------------

def download_product(
    product: dict,
    token: str,
    output_dir: Path,
    overwrite: bool = False,
    session=None,
    logger=None,
):
    """Download one Sentinel-1 product."""
    if not logger:
        logger = setup_logging("download_sentinel")

    product_id = product["Id"]
    product_name = product["Name"]

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / product_name

    # Check existing file safety
    if check_existing_file(output_file, overwrite=overwrite, logger=logger):
        print(f"File already exists: {output_file}")
        print("Skipping download. Use --overwrite to re-download.")
        return output_file

    url = f"{DOWNLOAD_URL}({product_id})/$value"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    print()
    print("=" * 80)
    print("DOWNLOADING SENTINEL-1 PRODUCT")
    print("=" * 80)
    print(f"Product : {product_name}")
    print(f"ID      : {product_id}")
    print(f"Output  : {output_file}")
    print("=" * 80)
    print()

    logger.info("Initiating download for product ID: %s", product_id)
    http = session or create_retry_session()

    response = http.get(
        url,
        headers=headers,
        stream=True,
        timeout=120,
    )

    if response.status_code != 200:
        logger.error("Download failed with HTTP %d: %s", response.status_code, response.text[:1000])
        raise RuntimeError(
            f"Download failed: {response.status_code}\n"
            f"{response.text[:1000]}"
        )

    total = int(response.headers.get("Content-Length", 0))
    downloaded = 0
    chunk_size = 1024 * 1024

    with open(output_file, "wb") as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue

            file.write(chunk)
            downloaded += len(chunk)

            if total:
                percent = downloaded * 100 / total
                downloaded_gb = downloaded / (1024 ** 3)
                total_gb = total / (1024 ** 3)
                print(
                    f"\rDownloaded: {downloaded_gb:.2f}/{total_gb:.2f} GB ({percent:.1f}%)",
                    end="",
                    flush=True,
                )
            else:
                downloaded_gb = downloaded / (1024 ** 3)
                print(
                    f"\rDownloaded: {downloaded_gb:.2f} GB",
                    end="",
                    flush=True,
                )

    print()
    print()
    logger.info("Download completed successfully.")
    print(f"Saved to: {output_file}")
    return output_file


# ---------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Search and download Sentinel-1 data from CDSE."
    )

    parser.add_argument(
        "--event",
        default="wakashio",
        help="Event name from config/events.json (default: wakashio)",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Maximum number of products to show (default: 10)",
    )

    parser.add_argument(
        "--download",
        type=int,
        help="Download product by result index (e.g. --download 1)",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files if they already exist",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logger = setup_logging("download_sentinel", args.log_level)

    # Validate and load event configuration (exits cleanly on invalid event)
    event = get_event(args.event)

    latitude = event["latitude"]
    longitude = event["longitude"]
    start_date = event["start_date"]
    end_date = event["end_date"]

    print()
    print("=" * 80)
    print("OCEANEYE - SENTINEL-1 INGESTION")
    print("=" * 80)
    print(f"Event: {event['name']} ({args.event})")
    print("=" * 80)

    session = create_retry_session()

    products = search_sentinel(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        top=args.top,
        session=session,
        logger=logger,
    )

    print_products(products)

    if not products:
        return

    # Search-only mode
    if args.download is None:
        print("Search complete.")
        print()
        print("To download a product, use:")
        print(
            f"python scripts/download_sentinel.py "
            f"--event {args.event} --download 1"
        )
        return

    # Validate selected result index
    index = args.download - 1
    if index < 0 or index >= len(products):
        print(f"Error: Invalid product number {args.download}. Must be between 1 and {len(products)}.", file=sys.stderr)
        sys.exit(1)

    # Authentication only when actually downloading
    token = get_access_token(session=session, logger=logger)
    event_dir = get_data_dir("sentinel", args.event)

    download_product(
        product=products[index],
        token=token,
        output_dir=event_dir,
        overwrite=args.overwrite,
        session=session,
        logger=logger,
    )


if __name__ == "__main__":
    main()
