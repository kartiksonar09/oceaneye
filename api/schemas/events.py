"""
Events API Pydantic schemas.
"""

from typing import Any
from pydantic import BaseModel, Field


class EventSummary(BaseModel):
    """Concise representation of an ocean event."""
    event_id: str = Field(..., description="Unique event slug/identifier", example="wakashio")
    name: str = Field(..., description="Full descriptive name of the event", example="Wakashio Oil Spill")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Center latitude in degrees", example=-20.4)
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Center longitude in degrees", example=57.75)
    start_date: str = Field(..., description="Start date YYYY-MM-DD", example="2020-08-05")
    end_date: str = Field(..., description="End date YYYY-MM-DD", example="2020-08-17")
    radius_km: float = Field(..., gt=0, description="Operational radius in kilometers", example=100.0)


class EventDetail(EventSummary):
    """Comprehensive event metadata including bounding box and availability flags."""
    bounding_box: dict[str, float] = Field(
        ...,
        description="Bounding coordinates {min_lon, max_lon, min_lat, max_lat}",
        example={"min_lon": 56.5, "max_lon": 59.0, "min_lat": -21.5, "max_lat": -19.0},
    )
    data_availability: dict[str, bool] = Field(
        default_factory=dict,
        description="Availability of multi-source data outputs (sentinel, cmems, drift, attribution)",
        example={"sentinel": True, "cmems": True, "drift": True, "attribution": True},
    )
