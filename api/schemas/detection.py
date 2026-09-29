"""
Detection API Pydantic schemas.
"""

from typing import Any
from pydantic import BaseModel, Field
from api.schemas.common import GeoJSONGeometry


class DetectionResponse(BaseModel):
    """
    Sentinel-1 SAR observation metadata and oil spill detection response.
    Explicitly enforces `geometry: null` when pixel-level segmentation mask is unavailable.
    """
    event_id: str = Field(..., description="Unique event identifier", example="wakashio")
    detection_status: str = Field(..., description="Detection processing status", example="metadata_available")
    geometry: GeoJSONGeometry | None = Field(
        None,
        description="Spill polygon geometry (null unless verified pixel segmentation exists)",
    )
    geometry_notice: str = Field(
        ...,
        description="Explanation of geometry availability",
        example="Pixel-level segmentation mask unavailable. Satellite scene footprint bounds are provided in metadata.",
    )
    acquisition_timestamp: str | None = Field(
        None, description="UTC ISO-8601 acquisition time", example="2020-08-10T01:37:55.041956Z"
    )
    platform: str | None = Field(None, description="Satellite platform name", example="Synthetic Aperture Radar")
    sensor_mode: str | None = Field(None, description="SAR sensor mode", example="IW")
    product_type: str | None = Field(None, description="SAR product type", example="GRD")
    product_id: str | None = Field(None, description="Sentinel-1 SAFE product identifier")
    polarization: list[str] | None = Field(None, description="SAR transmit/receive polarizations", example=["VH", "VV"])
    orbit_number: int | None = Field(None, description="Absolute orbit number", example=22854)
    pass_direction: str | None = Field(None, description="Orbit pass direction", example="DESCENDING")
    footprint_polygon: list[list[float]] | None = Field(
        None,
        description="Satellite scene acquisition footprint [[lat, lon], ...] (not a spill geometry)",
    )
    detection_source: str | None = Field(
        None, description="Source of detection coordinates", example="Sentinel-1 Metadata"
    )
    model_status: str = Field("trained_synthetic_baseline", description="Phase 3 U-Net model deployment status")
    validation_data_mode: str = Field("satellite_metadata", description="Data validation mode")
    disclaimer: str = Field(..., description="SAR detection scientific disclaimer")
