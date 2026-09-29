"""
FastAPI Dependencies for OceanEye API.
Provides reusable dependency providers for services and logging.
"""

from functools import lru_cache
import logging

from api.config import APP_NAME
from common import setup_logging


@lru_cache
def get_logger() -> logging.Logger:
    """Return application logger."""
    return setup_logging("oceaneye.api")
