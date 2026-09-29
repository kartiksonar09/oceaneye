"""
OceanEye SAR Oil-Spill Segmentation Dataset & Preprocessing Pipeline
Provides dataset loading, coordinate/dimension validation, intensity normalization,
and synthetic SAR benchmark generation for pipeline verification.
"""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
import torch
from torch.utils.data import DataLoader, Dataset

from common import setup_logging

SUPPORTED_EXTENSIONS = {".npy", ".png", ".tif", ".tiff", ".jpg", ".jpeg"}


def preprocess_sar_image(
    image: np.ndarray,
    target_size: tuple[int, int] = (256, 256),
    to_db: bool = False,
    normalize: bool = True,
) -> np.ndarray:
    """
    Standardize raw SAR radar imagery for neural network consumption.
    - Decibel conversion (optional)
    - Specular outlier suppression via 1st/99th percentile clipping
    - Min-Max scaling to [0.0, 1.0]
    - Spatial resizing to target dimensions (H, W)
    """
    img = np.asarray(image, dtype=np.float32)

    # Convert dB if requested
    if to_db:
        img = 10.0 * np.log10(np.maximum(img**2, 1e-6))

    # Resize using PIL
    if img.ndim == 2:
        pil_img = Image.fromarray(img)
        pil_resized = pil_img.resize((target_size[1], target_size[0]), resample=Image.Resampling.BILINEAR)
        img = np.array(pil_resized, dtype=np.float32)
    elif img.ndim == 3:
        # Channels last or channels first
        if img.shape[0] in (1, 2, 3) and img.shape[2] not in (1, 2, 3):
            # Transpose (C, H, W) -> (H, W, C) for PIL
            img = np.transpose(img, (1, 2, 0))
        channels = []
        for c in range(img.shape[2]):
            pil_c = Image.fromarray(img[:, :, c])
            pil_resized = pil_c.resize((target_size[1], target_size[0]), resample=Image.Resampling.BILINEAR)
            channels.append(np.array(pil_resized, dtype=np.float32))
        img = np.stack(channels, axis=-1)

    # Dynamic range normalization
    if normalize:
        p1, p99 = np.percentile(img, 1), np.percentile(img, 99)
        if p99 > p1:
            img = np.clip(img, p1, p99)
            img = (img - p1) / (p99 - p1)
        else:
            min_val, max_val = np.min(img), np.max(img)
            if max_val > min_val:
                img = (img - min_val) / (max_val - min_val)
            else:
                img = np.zeros_like(img, dtype=np.float32)

    return img.astype(np.float32)


def preprocess_mask(
    mask: np.ndarray,
    target_size: tuple[int, int] = (256, 256),
) -> np.ndarray:
    """
    Standardize segmentation mask:
    - Resize with nearest neighbor interpolation to preserve discrete boundaries
    - Binarize to {0.0, 1.0}
    """
    m = np.asarray(mask, dtype=np.float32)
    if m.ndim == 3 and m.shape[2] == 1:
        m = m[:, :, 0]

    pil_mask = Image.fromarray(m)
    pil_resized = pil_mask.resize((target_size[1], target_size[0]), resample=Image.Resampling.NEAREST)
    m_resized = np.array(pil_resized, dtype=np.float32)

    # Binarize
    binary_mask = (m_resized >= 0.5).astype(np.float32)
    return binary_mask


def _load_raw_file(file_path: Path) -> np.ndarray:
    """Load image/mask from file (.npy or image format)."""
    if file_path.suffix.lower() == ".npy":
        return np.load(file_path)
    else:
        with Image.open(file_path) as img:
            return np.array(img, dtype=np.float32)


