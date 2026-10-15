#!/usr/bin/env python3
"""Offline institution counts and app export (CRTKY-190).

Run with Shapely >=2.1 (already a CI pipeline dependency):
  python scripts/institutions/compute-institutions.py [--check]
Only aggregate counts, source links and provenance leave the internal JNTO input.
Station distances are great-circle/straight-line, never walking routes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import MultiPolygon, Point, Polygon

ROOT = Path(__file__).resolve().parents[2]
SNAP = Path('research/snapshots/2026-10-14')
EMBASSY_RADIUS_M = 800
MEDICINE_RADIUS_M = 2000
SOURCES = {
    'osm': 'https://www.openstreetmap.org/copyright',
    'wikidata': 'https://www.wikidata.org/wiki/Wikidata:Licensing',
    'medicine': 'https://www.jnto.go.jp/emergency/eng/mi_guide.html',
}


def read(root: Path, path: Path | str):
    return json.loads((root / path).read_text(encoding='utf-8'))


def coordinate(lat, lon) -> tuple[float, float]:
    if isinstance(lat, bool) or isinstance(lon, bool):
        raise ValueError('Invalid coordinate')
    lat, lon = float(lat), float(lon)
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Invalid coordinate')
    return lat, lon


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return 6371000 * 2 * math.asin(math.sqrt(min(1, max(0, a))))


def count_nearby(points, lat, lng, radius_m):
    lat, lng = coordinate(lat, lng)
    return sum(haversine_m(lat, lng, *p) <= radius_m for p in points)


def embassy_points(features):
    """Curated input must already be QA-filtered; never silently invent coordinates."""
    points, seen = [], set()
    for feature in features:
        geometry, props = feature.get('geometry'), feature['properties']
        if not geometry or geometry.get('type') != 'Point' or len(geometry.get('coordinates', [])) != 2:
            raise ValueError('Embassy without Point coordinates')
        lon, lat = geometry['coordinates']
        point = coordinate(lat, lon)
        name = props.get('name', '').strip()
        if not name or 'syldav' in name.casefold():
            raise ValueError('Unresolved embassy QA')
        identity = (name, point)
        if identity in seen:
            raise ValueError('Duplicate embassy: upstream QA required')
        seen.add(identity)
        points.append(point)
    return points


def validate_qa(features, summary):
    if len(features) != summary['counts']['features']:
        raise ValueError('Embassy QA count mismatch')
    for finding in summary['qa']['p137_vs_osm_country_disagree']:
        retained = [f for f in features if f['properties']['name'] == finding['name']]
        if len(retained) != 1 or retained[0]['properties']['country'] != finding['p137']:
            raise ValueError('Country correction missing')
    excluded = {r['name'] for r in summary['excluded'] if r['reason'] in ('data_noise', 'defunct', 'no_coordinates')}
    if excluded.intersection(f['properties']['name'] for f in features):
        raise ValueError('Excluded embassy reintroduced')


def medicine_points(rows):
    points, seen = [], set()
    for row in rows:
        if row['pref'] != 'Tokyo':
            continue
        point = coordinate(row['lat'], row['lon'])
        identity = (row['name'], row['address'], point)
        if identity in seen:
            raise ValueError('Duplicate medical facility: upstream QA required')
        seen.add(identity)
        points.append(point)
    return points


def unique_rows(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f'Duplicate join key: {key}')
    return result


def district_counts(points, geometry, expected_slugs):
    if set(geometry) != set(expected_slugs):
        raise ValueError('District geometry join mismatch')
    shapes = {}
    for slug, entry in geometry.items():
        polygons = []
        for rings in entry['polygons']:
            lonlat = [[tuple(reversed(coordinate(*p))) for p in ring] for ring in rings]
            polygons.append(Polygon(lonlat[0], lonlat[1:]))
        shape = MultiPolygon(polygons)
        if shape.is_empty or not shape.is_valid:
            raise ValueError(f'Invalid district geometry: {slug}')
        shapes[slug] = shape
    counts = {slug: 0 for slug in sorted(shapes)}
    audit = {'outside': 0, 'boundary_assigned': 0, 'total_assigned': 0}
    for lat, lon in points:
        point = Point(lon, lat)
        interior = [slug for slug, shape in shapes.items() if shape.contains(point)]
        covered = sorted(slug for slug, shape in shapes.items() if shape.covers(point))
        if len(interior) > 1 or (interior and len(covered) > 1):
            raise ValueError('Embassy in overlapping district interiors')
        if not covered:
            audit['outside'] += 1
            continue
        # An exact shared-edge point belongs to one district, stable slug order.
        counts[covered[0]] += 1
        audit['total_assigned'] += 1
        audit['boundary_assigned'] += not bool(interior)
    return counts, audit


def build(root=ROOT):
    paths = [SNAP / 'embassies' / f'embassies-{city}.geojson' for city in ('tokyo', 'bangkok')]
    paths += [SNAP / 'embassies/summary.json', SNAP / 'embassies/LICENSE.txt',
              SNAP / 'medicine-jnto/medicine-jnto.json', SNAP / 'medicine-jnto/LICENSE.txt',
              Path('data/stations.json'), Path('app/src/data/stations.json'),
              Path('app/src/data/bangkok/geometry.json'), Path('app/src/data/bangkok/districts.json'),
              Path('app/src/data/bangkok/stations.json')]
    summary = read(root, SNAP / 'embassies/summary.json')
    embassies = {}
    for city in ('tokyo', 'bangkok'):
        features = read(root, SNAP / 'embassies' / f'embassies-{city}.geojson')['features']
        validate_qa(features, summary['cities'][city])
        embassies[city] = embassy_points(features)
    medicine = medicine_points(read(root, SNAP / 'medicine-jnto/medicine-jnto.json'))
    stations = unique_rows(read(root, 'data/stations.json'), 'slug')
    app_stations = unique_rows(read(root, 'app/src/data/stations.json'), 'slug')
    if set(stations) != set(app_stations) or any(
        coordinate(s['lat'], s['lng']) != coordinate(app_stations[k]['lat'], app_stations[k]['lng'])
        for k, s in stations.items()
    ):
        raise ValueError('Tokyo app station anchor mismatch')
    districts = unique_rows(read(root, 'app/src/data/bangkok/districts.json')['districts'], 'slug')
    areas = unique_rows(read(root, 'app/src/data/bangkok/stations.json')['areas'], 'id')
    if len(districts) != 50:
        raise ValueError('Expected all 50 Bangkok districts')
    counts, audit = district_counts(embassies['bangkok'], read(root, 'app/src/data/bangkok/geometry.json'), districts)
    meta = {
        'snapshot_date': '2026-10-14', 'source_urls': SOURCES,
        'embassy_license': 'OpenStreetMap ODbL 1.0; Wikidata CC0',
        'medicine_license': '© Japan Tourism Agency / JNTO; aggregate counts and links only',
        'embassy_radius_m': EMBASSY_RADIUS_M, 'medicine_radius_m': MEDICINE_RADIUS_M,
        'distance': 'great-circle, Earth radius 6371000 m; inclusive threshold; not walking distance',
        'district_rule': 'committed polygons including holes; covers; shared boundary assigned to first sorted slug; overlapping interiors rejected',
        'coverage': 'Snapshot records, not exhaustive inventories. Tokyo medicine includes only 508 Tokyo-prefecture JNTO records, including counts near the prefecture border.',
        'bangkok_medicine': 'unavailable: no verified publishable English-service source',
        'source_dates': {'bangkok_osm': '2026-06-01T08:52:28Z', 'tokyo_osm': '2026-07-24T11:04:51Z'},
        'retained_embassies': {city: len(points) for city, points in embassies.items()},
        'tokyo_medicine_records': len(medicine),
        'excluded_by_reason': {city: summary['cities'][city]['counts']['excluded_by_reason'] for city in embassies},
        'input_sha256': {str(p): hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths},
    }
    tokyo = {'_meta': meta, 'stations': {
        slug: {'embassies_within_800m': count_nearby(embassies['tokyo'], s['lat'], s['lng'], EMBASSY_RADIUS_M),
               'english_medicine_within_2km': count_nearby(medicine, s['lat'], s['lng'], MEDICINE_RADIUS_M)}
        for slug, s in sorted(stations.items())
    }}
    bangkok = {'_meta': {**meta, 'district_join': audit},
               'districts': {slug: {'embassies_inside_district': n, 'english_medicine_within_2km': None} for slug, n in counts.items()},
               'station_areas': {slug: {'embassies_within_800m': count_nearby(embassies['bangkok'], a['lat'], a['lng'], EMBASSY_RADIUS_M),
                                       'english_medicine_within_2km': None} for slug, a in sorted(areas.items())}}
    return {'station-institutions.json': tokyo, 'district-institutions.json': bangkok}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify generated and app exports without writing')
    args = parser.parse_args(argv)
    documents = build()
    stale = []
    for name, doc in documents.items():
        payload = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
        for directory in ('data/institutions', 'app/src/data/institutions'):
            target = ROOT / directory / name
            if args.check:
                if not target.exists() or target.read_text(encoding='utf-8') != payload:
                    stale.append(str(target.relative_to(ROOT)))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(payload, encoding='utf-8')
    if stale:
        parser.error('Stale institution exports: ' + ', '.join(stale))
    print('Institution exports verified' if args.check else 'Institution exports written')


if __name__ == '__main__':
    main()
