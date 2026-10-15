"""Offline joins, QA lineage, publication boundary and generated/app byte parity."""
import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('institutions', ROOT / 'scripts/institutions/compute-institutions.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def square(south=0, west=0, north=1, east=1):
    return [[south, west], [south, east], [north, east], [north, west], [south, west]]


def feature(name='Embassy', lat=0, lon=0, country='A'):
    return {'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
            'properties': {'name': name, 'country': country}}


def test_radius_inclusive_and_outside():
    latitude = math.degrees(800 / 6371000)
    assert m.count_nearby([(latitude, 0), (latitude * 1.00001, 0)], 0, 0, 800) == 1
    assert m.count_nearby([(math.degrees(2000 / 6371000), 0)], 0, 0, 2000) == 1


def test_district_holes_multipolygons_and_shared_edge_once():
    geometry = {'z': {'polygons': [[square(0, 1, 1, 2)]]},
                'a': {'polygons': [[square(), square(.2, .2, .4, .4)], [square(2, 2, 3, 3)]]}}
    counts, audit = m.district_counts([(.5, 1), (.3, .3), (2.5, 2.5), (.5, 1.5)], geometry, {'z', 'a'})
    assert counts == {'a': 2, 'z': 1}  # shared edge -> a; hole -> outside
    assert audit == {'outside': 1, 'boundary_assigned': 1, 'total_assigned': 3}
    assert m.district_counts([(.5, 1)], dict(reversed(list(geometry.items()))), {'a', 'z'})[0] == {'a': 1, 'z': 0}


def test_overlapping_interiors_rejected():
    with pytest.raises(ValueError, match='overlapping'):
        m.district_counts([(.5, .5)], {s: {'polygons': [[square()]]} for s in ('a', 'b')}, {'a', 'b'})


def test_missing_geometry_or_duplicate_anchor_rejected():
    with pytest.raises(ValueError, match='join mismatch'):
        m.district_counts([], {}, {'missing'})
    with pytest.raises(ValueError, match='Duplicate join key'):
        m.unique_rows([{'id': 'a'}, {'id': 'a'}], 'id')


def test_invalid_geometry_rejected():
    with pytest.raises(ValueError, match='Invalid district geometry'):
        m.district_counts([], {'a': {'polygons': [[[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]]}}, {'a'})


@pytest.mark.parametrize('lat,lon', [(float('nan'), 0), (91, 0), (0, 181), (True, 0)])
def test_bad_coordinates_rejected(lat, lon):
    with pytest.raises(ValueError, match='coordinate'):
        m.embassy_points([feature(lat=lat, lon=lon)])


def test_absent_coordinates_noise_and_duplicates_rejected():
    f = feature()
    with pytest.raises(ValueError, match='Duplicate embassy'):
        m.embassy_points([f, copy.deepcopy(f)])
    f['geometry'] = None
    with pytest.raises(ValueError, match='Point coordinates'):
        m.embassy_points([f])
    with pytest.raises(ValueError, match='QA'):
        m.embassy_points([feature('Consulat de Syldavie')])


def test_qa_actual_corrections_and_exclusions_retained():
    summary = m.read(ROOT, m.SNAP / 'embassies/summary.json')
    for city, expected, corrected in [('bangkok', 79, 'Ireland'), ('tokyo', 167, 'Armenia')]:
        rows = m.read(ROOT, m.SNAP / f'embassies/embassies-{city}.geojson')['features']
        qa = summary['cities'][city]
        m.validate_qa(rows, qa)
        assert len(m.embassy_points(rows)) == expected
        finding = qa['qa']['p137_vs_osm_country_disagree'][0]
        row = next(r for r in rows if r['properties']['name'] == finding['name'])
        assert row['properties']['country'] == corrected
        row['properties']['country'] = finding['osm_country_tag']
        with pytest.raises(ValueError, match='correction missing'):
            m.validate_qa(rows, qa)
    assert sum(c['counts']['excluded_by_reason']['no_coordinates'] for c in summary['cities'].values()) == 31
    assert summary['cities']['bangkok']['counts']['excluded_by_reason']['data_noise'] == 1
    assert summary['cities']['tokyo']['counts']['excluded_by_reason']['defunct'] == 2
    assert summary['cities']['tokyo']['counts']['excluded_by_reason']['duplicate'] == 1


def test_excluded_coordinate_less_record_cannot_reenter():
    summary = {'counts': {'features': 1}, 'qa': {'p137_vs_osm_country_disagree': []},
               'excluded': [{'name': 'Excluded', 'reason': 'no_coordinates'}]}
    with pytest.raises(ValueError, match='reintroduced'):
        m.validate_qa([feature('Excluded')], summary)


def test_jnto_scope_and_duplicate_rejection():
    row = {'pref': 'Tokyo', 'name': 'A', 'address': 'B', 'lat': 35, 'lon': 139}
    assert m.medicine_points([row, {**row, 'pref': 'Chiba'}]) == [(35, 139)]
    with pytest.raises(ValueError, match='Duplicate medical'):
        m.medicine_points([row, row.copy()])


@pytest.fixture(scope='module')
def generated():
    return m.build()


def test_real_export_completeness_and_publication_boundary(generated):
    tokyo = generated['station-institutions.json']
    bangkok = generated['district-institutions.json']
    assert len(tokyo['stations']) == 1493
    assert len(bangkok['districts']) == 50
    assert len(bangkok['station_areas']) == 133
    assert tokyo['stations']['hiroo'] == {'embassies_within_800m': 40, 'english_medicine_within_2km': 61}
    assert tokyo['_meta']['tokyo_medicine_records'] == 508
    assert bangkok['_meta']['district_join'] == {'outside': 0, 'boundary_assigned': 0, 'total_assigned': 79}
    assert sum(r['embassies_inside_district'] for r in bangkok['districts'].values()) == 79
    assert bangkok['districts']['pathum-wan']['embassies_inside_district'] == 23
    assert bangkok['districts']['bang-rak']['embassies_inside_district'] == 11
    assert bangkok['districts']['bang-bon']['embassies_inside_district'] == 0
    for group in (bangkok['districts'], bangkok['station_areas']):
        assert all(row['english_medicine_within_2km'] is None for row in group.values())
    # Only counts leave restricted JNTO rows: no names, phones, addresses or coordinates.
    assert all(set(row) == {'embassies_within_800m', 'english_medicine_within_2km'} for row in tokyo['stations'].values())
    baseline = m.read(ROOT, 'app/src/data/environment-data.json')
    for slug, row in baseline.items():
        if 'english_medicine_2km' in row:
            assert tokyo['stations'][slug]['english_medicine_within_2km'] == row['english_medicine_2km']
            assert tokyo['stations'][slug]['embassies_within_800m'] == row['embassies_800m']


def test_actual_committed_exports_byte_replay(generated):
    for name, doc in generated.items():
        expected = (json.dumps(doc, ensure_ascii=False, indent=1) + '\n').encode()
        for directory in ('data/institutions', 'app/src/data/institutions'):
            assert (ROOT / directory / name).read_bytes() == expected


def test_main_check_catches_stale_app_export_before_any_write(tmp_path, monkeypatch, generated):
    for name, doc in generated.items():
        for directory in ('data/institutions', 'app/src/data/institutions'):
            path = tmp_path / directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    target = tmp_path / 'app/src/data/institutions/district-institutions.json'
    target.write_text('{}\n')
    monkeypatch.setattr(m, 'ROOT', tmp_path)
    monkeypatch.setattr(m, 'build', lambda: generated)
    with pytest.raises(SystemExit):
        m.main(['--check'])
    assert target.read_text() == '{}\n'
    m.main([])
    m.main(['--check'])
