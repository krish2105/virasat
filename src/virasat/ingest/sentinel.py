"""Sentinel-2 L2A acquisition from Earth Search (AWS open data, no registration).

Scenes are pinned by STAC item id so the download is reproducible. Bands are read
straight out of the cloud-optimised GeoTIFFs, windowed to the study bbox, and
written unchanged to data/raw/. Nothing here is resampled or edited.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import rasterio
from pystac_client import Client
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from virasat.ingest.manifest import record

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
# Walled city + buffer, generous, WGS84 (west, south, east, north).
BBOX = (75.785, 26.885, 75.875, 26.955)
BANDS = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08"}
# Same season (December) in both epochs; lowest cloud cover available on 2026-09-09.
SCENES = {
    "2019": "S2A_43REK_20191226_3_L2A",
    "current": "S2C_43REK_20251204_0_L2A",
}
LICENCE = "Copernicus Sentinel data, free and open (Copernicus Sentinel Data legal notice)"
RAW = Path("data/raw/sentinel")


def download_scene(label: str, item_id: str) -> None:
    client = Client.open(STAC_URL)
    items = list(client.search(collections=[COLLECTION], ids=[item_id]).items())
    if len(items) != 1:
        sys.exit(f"sentinel: STAC returned {len(items)} items for {item_id}; expected 1")
    item = items[0]
    out = RAW / label / item_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "stac_item.json").write_text(json.dumps(item.to_dict(), indent=1))

    for key, band in BANDS.items():
        href = item.assets[key].href
        with rasterio.open(href) as src:
            if src.crs is None:
                sys.exit(f"sentinel: {href} has no CRS; refusing to guess")
            bounds = transform_bounds("EPSG:4326", src.crs, *BBOX)
            win = from_bounds(*bounds, src.transform).round_offsets().round_lengths()
            data = src.read(1, window=win)
            profile = src.profile.copy()
            profile.update(
                driver="GTiff",
                height=data.shape[0],
                width=data.shape[1],
                transform=src.window_transform(win),
                compress="deflate",
            )
            dest = out / f"{band}.tif"
            with rasterio.open(dest, "w", **profile) as dst:
                dst.write(data, 1)
            record(
                dest,
                source=href,
                licence=LICENCE,
                extent=f"bbox {BBOX} (windowed read)",
                crs=str(src.crs),
                notes=f"scene {item_id}, {item.datetime:%Y-%m-%d}, "
                f"cloud {item.properties.get('eo:cloud_cover')}%",
            )
        print(f"sentinel: {label} {band} {data.shape} -> {dest}")


def main() -> None:
    for label, item_id in SCENES.items():
        download_scene(label, item_id)


if __name__ == "__main__":
    main()
