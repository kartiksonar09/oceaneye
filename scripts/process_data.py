"""
OceanEye - Master Data Processing, Validation & Normalization CLI
Orchestrates multi-source scientific data cleaning, coordinate validation,
derived variable computation, and standardized metadata generation.
"""

import argparse
import sys
from pathlib import Path

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import get_event, setup_logging
from processing.process_ais import process_ais
from processing.process_cmems import process_currents
from processing.process_sentinel import process_sentinel
from processing.process_wind import process_wind


def print_header(event_name: str, event_info: dict, source_choice: str):
    print()
    print("=" * 80)
    print("OCEANEYE - DATA PROCESSING & NORMALIZATION LAYER")
    print("=" * 80)
    print(f"Event        : {event_info.get('name', event_name)} ({event_name})")
    print(f"Coordinates  : lat {event_info.get('latitude')}, lon {event_info.get('longitude')}")
    print(f"Event Dates  : {event_info.get('start_date')} -> {event_info.get('end_date')}")
    print(f"Source Scope : {source_choice.upper()}")
    print("=" * 80)
    print()


def print_summary_card(title: str, result: dict):
    status = result.get("status", "unknown")
    status_display = {
        "success": "[SUCCESS] Processed & Standardized",
        "skipped": "[SKIPPED] Raw input not found",
        "skipped_already_exists": "[SKIPPED] Processed output already exists",
        "empty_raw_file": "[WARNING] Raw input file is empty",
        "invalid_raw_data": "[WARNING] Raw data contains API error / invalid format",
        "failed": "[FAILED] Processing error encountered",
    }.get(status, f"[{status.upper()}]")

    print(f"--- {title} ---")
    print(f"Status       : {status_display}")

    if "output_file" in result:
        print(f"Output File  : {result['output_file']}")
    if "metadata_file" in result:
        print(f"Metadata     : {result['metadata_file']}")
    if "input_records" in result and "output_records" in result:
        print(f"Records      : {result['input_records']} input -> {result['output_records']} valid output")
    if "product_name" in result:
        print(f"Product      : {result['product_name']}")
    if "reason" in result and result["reason"] == "raw_input_not_found":
        print(f"Notice       : No raw dataset found in {result.get('raw_dir') or result.get('raw_file')}")
    if "error" in result:
        print(f"Error        : {result['error']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="OceanEye Data Processing, Validation & Normalization CLI"
    )

    parser.add_argument(
        "--event",
        default="wakashio",
        help="Event name from config/events.json (default: wakashio)",
    )

    parser.add_argument(
        "--source",
        default="all",
        choices=["all", "ais", "currents", "cmems_currents", "wind", "cmems_wind", "sentinel", "sentinel1"],
        help="Data source to process (default: all)",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing processed files if they already exist",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logger = setup_logging("process_data", args.log_level)

    # Validate and load event configuration (exits cleanly without traceback on invalid event)
    event_info = get_event(args.event)

    print_header(args.event, event_info, args.source)

    results = {}
    has_failure = False

    # Dispatch AIS Processing
    if args.source in ("all", "ais"):
        logger.info("Processing AIS data for event '%s'...", args.event)
        res = process_ais(event_name=args.event, overwrite=args.overwrite, logger=logger)
        results["AIS Vessel Tracking"] = res
        if res.get("status") == "failed":
            has_failure = True

    # Dispatch CMEMS Current Processing
    if args.source in ("all", "currents", "cmems_currents"):
        logger.info("Processing CMEMS ocean currents for event '%s'...", args.event)
        res = process_currents(event_name=args.event, overwrite=args.overwrite, logger=logger)
        results["CMEMS Ocean Currents"] = res
        if res.get("status") == "failed":
            has_failure = True

    # Dispatch CMEMS Wind Processing
    if args.source in ("all", "wind", "cmems_wind"):
        logger.info("Processing CMEMS wind observations for event '%s'...", args.event)
        res = process_wind(event_name=args.event, overwrite=args.overwrite, logger=logger)
        results["CMEMS Wind Observations"] = res
        if res.get("status") == "failed":
            has_failure = True

    # Dispatch Sentinel-1 SAR Metadata Processing
    if args.source in ("all", "sentinel", "sentinel1"):
        logger.info("Processing Sentinel-1 SAR product metadata for event '%s'...", args.event)
        res = process_sentinel(event_name=args.event, overwrite=args.overwrite, logger=logger)
        results["Sentinel-1 SAR Imagery"] = res
        if res.get("status") == "failed":
            has_failure = True

    # Print Summary Report
    print("=" * 80)
    print("PROCESSING SUMMARY REPORT")
    print("=" * 80)
    for title, res in results.items():
        print_summary_card(title, res)
    print("=" * 80)

    if has_failure:
        logger.error("One or more data sources encountered processing failures.")
        sys.exit(1)
    else:
        logger.info("Data processing stage completed successfully.")


if __name__ == "__main__":
    main()
