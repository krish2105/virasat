"""Building-scale change candidates from Google Open Buildings 2.5D Temporal.

Per building footprint (OSM, synthetic id), compare presence and height between the
first and last available years inside each footprint. This is a deterministic
adapter, not a learned model; its confidence is the dataset's own presence score,
so it is *not* calibrated by our temperature scaling and is flagged as such.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask
from shapely.geometry import Polygon, mapping
from shapely.ops import transform as sh_transform

RAW = Path("data/raw/open_buildings")
BUILDINGS = sorted(Path("data/raw/osm/bld_parts").glob("part*.json"))
OUT = Path("data/processed/ob_candidates.jsonl")
NODATA = -99.0
PRESENCE_ON, PRESENCE_OFF = 0.6, 0.3
HEIGHT_DELTA_M = 3.0  # roughly one storey
MIN_AREA_M2 = 40.0


@dataclass(frozen=True)
class Candidate:
    building_id: str
    change_type: str
    confidence: float
    year_before: int
    year_after: int
    presence_before: float
    presence_after: float
    height_before: float
    height_after: float
    centroid_lon: float
    centroid_lat: float
    footprint: dict[str, object]


def synthetic_id(osm_type: str, osm_id: int) -> str:
    return "B-" + hashlib.sha256(f"{osm_type}/{osm_id}".encode()).hexdigest()[:10]


def footprints(to_utm: Transformer) -> list[tuple[str, Polygon, tuple[float, float]]]:
    out = []
    seen: set[str] = set()  # ways straddling a bbox quadrant appear in two parts
    for part in BUILDINGS:
        for e in json.loads(part.read_text())["elements"]:
            if e["type"] != "way" or "geometry" not in e:
                continue
            ring = [(p["lon"], p["lat"]) for p in e["geometry"]]
            if len(ring) < 4:
                continue
            bid = synthetic_id(e["type"], e["id"])
            if bid in seen:
                continue
            poly = sh_transform(to_utm.transform, Polygon(ring))
            if poly.is_valid and poly.area >= MIN_AREA_M2:
                seen.add(bid)
                c = Polygon(ring).centroid
                out.append((bid, poly, (c.x, c.y)))
    return out


def _stats(src: rasterio.DatasetReader, poly: Polygon) -> tuple[float, float] | None:
    win = rasterio.windows.from_bounds(*poly.bounds, src.transform).round_offsets().round_lengths()
    if win.width < 1 or win.height < 1:
        return None
    data = src.read(window=win)
    mask = geometry_mask(
        [mapping(poly)], out_shape=data.shape[1:], transform=src.window_transform(win), invert=True
    )
    presence, height = data[2][mask], data[1][mask]
    valid = presence != NODATA
    if not valid.any():
        return None
    return float(presence[valid].mean()), float(height[valid].mean())


def candidates(year_before: int, year_after: int) -> list[Candidate]:
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    out: list[Candidate] = []
    with (
        rasterio.open(RAW / f"open_buildings_{year_before}.tif") as a,
        rasterio.open(RAW / f"open_buildings_{year_after}.tif") as b,
    ):
        for bid, poly, (lon, lat) in footprints(to_utm):
            sa, sb = _stats(a, poly), _stats(b, poly)
            if sa is None or sb is None:
                continue
            (pa, ha), (pb, hb) = sa, sb
            ctype = None
            if pa < PRESENCE_OFF and pb > PRESENCE_ON:
                ctype, conf = "NEW_CONSTRUCTION", pb
            elif pa > PRESENCE_ON and pb < PRESENCE_OFF:
                ctype, conf = "DEMOLITION", pa
            elif pa > PRESENCE_ON and pb > PRESENCE_ON and hb - ha >= HEIGHT_DELTA_M:
                ctype, conf = "VERTICAL_ADDITION", min(pa, pb)
            if ctype:
                out.append(
                    Candidate(
                        bid,
                        ctype,
                        round(conf, 3),
                        year_before,
                        year_after,
                        round(pa, 3),
                        round(pb, 3),
                        round(ha, 1),
                        round(hb, 1),
                        round(lon, 6),
                        round(lat, 6),
                        mapping(
                            sh_transform(
                                Transformer.from_crs(
                                    "EPSG:32643", "EPSG:4326", always_xy=True
                                ).transform,
                                poly,
                            )
                        ),
                    )
                )
    return out


def main() -> None:
    years = sorted(int(p.stem.split("_")[-1]) for p in RAW.glob("open_buildings_*.tif"))
    if len(years) < 2:
        raise SystemExit("open_buildings: need at least two annual mosaics")
    found = candidates(years[0], years[-1])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for c in found:
            f.write(json.dumps(c.__dict__) + "\n")
    by_type = {
        t: sum(c.change_type == t for c in found)
        for t in ("NEW_CONSTRUCTION", "DEMOLITION", "VERTICAL_ADDITION")
    }
    print(f"open_buildings: {len(found)} candidates {years[0]}->{years[-1]} {by_type} -> {OUT}")


if __name__ == "__main__":
    main()
