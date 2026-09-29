"""
OceanEye Machine Learning & Artificial Intelligence Framework
Modules:
  - segmentation: Sentinel-1 SAR oil-spill candidate segmentation (PyTorch U-Net)
  - classification: Look-alike vs true spill discrimination (XGBoost)
  - ranking: AIS vessel anomaly and trajectory attribution scoring (XGBoost)
"""

from .common import get_model_dir, get_ml_data_dir, set_random_seed, save_model_metadata, load_model_metadata

__all__ = [
    "get_model_dir",
    "get_ml_data_dir",
    "set_random_seed",
    "save_model_metadata",
    "load_model_metadata",
]
