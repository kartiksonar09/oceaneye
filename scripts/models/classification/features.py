"""
OceanEye Look-Alike Classification Feature Extraction Layer
Extracts radiometric, morphological, boundary gradient, and oceanographic context
features from SAR candidate patches to discriminate oil slicks from look-alikes.
"""

from typing import Any
import numpy as np


def extract_candidate_features(
    region_mask: np.ndarray,
    sar_image: np.ndarray,
    wind_speed: float | None = None,
    current_speed: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, float]:
    """
    Extract standardized feature vector for a candidate dark formation:
    - Radiometric backscatter statistics (mean, min, max, variance, skewness)
    - Geometry & morphology (area, perimeter approximation, compactness, aspect ratio)
    - Boundary contrast (background ring mean, contrast damping ratio, border gradient)
    - Oceanographic context (local wind speed, surface current velocity)
    """
    mask_bool = np.asarray(region_mask, dtype=bool)
    img = np.asarray(sar_image, dtype=np.float32)

    # Ensure 2D spatial dimensions match
    if mask_bool.shape[:2] != img.shape[:2]:
        raise ValueError(f"Spatial dimension mismatch: mask {mask_bool.shape} vs image {img.shape}")

    if img.ndim == 3:
        # Default to first polarization channel for intensity stats
        img_2d = img[:, :, 0]
    else:
        img_2d = img

    slick_pixels = img_2d[mask_bool]
    total_slick_count = len(slick_pixels)

    if total_slick_count == 0:
        # Fallback for empty mask
        return {
            "mean_intensity": 0.0,
            "min_intensity": 0.0,
            "max_intensity": 0.0,
            "intensity_variance": 0.0,
            "intensity_skewness": 0.0,
            "area_pixels": 0.0,
            "perimeter_approx": 0.0,
            "compactness": 0.0,
            "aspect_ratio": 1.0,
            "background_mean": float(np.mean(img_2d)),
            "contrast_ratio": 0.0,
            "gradient_boundary_mean": 0.0,
            "local_wind_speed": float(wind_speed or 5.0),
            "local_current_speed": float(current_speed or 0.2),
        }

    # 1. Radiometric Backscatter Statistics
    mean_int = float(np.mean(slick_pixels))
    min_int = float(np.min(slick_pixels))
    max_int = float(np.max(slick_pixels))
    var_int = float(np.var(slick_pixels))

    # Skewness
    std_int = np.std(slick_pixels)
    if std_int > 1e-6:
        skew_int = float(np.mean(((slick_pixels - mean_int) / std_int) ** 3))
    else:
        skew_int = 0.0

    # 2. Geometry & Morphology
    area = float(total_slick_count)

    # Approximate perimeter via edge detection on binary mask
    eroded_mask = np.zeros_like(mask_bool)
    eroded_mask[1:-1, 1:-1] = (
        mask_bool[1:-1, 1:-1]
        & mask_bool[:-2, 1:-1]
        & mask_bool[2:, 1:-1]
        & mask_bool[1:-1, :-2]
        & mask_bool[1:-1, 2:]
    )
    border_mask = mask_bool & (~eroded_mask)
    perimeter = float(np.sum(border_mask))
    if perimeter < 1.0:
        perimeter = 1.0

    # Compactness (Isoperimetric quotient: 4 * pi * Area / Perimeter^2)
    compactness = float((4.0 * np.pi * area) / (perimeter**2))
    compactness = min(1.0, compactness)

    # Bounding Box Aspect Ratio
    y_indices, x_indices = np.where(mask_bool)
    h_box = float(np.max(y_indices) - np.min(y_indices) + 1)
    w_box = float(np.max(x_indices) - np.min(x_indices) + 1)
    aspect_ratio = float(max(h_box, w_box) / max(min(h_box, w_box), 1.0))

    # 3. Contextual Contrast & Boundary Gradient
    # Create background ring by dilating mask and subtracting original mask
    dilated_mask = np.zeros_like(mask_bool)
    dilated_mask[:-1, :] |= mask_bool[1:, :]
    dilated_mask[1:, :] |= mask_bool[:-1, :]
    dilated_mask[:, :-1] |= mask_bool[:, 1:]
    dilated_mask[:, 1:] |= mask_bool[:, :-1]
    ring_mask = dilated_mask & (~mask_bool)

    if np.sum(ring_mask) > 0:
        bg_mean = float(np.mean(img_2d[ring_mask]))
    else:
        bg_mean = float(np.mean(img_2d[~mask_bool])) if np.sum(~mask_bool) > 0 else mean_int

    # Damping / Contrast Ratio
    contrast_ratio = float((bg_mean - mean_int) / (bg_mean + 1e-6))

    # Boundary gradient magnitude
    grad_y, grad_x = np.gradient(img_2d)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    if np.sum(border_mask) > 0:
        border_grad = float(np.mean(grad_mag[border_mask]))
    else:
        border_grad = 0.0

    # 4. Oceanographic Context
    wind = float(wind_speed if wind_speed is not None else 5.0)
    current = float(current_speed if current_speed is not None else 0.2)

    return {
        "mean_intensity": round(mean_int, 4),
        "min_intensity": round(min_int, 4),
        "max_intensity": round(max_int, 4),
        "intensity_variance": round(var_int, 4),
        "intensity_skewness": round(skew_int, 4),
        "area_pixels": round(area, 1),
        "perimeter_approx": round(perimeter, 1),
        "compactness": round(compactness, 4),
        "aspect_ratio": round(aspect_ratio, 3),
        "background_mean": round(bg_mean, 4),
        "contrast_ratio": round(contrast_ratio, 4),
        "gradient_boundary_mean": round(border_grad, 4),
        "local_wind_speed": round(wind, 2),
        "local_current_speed": round(current, 2),
    }
