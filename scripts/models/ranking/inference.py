"""
OceanEye Vessel Prioritization & Ranking Inference Pipeline
Loads trained XGBoost ranking model, evaluates AIS trajectories against spill candidates,
and produces evidentiary suspect prioritization rankings with mandatory disclaimers.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from models.common import get_model_dir, load_model_metadata
from models.ranking.features import RANKING_FEATURE_NAMES, extract_vessel_features
from common import setup_logging

LEGAL_INVESTIGATORY_DISCLAIMER = (
    "DISCLAIMER: Vessel prioritization scores indicate spatial, temporal, and kinematic "
    "correlation with a detected anomaly. A high score or rank DOES NOT constitute legal "
    "proof, attribution, or certainty of responsibility for any pollutant discharge. "
    "All outputs are decision-support indicators intended to guide investigative inspection."
)


def load_ranking_model(
    model_path: Path | str | None = None,
    logger: logging.Logger | None = None,
) -> tuple[xgb.XGBClassifier, dict[str, Any]]:
    """
    Load saved XGBoost vessel ranking model artifact and metadata.
    """
    if logger is None:
        logger = setup_logging("inference_ranking")

    if model_path is None:
        model_dir = get_model_dir("ranking")
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
    logger.info("Loaded XGBoost vessel ranking model from %s", artifact_path)

    return model, metadata


def predict_vessel_scores(
    model: xgb.XGBClassifier,
    features_df: pd.DataFrame,
) -> np.ndarray:
    """
    Predict prioritization probability scores for a batch of candidate vessel feature rows.
    Returns float array in range [0.0, 1.0].
    """
    df_aligned = features_df[RANKING_FEATURE_NAMES]
    probs = model.predict_proba(df_aligned)[:, 1]
    return probs.astype(float)


def rank_vessels(
    model: xgb.XGBClassifier,
    candidate_spill: dict[str, Any],
    vessels_df: pd.DataFrame,
    environmental_data: dict[str, Any] | None = None,
    id_col: str = "mmsi",
) -> list[dict[str, Any]]:
    """
    Correlate vessel AIS trajectories with a detected spill candidate,
    extract kinematic features, score attribution likelihood, and return
    a sorted priority ranking.
    """
    if vessels_df.empty:
        return []

    spill_lat = float(candidate_spill["latitude"])
    spill_lon = float(candidate_spill["longitude"])
    spill_time = candidate_spill.get("timestamp") or candidate_spill.get("start_date")

    env = environmental_data or {}
    curr_u = float(env.get("uo", env.get("current_u", 0.0)))
    curr_v = float(env.get("vo", env.get("current_v", 0.0)))
    wind_u = float(env.get("eastward_wind", env.get("wind_u", 0.0)))
    wind_v = float(env.get("northward_wind", env.get("wind_v", 0.0)))

    # Determine vessel identifier column
    vessel_id_column = id_col if id_col in vessels_df.columns else (
        "vessel_id" if "vessel_id" in vessels_df.columns else vessels_df.columns[0]
    )

    vessel_groups = vessels_df.groupby(vessel_id_column)
    vessel_records = []

    for v_id, group in vessel_groups:
        feats = extract_vessel_features(
            vessel_points=group,
            spill_lat=spill_lat,
            spill_lon=spill_lon,
            spill_timestamp=spill_time,
            current_u=curr_u,
            current_v=curr_v,
            wind_u=wind_u,
            wind_v=wind_v,
        )
        vessel_name = (
            str(group["vessel_name"].dropna().iloc[0])
            if "vessel_name" in group.columns and not group["vessel_name"].dropna().empty
            else str(v_id)
        )
        vessel_records.append({
            "vessel_id": str(v_id),
            "vessel_name": vessel_name,
            "features": feats,
        })

    if not vessel_records:
        return []

    # Batch score
    df_feat_matrix = pd.DataFrame([r["features"] for r in vessel_records])[RANKING_FEATURE_NAMES]
    scores = predict_vessel_scores(model, df_feat_matrix)

    # Attach scores
    for i, r in enumerate(vessel_records):
        r["prioritization_score"] = round(float(scores[i]), 4)
        r["min_distance_km"] = r["features"]["min_distance_km"]
        r["temporal_offset_hours"] = r["features"]["temporal_offset_hours"]

    # Sort descending by prioritization score
    vessel_records.sort(key=lambda x: x["prioritization_score"], reverse=True)

    # Assign ranks and attach mandatory disclaimer
    ranked_results = []
    for rank_idx, record in enumerate(vessel_records, 1):
        record["rank"] = rank_idx
        record["candidate_spill"] = {
            "latitude": spill_lat,
            "longitude": spill_lon,
            "timestamp": str(spill_time),
        }
        record["disclaimer"] = LEGAL_INVESTIGATORY_DISCLAIMER
        ranked_results.append(record)

    return ranked_results
