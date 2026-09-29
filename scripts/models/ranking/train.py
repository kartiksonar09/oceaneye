"""
OceanEye Vessel Prioritization & Ranking Model Training Pipeline
Trains an XGBoost attribution and ranking model to prioritize candidate vessels
based on spatial-temporal convergence, kinematic anomalies, and oceanographic drift.
"""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
import xgboost as xgb

from models.common import get_model_dir, get_ml_data_dir, save_model_metadata, set_random_seed
from models.ranking.features import RANKING_FEATURE_NAMES
from common import setup_logging


def create_synthetic_ranking_data(
    num_samples: int = 160, seed: int = 42
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Generate synthetic vessel ranking feature distributions strictly for testing
    and verifying the vessel attribution pipeline.
    Label 1 = High Prioritization (high investigative relevance),
    Label 0 = Low Prioritization (distant or uncoordinated transit).
    """
    rng = np.random.RandomState(seed)
    n_high = num_samples // 2
    n_low = num_samples - n_high

    rows = []
    labels = []

    # 1. High Prioritization Candidates (Label 1)
    # Passed near spill location around incident time, possible loitering/speed drop
    for _ in range(n_high):
        min_d = rng.uniform(0.2, 5.0)  # Near spill
        time_offset = rng.uniform(0.1, 3.5)  # Recent
        drift_dist = min_d * rng.uniform(0.5, 1.2)  # Drift aligns
        traj_p = np.exp(-min_d / 20.0)
        temp_p = np.exp(-time_offset / 12.0)
        mean_spd = rng.uniform(2.0, 12.0)
        var_spd = rng.uniform(8.0, 30.0)  # Speed fluctuation / stop
        anomaly = rng.uniform(0.5, 0.95)
        heading_dev = rng.uniform(5.0, 45.0)

        rows.append({
            "min_distance_km": min_d,
            "distance_at_spill_time_km": min_d * rng.uniform(1.0, 1.5),
            "temporal_offset_hours": time_offset,
            "trajectory_proximity_score": traj_p,
            "temporal_proximity_score": temp_p,
            "mean_speed_knots": mean_spd,
            "speed_variance": var_spd,
            "speed_anomaly_score": anomaly,
            "heading_deviation_deg": heading_dev,
            "drift_corrected_distance_km": drift_dist,
            "ais_ping_count": float(rng.randint(20, 150)),
        })
        labels.append(1)

    # 2. Low Prioritization Candidates (Label 0)
    # Distant transit or passed days earlier/later
    for _ in range(n_low):
        min_d = rng.uniform(18.0, 95.0)  # Far
        time_offset = rng.uniform(10.0, 72.0)
        drift_dist = min_d * rng.uniform(0.9, 1.8)
        traj_p = np.exp(-min_d / 20.0)
        temp_p = np.exp(-time_offset / 12.0)
        mean_spd = rng.uniform(11.0, 19.0)  # Steady cruising
        var_spd = rng.uniform(0.1, 4.0)
        anomaly = rng.uniform(0.0, 0.3)
        heading_dev = rng.uniform(60.0, 175.0)

        rows.append({
            "min_distance_km": min_d,
            "distance_at_spill_time_km": min_d + rng.uniform(5.0, 20.0),
            "temporal_offset_hours": time_offset,
            "trajectory_proximity_score": traj_p,
            "temporal_proximity_score": temp_p,
            "mean_speed_knots": mean_spd,
            "speed_variance": var_spd,
            "speed_anomaly_score": anomaly,
            "heading_deviation_deg": heading_dev,
            "drift_corrected_distance_km": drift_dist,
            "ais_ping_count": float(rng.randint(5, 60)),
        })
        labels.append(0)

    df_X = pd.DataFrame(rows)[RANKING_FEATURE_NAMES]
    s_y = pd.Series(labels, name="priority_label")

    return df_X, s_y


def evaluate_ranking_model(
    model: xgb.XGBClassifier, X_test: pd.DataFrame, y_test: pd.Series
) -> dict[str, Any]:
    """Calculate ranking classifier evaluation metrics."""
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))

    try:
        auc = float(roc_auc_score(y_test, y_prob))
    except ValueError:
        auc = 0.5

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
        "test_sample_count": len(y_test),
    }


def save_ranking_model(
    model: xgb.XGBClassifier,
    output_dir: Path | str,
    metadata: dict[str, Any],
    model_filename: str = "vessel_ranking_model.json",
    metadata_filename: str = "ranking_metadata.json",
    logger: logging.Logger | None = None,
) -> tuple[Path, Path]:
    """Save XGBoost ranking model artifact (JSON) and metadata."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / model_filename
    meta_path = out_dir / metadata_filename

    model.save_model(str(model_path))

    meta_full = {
        "model_architecture": "xgboost_vessel_ranker",
        "feature_names": RANKING_FEATURE_NAMES,
        "model_artifact_file": str(model_path.name),
        "legal_notice": (
            "IMPORTANT: Vessel ranking scores represent investigative prioritization only. "
            "A high rank or score is NOT evidence or proof that a vessel caused a discharge."
        ),
    }
    meta_full.update(metadata)
    save_model_metadata("ranking", meta_full, meta_path, logger=logger)

    return model_path, meta_path


def train_ranking_model(
    data_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    use_synthetic: bool = False,
    seed: int = 42,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Execute vessel ranking training and evaluation pipeline."""
    if logger is None:
        logger = setup_logging("train_ranking")

    set_random_seed(seed)
    is_synthetic = False

    if data_path is None or use_synthetic:
        logger.info("Using synthetic vessel ranking benchmark data for pipeline validation.")
        X, y = create_synthetic_ranking_data(num_samples=160, seed=seed)
        is_synthetic = True
    else:
        p = Path(data_path)
        if p.exists() and p.suffix == ".csv":
            df = pd.read_csv(p)
            if "priority_label" in df.columns:
                y = df["priority_label"]
                X = df[[c for c in RANKING_FEATURE_NAMES if c in df.columns]]
            else:
                raise ValueError("Dataset CSV missing 'priority_label' column.")
        else:
            logger.warning("Dataset at '%s' not found. Generating synthetic benchmark.", p)
            X, y = create_synthetic_ranking_data(num_samples=160, seed=seed)
            is_synthetic = True

    if output_dir is None:
        output_dir = get_model_dir("ranking")
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Splitting dataset (%d samples) into 75%% train / 25%% test...", len(X))
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=seed, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=seed,
    )

    logger.info("Training XGBoost vessel ranking model...")
    model.fit(X_train, y_train)

    metrics = evaluate_ranking_model(model, X_test, y_test)
    logger.info(
        "Vessel Ranking Model Evaluation: Accuracy: %.4f | F1: %.4f | Recall: %.4f | AUC: %.4f",
        metrics["accuracy"], metrics["f1"], metrics["recall"], metrics["roc_auc"]
    )

    importances = {
        feat: round(float(imp), 4)
        for feat, imp in zip(RANKING_FEATURE_NAMES, model.feature_importances_)
    }
    sorted_importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

    training_meta = {
        "is_synthetic_training_data": is_synthetic,
        "dataset_source": str(data_path or "synthetic_generator"),
        "training_sample_count": len(X_train),
        "test_sample_count": len(X_test),
        "evaluation_metrics": metrics,
        "feature_importances": sorted_importances,
        "scientific_notice": (
            "Trained on SYNTHETIC vessel trajectory distributions for pipeline verification. "
            "Attribution scores reflect geometric/kinematic correlation, NOT proof of spill responsibility."
            if is_synthetic else "Trained on real dataset."
        ),
    }

    model_file, meta_file = save_ranking_model(model, output_dir, training_meta, logger=logger)
    logger.info("Vessel ranking model saved to: %s", model_file)

    return {
        "status": "success",
        "model_type": "ranking",
        "is_synthetic": is_synthetic,
        "model_file": str(model_file),
        "metadata_file": str(meta_file),
        "metrics": metrics,
        "top_features": list(sorted_importances.items())[:5],
    }
