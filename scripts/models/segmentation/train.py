"""
OceanEye SAR Oil-Spill Segmentation Training Pipeline
Implements U-Net training with composite BCE + Dice loss, validation monitoring,
IoU/Dice tracking, checkpointing, and standardized metadata serialization.
"""

import datetime
import logging
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from models.common import get_model_dir, get_ml_data_dir, save_model_metadata, set_random_seed
from models.segmentation.dataset import (
    SARSPILLDataset,
    create_synthetic_segmentation_data,
)
from models.segmentation.metrics import compute_segmentation_metrics
from models.segmentation.model import UNet, build_segmentation_model
from common import setup_logging


class DiceLoss(nn.Module):
    """Soft Dice Loss for segmentation with smooth factor"""

    def __init__(self, smooth: float = 1.0):
        super().__init__()
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        probs = torch.sigmoid(logits)
        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)

        intersection = (probs_flat * targets_flat).sum()
        total = probs_flat.sum() + targets_flat.sum()

        dice = (2.0 * intersection + self.smooth) / (total + self.smooth)
        return 1.0 - dice


class BCEDiceLoss(nn.Module):
    """Combined Binary Cross Entropy and Soft Dice Loss"""

    def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5):
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss()
        self.dice = DiceLoss()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        loss_bce = self.bce(logits, targets)
        loss_dice = self.dice(logits, targets)
        return self.bce_weight * loss_bce + self.dice_weight * loss_dice


def save_segmentation_model(
    model: nn.Module,
    output_dir: Path | str,
    metadata: dict[str, Any],
    weights_filename: str = "sar_unet_weights.pt",
    metadata_filename: str = "segmentation_metadata.json",
    logger: logging.Logger | None = None,
) -> tuple[Path, Path]:
    """
    Save PyTorch model weights and accompanying standardized JSON metadata.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    weights_path = out_dir / weights_filename
    meta_path = out_dir / metadata_filename

    # Save state dict
    torch.save(model.state_dict(), weights_path)

    # Save metadata
    meta_full = {
        "model_architecture": "unet",
        "in_channels": getattr(model, "in_channels", 1),
        "out_channels": getattr(model, "out_channels", 1),
        "base_filters": getattr(model, "base_filters", 32),
        "weights_file": str(weights_path.name),
    }
    meta_full.update(metadata)
    save_model_metadata("segmentation", meta_full, meta_path, logger=logger)

    return weights_path, meta_path


def train_segmentation_model(
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    epochs: int = 5,
    batch_size: int = 4,
    lr: float = 1e-3,
    base_filters: int = 32,
    device: str = "cpu",
    use_synthetic: bool = False,
    seed: int = 42,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """
    Execute U-Net segmentation training pipeline.
    If data_dir is not provided or use_synthetic is True, generates a synthetic test benchmark.
    """
    if logger is None:
        logger = setup_logging("train_segmentation")

    set_random_seed(seed)
    is_synthetic = False

    # Resolve dataset directory
    if data_dir is None or use_synthetic:
        logger.info("Using synthetic SAR benchmark dataset for pipeline validation.")
        syn_dir = get_ml_data_dir("synthetic_sar")
        create_synthetic_segmentation_data(syn_dir, num_samples=12, patch_size=(256, 256), seed=seed)
        data_dir = syn_dir
        is_synthetic = True
    else:
        data_dir = Path(data_dir)
        if not data_dir.exists() or not (data_dir / "images").exists():
            logger.warning("Specified data_dir '%s' not found. Falling back to synthetic benchmark.", data_dir)
            syn_dir = get_ml_data_dir("synthetic_sar")
            create_synthetic_segmentation_data(syn_dir, num_samples=12, patch_size=(256, 256), seed=seed)
            data_dir = syn_dir
            is_synthetic = True

    # Resolve output directory
    if output_dir is None:
        output_dir = get_model_dir("segmentation")
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing dataset from %s...", data_dir)
    full_dataset = SARSPILLDataset(data_dir=data_dir, logger=logger)

    # Train / Val Split (80% / 20%)
    val_size = max(1, int(len(full_dataset) * 0.25))
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size], generator=torch.Generator().manual_seed(seed)
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    logger.info("Training samples: %d, Validation samples: %d", train_size, val_size)

    # Model instantiation
    model = build_segmentation_model(
        architecture="unet", in_channels=1, out_channels=1, base_filters=base_filters
    ).to(device)

    criterion = BCEDiceLoss(bce_weight=0.5, dice_weight=0.5)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    best_val_loss = float("inf")
    history: list[dict[str, Any]] = []

    logger.info("Starting U-Net training for %d epochs on device '%s'...", epochs, device)

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0

        for images, masks, _ in train_loader:
            images = images.to(device)
            masks = masks.to(device)

            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, masks)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)

        train_loss /= train_size

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_iou_total = 0.0
        val_dice_total = 0.0
        val_prec_total = 0.0
        val_rec_total = 0.0
        val_batches = 0

        with torch.no_grad():
            for images, masks, _ in val_loader:
                images = images.to(device)
                masks = masks.to(device)

                logits = model(images)
                loss = criterion(logits, masks)
                val_loss += loss.item() * images.size(0)

                probs = torch.sigmoid(logits)
                metrics = compute_segmentation_metrics(masks, probs, threshold=0.5)

                val_iou_total += metrics["iou"]
                val_dice_total += metrics["dice"]
                val_prec_total += metrics["precision"]
                val_rec_total += metrics["recall"]
                val_batches += 1

        val_loss /= val_size
        val_iou = val_iou_total / max(1, val_batches)
        val_dice = val_dice_total / max(1, val_batches)
        val_prec = val_prec_total / max(1, val_batches)
        val_rec = val_rec_total / max(1, val_batches)

        logger.info(
            "Epoch [%d/%d] - Train Loss: %.4f | Val Loss: %.4f | Val IoU: %.4f | Val Dice: %.4f | Val Rec: %.4f",
            epoch, epochs, train_loss, val_loss, val_iou, val_dice, val_rec
        )

        epoch_stats = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "val_iou": round(val_iou, 4),
            "val_dice": round(val_dice, 4),
            "val_precision": round(val_prec, 4),
            "val_recall": round(val_rec, 4),
        }
        history.append(epoch_stats)

        # Checkpoint if best
        if val_loss < best_val_loss:
            best_val_loss = val_loss

    # Compile final metadata and save model
    final_metrics = history[-1] if history else {}
    training_meta = {
        "is_synthetic_training_data": is_synthetic,
        "dataset_source": str(data_dir),
        "epochs_trained": epochs,
        "batch_size": batch_size,
        "learning_rate": lr,
        "best_val_loss": round(best_val_loss, 4),
        "final_metrics": final_metrics,
        "training_history": history,
        "scientific_notice": (
            "Model trained strictly on SYNTHETIC benchmark data for pipeline validation. "
            "Operational deployment requires verified labeled satellite ground truth."
            if is_synthetic else "Model trained on provided dataset."
        ),
    }

    weights_file, meta_file = save_segmentation_model(
        model, output_dir, training_meta, logger=logger
    )
    logger.info("Segmentation model checkpoint saved to: %s", weights_file)

    return {
        "status": "success",
        "model_type": "segmentation",
        "is_synthetic": is_synthetic,
        "weights_file": str(weights_file),
        "metadata_file": str(meta_file),
        "metrics": final_metrics,
        "output_dir": str(output_dir),
    }
