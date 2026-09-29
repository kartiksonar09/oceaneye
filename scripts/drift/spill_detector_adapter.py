"""
OceanEye Spill Detection Adapter Layer
Defines clean interfaces for obtaining spill candidate coordinates and timestamps:
1. SegmentationInferenceAdapter: Consumes Phase 3 U-Net pixel segmentation masks/clusters
2. SentinelMetadataAdapter: Extracts footprint centroids from Sentinel-1 SAFE metadata
3. EventConfigAdapter: Uses default incident coordinates from config/events.json
"""

import json
from pathlib import Path
from typing import Any

import numpy as np


class SpillDetectionAdapter:
    """
    Standardized adapter resolving spill detection locations and timestamps.
    Explicitly tracks the origin source type to prevent misrepresenting metadata
    centroids as model-derived pixel detections.
    """

    @staticmethod
    def from_segmentation_output(detection_result: dict[str, Any]) -> dict[str, Any]:
        """
        Adapter for future Phase 3 segmentation model inference outputs.
        Expects georeferenced candidate slick cluster or detection dictionary.
        """
        return {
            "latitude": float(detection_result["latitude"]),
            "longitude": float(detection_result["longitude"]),
            "timestamp": str(detection_result["timestamp"]),
            "detection_source_type": "phase3_segmentation_inference",
            "detection_source_name": detection_result.get("model_name", "U-Net SAR Segmentation"),
            "confidence": float(detection_result.get("confidence", 1.0)),
            "area_km2": float(detection_result.get("area_km2", 0.0)),
        }

    @staticmethod
    def from_sentinel_metadata(metadata_path: Path | str) -> dict[str, Any] | None:
        """
        Adapter extracting observation timestamp and spatial centroid from
        Sentinel-1 SAFE metadata JSON (Phase 2 normalization layer).
        """
        p = Path(metadata_path)
        if not p.exists():
            return None

        try:
            with open(p, "r", encoding="utf-8") as f:
                meta = json.load(f)

            poly = meta.get("footprint_polygon", [])
            if poly:
                avg_lat = float(np.mean([pt[0] for pt in poly]))
                avg_lon = float(np.mean([pt[1] for pt in poly]))
            else:
                return None

            t_start = meta.get("temporal_coverage", {}).get("start")
            if not t_start:
                return None

            timestamp = t_start
            if not timestamp.endswith("Z") and "+" not in timestamp:
                timestamp += "Z"

            return {
                "latitude": round(avg_lat, 5),
                "longitude": round(avg_lon, 5),
                "timestamp": timestamp,
                "detection_source_type": "sentinel1_metadata_centroid",
                "detection_source_name": meta.get("product_id", "Sentinel-1 Product"),
                "confidence": None,
                "area_km2": None,
            }
        except Exception:
            return None

    @staticmethod
    def from_event_config(event_name: str, event_info: dict[str, Any]) -> dict[str, Any]:
        """
        Adapter extracting default coordinates from config/events.json.
        """
        return {
            "latitude": float(event_info["latitude"]),
            "longitude": float(event_info["longitude"]),
            "timestamp": f"{event_info['start_date']}T06:00:00Z",
            "detection_source_type": "event_config_center",
            "detection_source_name": f"config/events.json ({event_name})",
            "confidence": None,
            "area_km2": None,
        }
