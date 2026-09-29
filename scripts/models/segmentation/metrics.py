"""
OceanEye SAR Segmentation Evaluation Metrics
Computes standardized pixel-level segmentation metrics:
- Intersection over Union (IoU / Jaccard Index)
- Dice Similarity Coefficient (F1-score)
- Precision (Positive Predictive Value)
- Recall (Sensitivity / True Positive Rate)
Supports both PyTorch Tensors and NumPy ndarrays.
"""

from typing import Any
import numpy as np


def _to_numpy_binary(arr: Any, threshold: float = 0.5) -> np.ndarray:
    """Convert tensor or array to boolean numpy mask."""
    if hasattr(arr, "detach"):
        arr = arr.detach().cpu().numpy()
    arr = np.asarray(arr)
    if arr.dtype == bool:
        return arr
    return arr >= threshold


def calculate_iou(y_true: Any, y_pred: Any, threshold: float = 0.5, eps: float = 1e-7) -> float:
    """
    Calculate Intersection over Union (IoU / Jaccard Index).
    IoU = |A ∩ B| / |A ∪ B|
    """
    t = _to_numpy_binary(y_true, threshold=threshold)
    p = _to_numpy_binary(y_pred, threshold=threshold)

    intersection = np.logical_and(t, p).sum()
    union = np.logical_or(t, p).sum()

    if union == 0:
        # Both true and predicted masks are empty: perfect match
        return 1.0
    return float((intersection + eps) / (union + eps))


def calculate_dice(y_true: Any, y_pred: Any, threshold: float = 0.5, eps: float = 1e-7) -> float:
    """
    Calculate Dice Similarity Coefficient (F1-score).
    Dice = 2 * |A ∩ B| / (|A| + |B|)
    """
    t = _to_numpy_binary(y_true, threshold=threshold)
    p = _to_numpy_binary(y_pred, threshold=threshold)

    intersection = np.logical_and(t, p).sum()
    total = t.sum() + p.sum()

    if total == 0:
        return 1.0
    return float((2.0 * intersection + eps) / (total + eps))


def calculate_precision_recall(
    y_true: Any, y_pred: Any, threshold: float = 0.5, eps: float = 1e-7
) -> tuple[float, float]:
    """
    Calculate Precision and Recall.
    Precision = TP / (TP + FP)
    Recall = TP / (TP + FN)
    """
    t = _to_numpy_binary(y_true, threshold=threshold)
    p = _to_numpy_binary(y_pred, threshold=threshold)

    tp = np.logical_and(t, p).sum()
    fp = np.logical_and(~t, p).sum()
    fn = np.logical_and(t, ~p).sum()

    precision = float((tp + eps) / (tp + fp + eps)) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    recall = float((tp + eps) / (tp + fn + eps)) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)

    return precision, recall


def compute_segmentation_metrics(
    y_true: Any, y_pred: Any, threshold: float = 0.5
) -> dict[str, float]:
    """
    Compute full dictionary of pixel-level segmentation evaluation metrics.
    """
    iou = calculate_iou(y_true, y_pred, threshold=threshold)
    dice = calculate_dice(y_true, y_pred, threshold=threshold)
    precision, recall = calculate_precision_recall(y_true, y_pred, threshold=threshold)

    return {
        "iou": round(iou, 4),
        "dice": round(dice, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }
