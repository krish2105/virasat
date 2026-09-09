"""Export the massing model for the landing page: OSM footprints inside the core and
near buffer, Open Buildings heights, and per-building change events from the
candidate list. Coordinates are metres relative to the core centroid (EPSG:32643).
Writes web/public/city.json. No building identity beyond the synthetic id."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds
from shapely.geometry import shape
from shapely.ops import transform as sh_transform

from virasat.vision.open_buildings import footprints

OUT = Path("web/public/city.json")
CORE = Path("data/boundaries/core.geojson")
BUFFER = Path("data/boundaries/buffer.geojson")
CANDIDATES = Path("data/processed/ob_candidates.jsonl")
HEIGHT_RASTER = Path("data/raw/open_buildings/open_buildings_2023.tif")
RADIUS_M = 1900.0


def main() -> None:
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    core = sh_transform(
        to_utm.transform, shape(json.loads(CORE.read_text())["features"][0]["geometry"])
    )
    cx, cy = core.centroid.x, core.centroid.y
    changes = {}
    if CANDIDATES.exists():
        for ln in CANDIDATES.read_text().splitlines():
            r = json.loads(ln)
            changes[r["building_id"]] = {
                "type": r["change_type"],
                "year": r["year_after"],
                "from": r["year_before"],
            }
    buildings = []
    with rasterio.open(HEIGHT_RASTER) as src:
        for bid, poly, _ in footprints(to_utm):
            if poly.centroid.distance(core.centroid) > RADIUS_M:
                continue
            win = from_bounds(*poly.bounds, src.transform).round_offsets().round_lengths()
            h = 6.0
            if win.width >= 1 and win.height >= 1:
                data = src.read(2, window=win)
                valid = data[data > 0]
                if valid.size:
                    h = float(np.clip(np.median(valid), 3.0, 30.0))
            simple = poly.simplify(1.5)
            ring = [[round(x - cx, 1), round(y - cy, 1)] for x, y in simple.exterior.coords[:-1]]
            if len(ring) < 3:
                continue
            b: dict[str, object] = {
                "id": bid,
                "ring": ring,
                "h": round(h, 1),
                "core": core.contains(poly.centroid),
            }
            if bid in changes:
                b["change"] = changes[bid]
            buildings.append(b)

    def outline(path: Path) -> list[list[list[float]]]:
        g = sh_transform(
            to_utm.transform, shape(json.loads(path.read_text())["features"][0]["geometry"])
        )
        polys = getattr(g, "geoms", [g])
        return [
            [[round(x - cx, 1), round(y - cy, 1)] for x, y in p.exterior.simplify(5).coords]
            for p in polys
        ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "origin": [cx, cy],
                "crs": "EPSG:32643",
                "buildings": buildings,
                "core": outline(CORE),
                "buffer": outline(BUFFER),
                "years": [2016, 2026],
                "attribution": "OSM ODbL · Open Buildings CC BY 4.0 · UNESCO WHC 1605",
            },
            separators=(",", ":"),
        )
    )
    print(
        f"city_export: {len(buildings)} buildings, "
        f"{sum('change' in b for b in buildings)} with changes -> {OUT} "
        f"({OUT.stat().st_size / 1e6:.1f} MB)"
    )


if __name__ == "__main__":
    main()
