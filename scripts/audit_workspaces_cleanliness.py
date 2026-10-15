#!/usr/bin/env python3
"""Offline CRTKY-196 evidence audit. Prints aggregates, never locator records.

This is a research audit, not a product export or a publication permission check.
No network, geocoding, scoring, repairs or writes are performed.
"""
from __future__ import annotations

import calendar
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path('research/snapshots/2026-10-14')


def coworking_summary(doc):
    rows = doc['locations']
    if doc['count'] != len(rows):
        raise ValueError('Declared coworking count differs from records')
    groups = defaultdict(Counter)
    for row in rows:
        lat, lng = row.get('lat'), row.get('lng')
        if (lat is None) != (lng is None):
            raise ValueError('Partial coordinate pair; do not geocode or count implicitly')
        if lat is not None:
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                       and math.isfinite(v) for v in (lat, lng)):
                raise ValueError('Invalid coordinate pair')
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError('Coordinate outside geographic bounds')
        if not row.get('address') or not row.get('source_url', '').startswith('https://'):
            raise ValueError('Missing address or HTTPS source citation')
        groups[row['brand']]['with_coordinates' if lat is not None else 'without_coordinates'] += 1
    with_coordinates = sum(g['with_coordinates'] for g in groups.values())
    return {
        'records': len(rows), 'with_address_and_source': len(rows), 'with_coordinates': with_coordinates,
        'without_coordinates': len(rows) - with_coordinates,
        'by_brand': {brand: {key: group[key] for key in ('with_coordinates', 'without_coordinates')}
                     for brand, group in sorted(groups.items())},
    }


def waste_summary(rows, raw_rows, codes, district_slugs):
    mapping = {r['dcode']: r['slug'] for r in codes}
    expected_codes = {str(i) for i in range(1001, 1051)}
    if (len(codes) != 50 or set(mapping) != expected_codes
            or set(mapping.values()) != district_slugs or len(district_slugs) != 50):
        raise ValueError('District code mapping must join all 50 distinct districts')
    raw = {r['dcode']: r for r in raw_rows}
    if len(raw_rows) != 51 or set(raw) != expected_codes | {'1000'}:
        raise ValueError('Raw waste table must contain 50 districts plus other code 1000')
    expected_keys = {(code, year) for code in raw for year in range(2010, 2019)}
    seen = set()
    annual = defaultdict(Decimal)
    zero_daily = Counter()
    inconsistent = Counter()
    other = defaultdict(Decimal)
    for row in rows:
        code, year = row['dcode'], int(row['year_ad'])
        key = code, year
        if key in seen or key not in expected_keys:
            raise ValueError('Duplicate or unexpected district-year')
        seen.add(key)
        if int(row['year_be']) != year + 543 or row['slug'] != mapping.get(code, ''):
            raise ValueError('Incorrect calendar conversion or district join')
        tons, daily = Decimal(row['waste_tons']), Decimal(row['waste_tons_per_day'])
        suffix = str(year + 543)[-2:]
        if (tons != Decimal(raw[code]['garbage' + suffix])
                or daily != Decimal(raw[code]['garbageperday' + suffix])):
            raise ValueError('Tidy values differ from original waste CSV')
        if not tons.is_finite() or not daily.is_finite() or min(tons, daily) < 0:
            raise ValueError('Invalid waste quantity')
        if code == '1000':
            other[year] += tons
            continue
        annual[year] += tons
        zero_daily[year] += daily == 0
        # Diagnostic only: calendar-year consistency, not a repaired value or
        # a claim that the source specifies calendar rather than fiscal years.
        days = 366 if calendar.isleap(year) else 365
        inconsistent[year] += abs(tons - daily * days) > max(Decimal(1), tons * Decimal('.01'))
    if seen != expected_keys:
        raise ValueError('Missing district-year observations')
    return {
        'rows': len(rows), 'district_rows': len(rows) - 9, 'other_rows': 9,
        'districts_joined': len(mapping), 'years_ad': list(range(2010, 2019)),
        'code_1000': 'other, not a city total',
        'measure': 'municipal solid-waste quantity',
        'units': ['tonnes per reported year', 'tonnes per day'],
        'annual_tonnes_excluding_other': {str(y): str(v) for y, v in sorted(annual.items())},
        'other_tonnes': {str(y): str(v) for y, v in sorted(other.items())},
        'district_zero_daily_values': {str(y): zero_daily[y] for y in range(2010, 2019)},
        'district_calendar_year_discrepancies_over_1pct': {
            str(y): inconsistent[y] for y in range(2010, 2019)},
    }


def audit(root=ROOT):
    snap = root / SNAPSHOT
    cow = {city: coworking_summary(json.loads((snap / 'coworking' / f'coworking-{city}.json').read_text()))
           for city in ('tokyo', 'bangkok')}
    waste = snap / 'cleanliness-bangkok'
    def csv_rows(name):
        with (waste / name).open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))
    slugs = {d['slug'] for d in json.loads((root / 'app/src/data/bangkok/districts.json').read_text())['districts']}
    summary = waste_summary(csv_rows('waste-by-khet-tidy.csv'), csv_rows('garbage-by-khet.csv'),
                            json.loads((waste / 'khet-codes.json').read_text()), slugs)
    inputs = [snap / 'coworking' / name for name in ('coworking-tokyo.json', 'coworking-bangkok.json', 'LICENSE.txt')]
    inputs += [waste / name for name in ('waste-by-khet-tidy.csv', 'garbage-by-khet.csv',
                                        'garbage-metadata.docx', 'khet-codes.json', 'LICENSE.txt')]
    return {'coworking': cow, 'coworking_total_without_coordinates': sum(d['without_coordinates'] for d in cow.values()),
            'waste': summary, 'input_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                              for p in inputs}}


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
