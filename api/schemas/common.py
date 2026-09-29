"""
Common and GeoJSON Pydantic schemas.
"""

from typing import Any, Generic, Literal, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ServiceStatusResponse(BaseModel):
    """Basic root status response."""
    status: str = Field(..., example="ok")
    app_name: str = Field(..., example="OceanEye Maritime Intelligence API")
    version: str = Field(..., example="1.0.0")
    docs_url: str = Field("/docs", example="/docs")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field("healthy", example="healthy")
    version: str = Field("1.0.0", example="1.0.0")
    app_name: str = Field("OceanEye Maritime Intelligence API", example="OceanEye Maritime Intelligence API")
    timestamp: str = Field(..., example="2026-09-21T23:00:00Z")


class ErrorResponse(BaseModel):
    """Standardized error response envelope."""
    detail: str = Field(..., example="Event 'unknown_event' not found")


class GeoJSONGeometry(BaseModel):
    """Base GeoJSON geometry object."""
    type: str = Field(..., example="LineString")
    coordinates: Any = Field(...)


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature representation."""
    type: Literal["Feature"] = "Feature"
    geometry: GeoJSONGeometry | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
