"""
OceanEye Look-Alike Classification Inference Pipeline
Loads trained XGBoost classifier and evaluates candidate SAR dark formations,
returning probabilistic screening scores with operational disclaimers.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from models.classification.train import FEATURE_NAMES
from models.common import get_model_dir, load_model_metadata
from common import setup_logging


def load_classifier(
    model_path: Path | str | None = None,
    logger: logging.Logger | None = None,
) -> tuple[xgb.XGBClassifier, dict[str, Any]]:
    """
    Load saved XGBoost look-alike classifier model artifact and metadata.
    """
    if logger is None:
        logger = setup_logging("inference_classification")

    if model_path is None:
        model_dir = get_model_dir("classification")
    else:
        model_path = Path(model_path)
        model_dir = model_path if model_path.is_dir() else model_path.parent

    # Find model file (.json)
    model_files = list(model_dir.glob("*.json"))
    meta_files = [p for p in model_files if "metadata" in p.name]
    model_artifacts = [p for p in model_files if "metadata" not in p.name]

    if not model_artifacts:
        raise FileNotFoundError(f"No XGBoost model file (.json) found in {model_dir}")
    artifact_path = model_artifacts[0]

    metadata = {}
    if meta_files:
        metadata = load_model_metadata(meta_files[0])

    model = xgb.XGBClassifier()
    model.load_model(str(artifact_path))
    logger.info("Loaded XGBoost look-alike classifier from %s", artifact_path)

    return model, metadata


def predict_classifier(
    model: xgb.XGBClassifier,
    features: dict[str, float] | pd.DataFrame,
) -> dict[str, Any]:
    """
    Classify a candidate dark SAR region into 'likely_oil_spill' or 'likely_lookalike'.
    Accepts single feature dict or DataFrame.
    """
    if isinstance(features, dict):
        # Format DataFrame with expected feature column ordering
        row = {col: features.get(col, 0.0) for col in FEATURE_NAMES}
        df_in = pd.DataFrame([row])[FEATURE_NAMES]
    else:
        df_in = features[FEATURE_NAMES]

    probabilities = model.predict_proba(df_in)[0]  # [p_lookalike, p_spill]
    p_lookalike = float(probabilities[0])
    p_spill = float(probabilities[1])

    predicted_label = int(p_spill >= 0.5)
    class_name = "likely_oil_spill" if predicted_label == 1 else "likely_lookalike"
    confidence = float(max(p_lookalike, p_spill))

    return {
        "predicted_class": class_name,
        "is_likely_oil_spill": bool(predicted_label == 1),
        "probability_oil_spill": round(p_spill, 4),
        "probability_lookalike": round(p_lookalike, 4),
        "confidence_score": round(confidence, 4),
        "input_features": df_in.iloc[0].to_dict(),
        "disclaimer": (
            "NOTICE: Look-alike classification is an automated screening aid based on "
            "radiometric, geometric, and wind features. It does not provide legal or chemical "
            "proof of petroleum hydrocarbons."
        ),
    }
