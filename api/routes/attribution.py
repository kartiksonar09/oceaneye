"""
Attribution API Routes.
"""

from fastapi import APIRouter, HTTPException, status
from api.schemas.attribution import AttributionResponse
from api.schemas.common import ErrorResponse
from api.services.attribution_service import AttributionService
from api.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["Attribution"])


@router.get(
    "/{event_id}/attribution",
    response_model=AttributionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Event or attribution output not found"}
    },
    summary="Get Suspect Vessel Prioritization Rankings",
    description=(
        "Retrieve ranked candidate suspect vessels correlated with the backward drift trajectory "
        "and estimated source region. Prioritization scores indicate correlation only and DO NOT "
        "constitute confirmed legal fault or causation."
    ),
)
def get_event_attribution(event_id: str):
    """Retrieve candidate suspect vessels for an incident."""
    if not EventService.get_event(event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found.",
        )

    attribution_data = AttributionService.get_event_attribution(event_id)
    if not attribution_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attribution data not found for event '{event_id}'.",
        )
    return attribution_data
