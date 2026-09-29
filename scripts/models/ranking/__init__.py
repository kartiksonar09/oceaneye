"""
OceanEye Vessel Prioritization & Ranking Module
Exports:
  - extract_vessel_features, haversine_distance, calculate_bearing
  - train_ranking_model, evaluate_ranking_model, save_ranking_model, create_synthetic_ranking_data
  - load_ranking_model, predict_vessel_scores, rank_vessels
"""

from .features import (
    RANKING_FEATURE_NAMES,
    calculate_bearing,
    extract_vessel_features,
    haversine_distance,
)
from .inference import (
    LEGAL_INVESTIGATORY_DISCLAIMER,
    load_ranking_model,
    predict_vessel_scores,
    rank_vessels,
)
from .train import (
    create_synthetic_ranking_data,
    evaluate_ranking_model,
    save_ranking_model,
    train_ranking_model,
)

__all__ = [
    "extract_vessel_features",
    "haversine_distance",
    "calculate_bearing",
    "RANKING_FEATURE_NAMES",
    "train_ranking_model",
    "evaluate_ranking_model",
    "save_ranking_model",
    "create_synthetic_ranking_data",
    "load_ranking_model",
    "predict_vessel_scores",
    "rank_vessels",
    "LEGAL_INVESTIGATORY_DISCLAIMER",
]
