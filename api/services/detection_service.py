"""
Detection Service.
Extracts Sentinel-1 SAR observation metadata and ensures strict geometry contracts.
"""

import json
from pathlib import Path
from typing import Any

from api.config import DATA_DIR, SAR_DETECTION_DISCLAIMER
from api.schemas.detection import DetectionResponse
from api.services.event_service import EventService


class DetectionService:
    """Service managing Sentinel-1 SAR detections and metadata."""

    @classmethod
    def get_detection(cls, event_id: str) -> DetectionResponse | None:
        """
        Retrieve Sentinel-1 SAR detection metadata for an event.
        Returns None if event does not exist in event configuration.
        Explicitly enforces geometry=None when a pixel-level segmentation mask is not present.
        """
        event = EventService.get_event(event_id)
        if not event:
            return None

        meta_file = DATA_DIR / "sentinel" / event_id / "processed" / f"{event_id}_sentinel_metadata.json"
        
        if not meta_file.exists():
            return DetectionResponse(
                event_id=event_id,
                detection_status="no_sentinel_data",
                geometry=None,
                geometry_notice="No Sentinel-1 satellite imagery has been processed for this event.",
                acquisition_timestamp=f"{event.start_date}T00:00:00Z",
                platform=None,
                sensor_mode=None,
                product_type=None,
                product_id=None,
                polarization=None,
                orbit_number=None,
                pass_direction=None,
                footprint_polygon=None,
                detection_source="event_config",
                model_status="trained_synthetic_baseline",
                validation_data_mode="event_coordinates",
                disclaimer=SAR_DETECTION_DISCLAIMER,
            )

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            temp_cov = meta.get("temporal_coverage", {})
            acq_time = temp_cov.get("start")
            if acq_time and not acq_time.endswith("Z") and "+" not in acq_time:
                acq_time += "Z"

            # Strict contract: geometry is null because footprint is a satellite scene boundary,
            # not a pixel-level oil slick polygon.
            return DetectionResponse(
                event_id=event_id,
                detection_status="metadata_available",
                geometry=None,
                geometry_notice=(
                    "Pixel-level segmentation mask is unavailable for this event; geometry is null. "
                    "The footprint_polygon in metadata represents the satellite acquisition boundary, "
                    "not an oil spill polygon."
                ),
                acquisition_timestamp=acq_time,
                platform=meta.get("platform", "Synthetic Aperture Radar"),
                sensor_mode=meta.get("sensor_mode", "IW"),
                product_type=meta.get("product_type", "GRD"),
                product_id=meta.get("product_id"),
                polarization=meta.get("polarization", []),
                orbit_number=meta.get("orbit_number"),
                pass_direction=meta.get("pass_direction"),
                footprint_polygon=meta.get("footprint_polygon"),
                detection_source=f"Sentinel-1 SAFE Metadata ({meta.get('product_id', 'SAFE')})",
                model_status="trained_synthetic_baseline",
                validation_data_mode="satellite_metadata",
                disclaimer=SAR_DETECTION_DISCLAIMER,
            )
        except Exception:
            return DetectionResponse(
                event_id=event_id,
                detection_status="metadata_read_error",
                geometry=None,
                geometry_notice="Failed to parse Sentinel-1 metadata file.",
                disclaimer=SAR_DETECTION_DISCLAIMER,
            )
