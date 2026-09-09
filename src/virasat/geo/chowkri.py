"""Chowkri (ward) assignment for fairness slicing."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as sh_transform

CONFIG = Path("config/zones.yaml")


@lru_cache(maxsize=1)
def _chowkris() -> list[tuple[str, BaseGeometry]]:
    cfg = yaml.safe_load(CONFIG.read_text())
    path = Path(cfg["boundaries"]["chowkris"])
    if not path.exists():
        return []
    to_utm = Transformer.from_crs("EPSG:4326", cfg["crs"], always_xy=True).transform
    out = []
    for f in json.loads(path.read_text())["features"]:
        out.append((f["properties"]["name"], sh_transform(to_utm, shape(f["geometry"]))))
    return out


def chowkri_of(x: float, y: float) -> str | None:
    p = Point(x, y)
    for name, geom in _chowkris():
        if geom.contains(p):
            return name
    return None
