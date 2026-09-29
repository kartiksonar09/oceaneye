"""
Root and Health Check Routes.
"""

import datetime
from fastapi import APIRouter
from api.config import APP_NAME, APP_VERSION
from api.schemas.common import HealthResponse, ServiceStatusResponse

router = APIRouter(tags=["System"])


@router.get("/", response_model=ServiceStatusResponse)
def get_root():
    """Service status and API landing endpoint."""
    return ServiceStatusResponse(
        status="ok",
        app_name=APP_NAME,
        version=APP_VERSION,
        docs_url="/docs",
    )


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Health check endpoint providing uptime and version information."""
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        app_name=APP_NAME,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
