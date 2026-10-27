"""Bangkok projection, boundary assembly and simplification."""
from __future__ import annotations
import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union
from bangkok.bkk_config import KX, KY, LAT0, LON0, SIMPLIFY_M

def xy(lon: float, lat: float) -> tuple[float, float]:
    return ((lon - LON0) * KX, (lat - LAT0) * KY)

def xy_arr(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return ((lon - LON0) * KX, (lat - LAT0) * KY)

def lonlat(x: float, y: float) -> tuple[float, float]:
    return (x / KX + LON0, y / KY + LAT0)

def latlng_pair(x: float, y: float) -> list[float]:
    lon, lat = lonlat(x, y)
    return [round(lat, 5), round(lon, 5)]

def ring_lines(members: list[dict], roles: tuple[str, ...]):
    for m in members:
        if m.get("type") != "way" or m.get("role", "") not in roles or "geometry" not in m:
            continue
        pts = [xy(p["lon"], p["lat"]) for p in m["geometry"]]
        if len(pts) >= 2:
            yield LineString(pts)

def assemble_multipolygon(members: list[dict]) -> MultiPolygon | None:
    outer = list(polygonize(unary_union(list(ring_lines(members, ("outer", ""))))))
    if not outer:
        return None
    geom = unary_union(outer)
    inner_lines = list(ring_lines(members, ("inner",)))
    if inner_lines:
        inner = list(polygonize(unary_union(inner_lines)))
        if inner:
            geom = geom.difference(unary_union(inner))
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    return geom if geom.geom_type == "MultiPolygon" and not geom.is_empty else None

def simplify_coverage(
    geoms: list[MultiPolygon], tolerance: float = SIMPLIFY_M, min_part_m2: float = 20_000
) -> list[MultiPolygon]:
    """Simplify shared borders once so neighbouring polygons stay gap-free."""
    arr = np.array(geoms, dtype=object)
    try:
        if not shapely.coverage_is_valid(arr):
            raise ValueError("coverage not edge-matched")
        simp = shapely.coverage_simplify(arr, tolerance, simplify_boundary=True)
    except Exception as err:  # fall back to per-polygon simplification
        print(f"  coverage_simplify unavailable ({err}); simplifying polygons independently")
        simp = [g.simplify(tolerance, preserve_topology=True) for g in geoms]
    out = []
    for g in simp:
        if g.geom_type == "Polygon":
            g = MultiPolygon([g])
        polys = [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon" and not p.is_empty]
        parts = [p for p in polys if p.area > min_part_m2] or [max(polys, key=lambda p: p.area)]
        out.append(MultiPolygon(parts))
    return out

def polygon_to_latlng(poly: Polygon) -> list[list[list[float]]]:
    rings = [poly.exterior, *poly.interiors]
    return [[latlng_pair(x, y) for x, y in ring.coords] for ring in rings]
