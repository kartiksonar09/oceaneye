"""
Drift API Pydantic schemas.
"""

from typing import Any
from pydantic import BaseModel, Field, field_validator
from api.schemas.common import GeoJSONFeature
from api.config import (
    DEFAULT_WINDAGE,
    MAX_PARTICLES,
    MAX_SIMULATION_DURATION_HOURS,
    MAX_TIMESTEP_SECONDS,
    MAX_WINDAGE,
    MIN_PARTICLES,
    MIN_SIMULATION_DURATION_HOURS,
    MIN_TIMESTEP_SECONDS,
    MIN_WINDAGE,
)


class DriftResponse(BaseModel):
    """Event drift trajectory and source region response."""
    event_id: str = Field(..., description="Unique event identifier", example="wakashio")
    forward_trajectory: GeoJSONFeature | None = Field(
        None, description="Forward drift trajectory as GeoJSON LineString [lon, lat]"
    )
    backward_trajectory: GeoJSONFeature | None = Field(
        None, description="Backward backtrack trajectory as GeoJSON LineString [lon, lat]"
    )
    source_region: GeoJSONFeature | None = Field(
        None, description="Estimated possible source region as GeoJSON Polygon [lon, lat]"
    )
    source_region_centroid: dict[str, float] | None = Field(
        None, description="Centroid of the estimated source region {latitude, longitude}"
    )
    dispersion_radius_95_km: float | None = Field(
        None, description="95% dispersion radius of source particles in km"
    )
    timestep_seconds: int = Field(3600, description="Euler integration timestep in seconds")
    windage_coefficient: float = Field(0.03, description="Wind leeway factor")
    particle_count: int = Field(5, description="Number of Monte Carlo particles")
    forward_duration_hours: float = Field(6.0, description="Forward forecast duration in hours")
    backward_duration_hours: float = Field(6.0, description="Backward backtrack duration in hours")
    model_version: str = Field("Phase 4 Lagrangian Transport v1.0", description="Physics engine version")
    validation_data_mode: str = Field("operational_forcing", description="Environmental forcing data mode")
    disclaimer: str = Field(..., description="Lagrangian simulation operational notice")


class DriftSimulateRequest(BaseModel):
    """Request schema for on-demand Lagrangian drift simulation."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Initial latitude in degrees", example=-19.79856)
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Initial longitude in degrees", example=57.88786)
    timestamp: str = Field(..., description="Simulation initial UTC timestamp (ISO-8601)", example="2020-08-10T01:37:55Z")
    forward_duration_hours: float = Field(
        24.0,
        ge=MIN_SIMULATION_DURATION_HOURS,
        le=MAX_SIMULATION_DURATION_HOURS,
        description="Forward drift duration in hours",
    )
    backward_duration_hours: float = Field(
        24.0,
        ge=MIN_SIMULATION_DURATION_HOURS,
        le=MAX_SIMULATION_DURATION_HOURS,
        description="Backward backtrack duration in hours",
    )
    timestep_seconds: int = Field(
        1800,
        ge=MIN_TIMESTEP_SECONDS,
        le=MAX_TIMESTEP_SECONDS,
        description="Integration timestep in seconds",
    )
    windage: float = Field(
        DEFAULT_WINDAGE,
        ge=MIN_WINDAGE,
        le=MAX_WINDAGE,
        description="Wind leeway coefficient (0.0 to 0.08)",
    )
    particle_count: int = Field(
        10,
        ge=MIN_PARTICLES,
        le=MAX_PARTICLES,
        description="Monte Carlo particle count for source region estimation",
    )
    event_id: str | None = Field(
        None,
        description="Optional event identifier to use pre-downloaded CMEMS forcing fields",
        example="wakashio",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        """Ensure timestamp is valid ISO string."""
        import datetime
        cleaned = v.replace("Z", "+00:00") if v.endswith("Z") else v
        try:
            datetime.datetime.fromisoformat(cleaned)
        except Exception:
            raise ValueError("Timestamp must be a valid ISO-8601 string (e.g. 2020-08-10T01:37:55Z)")
        return v


class DriftSimulateResponse(BaseModel):
    """Response schema for on-demand Lagrangian drift simulation."""
    is_simulation: bool = Field(True, description="Indicates result is a simulation output")
    simulation_type: str = Field("on_demand_simulation", description="Simulation mode identifier")
    forward_trajectory: GeoJSONFeature | None = Field(None, description="Forward trajectory GeoJSON LineString")
    backward_trajectory: GeoJSONFeature | None = Field(None, description="Backward trajectory GeoJSON LineString")
    source_region: GeoJSONFeature | None = Field(None, description="Source region GeoJSON Polygon")
    summary: dict[str, Any] = Field(default_factory=dict, description="Simulation summary metrics")
    forcing_used: dict[str, Any] = Field(default_factory=dict, description="Forcing datasets utilized")
    disclaimer: str = Field(..., description="Operational disclaimer")
