"""
OceanEye AI Models - Shared Infrastructure & Registry Utilities
Provides centralized model artifact directories, reproducibility controls,
standardized metadata generation, and security sanitization.
"""

import datetime
import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

# Add scripts directory to sys.path if not present
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import PROJECT_ROOT, setup_logging

MODELS_DIR = PROJECT_ROOT / "models"
ML_DATA_DIR = PROJECT_ROOT / "data" / "ml"

SENSITIVE_KEYS = {"api_key", "token", "password", "secret", "credentials", "authorization", "auth"}


def get_model_dir(model_type: str) -> Path:
    """
    Return the model artifact directory for a specific model type:
    models/<model_type>/
    Creates the directory if it does not already exist.
    """
    valid_types = {"segmentation", "classification", "ranking"}
    if model_type not in valid_types:
        raise ValueError(f"Invalid model_type '{model_type}'. Expected one of {valid_types}")

    target_dir = MODELS_DIR / model_type
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def get_ml_data_dir(component: str = "") -> Path:
    """
    Return the standardized machine learning data directory:
    data/ml/<component>/
    Creates the directory if it does not already exist.
    """
    if component:
        target_dir = ML_DATA_DIR / component
    else:
        target_dir = ML_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def set_random_seed(seed: int = 42) -> None:
    """
    Configure global random seeds across random, numpy, and torch
    to guarantee deterministic, reproducible model training and evaluations.
    """
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


def _sanitize_metadata(data: Any) -> Any:
    """
    Recursively remove any keys or values that may contain sensitive credentials.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(s in str(k).lower() for s in SENSITIVE_KEYS):
                continue
            sanitized[k] = _sanitize_metadata(v)
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_metadata(item) for item in data]
    elif isinstance(data, (np.floating, np.integer)):
        return data.item()
    elif isinstance(data, np.ndarray):
        return data.tolist()
    return data


def save_model_metadata(
    model_type: str,
    metadata: dict[str, Any],
    output_file: Path | str,
    logger: logging.Logger | None = None,
) -> Path:
    """
    Serialize standardized model metadata to JSON with system environment context.
    Automatically scrubs sensitive credentials and converts non-serializable objects.
    """
    if logger is None:
        logger = setup_logging("models.common")

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Collect framework library versions
    lib_versions: dict[str, str] = {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
    }

    try:
        import torch
        lib_versions["torch"] = torch.__version__
    except ImportError:
        pass

    try:
        import xgboost
        lib_versions["xgboost"] = xgboost.__version__
    except ImportError:
        pass

    try:
        import sklearn
        lib_versions["scikit-learn"] = sklearn.__version__
    except ImportError:
        pass

    enriched_meta = {
        "model_type": model_type,
        "saved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "framework_versions": lib_versions,
    }
    enriched_meta.update(metadata)

    # Sanitize dictionary
    cleaned_meta = _sanitize_metadata(enriched_meta)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_meta, f, indent=2, default=str)

    logger.debug("Model metadata written to: %s", out_path)
    return out_path


def load_model_metadata(metadata_file: Path | str) -> dict[str, Any]:
    """
    Load model metadata JSON file.
    """
    path = Path(metadata_file)
    if not path.exists():
        raise FileNotFoundError(f"Model metadata file does not exist: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
