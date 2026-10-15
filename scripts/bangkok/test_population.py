"""Offline fixtures exercise actual GeoTIFF masking, validation and fetch atomicity."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box, Polygon

sys.path.insert(0, str(Path(__file__).parent))
from population import aggregate, crowd_raw, district_geometries, sha256


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fetcher = module('fetch_population', 'fetch-population.py')
rebuild = module('rebuild_population', 'rebuild-population.py')


@pytest.fixture
def raster(tmp_path):
    path = tmp_path / 'population.tif'
    values = np.array([[1, 2, 3, 4], [5, -99999, 7, 8], [9, 10, 11, 12]], dtype='float32')
    transform = from_origin(100, 14, 0.001, 0.001)
    with rasterio.open(path, 'w', driver='GTiff', width=4, height=3, count=1,
                       dtype='float32', crs='EPSG:4326', nodata=-99999, transform=transform) as dst:
        dst.write(values, 1)
    source = {'filename': path.name, 'bytes': path.stat().st_size, 'sha256': sha256(path),
              'units': 'people_per_pixel', 'nodata_semantics': 'BSGM_unsettled',
              'raster': {'shape': [3, 4], 'transform': list(transform)[:6]}}
    return path, source


def test_counts_not_density_center_mask_nodata_and_union(raster):
    path, source = raster
    # Non-square-metre angular cells; sums must not multiply by pixel area.
    geoms = {'left': box(100, 13.997, 100.002, 14), 'right': box(100.002, 13.997, 100.004, 14)}
    rows, summary = aggregate(path, geoms, source)
    assert rows['left']['population'] == 27
    assert rows['left']['pixels'] == 6 and rows['left']['settled_pixels'] == 5
    assert 0.06 < rows['left']['polygon_area_km2'] < 0.08
    assert rows['right']['population'] == 45
    assert summary['population'] == 72
    assert summary['pixels'] == 12 and summary['settled_pixels'] == 11


def test_holes_and_boundary_centers(raster):
    path, source = raster
    outer = box(100, 13.997, 100.004, 14)
    hole = box(100, 13.999, 100.001, 14)
    geom = Polygon(outer.exterior.coords, [hole.exterior.coords])
    rows, _ = aggregate(path, {'holed': geom}, source)
    assert rows['holed']['population'] == 71
    # A polygon touching two columns includes only centers inside it.
    rows, _ = aggregate(path, {'narrow': box(100.0004, 13.997, 100.0014, 14)}, source)
    assert rows['narrow']['population'] == 15


def test_overlap_and_outside_fail(raster):
    path, source = raster
    with pytest.raises(ValueError, match='Overlapping'):
        aggregate(path, {'a': box(100, 13.997, 100.003, 14), 'b': box(100.002, 13.997, 100.004, 14)}, source)
    with pytest.raises(ValueError, match='outside'):
        aggregate(path, {'a': box(99, 13.997, 100.004, 14)}, source)


@pytest.mark.parametrize('mutation', ['checksum', 'shape', 'transform', 'units', 'nodata', 'crs', 'negative', 'nan'])
def test_invalid_source_fails_closed(raster, mutation):
    path, source = raster
    if mutation == 'checksum':
        source['sha256'] = '0' * 64
    elif mutation in ('shape', 'transform'):
        source['raster'][mutation][0] += 1
    elif mutation == 'units':
        source['units'] = 'people_per_square_km'
    else:
        with rasterio.open(path, 'r+') as dst:
            if mutation == 'nodata':
                dst.nodata = -1
            elif mutation == 'crs':
                dst.crs = 'EPSG:3857'
            else:
                values = dst.read(1)
                values[0, 0] = -1 if mutation == 'negative' else np.nan
                dst.write(values, 1)
        source.update(bytes=path.stat().st_size, sha256=sha256(path))
    with pytest.raises(ValueError):
        aggregate(path, {'a': box(100, 13.997, 100.004, 14)}, source)


def test_missing_join_and_invalid_geometry():
    with pytest.raises(ValueError, match='50 district'):
        district_geometries({}, {'a'})
    slugs = {str(i) for i in range(50)}
    entry = {'polygons': [[[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]]}
    with pytest.raises(ValueError, match='Invalid district'):
        district_geometries(dict.fromkeys(slugs, entry), slugs)


def test_fetch_cached_verification_and_atomic_failure(raster, tmp_path, monkeypatch):
    path, source = raster
    assert fetcher.fetch(path.parent, source) == path
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_content(self, size): yield b'not a raster'
    monkeypatch.setattr(fetcher.requests, 'get', lambda *a, **k: Response())
    source['url'] = 'https://example.invalid/population'
    out = tmp_path / 'download'
    with pytest.raises(ValueError, match='checksum'):
        fetcher.fetch(out, source)
    assert list(out.iterdir()) == []
    original = path.read_bytes()
    with pytest.raises(ValueError, match='checksum'):
        fetcher.fetch(path.parent, source, refresh=True)
    assert path.read_bytes() == original
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        fetcher.fetch(path.parent, source)


def test_replay_original_ratings_and_rounding_guard():
    root = Path(__file__).resolve().parents[2]
    baseline = json.loads((root / 'data/bangkok/population-baseline.json').read_text())['districts']
    pop = {s: {'population': b['registered_density_input'] * b['official_area_km2']} for s, b in baseline.items()}
    rows = rebuild.compare(baseline, pop)
    assert all(r['rating_delta'] == 0 for r in rows.values())
    baseline['watthana']['crowd_rating'] = 10
    with pytest.raises(ValueError, match='original ratings'):
        rebuild.compare(baseline, pop)


@pytest.mark.parametrize('density,poi', [(0, 1), (float('nan'), 1), (5, -1)])
def test_invalid_crowd_input(density, poi):
    with pytest.raises(ValueError): crowd_raw(density, poi)




def test_fetch_success_and_network_failure_are_atomic(raster, tmp_path, monkeypatch):
    path, source = raster
    source['url'] = 'https://example.invalid/population'
    payload = path.read_bytes()
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_content(self, size):
            yield payload[:10]
            yield payload[10:]
    monkeypatch.setattr(fetcher.requests, 'get', lambda *a, **k: Response())
    out = tmp_path / 'success'
    assert fetcher.fetch(out, source).read_bytes() == payload
    class Interrupted(Response):
        def iter_content(self, size):
            yield payload[:10]
            raise ConnectionError('fixture network interrupted')
    monkeypatch.setattr(fetcher.requests, 'get', lambda *a, **k: Interrupted())
    out = tmp_path / 'interrupted'
    with pytest.raises(ConnectionError):
        fetcher.fetch(out, source)
    assert list(out.iterdir()) == []
