"""Zone assignment from the georeferenced inscribed-property polygons."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as sh_transform

Zone = Literal["core", "buffer", "outside"]
CONFIG = Path("config/zones.yaml")
SECTORS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]


@lru_cache(maxsize=1)
def _polygons() -> tuple[BaseGeometry, BaseGeometry]:
    cfg = yaml.safe_load(CONFIG.read_text())
    to_utm = Transformer.from_crs("EPSG:4326", cfg["crs"], always_xy=True).transform

    def load(key: str) -> BaseGeometry:
        path = Path(cfg["boundaries"][key])
        if not path.exists():
            raise FileNotFoundError(f"{path} missing — run virasat.ingest.whc_boundary")
        geom = shape(json.loads(path.read_text())["features"][0]["geometry"])
        return sh_transform(to_utm, geom)

    return load("core"), load("buffer")


def zone_of(x: float, y: float) -> Zone:
    """Zone for a point in EPSG:32643."""
    core, buf = _polygons()
    p = Point(x, y)
    if core.contains(p):
        return "core"
    if buf.contains(p):
        return "buffer"
    return "outside"


def sector_of(x: float, y: float) -> str:
    """Compass sector around the core centroid; the spatial block for non-core tiles."""
    core, _ = _polygons()
    c = core.centroid
    ang = math.degrees(math.atan2(y - c.y, x - c.x)) % 360
    return "buffer_" + SECTORS[int((ang + 22.5) // 45) % 8]
