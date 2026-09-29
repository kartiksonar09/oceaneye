"""
OceanEye Look-Alike Classification Training Pipeline
Trains an XGBoost gradient-boosted decision tree to discriminate candidate oil slicks
from natural look-alikes (low-wind calm seas, biogenic sheens, internal waves).
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
from common import setup_logging


FEATURE_NAMES = [
    "mean_intensity",
    "min_intensity",
    "max_intensity",
    "intensity_variance",
    "intensity_skewness",
    "area_pixels",
    "perimeter_approx",
    "compactness",
    "aspect_ratio",
    "background_mean",
    "contrast_ratio",
    "gradient_boundary_mean",
    "local_wind_speed",
    "local_current_speed",
]


def create_synthetic_classification_data(
    num_samples: int = 150, seed: int = 42
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Generate synthetic candidate feature distributions strictly for testing
    and verifying the classification training/inference pipeline.
    Simulates physics-based differences between mineral oil slicks and look-alikes.
    Label 1 = Likely Oil Spill, Label 0 = Likely Look-Alike
    """
    rng = np.random.RandomState(seed)
    n_spills = num_samples // 2
    n_lookalikes = num_samples - n_spills

    rows = []
    labels = []

    # 1. Synthesize Oil Spills (Label 1)
    # Characteristics: higher damping (high contrast), moderate winds (3-9 m/s), sharp gradients, elongated trails
    for _ in range(n_spills):
        bg_mean = rng.uniform(0.6, 0.9)
        contrast = rng.uniform(0.55, 0.85)  # Strong damping
        mean_int = bg_mean * (1.0 - contrast)
        wind = rng.uniform(3.0, 9.0)  # Favorable radar SAR imaging wind regime
        aspect = rng.exponential(scale=2.5) + 2.0  # Elongated slick shape
        area = rng.uniform(200, 3000)
        perim = np.sqrt(area) * rng.uniform(4.0, 8.0)
        grad = rng.uniform(0.25, 0.60)  # Sharper boundary

        rows.append({
            "mean_intensity": mean_int,
            "min_intensity": max(0.01, mean_int - rng.uniform(0.02, 0.08)),
            "max_intensity": mean_int + rng.uniform(0.05, 0.15),
            "intensity_variance": rng.uniform(0.002, 0.012),
            "intensity_skewness": rng.uniform(-0.5, 0.8),
            "area_pixels": area,
            "perimeter_approx": perim,
            "compactness": (4 * np.pi * area) / (perim**2),
            "aspect_ratio": aspect,
            "background_mean": bg_mean,
            "contrast_ratio": contrast,
            "gradient_boundary_mean": grad,
            "local_wind_speed": wind,
            "local_current_speed": rng.uniform(0.1, 0.5),
        })
        labels.append(1)

    # 2. Synthesize Look-Alikes (Label 0)
    # Characteristics: low wind (<3 m/s calm seas) or diffuse biogenic films (lower contrast, diffuse gradient)
    for _ in range(n_lookalikes):
        is_low_wind = rng.rand() > 0.4
        if is_low_wind:
            wind = rng.uniform(0.5, 2.8)  # Mirror calm ocean surface
            contrast = rng.uniform(0.2, 0.5)
            grad = rng.uniform(0.05, 0.20)  # Gradual diffuse boundary
        else:
            wind = rng.uniform(3.0, 7.0)  # Biogenic / algal film
            contrast = rng.uniform(0.15, 0.45)  # Weak damping
            grad = rng.uniform(0.08, 0.22)

        bg_mean = rng.uniform(0.4, 0.8)
        mean_int = bg_mean * (1.0 - contrast)
        area = rng.uniform(300, 5000)
        perim = np.sqrt(area) * rng.uniform(3.5, 6.0)
        aspect = rng.uniform(1.0, 2.5)  # Amorphous patch

        rows.append({
            "mean_intensity": mean_int,
            "min_intensity": max(0.01, mean_int - rng.uniform(0.01, 0.05)),
            "max_intensity": mean_int + rng.uniform(0.03, 0.10),
            "intensity_variance": rng.uniform(0.001, 0.006),
            "intensity_skewness": rng.uniform(-0.2, 0.5),
            "area_pixels": area,
            "perimeter_approx": perim,
            "compactness": (4 * np.pi * area) / (perim**2),
            "aspect_ratio": aspect,
            "background_mean": bg_mean,
            "contrast_ratio": contrast,
            "gradient_boundary_mean": grad,
            "local_wind_speed": wind,
            "local_current_speed": rng.uniform(0.05, 0.3),
        })
        labels.append(0)

    df_X = pd.DataFrame(rows)[FEATURE_NAMES]
    s_y = pd.Series(labels, name="label")

    return df_X, s_y


