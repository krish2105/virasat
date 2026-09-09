"""Turn change candidates into `changes` rows with evidence crops, ready for the graph.

Sources:
  * Open Buildings candidates (data/processed/ob_candidates.jsonl) — building scale.
  * Siamese detector outputs — only once a trained, calibrated checkpoint exists.

Evidence crops are rendered from the manifested rasters: Sentinel-2 true colour
(before/after) and the Open Buildings presence delta as the change mask.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from datetime import date
from pathlib import Path
from typing import cast

import numpy as np
import rasterio
import structlog
from geoalchemy2.shape import from_shape
from PIL import Image
from pyproj import Transformer
from rasterio.windows import from_bounds
from shapely.geometry import Point, shape
from sqlalchemy import select

from virasat.db.models import Building, Change, ChangeType, Run, Tile
from virasat.db.session import session_scope
from virasat.geo.chowkri import chowkri_of
from virasat.geo.zoning import zone_of
from virasat.vision.calibrate import load as load_temperature

log = structlog.get_logger()
CANDIDATES = Path("data/processed/ob_candidates.jsonl")
EVIDENCE = Path("data/processed/evidence")
INDEX = Path("data/processed/index.jsonl")
CROP_M = 160.0
UPSCALE = 8


def _sentinel(label: str) -> Path:
    return sorted(Path(f"data/raw/sentinel/{label}").glob("S2*"))[0]


def _rgb_crop(scene: Path, x: float, y: float) -> Image.Image:
    bands = []
    for b in ("B04", "B03", "B02"):
        with rasterio.open(scene / f"{b}.tif") as src:
            win = from_bounds(x - CROP_M, y - CROP_M, x + CROP_M, y + CROP_M, src.transform)
            bands.append(src.read(1, window=win.round_offsets().round_lengths()).astype(float))
    rgb = np.stack(bands, -1)
    rgb = np.clip((rgb - 200) / 2500, 0, 1) ** 0.7 * 255
    img = Image.fromarray(rgb.astype(np.uint8))
    return img.resize((img.width * UPSCALE, img.height * UPSCALE), Image.Resampling.NEAREST)


def _mask_crop(year_before: int, year_after: int, x: float, y: float) -> Image.Image:
    arrs = []
    for yr in (year_before, year_after):
        with rasterio.open(f"data/raw/open_buildings/open_buildings_{yr}.tif") as src:
            win = from_bounds(x - CROP_M, y - CROP_M, x + CROP_M, y + CROP_M, src.transform)
            arrs.append(src.read(3, window=win.round_offsets().round_lengths()))
    delta = arrs[1] - arrs[0]
    rgb = np.zeros((*delta.shape, 3), np.uint8)
    rgb[..., 0] = np.clip(-delta * 255, 0, 255)  # red: presence lost
    rgb[..., 1] = np.clip(delta * 255, 0, 255)  # green: presence gained
    img = Image.fromarray(rgb)
    return img.resize((img.width * 2, img.height * 2), Image.Resampling.NEAREST)


def _tile_for(x: float, y: float, tiles: list[dict[str, object]]) -> dict[str, object] | None:
    for m in tiles:
        x0, y0, size = float(m["x0"]), float(m["y0"]), float(m["size_m"])  # type: ignore[arg-type]
        if x0 <= x < x0 + size and y0 - size < y <= y0:
            return m
    return None


def main() -> None:
    if not CANDIDATES.exists():
        raise SystemExit("infer: run `python -m virasat.vision.open_buildings` first")
    rows = [json.loads(ln) for ln in CANDIDATES.read_text().splitlines()]
    tiles = [json.loads(ln) for ln in INDEX.read_text().splitlines()]
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    temp = load_temperature()
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    before_scene, after_scene = _sentinel("2019"), _sentinel("current")
    created = 0
    with session_scope() as s:
        run = Run(
            epoch_before=date(rows[0]["year_before"], 6, 30),
            epoch_after=date(rows[0]["year_after"], 6, 30),
            git_sha=sha,
            config_hash="open_buildings",
            status="running",
            progress={"source": "open_buildings_2.5d_temporal", "candidates": len(rows)},
        )
        s.add(run)
        s.flush()
        existing = set(s.scalars(select(Change.building_id).where(Change.building_id.is_not(None))))
        known_tiles = set(s.scalars(select(Tile.id)))
        for r in rows:
            if r["building_id"] in existing:
                continue
            x, y = to_utm.transform(r["centroid_lon"], r["centroid_lat"])
            zone = zone_of(x, y)
            chowkri = chowkri_of(x, y) if zone == "core" else None
            m = _tile_for(x, y, tiles)
            if m is None:
                continue
            if m["tile_id"] not in known_tiles:
                x0, y0, size = float(m["x0"]), float(m["y0"]), float(m["size_m"])  # type: ignore[arg-type]
                poly = shape(
                    {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                (x0, y0),
                                (x0 + size, y0),
                                (x0 + size, y0 - size),
                                (x0, y0 - size),
                                (x0, y0),
                            ]
                        ],
                    }
                )
                centroid = [float(v) for v in cast(list[float], m["centroid"])]
                s.add(
                    Tile(
                        id=str(m["tile_id"]),
                        geom=from_shape(poly, srid=32643),
                        centroid_lon=float(centroid[0]),
                        centroid_lat=float(centroid[1]),
                        zone=m["zone"],
                        chowkri_id=m["chowkri_id"],
                        quarantined=bool(m["quarantined"]),
                        residual_px=float(str(m["residual_px"])),
                        season_mismatch=bool(m["season_mismatch"]),
                    )
                )
                known_tiles.add(str(m["tile_id"]))
            if s.get(Building, r["building_id"]) is None:
                fp = shape(r["footprint"])
                fp_utm = shape(
                    {
                        "type": "Polygon",
                        "coordinates": [[to_utm.transform(*c) for c in fp.exterior.coords]],
                    }
                )
                s.add(
                    Building(
                        id=r["building_id"],
                        footprint=from_shape(fp_utm, srid=32643),
                        zone=zone,
                        chowkri_id=chowkri,
                        source_ref="osm-way",
                    )
                )
            change_id = uuid.uuid4()
            out = EVIDENCE / str(change_id)
            out.mkdir(parents=True, exist_ok=True)
            _rgb_crop(before_scene, x, y).save(out / "before.png")
            _rgb_crop(after_scene, x, y).save(out / "after.png")
            _mask_crop(r["year_before"], r["year_after"], x, y).save(out / "mask.png")
            s.add(
                Change(
                    id=change_id,
                    run_id=run.id,
                    tile_id=str(m["tile_id"]),
                    building_id=r["building_id"],
                    geom=from_shape(Point(x, y), srid=32643),
                    zone=zone,
                    chowkri_id=chowkri,
                    epoch_before=date(r["year_before"], 6, 30),
                    epoch_after=date(r["year_after"], 6, 30),
                    change_prob=float(r["confidence"]),
                    calibration_date=date.fromisoformat(str(temp["calibration_date"]))
                    if temp
                    else None,
                    change_type=ChangeType(r["change_type"]),
                    before_uri=f"/evidence/{change_id}/before.png",
                    after_uri=f"/evidence/{change_id}/after.png",
                    mask_uri=f"/evidence/{change_id}/mask.png",
                )
            )
            created += 1
        run.status = "detected"
        run.progress = {
            **run.progress,
            "changes_created": created,
            "note": (
                "confidence is the Open Buildings presence score, not a calibrated Siamese output"
            ),
        }
    log.info("infer_done", changes_created=created)
    print(f"infer: created {created} changes with evidence crops under {EVIDENCE}")


if __name__ == "__main__":
    main()
