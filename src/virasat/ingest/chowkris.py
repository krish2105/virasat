"""Derive the nine chowkri polygons by cutting the core with the main bazaar streets.

Jaipur's chowkris are the blocks of the 1727 grid, bounded by the bazaar streets.
No open dataset carries their polygons, so they are derived: each bazaar is a
straight street, so a PCA line is fitted through its OpenStreetMap vertices,
clipped to the core polygon and to the half of the city it belongs to, and the
core is polygonised along those lines. Names are assigned from the published
description of the grid (west -> east):
  north of the axis: Purani Basti | Sarhad | Ramchandraji | Gangapole
  south of the axis: Topkhana Hazuri | Modikhana | Vishveshwarji | Topkhana Desh | Ghat Darwaza
The name mapping is an assumption to be verified by the JNN Heritage Cell; the
geometry is reproducible from the manifested inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import linemerge, polygonize, split, unary_union
from shapely.ops import transform as sh_transform

from virasat.ingest.manifest import record

ROADS = Path("data/raw/osm/roads.json")
CORE = Path("data/boundaries/core.geojson")
OUT = Path("data/boundaries/chowkris.geojson")
AXIS = ["Chandpol Bazaar", "Tripolia Bazaar", "Ramganj Bazaar"]
SOUTH_CUTS = ["Kishanpole Bazar Road", "Chaura Rasta", "Johari Bazar", "Ghat Darwaja Bazaar Road"]
# North of the axis the grid is: Gangauri Bazaar (N-S), then Amer Road / Sireh Deori
# Bazar as drawn (it bends), then Moti Katla Bazaar (E-W) east of Amer Road separating
# Ramchandraji from Gangapole.
NORTH_PCA = ["Gangauri Bazaar"]
NORTH_RAW = ["Amer Road"]
NORTH_EW = ["Moti Katla Bazaar"]
NORTH = ["Purani Basti", "Sarhad", "Ramchandraji", "Gangapole"]
SOUTH = ["Topkhana Hazuri", "Modikhana", "Vishveshwarji", "Topkhana Desh", "Ghat Darwaza"]
MIN_HA = 5.0


def _streets(to_utm: Transformer) -> dict[str, list[LineString]]:
    out: dict[str, list[LineString]] = {}
    for e in json.loads(ROADS.read_text())["elements"]:
        tags = e.get("tags", {})
        if e["type"] == "way" and "highway" in tags and tags.get("name"):
            line = LineString([to_utm.transform(p["lon"], p["lat"]) for p in e["geometry"]])
            out.setdefault(tags["name"], []).append(line)
    return out


def _pca_line(
    streets: dict[str, list[LineString]], names: list[str], within: BaseGeometry
) -> LineString:
    pts = np.array(
        [c for n in names for ln in streets[n] for c in ln.coords if within.contains(Point(c))]
    )
    mean = pts.mean(axis=0)
    direction = np.linalg.svd(pts - mean)[2][0]
    return LineString([mean - direction * 6000, mean + direction * 6000])


def _lines(geom: BaseGeometry) -> BaseGeometry:
    """Keep only the linear parts of an intersection result (polygonize rejects points)."""
    parts = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type == "LineString"]
    return unary_union(parts) if parts else LineString()


def _extend(geom: BaseGeometry, by: float = 200.0) -> BaseGeometry:
    """Extend both ends of each line by `by` metres so it reaches the cutting boundary."""
    out = []
    for ln in getattr(geom, "geoms", [geom]):
        c = list(ln.coords)
        (x0, y0), (x1, y1) = c[0], c[1]
        d = np.hypot(x1 - x0, y1 - y0)
        head = (x0 + (x0 - x1) / d * by, y0 + (y0 - y1) / d * by)
        (x0, y0), (x1, y1) = c[-2], c[-1]
        d = np.hypot(x1 - x0, y1 - y0)
        tail = (x1 + (x1 - x0) / d * by, y1 + (y1 - y0) / d * by)
        out.append(LineString([head, *c, tail]))
    return unary_union(out)


def _merge_slivers(faces: list[Polygon]) -> list[Polygon]:
    faces = sorted(faces, key=lambda f: f.area, reverse=True)
    keep = [f for f in faces if f.area / 1e4 >= MIN_HA]
    for sliver in (f for f in faces if f.area / 1e4 < MIN_HA):
        i = max(
            range(len(keep)), key=lambda k: keep[k].boundary.intersection(sliver.boundary).length
        )
        keep[i] = unary_union([keep[i], sliver])
    return keep


def main() -> None:
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
    core = sh_transform(
        to_utm.transform, shape(json.loads(CORE.read_text())["features"][0]["geometry"])
    )
    streets = _streets(to_utm)

    axis = _pca_line(streets, AXIS, core)
    halves = sorted(
        polygonize(unary_union([core.buffer(2000).envelope.boundary, axis])),
        key=lambda h: h.centroid.y,
    )
    south, north = core.intersection(halves[0]), core.intersection(halves[1])
    cuts = [axis.intersection(core)]
    cuts += [_pca_line(streets, [n], south).intersection(south) for n in SOUTH_CUTS]
    cuts += [_pca_line(streets, [n], north).intersection(north) for n in NORTH_PCA]
    amer = _lines(_extend(linemerge(unary_union(streets[NORTH_RAW[0]]))).intersection(north))
    cuts.append(amer)
    ew = _lines(_pca_line(streets, NORTH_EW, north).intersection(north))
    east_of_amer = [g for g in split(ew, amer).geoms if g.centroid.x > amer.centroid.x]
    cuts += east_of_amer
    cuts = [_lines(c) for c in cuts]
    faces = [
        f
        for f in polygonize(unary_union([core.boundary, *cuts]))
        if f.representative_point().within(core)
    ]
    faces = _merge_slivers(faces)

    north_faces = sorted(
        (f for f in faces if f.centroid.y > axis.interpolate(0.5, True).y),
        key=lambda f: f.centroid.x,
    )
    south_faces = sorted(
        (f for f in faces if f.centroid.y <= axis.interpolate(0.5, True).y),
        key=lambda f: f.centroid.x,
    )
    if len(north_faces) != len(NORTH) or len(south_faces) != len(SOUTH):
        raise SystemExit(f"chowkris: got {len(north_faces)} north / {len(south_faces)} south faces")

    features = []
    for name, geom in [
        *zip(NORTH, north_faces, strict=True),
        *zip(SOUTH, south_faces, strict=True),
    ]:
        wgs = sh_transform(to_wgs.transform, geom)
        features.append(
            {
                "type": "Feature",
                "properties": {"name": name, "area_ha": round(geom.area / 1e4, 1)},
                "geometry": mapping(wgs),
            }
        )
        print(f"chowkris: {name:<16} {geom.area / 1e4:6.1f} ha")
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    record(
        OUT,
        source="derived: data/boundaries/core.geojson cut by PCA lines through OSM bazaar streets",
        licence="derived (UNESCO map + OSM ODbL)",
        extent=f"{len(features)} chowkris",
        crs="EPSG:4326",
        notes="name assignment per published grid description; verify with JNN Heritage Cell",
    )


if __name__ == "__main__":
    main()