def evaluate_classifier(
    model: xgb.XGBClassifier, X_test: pd.DataFrame, y_test: pd.Series
) -> dict[str, Any]:
    """Calculate comprehensive classification metrics."""
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


def save_classifier(
    model: xgb.XGBClassifier,
    output_dir: Path | str,
    metadata: dict[str, Any],
    model_filename: str = "sar_lookalike_classifier.json",
    metadata_filename: str = "classification_metadata.json",
    logger: logging.Logger | None = None,
) -> tuple[Path, Path]:
    """
    Save XGBoost model artifact (JSON format) and standardized metadata.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / model_filename
    meta_path = out_dir / metadata_filename

    # Save XGBoost native JSON model
    model.save_model(str(model_path))

    # Save standardized metadata
    meta_full = {
        "model_architecture": "xgboost_classifier",
        "feature_names": FEATURE_NAMES,
        "classes": ["likely_lookalike", "likely_oil_spill"],
        "model_artifact_file": str(model_path.name),
    }
    meta_full.update(metadata)
    save_model_metadata("classification", meta_full, meta_path, logger=logger)

    return model_path, meta_path


def train_classification_model(
    data_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    use_synthetic: bool = False,
    seed: int = 42,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """
    Execute look-alike classification training and evaluation pipeline.
    """
    if logger is None:
        logger = setup_logging("train_classification")

    set_random_seed(seed)
    is_synthetic = False

    # Load or generate dataset
    if data_path is None or use_synthetic:
        logger.info("Using synthetic look-alike benchmark data for pipeline validation.")
        X, y = create_synthetic_classification_data(num_samples=160, seed=seed)
        is_synthetic = True
    else:
        p = Path(data_path)
        if p.exists() and p.suffix == ".csv":
            df = pd.read_csv(p)
            if "label" in df.columns:
                y = df["label"]
                X = df[[c for c in FEATURE_NAMES if c in df.columns]]
            else:
                raise ValueError("Dataset CSV missing 'label' column.")
        else:
            logger.warning("Dataset at '%s' not found. Generating synthetic benchmark.", p)
            X, y = create_synthetic_classification_data(num_samples=160, seed=seed)
            is_synthetic = True

    if output_dir is None:
        output_dir = get_model_dir("classification")
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Splitting dataset (%d samples) into 75%% train / 25%% test...", len(X))
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=seed, stratify=y
    )

    # Instantiate and fit XGBoost classifier
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=seed,
    )

    logger.info("Training XGBoost classifier...")
    model.fit(X_train, y_train)

    # Evaluate
    metrics = evaluate_classifier(model, X_test, y_test)
    logger.info(
        "Look-Alike Classifier Evaluation: Accuracy: %.4f | F1: %.4f | Recall: %.4f | AUC: %.4f",
        metrics["accuracy"], metrics["f1"], metrics["recall"], metrics["roc_auc"]
    )

    # Extract feature importances
    importances = {
        feat: round(float(imp), 4)
        for feat, imp in zip(FEATURE_NAMES, model.feature_importances_)
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
            "Trained on SYNTHETIC feature distribution for pipeline verification. "
            "Predictions are screening estimates, not proof of mineral oil presence."
            if is_synthetic else "Trained on real dataset."
        ),
    }

    model_file, meta_file = save_classifier(model, output_dir, training_meta, logger=logger)
    logger.info("Classifier saved to: %s", model_file)

    return {
        "status": "success",
        "model_type": "classification",
        "is_synthetic": is_synthetic,
        "model_file": str(model_file),
        "metadata_file": str(meta_file),
        "metrics": metrics,
        "top_features": list(sorted_importances.items())[:5],
    }
