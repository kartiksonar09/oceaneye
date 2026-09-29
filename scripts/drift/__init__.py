"""
OceanEye Lagrangian Drift Simulation & Vessel Attribution Framework
Modules:
  - geo: Vectorized geodesics, bearing, coordinate projections, and bounding geometry.
  - interpolation: Spatio-temporal interpolation of CMEMS currents and wind fields.
  - model: Forward and backward Lagrangian oil drift numerical integration.
  - ensemble: Monte Carlo backward particle ensembles and source region density estimation.
  - attribution: AIS track correlation, feature extraction, and Phase 3 ranking model scoring.
"""

from .geo import (
    calculate_bearing,
    calculate_trajectory_length,
    compute_bounding_box,
    compute_convex_hull,
    displacement_to_latlon,
    haversine_distance,
    latlon_to_displacement,
    point_to_trajectory_distance,
)
from .interpolation import EnvironmentalForcing
from .model import (
    calculate_trajectory_summary,
    simulate_backward_drift,
    simulate_forward_drift,
)
from .ensemble import simulate_particle_ensemble
from .attribution import (
    correlate_and_rank_vessels,
    correlate_vessel_with_drift,
)

__all__ = [
    "haversine_distance",
    "calculate_bearing",
    "displacement_to_latlon",
    "latlon_to_displacement",
    "point_to_trajectory_distance",
    "calculate_trajectory_length",
    "compute_bounding_box",
    "compute_convex_hull",
    "EnvironmentalForcing",
    "simulate_forward_drift",
    "simulate_backward_drift",
    "calculate_trajectory_summary",
    "simulate_particle_ensemble",
    "correlate_vessel_with_drift",
    "correlate_and_rank_vessels",
]
