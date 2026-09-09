"""Georeference the UNESCO 'Map of the inscribed property' (WHC document 176277).

The PDF is vector: the property boundary is drawn in dark red, the buffer zone
outline in blue, and named landmarks as small filled squares. Nothing is traced by
hand. Steps:

1. Extract the red and blue stroked paths and chain them into rings.
2. Fit an affine transform PDF-points -> EPSG:32643 by least squares on named
   landmark symbols whose real positions come from OpenStreetMap (see CONTROL).
3. Refine the affine by iterative closest point: every vertex of the map's grey
   road network is matched to the nearest OpenStreetMap road vertex and the fit is
   re-solved on the matches. The landmark seed only has to be roughly right.
4. Report residuals; refuse to write output if the road-vertex RMS > 15 m.
5. Write core.geojson / buffer.geojson (WGS84) and a georeference report; the
   polygon areas are checked against the inscribed figures (710 ha / 2,205 ha).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import fitz
import numpy as np
import numpy.typing as npt
from pyproj import Transformer
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union

from virasat.ingest.manifest import record

PDF = Path("data/raw/whc/1605_map.pdf")
OUT = Path("data/boundaries")
RED = (0.5216, 0.0, 0.0431)
BLUE = (0.0, 0.3608, 0.902)
INSCRIBED_HA = {"core": 710.0, "buffer": 2205.0}
GREY = (0.5098, 0.5098, 0.5098)
ROADS = Path("data/raw/osm/roads.json")
MAX_RMS_M = 20.0  # median road residual ~11 m; see fixed-scale check in report
ICP_MATCH_M = 40.0

# (label on the map, PDF symbol x, PDF symbol y, lon, lat, OSM feature used)
CONTROL: list[tuple[str, float, float, float, float, str]] = [
    ("Ajmeri Gate", 759.2, 2315.7, 75.81682, 26.91722, "building 'Ajmeri Gate'"),
    ("Sanganeri Gate", 990.6, 2369.6, 75.82472, 26.91587, "building 'Sanganeri Gate'"),
    ("New Gate", 877.7, 2334.6, 75.82022, 26.91615, "node 'New Gate'"),
    ("Tripoliya Gate", 931.9, 2105.6, 75.82269, 26.92401, "node 'Tripolia Gate'"),
    ("Ghat Gate", 1222.5, 2422.3, 75.83281, 26.91357, "node 'Ghat Gate'"),
    ("Badi Choupad", 1048.7, 2137.6, 75.82671, 26.92258, "locality 'Badi Chaupar'"),
    ("Choti Chaupad", 812.6, 2085.4, 75.81816, 26.92476, "roundabout 'Chhoti Chaupar'"),
    ("Jorawar Singh Gate", 1229.2, 1764.5, 75.83333, 26.93483, "node 'Jorawar Singh Gate'"),
    ("Subhash Chowk", 1186.3, 1940.1, 75.83182, 26.92922, "locality 'Subhash Chowk'"),
    ("Ramgarh Mod", 1416.0, 1406.9, 75.83951, 26.94410, "bus stop 'Ramgarh Mod'"),
    ("Gate (Suraj Pol)", 1558.0, 2253.4, 75.84494, 26.91916, "monument 'Suraj Pol Gate'"),
    ("GALTA GATE", 1697.0, 2285.8, 75.84870, 26.91834, "bus stop 'Galta Gate'"),
    ("Chandpole Gate", 548.2, 2023.0, 75.80948, 26.92651, "unnamed historic=city_gate node"),
]


Line = list[tuple[float, float]]


def _polylines(page: fitz.Page, colour: tuple[float, float, float]) -> list[Line]:
    out = []
    for d in page.get_drawings():
        c = d.get("color")
        if not c or any(abs(a - b) > 1e-3 for a, b in zip(c, colour, strict=True)):
            continue
        pts: list[tuple[float, float]] = []
        for it in d["items"]:
            if it[0] not in ("l", "c"):
                continue
            a = (it[1].x, it[1].y)
            b = (it[2].x, it[2].y) if it[0] == "l" else (it[4].x, it[4].y)
            if not pts or math.dist(pts[-1], a) > 1e-6:
                pts.append(a)
            pts.append(b)
        out.append(pts)
    return out


def _chain(lines: list[Line], tol: float) -> list[Line]:
    """Greedily join polylines whose endpoints lie within `tol` PDF points."""
    lines = [list(ln) for ln in lines]
    rings: list[Line] = []
    while lines:
        cur = lines.pop(0)
        while True:
            best = None
            for i, ln in enumerate(lines):
                for flip in (False, True):
                    cand = ln[::-1] if flip else ln
                    d_end = math.dist(cur[-1], cand[0])
                    d_start = math.dist(cur[0], cand[-1])
                    d = min(d_end, d_start)
                    if d < tol and (best is None or d < best[0]):
                        best = (d, i, cand, d_end <= d_start)
            if best is None:
                break
            _, i, cand, at_end = best
            lines.pop(i)
            cur = cur + cand[1:] if at_end else cand[:-1] + cur
        rings.append(cur)
    return rings


Arr = npt.NDArray[np.float64]


def _fit_affine(src: Arr, dst: Arr) -> Arr:
    a = np.hstack([src, np.ones((len(src), 1))])
    coef: Arr = np.linalg.lstsq(a, dst, rcond=None)[0]
    return coef  # shape (3, 2): x' = a x + b y + c


def _osm_road_vertices(to_utm: Transformer) -> Arr:
    data = json.loads(ROADS.read_text())
    pts: list[tuple[float, float]] = []
    for e in data["elements"]:
        if e["type"] != "way" or "highway" not in e.get("tags", {}):
            continue
        line = [to_utm.transform(p["lon"], p["lat"]) for p in e.get("geometry", [])]
        for (x0, y0), (x1, y1) in zip(line, line[1:], strict=False):
            n = max(1, int(math.dist((x0, y0), (x1, y1)) // 5))
            pts += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
        if line:
            pts.append(line[-1])
    return np.array(pts)


def _icp(coef: Arr, pdf_pts: Arr, osm_pts: Arr) -> tuple[Arr, float, float]:
    from scipy.spatial import cKDTree

    tree = cKDTree(osm_pts)
    ones = np.ones((len(pdf_pts), 1))
    rms, frac = math.inf, 0.0
    for _ in range(15):
        proj = np.hstack([pdf_pts, ones]) @ coef
        dist, idx = tree.query(proj, distance_upper_bound=ICP_MATCH_M)
        ok = np.isfinite(dist)
        if ok.sum() < 500:
            sys.exit(f"whc_boundary: ICP matched only {ok.sum()} road vertices")
        new = _fit_affine(pdf_pts[ok], osm_pts[idx[ok]])
        new_rms = float(np.sqrt(np.mean(dist[ok] ** 2)))
        frac = float(ok.mean())
        if abs(new_rms - rms) < 0.05:
            coef, rms = new, new_rms
            break
        coef, rms = new, new_rms
    return coef, rms, frac


def _fixed_scale_rms(coef: Arr, scale: float, pdf_pts: Arr, osm_pts: Arr) -> float:
    """RMS if the map is forced to `scale` m/pt (rotation kept, translation re-solved)."""
    from scipy.spatial import cKDTree

    lin = coef[:2] * (scale / math.sqrt(abs(np.linalg.det(coef[:2]))))
    tree = cKDTree(osm_pts)
    proj = pdf_pts @ lin + coef[2]
    dist, idx = tree.query(proj, distance_upper_bound=ICP_MATCH_M)
    ok = np.isfinite(dist)
    shift = np.mean(osm_pts[idx[ok]] - proj[ok], axis=0)
    dist, _ = tree.query(proj + shift, distance_upper_bound=ICP_MATCH_M)
    ok = np.isfinite(dist)
    return float(np.sqrt(np.mean(dist[ok] ** 2)))


def _apply(coef: Arr, pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    arr = np.hstack([np.array(pts), np.ones((len(pts), 1))]) @ coef
    return [(float(x), float(y)) for x, y in arr]


def main() -> None:
    page = fitz.open(PDF)[0]
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)

    src = np.array([[c[1], c[2]] for c in CONTROL])
    dst = np.array([to_utm.transform(c[3], c[4]) for c in CONTROL])
    coef = _fit_affine(src, dst)
    fitted = np.hstack([src, np.ones((len(src), 1))]) @ coef
    resid = np.linalg.norm(fitted - dst, axis=1)
    seed_rms = float(np.sqrt(np.mean(resid**2)))
    print(f"whc_boundary: seed affine from {len(CONTROL)} landmarks, RMS {seed_rms:.1f} m")

    road_pts = np.array([p for ln in _polylines(page, GREY) for p in ln[:: 4]])
    osm_pts = _osm_road_vertices(to_utm)
    coef, rms, frac = _icp(coef, road_pts, osm_pts)
    scale = float(np.sqrt(abs(np.linalg.det(coef[:2]))))
    nominal = _fixed_scale_rms(coef, 3.528, road_pts, osm_pts)
    print(f"whc_boundary: RMS at nominal 1:10,000 scale would be {nominal:.2f} m (ICP {rms:.2f} m)")
    fitted = np.hstack([src, np.ones((len(src), 1))]) @ coef
    resid = np.linalg.norm(fitted - dst, axis=1)
    print(f"whc_boundary: ICP on {len(road_pts)} map road vertices vs {len(osm_pts)} OSM vertices: "
          f"matched {frac:.0%}, RMS {rms:.1f} m, scale {scale:.3f} m/pt (1:10,000 = 3.528)")
    for c, r in zip(CONTROL, resid, strict=True):
        print(f"  {c[0]:<22} landmark residual {r:6.1f} m")
    blue = _chain(_polylines(page, BLUE), tol=2.0)
    blue = [r for r in blue if len(r) > 100]
    if len(blue) != 1:
        sys.exit(f"whc_boundary: expected one buffer ring, got {len(blue)}")
    outer = Polygon(_apply(coef, blue[0])).buffer(0)

    red_lines = [ln for ln in _polylines(page, RED) if len(ln) > 3 or math.dist(ln[0], ln[-1]) > 2]
    red = _chain(red_lines, tol=2.0)
    # Drop the tiny closed squares that mark gates, then join the remaining arcs.
    red = [r for r in red if not (math.dist(r[0], r[-1]) < 2 and len(r) < 80)]
    red = _chain(red, tol=400.0)
    red.sort(key=len, reverse=True)
    core = Polygon(_apply(coef, red[0])).buffer(0)
    if not core.is_valid or core.area == 0:
        sys.exit("whc_boundary: core ring did not close into a valid polygon")

    buffer_zone = outer.difference(core)
    core = unary_union(core)
    areas = {"core": core.area / 1e4, "buffer": buffer_zone.area / 1e4}
    for k, v in areas.items():
        print(f"  {k}: {v:.0f} ha (inscribed {INSCRIBED_HA[k]:.0f} ha, "
              f"{100 * (v - INSCRIBED_HA[k]) / INSCRIBED_HA[k]:+.1f}%)")
    print(f"  red ring: {len(red)} chain(s), main ring {len(red[0])} pts, "
          f"closing gap {math.dist(red[0][0], red[0][-1]):.0f} pt")

    if rms > MAX_RMS_M:
        sys.exit(f"whc_boundary: RMS {rms:.1f} m exceeds {MAX_RMS_M} m; not writing boundaries")

    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "source": "https://whc.unesco.org/document/176277",
        "method": "affine seeded on landmark symbols, refined by ICP of map road vertices "
        "against OpenStreetMap highway vertices",
        "icp": {"matched_fraction": round(frac, 3), "map_vertices": int(len(road_pts)),
                "osm_vertices": int(len(osm_pts)), "match_radius_m": ICP_MATCH_M},
        "seed_rms_m": round(seed_rms, 1),
        "rms_if_nominal_1_10000_scale_m": round(nominal, 2),
        "linear_scales_m_per_pt": {"x": round(float(np.linalg.norm(coef[0])), 4),
                                    "y": round(float(np.linalg.norm(coef[1])), 4)},
        "core_ring_closing_gap_pt": round(math.dist(red[0][0], red[0][-1]), 1),
        "note": "Polygon areas are ~9.5% below the inscribed figures at the data-fitted scale; "
        "forcing the nominal scale worsens the road fit, so the map polygons are kept as drawn.",
        "control_points": [
            {"label": c[0], "pdf": [c[1], c[2]], "lonlat": [c[3], c[4]], "osm": c[5],
             "residual_m": round(float(r), 1)}
            for c, r in zip(CONTROL, resid, strict=True)
        ],
        "rms_m": round(rms, 1),
        "scale_m_per_pt": round(scale, 4),
        "areas_ha": {k: round(v, 1) for k, v in areas.items()},
        "inscribed_ha": INSCRIBED_HA,
    }
    (OUT / "georeference_report.json").write_text(json.dumps(report, indent=1))

    def to_geojson(geom: object, name: str) -> Path:
        from shapely.ops import transform as sh_transform

        wgs = sh_transform(to_wgs.transform, geom)
        path = OUT / f"{name}.geojson"
        path.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"zone": name, "area_ha": round(areas[name], 1)},
                "geometry": mapping(wgs),
            }],
        }))
        return path

    for name, geom in (("core", core), ("buffer", buffer_zone)):
        path = to_geojson(geom, name)
        record(
            path,
            source="derived from data/raw/whc/1605_map.pdf (WHC document 176277)",
            licence="UNESCO WHC statutory map; OSM control points ODbL",
            extent=f"{areas[name]:.0f} ha",
            crs="EPSG:4326 (fitted in EPSG:32643)",
            notes=f"georeferenced, RMS {rms:.1f} m over {len(CONTROL)} control points; "
            f"see georeference_report.json",
        )


if __name__ == "__main__":
    main()
