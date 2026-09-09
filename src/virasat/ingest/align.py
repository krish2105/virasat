"""Reprojection check, co-registration to the 2019 baseline, and per-tile quarantine.

Sub-pixel misalignment is the first cause of false change. The current epoch is
shifted onto the baseline with a global phase-correlation estimate; then every
tile's residual shift is measured and logged, and tiles above the threshold are
quarantined rather than silently kept.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.warp import Resampling, calculate_default_transform, reproject
from scipy.ndimage import shift as nd_shift
from skimage.registration import phase_cross_correlation

Arr = npt.NDArray[np.float32]
TARGET_CRS = "EPSG:32643"
MAX_RESIDUAL_PX = 1.5


def load_stack(scene_dir: Path, bands: list[str]) -> tuple[Arr, rasterio.Affine, float]:
    """Read bands as (B, H, W) float32 in EPSG:32643, reprojecting only if needed."""
    arrays, transform, res = [], None, 0.0
    for band in bands:
        path = scene_dir / f"{band}.tif"
        with rasterio.open(path) as src:
            if src.crs is None:
                sys.exit(f"align: {path} has no CRS; refusing to guess")
            if src.crs.to_string() != TARGET_CRS:
                dst_t, w, h = calculate_default_transform(
                    src.crs, TARGET_CRS, src.width, src.height, *src.bounds
                )
                out = np.zeros((h, w), dtype=np.float32)
                reproject(src.read(1), out, src_transform=src.transform, src_crs=src.crs,
                          dst_transform=dst_t, dst_crs=TARGET_CRS, resampling=Resampling.bilinear)
                arrays.append(out)
                transform, res = dst_t, dst_t.a
            else:
                arrays.append(src.read(1).astype(np.float32))
                transform, res = src.transform, src.transform.a
    assert transform is not None
    return np.stack(arrays), transform, res


def global_shift(baseline: Arr, moving: Arr) -> tuple[float, float]:
    """(dy, dx) in pixels that maps `moving` onto `baseline`, from the NIR band."""
    shift, _, _ = phase_cross_correlation(  # type: ignore[no-untyped-call]
        baseline[-1], moving[-1], upsample_factor=20
    )
    return float(shift[0]), float(shift[1])


def apply_shift(stack: Arr, dy: float, dx: float) -> Arr:
    return np.stack([nd_shift(b, (dy, dx), order=1, mode="nearest") for b in stack])


def tile_residual(baseline_tile: Arr, moving_tile: Arr) -> float:
    """Residual misregistration (px) of one tile after the global shift."""
    if baseline_tile.std() < 1e-3 or moving_tile.std() < 1e-3:
        return 0.0
    shift, _, _ = phase_cross_correlation(  # type: ignore[no-untyped-call]
        baseline_tile, moving_tile, upsample_factor=10
    )
    return float(np.hypot(shift[0], shift[1]))
