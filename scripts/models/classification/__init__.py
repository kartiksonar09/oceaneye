"""
OceanEye Look-Alike Classification Module
Exports:
  - extract_candidate_features
  - train_classification_model, evaluate_classifier, save_classifier, create_synthetic_classification_data
  - load_classifier, predict_classifier
"""

from .features import extract_candidate_features
from .inference import load_classifier, predict_classifier
from .train import (
    FEATURE_NAMES,
    create_synthetic_classification_data,
    evaluate_classifier,
    save_classifier,
    train_classification_model,
)

__all__ = [
    "extract_candidate_features",
    "train_classification_model",
    "evaluate_classifier",
    "save_classifier",
    "create_synthetic_classification_data",
    "load_classifier",
    "predict_classifier",
    "FEATURE_NAMES",
]
