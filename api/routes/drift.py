"""
Drift API Routes.
"""

from fastapi import APIRouter, HTTPException, status
from api.schemas.common import ErrorResponse
from api.schemas.drift import DriftResponse, DriftSimulateRequest, DriftSimulateResponse
from api.services.drift_service import DriftService
from api.services.event_service import EventService

router = APIRouter(tags=["Drift & Trajectories"])


@router.get(
    "/api/events/{event_id}/drift",
    response_model=DriftResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Event or drift output not found"}
    },
    summary="Get Event Drift Simulation Outputs",
    description=(
        "Retrieve stored forward and backward Lagrangian drift trajectories and estimated source region "
        "as GeoJSON LineString and Polygon features for a specific event."
    ),
)
def get_event_drift(event_id: str):
    """Retrieve forward and backward drift trajectories for an incident."""
    if not EventService.get_event(event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found.",
        )

    drift_data = DriftService.get_event_drift(event_id)
    if not drift_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drift simulation output not found for event '{event_id}'.",
        )
    return drift_data


@router.post(
    "/api/drift/simulate",
    response_model=DriftSimulateResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute On-Demand Drift Simulation",
    description=(
        "Run an on-demand forward and backward Lagrangian drift trajectory simulation "
        "and Monte Carlo source region ensemble with user-specified coordinates and durations."
    ),
)
def simulate_drift(request: DriftSimulateRequest):
    """Execute on-demand Lagrangian forward/backward drift simulation."""
    if request.event_id and not EventService.get_event(request.event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specified event_id '{request.event_id}' not found.",
        )

    try:
        return DriftService.simulate_drift(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete drift simulation execution.",
        )
