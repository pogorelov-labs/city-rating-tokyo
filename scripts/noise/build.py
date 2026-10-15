#!/usr/bin/env python3
"""Offline day/night quietness facts (CRTKY-189). See data/noise/README.md."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/noise/raw'
SNAP = ROOT / 'research/snapshots/2026-10-14/noise'
RADIUS = 800
ROAD_RADIUS = 2000
VERSION = 'quietness-v1'


def read_json(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def address_key(address):
    # Exact address equivalence only; no fuzzy matching or neighborhood centroids.
    text = re.sub(r'\s+', '', unicodedata.normalize('NFKC', address))
    for token in ['丁目', '番地', '番', 'ｰ', '−']:
        text = text.replace(token, '-')
    return text.replace('号', '')


def recent_surveys():
    rows, excluded = [], {}
    for r in range(1, 6):
        path = SNAP / f'tmg_r{r}_jouji_monitoring.csv'
        rejected = 0
        for line, row in enumerate(csv.reader(path.read_text(encoding='cp932').splitlines()), 1):
            if len(row) < 19 or not row[0].strip().isdigit():
                continue
            try:
                day, night = float(row[17]), float(row[18])
                if not (20 <= day <= 100 and 20 <= night <= 100):
                    raise ValueError('Invalid Leq')
            except ValueError:
                rejected += 1
                continue
            rows.append({'id': f'tmg-{r+2018}-{row[0].strip()}', 'year': r+2018,
                         'address': row[1].strip(), 'address_key': address_key(row[1]),
                         'road': row[4].strip(), 'day_db': day, 'night_db': night,
                         'start_date': row[12].strip(), 'end_date': row[13].strip(),
                         'file': str(path.relative_to(ROOT)), 'line': line})
        excluded[str(r+2018)] = rejected
    return rows, excluded


def coordinate_index():
    groups = defaultdict(list)
    path = RAW / 'tmg-h25.csv'
    if sha(path) != read_json(RAW / 'tmg-h25.source.json')['sha256']:
        raise ValueError('SHA mismatch: TMG H25 coordinates')
    for row in list(csv.reader(path.read_text(encoding='cp932').splitlines()))[1:]:
        if len(row) < 5:
            continue
        try:
            lat, lng = float(row[2]), float(row[3])
        except ValueError:
            continue
        # JGD2011 coordinates, used as approximate WGS84 at this display scale.
        if not (34 < lat < 37 and 138 < lng < 142) or row[4] != 'JGD2011':
            continue
        groups[address_key(row[1])].append((lat, lng))
    # Conflicting coordinates for an address are not resolved by guessing.
    return {key: values[0] for key, values in groups.items() if len(set(values)) == 1}


def project(lat, lng, latitude):
    return math.radians(lng) * 6371000 * math.cos(math.radians(latitude)), math.radians(lat) * 6371000


def segment_distance(x, y, ax, ay, bx, by):
    dx, dy = bx-ax, by-ay
    t = max(0, min(1, ((x-ax)*dx + (y-ay)*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(x-ax-t*dx, y-ay-t*dy)


class ProxyIndex:
    """Local metric projection + 2 km buckets; distance to segments, not way centres."""
    def __init__(self, city):
        self.latitude = 35.6 if city == 'tokyo' else 13.7
        self.points, self.segments = defaultdict(list), defaultdict(list)
        self.sources = []
        self.bboxes = []
        for kind in ['nightlife', 'roads']:
            path = RAW / f'{city}-{kind}.json.gz'
            meta = read_json(RAW / f'{city}-{kind}.source.json')
            if sha(path) != meta['sha256']:
                raise ValueError(f'SHA mismatch: {path}')
            doc = json.loads(gzip.decompress(path.read_bytes()))
            if doc.get('remark') or not doc.get('elements') or len(doc['elements']) != meta['elements']:
                raise ValueError(f'Incomplete source: {path}')
            self.sources.append(meta)
            self.bboxes.append(meta['bbox'])
            for el in doc['elements']:
                if kind == 'nightlife':
                    coord = el if 'lat' in el else el.get('center')
                    if coord is None:
                        raise ValueError(f'Missing nightlife centre: {el["id"]}')
                    x, y = project(coord['lat'], coord['lon'], self.latitude)
                    self.points[self.bucket(x, y)].append((x, y))
                else:
                    geometry = el.get('geometry', [])
                    if len(geometry) < 2 or any('lat' not in p or 'lon' not in p for p in geometry):
                        raise ValueError(f'Missing road geometry: {el["id"]}')
                    expressway = el['tags']['highway'] in ('motorway', 'motorway_link')
                    for a, b in zip(geometry, geometry[1:]):
                        ax, ay = project(a['lat'], a['lon'], self.latitude)
                        bx, by = project(b['lat'], b['lon'], self.latitude)
                        for i in range(math.floor(min(ax, bx)/2000), math.floor(max(ax, bx)/2000)+1):
                            for j in range(math.floor(min(ay, by)/2000), math.floor(max(ay, by)/2000)+1):
                                self.segments[i, j].append((ax, ay, bx, by, expressway))

    @staticmethod
    def bucket(x, y):
        return math.floor(x/2000), math.floor(y/2000)

    def features(self, lat, lng):
        # Partial catchments at extract boundaries are unknown, never quiet zeros.
        for south, west, north, east in self.bboxes:
            margin_y = math.degrees(ROAD_RADIUS/6371000)
            margin_x = margin_y/math.cos(math.radians(self.latitude))
            if not (south+margin_y <= lat <= north-margin_y and west+margin_x <= lng <= east-margin_x):
                return None
        x, y = project(lat, lng, self.latitude)
        i, j = self.bucket(x, y)
        count, distances = 0, [float(ROAD_RADIUS), float(ROAD_RADIUS)]
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                for px, py in self.points[i+dx, j+dy]:
                    count += math.hypot(px-x, py-y) <= RADIUS
                for ax, ay, bx, by, expressway in self.segments[i+dx, j+dy]:
                    distances[expressway] = min(distances[expressway], segment_distance(x, y, ax, ay, bx, by))
        return {'nightlife_800m': count, 'arterial_distance_m': round(distances[0], 1),
                'expressway_distance_m': round(distances[1], 1)}


def vector(features):
    return [1, max(math.exp(-features['arterial_distance_m']/200),
                   math.exp(-features['expressway_distance_m']/400)), math.log1p(features['nightlife_800m'])]


def fit(rows, target, nightlife_slope):
    """Fit road effects with a declared, fixed nightlife contribution.

    An unconstrained intercept with non-negative road/nightlife effects makes
    denser nightlife or closer roads unable to imply greater quietness.
    """
    x, y = [vector(r['features']) for r in rows], [r[target] for r in rows]
    if len(rows) < 20:
        raise ValueError('Insufficient calibration rows')
    beta = [statistics.mean(y), 0., nightlife_slope]
    for _ in range(4000):
        previous = beta[:]
        for j in range(2):
            denom = sum(v[j]**2 for v in x)
            value = sum(v[j]*(actual-sum(v[k]*beta[k] for k in range(3) if k != j)) for v, actual in zip(x, y))/denom if denom else 0
            beta[j] = value if j == 0 else max(0, value)
        if max(abs(a-b) for a, b in zip(previous, beta)) < 1e-9:
            break
    # Quantize fitted coefficients for byte-stable output across Python/libm versions.
    return [round(value, 8) for value in beta]


def predict(features, beta):
    return sum(x*b for x, b in zip(vector(features), beta))


def quietness(db):
    # Product index endpoints, not legal limits or a measured quietness scale.
    return round(max(1, min(10, 10-9*(db-45)/35)), 1)


def complaints():
    out = {}
    for edition in [2022, 2023, 2024]:
        path = SNAP / f'yearbook1911_{edition}.csv'
        for row in csv.DictReader(path.read_text(encoding='utf-8-sig').splitlines()):
            if row['地域階層'] != '2' or row['Fiscal year'] != str(edition):
                continue
            value = row.get('騒音 Noise', row.get('騒音 Noises', '')).strip()
            if value.isdigit():
                out.setdefault(row['地域'], []).append({'year': edition, 'count': int(value)})
    return out


def build():
    surveys, invalid = recent_surveys()
    coords = coordinate_index()
    tokyo = ProxyIndex('tokyo')
    matched = []
    unmatched, outside = defaultdict(int), defaultdict(int)
    for row in surveys:
        coord = coords.get(row['address_key'])
        if coord is None:
            unmatched[str(row['year'])] += 1
            continue
        features = tokyo.features(*coord)
        if features is None:
            outside[str(row['year'])] += 1
            continue
        matched.append({**row, 'lat': coord[0], 'lng': coord[1], 'features': features})

    # FY2023 test locations never occur in the FY2019–22 training set.
    train = [r for r in matched if r['year'] < 2023]
    train_sites = {r['address_key'] for r in train}
    test = [r for r in matched if r['year'] == 2023 and r['address_key'] not in train_sites]
    if len(test) < 10:
        raise ValueError('Insufficient independent FY2023 evaluation locations')
    # Roadside surveys cannot identify entertainment noise. These are explicit
    # product assumptions, fixed before evaluation, NOT fitted acoustic effects.
    nightlife_slopes = {'day': 0.5, 'night': 1.5}
    models = {period: fit(train, f'{period}_db', nightlife_slopes[period]) for period in ['day', 'night']}
    evaluation = {period: {'mae_db': round(statistics.mean(abs(predict(r['features'], models[period])-r[f'{period}_db']) for r in test), 3),
                            'training_mean_baseline_mae_db': round(statistics.mean(abs(statistics.mean(t[f'{period}_db'] for t in train)-r[f'{period}_db']) for r in test), 3)}
                  for period in ['day', 'night']}
    report = {'model_version': VERSION, 'model': models, 'features': ['intercept', 'max(exp(-arterial_distance_m/200), exp(-expressway_distance_m/400))', 'ln(1+nightlife_800m)'],
              'evaluation_design': 'Retrospective spatial evaluation, not untouched validation: earlier fits were inspected; heuristic coefficients frozen for final model.',
              'fit': 'least squares intercept and non-negative road slopes; fixed nightlife slope; frozen FY2019–22 fit, no refit on evaluation data',
              'nightlife_assumption_db_per_log_count': nightlife_slopes,
              'road_exposure_assumption': 'Shared slope for primary/trunk and motorway/link, taking maximum proximity pressure. Decay lengths 200/400 m are heuristics, not fitted propagation or building shielding.',
              'nightlife_limit': '0.5 day / 1.5 night dB per ln(1+venues) is a declared heuristic, not an effect measured by roadside surveys. Day/night models are not constrained to night being quieter.',
              'coordinate_match': 'Exact normalized full address to unique FY2013 JGD2011 coordinate; approximate archival position, no fuzzy geocoding',
              'valid_readings_by_year': {str(year): sum(r['year']==year for r in surveys) for year in range(2019,2024)},
              'invalid_readings_by_year': invalid, 'unmatched_addresses_by_year': dict(unmatched), 'outside_proxy_extent_by_year': dict(outside),
              'matched_readings_by_year': {str(year): sum(r['year']==year for r in matched) for year in range(2019,2024)},
              'training_rows': len(train), 'training_locations': len(train_sites), 'test_rows': len(test),
              'test_locations': len({r['address_key'] for r in test}),
              'test_excluded_repeated_locations': sum(r['year']==2023 and r['address_key'] in train_sites for r in matched),
              'training_ids': [r['id'] for r in train], 'test_ids': [r['id'] for r in test], 'evaluation': evaluation,
              'target': 'Roadside campaign Leq dB, day 06–22 / night 22–06; NOT residential or 1–10 index accuracy',
              'temporal_limit': '2026 OSM proxies matched to FY2019–23 surveys using FY2013 coordinates; retrospective evaluation, not prospective validation',
              'bangkok': {'status': 'uncalibrated_transfer', 'measured_anchors': 0, 'mae_db': None,
                          'reason': 'PCD station and annual CSVs not acquired; TLS handshake timeout on 2026-10-15. Metadata only. No measured day/night in the acquired materials.'}}
    latest = [r for r in matched if r['year']==2023]
    wards, complaint_data = read_json(ROOT/'app/src/data/ward-data.json'), complaints()
    output = {'model_version': VERSION, 'tokyo': {}, 'bangkok': {}}
    for city in ['tokyo', 'bangkok']:
        index = tokyo if city == 'tokyo' else ProxyIndex(city)
        stations = read_json(ROOT/'data/stations.json') if city=='tokyo' else read_json(ROOT/'app/src/data/bangkok/stations.json')['areas']
        for station in stations:
            slug = station['slug'] if city=='tokyo' else station['id']
            features = index.features(station['lat'], station['lng'])
            entry = {'status': 'available' if features else 'missing_proxies', 'confidence': 'estimate',
                     'calibration': 'tokyo_roadside' if city=='tokyo' else 'uncalibrated_transfer',
                     'data_date': min(s['osm_base'][:10] for s in index.sources), 'model_version': VERSION,
                     'day': quietness(predict(features, models['day'])) if features else None,
                     'night': quietness(predict(features, models['night'])) if features else None,
                     'anchors': []}
            if features:
                entry['proxies'] = features
            if city=='tokyo':
                x, y = project(station['lat'], station['lng'], index.latitude)
                near = []
                for anchor in latest:
                    ax, ay = project(anchor['lat'], anchor['lng'], index.latitude)
                    distance = math.hypot(x-ax, y-ay)
                    if distance <= RADIUS:
                        near.append((distance, anchor))
                for distance, anchor in sorted(near, key=lambda item: (item[0], item[1]['id']))[:1]:
                    entry['anchors'].append({k: anchor[k] for k in ['id','address','road','year','day_db','night_db','start_date','end_date']}
                                            | {'distance_m': round(distance), 'coordinate_year': 2013,
                                               'source_url': 'https://www.kankyo.metro.tokyo.lg.jp/vehicle/noise/result/cyousakekka/reiwa5'})
                ward = wards.get(slug, {})
                # The station catalogue spans four prefectures. Chuo/Kita ward
                # names also occur outside Tokyo; require Tokyo's prefecture code.
                # Within Tokyo, city_name identifies the municipality (including
                # special wards); ward_name can instead be a submunicipal district.
                municipality = ward.get('city_name')
                if (station.get('prefecture') == '13'
                        and ward.get('prefecture_name', '') in ('', '東京都')
                        and municipality in complaint_data):
                    entry['complaints'] = {'municipality': municipality, 'series': complaint_data[municipality]}
            output[city][slug] = entry
    paths = sorted([*SNAP.glob('tmg_r*_jouji_monitoring.csv'), *SNAP.glob('yearbook1911_*.csv'),
                    SNAP/'pcd_resources_index.json', SNAP/'LICENSE.txt', *RAW.glob('*'),
                    ROOT/'data/stations.json', ROOT/'app/src/data/bangkok/stations.json',
                    ROOT/'app/src/data/ward-data.json', Path(__file__), ROOT/'scripts/noise/fetch.py'])
    report['inputs'] = [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in paths if p.is_file()]
    report['coverage'] = {city: {'stations': len(output[city]), 'estimated': sum(e['status']=='available' for e in output[city].values()),
                               'with_measured_anchor': sum(bool(e['anchors']) for e in output[city].values())} for city in ['tokyo','bangkok']}
    return output, report, matched


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify committed outputs byte-for-byte without writing')
    args = parser.parse_args()
    output, report, anchors = build()
    products = {ROOT/'app/src/data/noise/quietness.json': output, ROOT/'data/noise/calibration.json': report,
                ROOT/'data/noise/tmg-matched.json': anchors,
                ROOT/'app/src/data/noise/calibration-summary.json': {k: report[k] for k in ['training_rows', 'training_locations', 'test_locations', 'evaluation', 'matched_readings_by_year', 'unmatched_addresses_by_year']}}
    for path, doc in products.items():
        if args.check:
            expected = json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
            if not path.exists() or path.read_text()!=expected:
                raise SystemExit(f'Stale generated file: {path.relative_to(ROOT)}')
        else:
            write(path, doc)
    print(json.dumps({k: report[k] for k in ['coverage','training_rows','training_locations','test_rows','evaluation','model']}, indent=2))


if __name__ == '__main__':
    main()
