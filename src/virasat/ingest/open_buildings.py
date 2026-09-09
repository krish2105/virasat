"""Google Open Buildings 2.5D Temporal (v1) acquisition — public GCS bucket, no auth.

Annual rasters 2016-2023 of building presence, fractional count and height at an
effective ~4 m resolution (delivered at 0.5 m). For each year the tiles that
intersect the study bbox are read through their built-in overviews at 4 m and
mosaicked; nodata (-99) never overwrites data. Licence: CC BY 4.0 / ODbL 1.0.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from virasat.ingest.manifest import record
from virasat.ingest.sentinel import BBOX

BUCKET = "https://storage.googleapis.com/open-buildings-temporal-data/"
# S2 level-1 cell manifests that contain UTM 43N tiles; "3b" has none over Jaipur.
MANIFESTS = ["39"]
YEARS = range(2016, 2024)
BANDS = ["building_fractional_count", "building_height", "building_presence"]
NODATA = -99.0
RES_M = 4.0
RAW = Path("data/raw/open_buildings")
LICENCE = "CC BY 4.0 and ODbL 1.0 (Google Open Buildings 2.5D Temporal v1)"


def tiles_for_year(cell: str, year: int, bounds: tuple[float, float, float, float]) -> list[str]:
    url = f"{BUCKET}v1/manifests/{cell}_EPSG_32643_{year}_06_30.json"
    with urllib.request.urlopen(url, timeout=60) as r:
        man = json.load(r)
    prefix = man["uriPrefix"].replace("gs://open-buildings-temporal-data/", "")
    x0, y0, x1, y1 = bounds
    hits = []
    for src in man["tilesets"][0]["sources"]:
        a, dim = src["affineTransform"], src["dimensions"]
        tx0, ty1 = a["translateX"], a["translateY"]
        tx1, ty0 = tx0 + a["scaleX"] * dim["width"], ty1 + a["scaleY"] * dim["height"]
        if tx0 < x1 and tx1 > x0 and ty0 < y1 and ty1 > y0:
            hits.append(f"{BUCKET}{prefix}{src['uris'][0]}")
    return hits


def mosaic_year(year: int) -> None:
    bounds = transform_bounds("EPSG:4326", "EPSG:32643", *BBOX)
    x0 = np.floor(bounds[0] / RES_M) * RES_M
    y1 = np.ceil(bounds[3] / RES_M) * RES_M
    width = int(np.ceil((bounds[2] - x0) / RES_M))
    height = int(np.ceil((y1 - bounds[1]) / RES_M))
    out = np.full((3, height, width), NODATA, dtype=np.float32)
    transform = from_origin(x0, y1, RES_M, RES_M)

    urls = [u for cell in MANIFESTS for u in tiles_for_year(cell, year, bounds)]
    if not urls:
        sys.exit(f"open_buildings: no tiles intersect the study bbox for {year}")
    for url in urls:
        with rasterio.open(url) as src:
            if src.crs.to_epsg() != 32643:
                sys.exit(f"open_buildings: {url} is {src.crs}, expected EPSG:32643")
            ix0, ix1 = max(x0, src.bounds.left), min(x0 + width * RES_M, src.bounds.right)
            iy0, iy1 = max(y1 - height * RES_M, src.bounds.bottom), min(y1, src.bounds.top)
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            win = from_bounds(ix0, iy0, ix1, iy1, src.transform)
            c0, r0 = int(round((ix0 - x0) / RES_M)), int(round((y1 - iy1) / RES_M))
            w, h = int(round((ix1 - ix0) / RES_M)), int(round((iy1 - iy0) / RES_M))
            data = src.read(window=win, out_shape=(3, h, w))
            block = out[:, r0 : r0 + h, c0 : c0 + w]
            mask = data != NODATA
            block[mask] = data[mask]
    coverage = float((out[2] != NODATA).mean())
    dest = RAW / f"open_buildings_{year}.tif"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        dest,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype="float32",
        crs="EPSG:32643",
        transform=transform,
        nodata=NODATA,
        compress="deflate",
    ) as dst:
        dst.write(out)
        for i, b in enumerate(BANDS, start=1):
            dst.set_band_description(i, b)
    record(
        dest,
        source=", ".join(urls),
        licence=LICENCE,
        extent=f"bbox {BBOX}",
        crs="EPSG:32643",
        notes=f"year {year}; read at {RES_M} m via overviews; coverage {coverage:.1%}",
    )
    print(f"open_buildings: {year} {out.shape} coverage {coverage:.1%} -> {dest}")


def main() -> None:
    for year in YEARS:
        mosaic_year(year)


if __name__ == "__main__":
    main()
