"""
OceanEye SAR Oil-Spill Segmentation Inference Pipeline
Provides model checkpoint loading, preprocessing, probability map generation,
and candidate mask extraction with operational disclaimers.
"""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from models.common import get_model_dir, load_model_metadata
from models.segmentation.dataset import preprocess_sar_image
from models.segmentation.model import UNet, build_segmentation_model
from common import setup_logging


def load_segmentation_model(
    model_path: Path | str | None = None,
    device: str = "cpu",
    logger: logging.Logger | None = None,
) -> tuple[nn.Module, dict[str, Any]]:
    """
    Load saved PyTorch U-Net segmentation model checkpoint and metadata.
    Accepts either a model directory containing weights and metadata,
    or a direct path to the weights file.
    """
    if logger is None:
        logger = setup_logging("inference_segmentation")

    if model_path is None:
        model_dir = get_model_dir("segmentation")
    else:
        model_path = Path(model_path)
        model_dir = model_path if model_path.is_dir() else model_path.parent

    # Find weights file
    weights_files = list(model_dir.glob("*.pt")) + list(model_dir.glob("*.pth"))
    if not weights_files:
        raise FileNotFoundError(f"No model checkpoint (.pt / .pth) found in {model_dir}")
    weights_path = weights_files[0]

    # Find metadata file
    meta_files = list(model_dir.glob("*metadata*.json"))
    metadata = {}
    if meta_files:
        metadata = load_model_metadata(meta_files[0])
        logger.debug("Loaded segmentation metadata from %s", meta_files[0])

    in_channels = metadata.get("in_channels", 1)
    out_channels = metadata.get("out_channels", 1)
    base_filters = metadata.get("base_filters", 32)

    model = build_segmentation_model(
        architecture="unet",
        in_channels=in_channels,
        out_channels=out_channels,
        base_filters=base_filters,
    )

    state_dict = torch.load(weights_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    logger.info("Loaded U-Net segmentation model from %s", weights_path)
    return model, metadata


def predict_segmentation(
    model: nn.Module,
    image: np.ndarray,
    target_size: tuple[int, int] = (256, 256),
    threshold: float = 0.5,
    to_db: bool = False,
    normalize: bool = True,
    device: str = "cpu",
) -> dict[str, Any]:
    """
    Generate pixel-level oil spill probability map and binary mask from input SAR image.
    Appends domain disclaimers adhering to maritime intelligence standards.
    """
    model.eval()

    # Preprocess image
    proc_img = preprocess_sar_image(
        image, target_size=target_size, to_db=to_db, normalize=normalize
    )

    # Tensor formatting (1, C, H, W)
    if proc_img.ndim == 2:
        img_t = torch.from_numpy(proc_img).unsqueeze(0).unsqueeze(0).to(device)
    else:
        img_t = torch.from_numpy(np.transpose(proc_img, (2, 0, 1))).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(img_t)
        probs = torch.sigmoid(logits)

    prob_map = probs.squeeze().cpu().numpy()  # (H, W)
    binary_mask = (prob_map >= threshold).astype(np.uint8)

    total_pixels = binary_mask.size
    slick_pixels = int(binary_mask.sum())
    coverage_pct = round((slick_pixels / total_pixels) * 100.0, 3)

    mean_prob_slick = float(prob_map[binary_mask == 1].mean()) if slick_pixels > 0 else 0.0

    return {
        "probability_map": prob_map,
        "binary_mask": binary_mask,
        "threshold_used": threshold,
        "total_slick_pixels": slick_pixels,
        "slick_coverage_percent": coverage_pct,
        "mean_slick_probability": round(mean_prob_slick, 4),
        "disclaimer": (
            "NOTICE: Dark SAR formations indicate suppressed surface roughness. "
            "Detections are candidate anomalies and must be screened for look-alikes "
            "(e.g., wind shadows, biogenic films) before operational confirmation."
        ),
    }
