"""
Attribution API Pydantic schemas.
"""

from typing import Any
from pydantic import BaseModel, Field


class VesselCandidate(BaseModel):
    """Candidate suspect vessel prioritization record."""
    vessel_id: str = Field(..., description="MMSI vessel identifier", example="353123000")
    vessel_name: str = Field(..., description="Vessel name", example="MV PACIFIC VOYAGER")
    prioritization_score: float = Field(..., ge=0.0, le=1.0, description="Correlation prioritization score", example=0.9516)
    rank: int = Field(..., ge=1, description="Relative priority rank", example=1)
    min_distance_to_trajectory_km: float = Field(..., description="Closest approach to backtrack drift path (km)", example=0.0)
    min_distance_to_source_region_km: float = Field(..., description="Distance to estimated source centroid (km)", example=13.62)
    temporal_offset_to_source_hours: float = Field(..., description="Time difference from estimated release (hours)", example=12.0)
    data_mode: str = Field("operational", description="Mode of AIS tracking data (synthetic vs operational)", example="synthetic")
    responsibility_confirmed: bool = Field(
        False,
        description="Explicit flag confirming that prioritization score does NOT confirm legal fault or causation",
    )
    features: dict[str, Any] = Field(default_factory=dict, description="Kinematic and spatio-temporal correlation features")
    estimated_source_region: dict[str, Any] | None = Field(None, description="Reference source region info")
    disclaimer: str = Field(..., description="Legal non-attribution disclaimer")


class AttributionResponse(BaseModel):
    """Vessel attribution report for an event."""
    event_id: str = Field(..., description="Unique event identifier", example="wakashio")
    total_vessels_evaluated: int = Field(..., description="Count of candidate vessels analyzed", example=4)
    is_synthetic_ais_data: bool = Field(True, description="Flag indicating synthetic or demo AIS data")
    ranking_model_used: str = Field("Phase 3 XGBoost Attribution Model", description="Scoring model identifier")
    source_region_release_time: str | None = Field(None, description="Estimated spill release time")
    candidates: list[VesselCandidate] = Field(default_factory=list, description="Ranked candidate suspect vessels")
    disclaimer: str = Field(..., description="Mandatory legal disclaimer")
