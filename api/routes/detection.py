"""
Detection API Routes.
"""

from fastapi import APIRouter, HTTPException, status
from api.schemas.common import ErrorResponse
from api.schemas.detection import DetectionResponse
from api.services.detection_service import DetectionService

router = APIRouter(prefix="/api/events", tags=["Detection"])


@router.get(
    "/{event_id}/detection",
    response_model=DetectionResponse,
    responses={404: {"model": ErrorResponse, "description": "Event not found"}},
    summary="Get Sentinel-1 Detection Metadata",
    description=(
        "Retrieve Sentinel-1 SAR observation metadata and oil spill detection status for a specific event. "
        "Strictly enforces geometry=null when pixel-level segmentation masks are not present."
    ),
)
def get_event_detection(event_id: str):
    """Retrieve SAR detection and observation metadata for an event."""
    detection = DetectionService.get_detection(event_id)
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found.",
        )
    return detection
