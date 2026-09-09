"""Street-level imagery (Mapillary, CC BY-SA) with face and plate blurring at ingest.

Blurring happens in memory before any pixel is written to disk. The writer refuses
an image that has not passed through `blur`, and every written image carries a
sidecar recording that the blur ran. Detection is deliberately over-eager.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import httpx
import numpy as np
import numpy.typing as npt

from virasat.settings import settings

OUT = Path("data/processed/street")
GRAPH = "https://graph.mapillary.com/images"
FIELDS = "id,thumb_1024_url,computed_geometry,captured_at,is_pano"
Img = npt.NDArray[np.uint8]

_CASCADES = [
    "haarcascade_frontalface_default.xml",
    "haarcascade_profileface.xml",
    "haarcascade_russian_plate_number.xml",
]


@dataclass(frozen=True)
class Blurred:
    image: Img
    regions: int


def _detectors() -> list[cv2.CascadeClassifier]:
    base: str = cv2.data.haarcascades  # type: ignore[attr-defined]
    return [cv2.CascadeClassifier(base + name) for name in _CASCADES]


def blur(image: Img) -> Blurred:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    out = image.copy()
    n = 0
    for det in _detectors():
        boxes = det.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(16, 16))
        for x, y, w, h in boxes:
            pad_w, pad_h = int(w * 0.5), int(h * 0.5)  # over-blur: 1.5x boxes
            x0, y0 = max(0, x - pad_w), max(0, y - pad_h)
            x1, y1 = min(out.shape[1], x + w + pad_w), min(out.shape[0], y + h + pad_h)
            k = max(31, ((x1 - x0) // 2) | 1)
            out[y0:y1, x0:x1] = cv2.GaussianBlur(out[y0:y1, x0:x1], (k, k), 0)
            n += 1
    return Blurred(out, n)


def write(blurred: Blurred, image_id: str, meta: dict[str, object]) -> Path:
    if not isinstance(blurred, Blurred):
        raise TypeError("street.write only accepts a Blurred image")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{image_id}.jpg"
    cv2.imwrite(str(path), blurred.image)
    (OUT / f"{image_id}.json").write_text(
        json.dumps({**meta, "blur_applied": True, "blur_regions": blurred.regions})
    )
    return path


def fetch_bbox(bbox: tuple[float, float, float, float], limit: int = 200) -> int:
    if not settings.mapillary_token:
        sys.exit(
            "street: MAPILLARY_TOKEN is not set — register at mapillary.com and add it to .env"
        )
    params: dict[str, str | int] = {
        "access_token": settings.mapillary_token,
        "fields": FIELDS,
        "bbox": ",".join(str(v) for v in bbox),
        "limit": limit,
    }
    with httpx.Client(timeout=60) as client:
        items = client.get(GRAPH, params=params).raise_for_status().json()["data"]
        n = 0
        for it in items:
            if it.get("is_pano"):
                continue
            raw = np.frombuffer(client.get(it["thumb_1024_url"]).content, np.uint8)
            decoded = cv2.imdecode(raw, cv2.IMREAD_COLOR)
            if decoded is None:
                continue
            image: Img = decoded.astype(np.uint8)
            lon, lat = it["computed_geometry"]["coordinates"]
            write(
                blur(image),
                it["id"],
                {
                    "source": "mapillary",
                    "licence": "CC BY-SA 4.0",
                    "captured_at": it["captured_at"],
                    "lon": lon,
                    "lat": lat,
                },
            )
            n += 1
    return n


def main() -> None:
    from virasat.ingest.sentinel import BBOX

    print(f"street: wrote {fetch_bbox(BBOX)} blurred images to {OUT}")


if __name__ == "__main__":
    main()
