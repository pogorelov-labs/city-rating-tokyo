"""WorldPop constrained 2020 district counts (CRTKY-197).

Counts, not density: sum pixel centers; masked BSGM-unsettled cells contribute
zero. The official district area remains the density denominator. This module
never uses angular pixel size as square metres or extrapolates masked cells.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, Window
from rasterio.warp import transform_geom
from shapely.geometry import MultiPolygon, Polygon, mapping, shape, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'data/bangkok/population-source.json'


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_download(path: Path, source: dict) -> None:
    if path.stat().st_size != source['bytes'] or sha256(path) != source['sha256']:
        raise ValueError(f'WorldPop checksum/size mismatch: {path}; re-fetch the pinned source')


def district_geometries(geometry: dict, expected_slugs: set[str]) -> dict:
    if set(geometry) != expected_slugs or len(expected_slugs) != 50:
        raise ValueError('WorldPop requires an exact join to all 50 district slugs')
    result = {}
    for slug, entry in geometry.items():
        polygons = []
        for rings in entry['polygons']:
            lonlat = [[(lon, lat) for lat, lon in ring] for ring in rings]
            polygons.append(Polygon(lonlat[0], lonlat[1:]))
        geom = MultiPolygon(polygons)
        if geom.is_empty or not geom.is_valid:
            raise ValueError(f'Invalid district boundary: {slug}')
        result[slug] = geom
    return result


def validate_raster(src, source: dict) -> None:
    spec = source['raster']
    if (src.crs is None or src.crs.to_epsg() != 4326 or src.count != 1
            or list(src.shape) != spec['shape'] or src.dtypes != ('float32',)
            or src.nodata != -99999):
        raise ValueError('Unexpected WorldPop CRS/shape/bands/dtype/nodata')
    expected = spec['transform']
    if not np.allclose(list(src.transform)[:6], expected, rtol=0, atol=1e-12):
        raise ValueError('Unexpected WorldPop grid transform')
    if source['units'] != 'people_per_pixel' or source['nodata_semantics'] != 'BSGM_unsettled':
        raise ValueError('WorldPop count/nodata semantics must be explicit')


def aggregate(path: Path, geometries: dict, source: dict) -> tuple[dict, dict]:
    """Validate the grid, reject double assigned cells, reconcile district/union sums."""
    verify_download(path, source)
    with rasterio.open(path) as src:
        validate_raster(src, source)
        union = unary_union(list(geometries.values()))
        west, south, east, north = union.bounds
        b = src.bounds
        if not (b.left <= west < east <= b.right and b.bottom <= south < north <= b.top):
            raise ValueError('District extent outside raster coverage')
        win = from_bounds(west, south, east, north, src.transform)
        col, row = math.floor(win.col_off), math.floor(win.row_off)
        win = Window(col, row, math.ceil(win.col_off + win.width) - col,
                     math.ceil(win.row_off + win.height) - row)
        values = src.read(1, window=win, masked=True)
        valid = values.compressed()
        if not np.isfinite(valid).all() or (valid < 0).any():
            raise ValueError('Invalid population counts (negative/non-finite)')
        transform = src.window_transform(win)
        occupied = np.zeros(values.shape, dtype=bool)
        rows = {}
        for slug, geom in sorted(geometries.items()):
            mask = geometry_mask([mapping(geom)], values.shape, transform, invert=True,
                                 all_touched=False)
            if not mask.any():
                raise ValueError(f'No pixel centers in district: {slug}')
            if (occupied & mask).any():
                raise ValueError(f'Overlapping district pixel assignment: {slug}')
            occupied |= mask
            cells = values[mask]
            population = float(cells.sum(dtype=np.float64))
            if not math.isfinite(population) or population <= 0:
                raise ValueError(f'No populated cells in district: {slug}')
            projected = shape(transform_geom('EPSG:4326', 'EPSG:32647', mapping(geom)))
            rows[slug] = {'population': population, 'polygon_area_km2': projected.area / 1e6,
                          'pixels': int(mask.sum()),
                          'settled_pixels': int(cells.count())}
        union_mask = geometry_mask([mapping(union)], values.shape, transform, invert=True,
                                   all_touched=False)
        if not np.array_equal(occupied, union_mask):
            raise ValueError('District coverage does not reconcile to union')
        total = float(values[union_mask].sum(dtype=np.float64))
        if not math.isclose(total, sum(r['population'] for r in rows.values()), rel_tol=0, abs_tol=1e-6):
            raise ValueError('District population sums do not reconcile')
        # Physical area is an audit only: WGS84 angular cells are not 100×100 m.
        # Bangkok lies in UTM zone 47N; project cell corners at the window edges.
        dx, dy = src.res
        pixel_areas = [shape(transform_geom('EPSG:4326', 'EPSG:32647',
                       mapping(box(x, y, x + dx, y + dy)))).area
                       for x in (west, east - dx) for y in (south, north - dy)]
        return rows, {'population': total, 'pixels': int(occupied.sum()),
                      'pixel_area_m2_utm47n_range': [min(pixel_areas), max(pixel_areas)],
                      'settled_pixels': sum(r['settled_pixels'] for r in rows.values()),
                      'boundary_method': 'published OSM polygons; pixel center; holes excluded',
                      'pixel_area': 'angular 3 arc-second grid; varies with latitude; not used for counts'}


def crowd_raw(density: float, poi_log_term: float) -> float:
    if not math.isfinite(density) or density <= 0 or not math.isfinite(poi_log_term) or poi_log_term < 0:
        raise ValueError('Invalid crowd density or POI term')
    return 0.5 * math.log(max(density, 1)) + poi_log_term


def load_population(geometry: dict, slugs: set[str]) -> tuple[dict, dict]:
    source = json.loads(MANIFEST.read_text())
    path = ROOT / 'data/bangkok/raw' / source['filename']
    if not path.exists():
        raise FileNotFoundError('Missing pinned WorldPop raster; run uv run scripts/bangkok/fetch-population.py')
    return aggregate(path,
                     district_geometries(geometry, slugs), source)


def population_metadata() -> dict:
    source = json.loads(MANIFEST.read_text())
    return {'source': 'worldpop_2020', 'epoch': 2020, 'sha256': source['sha256'],
            'method': 'pixel_center_sum / official_area_km2'}
