"""
OceanEye SAR Oil-Spill Segmentation Module
Exports:
  - UNet, build_segmentation_model
  - SARSPILLDataset, load_segmentation_dataset, preprocess_sar_image, create_synthetic_segmentation_data
  - compute_segmentation_metrics, calculate_iou, calculate_dice
  - train_segmentation_model, save_segmentation_model
  - load_segmentation_model, predict_segmentation
"""

from .dataset import (
    SARSPILLDataset,
    create_synthetic_segmentation_data,
    load_segmentation_dataset,
    preprocess_mask,
    preprocess_sar_image,
)
from .inference import load_segmentation_model, predict_segmentation
from .metrics import (
    calculate_dice,
    calculate_iou,
    calculate_precision_recall,
    compute_segmentation_metrics,
)
from .model import UNet, build_segmentation_model
from .train import save_segmentation_model, train_segmentation_model

__all__ = [
    "UNet",
    "build_segmentation_model",
    "SARSPILLDataset",
    "load_segmentation_dataset",
    "preprocess_sar_image",
    "preprocess_mask",
    "create_synthetic_segmentation_data",
    "compute_segmentation_metrics",
    "calculate_iou",
    "calculate_dice",
    "calculate_precision_recall",
    "train_segmentation_model",
    "save_segmentation_model",
    "load_segmentation_model",
    "predict_segmentation",
]
