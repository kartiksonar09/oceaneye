"""
OceanEye Backend API Configuration.
Centralizes environment settings, directory paths, and operational limits.
"""

import os
import sys
from pathlib import Path

# Resolve project paths dynamically
API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
CONFIG_DIR = PROJECT_ROOT / "config"
EVENTS_FILE = CONFIG_DIR / "events.json"
DATA_DIR = PROJECT_ROOT / "data"

# Ensure scripts directory is available for importing common models and utilities
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Application Metadata
APP_NAME = "OceanEye Maritime Intelligence API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = (
    "AI-powered maritime intelligence backend exposing Sentinel-1 SAR spill detections, "
    "Lagrangian drift trajectory modeling, source region estimation, and AIS vessel attribution."
)

# CORS Configuration
# Accepts comma-separated list of origins, defaults to safe local development origins
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

_env_cors = os.getenv("CORS_ALLOWED_ORIGINS", "")
if _env_cors.strip():
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _env_cors.split(",") if origin.strip()]
else:
    CORS_ALLOWED_ORIGINS = DEFAULT_CORS_ORIGINS

# On-Demand Simulation Safety Limits
MAX_SIMULATION_DURATION_HOURS = 72.0
MIN_SIMULATION_DURATION_HOURS = 0.5
MIN_TIMESTEP_SECONDS = 300
MAX_TIMESTEP_SECONDS = 7200
MAX_PARTICLES = 50
MIN_PARTICLES = 1
DEFAULT_WINDAGE = 0.03
MAX_WINDAGE = 0.08
MIN_WINDAGE = 0.0

# Mandatory Disclaimers
LEGAL_DISCLAIMER = (
    "DISCLAIMER: Vessel prioritization scores indicate spatial, temporal, and kinematic correlation "
    "with a detected anomaly. A high score or rank DOES NOT constitute legal proof, attribution, or certainty "
    "of responsibility for any pollutant discharge. All outputs are decision-support indicators intended "
    "to guide investigative inspection."
)

SAR_DETECTION_DISCLAIMER = (
    "NOTICE: Dark SAR formations are not automatically oil spills. Surface tension phenomena, biogenic films, "
    "and low-wind shadows produce low radar backscatter look-alikes. Detections require screening by the look-alike "
    "classifier and validation with oceanographic context."
)

DRIFT_SIMULATION_DISCLAIMER = (
    "NOTICE: Forward and backward trajectories represent simplified Lagrangian transport (ocean currents + leeway) "
    "for investigative screening. Trajectories and source regions are statistical approximations and do not replace "
    "hydrodynamic forensic simulations."
)
