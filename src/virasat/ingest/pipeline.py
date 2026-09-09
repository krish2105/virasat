"""raw tiles -> reproject -> co-register -> tile -> normalise -> pair -> processed

`uv run pipeline`. Tiles are defined by ground extent in metres (config/zones.yaml)
so the same grid applies to every source resolution.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

import numpy as np
import structlog
import yaml
from pyproj import Transformer

from virasat.geo.chowkri import chowkri_of
from virasat.geo.zoning import sector_of, zone_of
from virasat.ingest.align import (
    MAX_RESIDUAL_PX,
    apply_shift,
    global_shift,
    load_stack,
    tile_residual,
)

log = structlog.get_logger()
RAW = Path("data/raw/sentinel")
INTERIM = Path("data/interim")
PROCESSED = Path("data/processed")
BANDS = ["B02", "B03", "B04", "B08"]
WINTER = {11, 12, 1, 2}


def _scene(label: str) -> tuple[Path, date]:
    dirs = sorted((RAW / label).glob("S2*"))
    if len(dirs) != 1:
        sys.exit(f"pipeline: expected one scene under {RAW / label}, found {len(dirs)}")
    item = json.loads((dirs[0] / "stac_item.json").read_text())
    return dirs[0], date.fromisoformat(item["properties"]["datetime"][:10])


def _season(d: date) -> str:
    return "winter" if d.month in WINTER else "other"


def main() -> None:
    cfg = yaml.safe_load(Path("config/zones.yaml").read_text())
    splits = yaml.safe_load(Path("config/splits.yaml").read_text())
    tile_m, overlap_m = cfg["tile_size_m"], cfg["tile_overlap_m"]

    before_dir, before_date = _scene("2019")
    after_dir, after_date = _scene("current")
    before, transform, res = load_stack(before_dir, BANDS)
    after, t2, res2 = load_stack(after_dir, BANDS)
    if before.shape != after.shape or transform != t2:
        sys.exit("pipeline: epochs are not on the same grid; extend align.py before continuing")

    dy, dx = global_shift(before, after)
    after = apply_shift(after, dy, dx)
    log.info("coregistration", global_shift_px={"dy": round(dy, 3), "dx": round(dx, 3)})

    px = int(round(tile_m / res))
    step = int(round((tile_m - overlap_m) / res))
    to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
    season_mismatch = _season(before_date) != _season(after_date)

    tiles_dir, quarantine = PROCESSED / "tiles", INTERIM / "quarantine"
    for d in (tiles_dir, quarantine):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    index: list[dict[str, object]] = []
    residuals: list[float] = []
    for r0 in range(0, before.shape[1] - px + 1, step):
        for c0 in range(0, before.shape[2] - px + 1, step):
            b, a = before[:, r0 : r0 + px, c0 : c0 + px], after[:, r0 : r0 + px, c0 : c0 + px]
            x0, y0 = transform * (c0, r0)
            cx, cy = transform * (c0 + px / 2, r0 + px / 2)
            zone = zone_of(cx, cy)
            chowkri = chowkri_of(cx, cy) if zone == "core" else None
            block = chowkri or sector_of(cx, cy)
            split = next((k for k in ("val", "test") if block in splits[k]), "train")
            resid = tile_residual(b[-1], a[-1])
            residuals.append(resid)
            tile_id = f"{int(x0)}_{int(y0)}"
            lon, lat = to_wgs.transform(cx, cy)
            meta = {
                "tile_id": tile_id, "x0": x0, "y0": y0, "size_m": tile_m, "res_m": res,
                "centroid": [round(lon, 6), round(lat, 6)], "zone": zone, "chowkri_id": chowkri,
                "spatial_block": block, "split": split,
                "epoch_before": before_date.isoformat(), "epoch_after": after_date.isoformat(),
                "season_mismatch": season_mismatch, "residual_px": round(resid, 3),
                "quarantined": resid > MAX_RESIDUAL_PX, "source": "sentinel-2-l2a",
            }
            dest = quarantine if meta["quarantined"] else tiles_dir
            np.savez_compressed(dest / f"{tile_id}.npz", before=b, after=a, meta=json.dumps(meta))
            index.append(meta)

    train = [m for m in index if m["split"] == "train" and not m["quarantined"]]
    if not train:
        sys.exit("pipeline: no training tiles; check splits.yaml")
    arrays = []
    for m in train:
        npz = np.load(tiles_dir / f"{m['tile_id']}.npz")
        arrays += [npz["before"], npz["after"]]
    stack = np.concatenate(arrays, axis=1)
    stats = {"bands": BANDS, "mean": stack.mean(axis=(1, 2)).tolist(),
             "std": stack.std(axis=(1, 2)).tolist(), "computed_on": "train split only",
             "n_train_tiles": len(train)}
    (PROCESSED / "norm_stats.json").write_text(json.dumps(stats, indent=1))
    with (PROCESSED / "index.jsonl").open("w") as f:
        for m in index:
            f.write(json.dumps(m) + "\n")

    q = sum(1 for m in index if m["quarantined"]) / len(index)
    summary = {
        "tiles": len(index), "tile_px": px, "quarantine_rate": round(q, 4),
        "residual_px": {"median": round(float(np.median(residuals)), 3),
                        "p95": round(float(np.percentile(residuals, 95)), 3)},
        "by_zone": {z: sum(m["zone"] == z for m in index) for z in ("core", "buffer", "outside")},
        "by_split": {s: sum(m["split"] == s for m in index) for s in ("train", "val", "test")},
        "season_mismatch": season_mismatch, "global_shift_px": [dy, dx],
    }
    (PROCESSED / "pipeline_report.json").write_text(json.dumps(summary, indent=1))
    log.info("pipeline_done", **summary)


if __name__ == "__main__":
    main()
