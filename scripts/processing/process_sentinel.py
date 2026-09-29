"""
OceanEye Data Processing - Sentinel-1 SAR Product Validation & Metadata Extraction
Extracts lightweight metadata from Sentinel-1 SAFE packages without memory-intensive raster operations.
"""

import datetime
import logging
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from common import get_data_dir, setup_logging
from processing.common import get_processed_dir, save_metadata


def _parse_manifest_xml(manifest_content: bytes | str) -> dict[str, Any]:
    """
    Parse Sentinel-1 manifest.safe XML string/bytes and extract structured metadata.
    """
    if isinstance(manifest_content, str):
        root = ET.fromstring(manifest_content.encode("utf-8"))
    else:
        root = ET.fromstring(manifest_content)

    meta: dict[str, Any] = {}

    # Extract basic elements by iterating or xpath
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        text = elem.text.strip() if elem.text else ""

        if tag == "familyName" and "SAR" not in text:
            meta["platform"] = text
        elif tag == "number" and "platform" in meta and "platform_number" not in meta:
            meta["platform_number"] = text
        elif tag == "mode" and "sensor_mode" not in meta:
            meta["sensor_mode"] = text
        elif tag == "productType" and "product_type" not in meta:
            meta["product_type"] = text
        elif tag == "orbitNumber" and "orbit_number" not in meta:
            meta["orbit_number"] = int(text) if text.isdigit() else text
        elif tag == "relativeOrbitNumber" and "relative_orbit" not in meta:
            meta["relative_orbit"] = int(text) if text.isdigit() else text
        elif tag == "pass" and "pass_direction" not in meta:
            meta["pass_direction"] = text
        elif tag == "startTime" and "start_time" not in meta:
            meta["start_time"] = text
        elif tag == "stopTime" and "stop_time" not in meta:
            meta["stop_time"] = text
        elif tag == "coordinates" and "footprint_polygon" not in meta and text:
            # GML coordinates: "lat1,lon1 lat2,lon2 ..."
            points = []
            lats = []
            lons = []
            for pair in text.split():
                if "," in pair:
                    p_lat, p_lon = pair.split(",", 1)
                    try:
                        lat_f = float(p_lat)
                        lon_f = float(p_lon)
                        points.append([lat_f, lon_f])
                        lats.append(lat_f)
                        lons.append(lon_f)
                    except ValueError:
                        continue
            if points:
                meta["footprint_polygon"] = points
                meta["spatial_coverage"] = {
                    "min_lon": min(lons),
                    "max_lon": max(lons),
                    "min_lat": min(lats),
                    "max_lat": max(lats),
                }

    # Extract polarisations
    polarisations = set()
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "transmitterReceiverPolarisation" and elem.text:
            polarisations.add(elem.text.strip())
        elif tag == "polarisation" and elem.text:
            polarisations.add(elem.text.strip())

    if polarisations:
        meta["polarization"] = sorted(list(polarisations))

    return meta


