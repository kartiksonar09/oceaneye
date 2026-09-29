"""
Events API Routes.
"""

from fastapi import APIRouter, HTTPException, status
from api.schemas.common import ErrorResponse
from api.schemas.events import EventDetail, EventSummary
from api.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get(
    "",
    response_model=list[EventSummary],
    summary="List All Configured Events",
    description="Retrieve all available maritime incident events dynamically loaded from system configuration.",
)
def list_events():
    """List all available maritime incidents."""
    return EventService.list_events()


@router.get(
    "/{event_id}",
    response_model=EventDetail,
    responses={404: {"model": ErrorResponse, "description": "Event not found"}},
    summary="Get Event Details",
    description="Retrieve detailed metadata, geographic bounding box, and pipeline dataset availability for an event.",
)
def get_event(event_id: str):
    """Retrieve details for a specific incident."""
    event = EventService.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found.",
        )
    return event