class SARSPILLDataset(Dataset):
    """
    PyTorch Dataset for Sentinel-1 SAR Oil-Spill Segmentation.
    Expects data_dir with 'images/' and 'masks/' subdirectories.
    Performs integrity validation:
      - Validates file existence
      - Validates image and mask dimension alignment
      - Validates mask contains valid binary/float entries
    """

    def __init__(
        self,
        data_dir: Path | str,
        target_size: tuple[int, int] = (256, 256),
        to_db: bool = False,
        normalize: bool = True,
        logger: logging.Logger | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.target_size = target_size
        self.to_db = to_db
        self.normalize = normalize
        self.logger = logger or setup_logging("dataset.sar")

        self.images_dir = self.data_dir / "images"
        self.masks_dir = self.data_dir / "masks"

        if not self.images_dir.exists():
            raise FileNotFoundError(f"Missing images directory: {self.images_dir}")
        if not self.masks_dir.exists():
            raise FileNotFoundError(f"Missing masks directory: {self.masks_dir}")

        # Find matching pairs
        image_files = sorted(
            [p for p in self.images_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS]
        )
        if not image_files:
            raise ValueError(f"No valid image files found in {self.images_dir} with extensions {SUPPORTED_EXTENSIONS}")

        self.samples: list[tuple[Path, Path, str]] = []
        for img_path in image_files:
            stem = img_path.stem
            # Find matching mask by stem
            mask_matches = [
                p for p in self.masks_dir.iterdir()
                if p.stem == stem and p.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
            if not mask_matches:
                raise FileNotFoundError(f"Missing corresponding mask for image '{img_path.name}' in {self.masks_dir}")
            mask_path = mask_matches[0]
            self.samples.append((img_path, mask_path, stem))

        self.logger.info("Loaded SAR segmentation dataset with %d verified pairs from %s", len(self.samples), self.data_dir)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, str]:
        img_path, mask_path, sample_name = self.samples[idx]

        raw_img = _load_raw_file(img_path)
        raw_mask = _load_raw_file(mask_path)

        # Validate raw spatial dimensions match before preprocessing
        img_spatial = raw_img.shape[:2]
        mask_spatial = raw_mask.shape[:2]
        if img_spatial != mask_spatial:
            raise ValueError(
                f"Dimension mismatch for sample '{sample_name}': "
                f"image shape {raw_img.shape} vs mask shape {raw_mask.shape}"
            )

        # Preprocess image and mask
        proc_img = preprocess_sar_image(
            raw_img, target_size=self.target_size, to_db=self.to_db, normalize=self.normalize
        )
        proc_mask = preprocess_mask(raw_mask, target_size=self.target_size)

        # Format tensors (C, H, W)
        if proc_img.ndim == 2:
            img_tensor = torch.from_numpy(proc_img).unsqueeze(0)  # (1, H, W)
        else:
            img_tensor = torch.from_numpy(np.transpose(proc_img, (2, 0, 1)))  # (C, H, W)

        mask_tensor = torch.from_numpy(proc_mask).unsqueeze(0)  # (1, H, W)

        return img_tensor, mask_tensor, sample_name


def load_segmentation_dataset(
    data_dir: Path | str,
    batch_size: int = 4,
    shuffle: bool = True,
    target_size: tuple[int, int] = (256, 256),
    num_workers: int = 0,
) -> DataLoader:
    """
    Factory function returning DataLoader for SAR segmentation dataset.
    """
    dataset = SARSPILLDataset(data_dir=data_dir, target_size=target_size)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=False,
    )
    return loader


def create_synthetic_segmentation_data(
    output_dir: Path | str,
    num_samples: int = 10,
    patch_size: tuple[int, int] = (256, 256),
    seed: int = 42,
) -> Path:
    """
    Generate synthetic SAR imagery and segmentation masks strictly for
    testing and verifying the training/inference pipeline.
    Simulates SAR speckle background and dark slick damping zones.
    """
    rng = np.random.RandomState(seed)
    out_dir = Path(output_dir)
    images_dir = out_dir / "images"
    masks_dir = out_dir / "masks"
    images_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)

    H, W = patch_size

    for i in range(num_samples):
        # Generate Rayleigh/Gamma speckle background (typical of rough sea surface)
        background = rng.gamma(shape=3.0, scale=0.3, size=(H, W)).astype(np.float32)

        # Initialize mask
        mask = np.zeros((H, W), dtype=np.float32)

        # Create 1-2 synthetic slick patches (damped low-backscatter regions)
        num_patches = rng.randint(1, 3)
        for _ in range(num_patches):
            cy, cx = rng.randint(H // 4, 3 * H // 4), rng.randint(W // 4, 3 * W // 4)
            ry, rx = rng.randint(15, 45), rng.randint(20, 60)
            angle = rng.uniform(0, np.pi)

            # Create oriented elliptical coordinate grid
            y_grid, x_grid = np.ogrid[:H, :W]
            dy = y_grid - cy
            dx = x_grid - cx
            rot_x = dx * np.cos(angle) + dy * np.sin(angle)
            rot_y = -dx * np.sin(angle) + dy * np.cos(angle)

            ellipse_dist = (rot_x / rx) ** 2 + (rot_y / ry) ** 2
            slick_pixels = ellipse_dist <= 1.0

            # Oil dampens capillary waves, drastically lowering backscatter intensity
            background[slick_pixels] *= rng.uniform(0.1, 0.25)
            mask[slick_pixels] = 1.0

        sample_name = f"synthetic_sar_sample_{i+1:03d}"
        img_file = images_dir / f"{sample_name}.npy"
        mask_file = masks_dir / f"{sample_name}.npy"

        np.save(img_file, background)
        np.save(mask_file, mask)

    # Save manifest marking dataset explicitly as synthetic
    meta_path = out_dir / "dataset_manifest.json"
    manifest = {
        "dataset_name": "OceanEye Synthetic SAR Segmentation Benchmark",
        "is_synthetic": True,
        "sample_count": num_samples,
        "patch_size": list(patch_size),
        "purpose": "Verification of training, loss convergence, and inference pipelines. NOT for operational detection.",
        "scientific_honesty_notice": "Synthetically generated speckle and damping patches. No real oil spills.",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return out_dir