def process_sentinel(
    event_name: str,
    overwrite: bool = False,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """
    Validate Sentinel-1 product and extract standardized metadata without raster decompression.
    """
    if not logger:
        logger = setup_logging("process_sentinel")

    raw_dir = get_data_dir("sentinel", event_name)
    proc_dir = get_processed_dir("sentinel", event_name)

    output_meta = proc_dir / f"{event_name}_sentinel_metadata.json"

    # Search for Sentinel-1 raw products (files or directories ending in .SAFE, .SAFE.zip, .zip)
    candidates = []
    if raw_dir.exists():
        for item in sorted(raw_dir.iterdir()):
            if "processed" in str(item):
                continue
            if item.suffix in (".SAFE", ".zip") or item.name.endswith(".SAFE"):
                candidates.append(item)

    if not candidates:
        logger.info("Sentinel-1 raw product not found for event '%s' at %s. Skipping.", event_name, raw_dir)
        return {
            "source": "sentinel",
            "event": event_name,
            "status": "skipped",
            "reason": "raw_input_not_found",
            "raw_dir": str(raw_dir),
        }

    raw_product = candidates[0]
    logger.info("Found Sentinel-1 product: %s", raw_product.name)

    # Check if already processed
    if output_meta.exists() and not overwrite:
        logger.info("Processed Sentinel-1 metadata already exists: %s. Skipping (use --overwrite to re-process).", output_meta)
        return {
            "source": "sentinel",
            "event": event_name,
            "status": "skipped_already_exists",
            "metadata_file": str(output_meta),
        }

    manifest_bytes = None
    measurement_files = []
    calibration_files = []

    # Case 1: Product is a Zip archive (including .SAFE zip files)
    if raw_product.is_file() and zipfile.is_zipfile(raw_product):
        logger.info("Reading Sentinel-1 metadata directly from ZIP package...")
        file_size_bytes = raw_product.stat().st_size

        try:
            with zipfile.ZipFile(raw_product, "r") as zf:
                namelist = zf.namelist()

                # Find manifest.safe
                manifest_matches = [n for n in namelist if n.endswith("manifest.safe")]
                if manifest_matches:
                    manifest_bytes = zf.read(manifest_matches[0])

                # Catalog measurement and calibration files
                for item_info in zf.infolist():
                    name = item_info.filename
                    if "/measurement/" in name and name.endswith((".tiff", ".tif")):
                        pol = "VV" if "-vv-" in name.lower() else ("VH" if "-vh-" in name.lower() else ("HH" if "-hh-" in name.lower() else "HV"))
                        measurement_files.append({
                            "filename": Path(name).name,
                            "relative_path": name,
                            "polarization": pol,
                            "size_bytes": item_info.file_size,
                            "size_mb": round(item_info.file_size / (1024 * 1024), 2),
                        })
                    elif "/annotation/calibration/" in name and name.endswith(".xml"):
                        calibration_files.append({
                            "filename": Path(name).name,
                            "relative_path": name,
                        })
        except Exception as exc:
            logger.error("Error inspecting Sentinel-1 ZIP file %s: %s", raw_product, exc)
            return {"source": "sentinel", "event": event_name, "status": "failed", "error": str(exc)}

    # Case 2: Product is an extracted directory
    elif raw_product.is_dir():
        logger.info("Reading Sentinel-1 metadata from extracted SAFE directory...")
        file_size_bytes = sum(f.stat().st_size for f in raw_product.glob("**/*") if f.is_file())

        manifest_path = raw_product / "manifest.safe"
        if manifest_path.exists():
            manifest_bytes = manifest_path.read_bytes()

        for tiff in raw_product.glob("measurement/*.tiff"):
            pol = "VV" if "-vv-" in tiff.name.lower() else ("VH" if "-vh-" in tiff.name.lower() else "unknown")
            measurement_files.append({
                "filename": tiff.name,
                "relative_path": str(tiff.relative_to(raw_product)),
                "polarization": pol,
                "size_bytes": tiff.stat().st_size,
                "size_mb": round(tiff.stat().st_size / (1024 * 1024), 2),
            })
        for cal in raw_product.glob("annotation/calibration/*.xml"):
            calibration_files.append({
                "filename": cal.name,
                "relative_path": str(cal.relative_to(raw_product)),
            })
    else:
        logger.warning("Unrecognized Sentinel-1 format: %s", raw_product)
        return {"source": "sentinel", "event": event_name, "status": "unsupported_format", "raw_product": str(raw_product)}

    # Parse manifest XML
    manifest_meta = {}
    if manifest_bytes:
        try:
            manifest_meta = _parse_manifest_xml(manifest_bytes)
        except Exception as exc:
            logger.warning("Failed to parse manifest XML: %s", exc)

    # Derive product type and properties from filename if not in XML
    prod_name = raw_product.stem
    if prod_name.startswith("S1A") or prod_name.startswith("S1B"):
        tokens = prod_name.split("_")
        if len(tokens) >= 5:
            manifest_meta.setdefault("platform", tokens[0][:3])
            manifest_meta.setdefault("sensor_mode", tokens[1])
            manifest_meta.setdefault("product_type", tokens[2][:3])

    # Assemble comprehensive standardized metadata
    metadata = {
        "event": event_name,
        "source": "sentinel_1_sar",
        "processing_status": "success",
        "product_name": raw_product.name,
        "product_id": raw_product.stem,
        "raw_product_path": str(raw_product),
        "package_type": "zip_safe" if raw_product.is_file() else "directory_safe",
        "raw_file_size_bytes": file_size_bytes,
        "raw_file_size_gb": round(file_size_bytes / (1024**3), 3),
        "platform": manifest_meta.get("platform", "Sentinel-1"),
        "sensor_mode": manifest_meta.get("sensor_mode", "IW"),
        "product_type": manifest_meta.get("product_type", "GRD"),
        "polarization": manifest_meta.get("polarization", [m["polarization"] for m in measurement_files if "polarization" in m]),
        "pass_direction": manifest_meta.get("pass_direction", "UNKNOWN"),
        "orbit_number": manifest_meta.get("orbit_number", None),
        "temporal_coverage": {
            "start": manifest_meta.get("start_time", None),
            "stop": manifest_meta.get("stop_time", None),
        },
        "spatial_coverage": manifest_meta.get("spatial_coverage", {}),
        "footprint_polygon": manifest_meta.get("footprint_polygon", []),
        "measurement_files": measurement_files,
        "calibration_files": calibration_files,
        "future_sar_preprocessing_roadmap": {
            "required_steps": [
                "1. Radiometric Calibration (Sigma0/Gamma0 computation)",
                "2. Speckle Filtering (Lee / Refined Lee filter)",
                "3. Range Doppler Terrain Correction (SRTM/Copernicus DEM)",
                "4. Adaptive Dark-Spot Thresholding for Oil Slick Detection",
            ],
            "notes": "Full raster preprocessing deferred to Prompt 4/5 pipeline.",
        },
        "processing_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    save_metadata(metadata, output_meta)
    logger.info("Saved Sentinel-1 metadata to %s", output_meta)

    return {
        "source": "sentinel",
        "event": event_name,
        "status": "success",
        "product_name": raw_product.name,
        "metadata_file": str(output_meta),
    }
