#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=2", "shapely>=2.1", "rasterio>=1.4,<2"]
# ///
"""Rebuild ONLY district crowd from the pinned CRTKY-197 baseline and raster.

No network or old raw POI cache required. Writes population-comparison.json,
all-50 CSV, district crowd/sources, signals crowd, and district meta anchors.
Run repeatedly with byte-identical outputs. Original population facts, all
other ratings, station areas and grid remain untouched. Full future pipeline
builds use population.py too, with their exact POI counts.
"""
import copy
import argparse
import hashlib
import csv
import io
import json
import math
from pathlib import Path

import ratings as R
from population import load_population, crowd_raw, sha256, population_metadata

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/bangkok'
APP = ROOT / 'app/src/data/bangkok'
BASELINES = {'adoption': 'population-baseline.json',
             'refresh-2026-10-24': 'population-baseline-refresh-2026-10-24.json'}


def compare(baseline, populations):
    if set(baseline) != set(populations):
        raise ValueError('Population/baseline district join mismatch')
    before = R.percentile_normalize({s: b['crowd_raw'] for s, b in baseline.items()}, invert=True)
    if any(before[s] != b['crowd_rating'] for s, b in baseline.items()):
        raise ValueError('Baseline rounded signals do not reproduce original ratings')
    rows = {}
    for slug, b in sorted(baseline.items()):
        pop = populations[slug]['population']
        area = b['official_area_km2']
        if area <= 0 or b['registered_population'] <= 0:
            raise ValueError(f'Invalid baseline area/population: {slug}')
        # Historical adoption has only rounded raw; the refresh freezes the
        # precise POI term from the spatial build. Never rewrite the old input.
        poi_term = (b['poi_log_term'] if 'poi_log_term' in b else
                    b['crowd_raw'] - 0.5 * math.log(max(b['registered_density_input'], 1)))
        raw = crowd_raw(pop / area, poi_term)
        rows[slug] = {**b, **populations[slug], 'density': pop / area,
                      'population_delta': pop - b['registered_population'],
                      'population_ratio': pop / b['registered_population'],
                      'registered_shortfall_pct_of_model': 100 * (1 - b['registered_population'] / pop),
                      'density_delta': pop / area - b['registered_density_input'],
                      'poi_log_term': poi_term, 'worldpop_raw': raw}
    after = R.percentile_normalize({s: r['worldpop_raw'] for s, r in rows.items()}, invert=True)
    # Ratings must be insensitive to the lost four-decimal raw precision:
    # compare extreme intervals per district against all others.
    for slug in rows:
        for delta in (-0.00005, 0.00005):
            perturbed = {s: r['worldpop_raw'] + (delta if s == slug else -delta) for s, r in rows.items()}
            if R.percentile_normalize(perturbed, invert=True)[slug] != after[slug]:
                raise ValueError(f'Rounded baseline could change rating for {slug}; raw POIs required')
        rows[slug]['worldpop_rating'] = after[slug]
        rows[slug]['rating_delta'] = after[slug] - before[slug]
    return rows



def snapshot_signature(doc, kind):
    """Hash everything the adoption replay is forbidden to change."""
    doc = copy.deepcopy(doc)
    if kind in ('districts', 'signals'):
        doc.pop('_meta')
        entries = doc['districts'] if kind == 'districts' else doc['districts'].values()
        for d in entries:
            d['ratings'].pop('crowd')
            d['sources' if kind == 'districts' else 'raw'].pop('crowd')
    elif kind == 'meta':
        doc['medians'].pop('crowd')
        doc.pop('default_anchors')
    else:
        raise ValueError(f'Unknown snapshot kind: {kind}')
    return hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_snapshot(baseline, districts, signals, meta):
    for name, doc in [('districts', districts), ('signals', signals), ('meta', meta)]:
        if snapshot_signature(doc, name) != baseline['_meta']['unchanged_signatures'][name]:
            raise ValueError(f'Incompatible {name} snapshot: non-crowd inputs changed; full build required')


def validate_crowd_state(baseline, districts, signals, meta, rows, weights):
    """Accept only the original inputs or a recomputed, verified previous replay."""
    original = all(
        d['ratings']['crowd'] == baseline['districts'][d['slug']]['crowd_rating']
        and d['sources']['crowd'] == ['dopa_population', 'overture']
        and signals['districts'][d['slug']]['ratings']['crowd'] == d['ratings']['crowd']
        and signals['districts'][d['slug']]['raw']['crowd'] == baseline['districts'][d['slug']]['crowd_raw']
        for d in districts['districts']
    )
    replayed = all(
        d['ratings']['crowd'] == rows[d['slug']]['worldpop_rating']
        and d['sources']['crowd'] == ['worldpop_2020', 'overture']
        and signals['districts'][d['slug']]['ratings']['crowd'] == d['ratings']['crowd']
        and signals['districts'][d['slug']]['raw']['crowd'] == round(rows[d['slug']]['worldpop_raw'], 4)
        for d in districts['districts']
    )
    if original:
        if sha256(DATA / 'signals.json') != baseline['_meta']['signals_sha256']:
            raise ValueError('Incompatible original signals checksum; full build required')
    elif replayed:
        expected = population_metadata()
        if any(doc['_meta'].get('population') != expected for doc in (districts, signals)):
            raise ValueError('Incompatible previous replay provenance')
    else:
        raise ValueError('Incompatible crowd snapshot: neither original baseline nor verified replay')
    ratings = [d['ratings'] for d in districts['districts']]
    if (meta['default_anchors'] != R.anchors([R.composite(r, weights) for r in ratings])
            or meta['medians']['crowd'] != R.median_int([r['crowd'] for r in ratings])):
        raise ValueError('Incompatible crowd medians/composite anchors')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', choices=BASELINES, required=True,
                        help='explicit immutable snapshot; adoption is historical only')
    args = parser.parse_args(argv)
    baseline = json.loads((DATA / BASELINES[args.baseline]).read_text())
    if sha256(APP / 'geometry.json') != baseline['_meta']['geometry_sha256']:
        raise ValueError('Incompatible geometry: replay requires the selected baseline district geometry')
    districts = json.loads((APP / 'districts.json').read_text())
    signals = json.loads((DATA / 'signals.json').read_text())
    meta = json.loads((APP / 'meta.json').read_text())
    validate_snapshot(baseline, districts, signals, meta)
    slugs = {d['slug'] for d in districts['districts']}
    if slugs != set(baseline['districts']) or slugs != set(signals['districts']):
        raise ValueError('District snapshot join mismatch')
    for d in districts['districts']:
        b = baseline['districts'][d['slug']]
        for field, key in [('population', 'registered_population'), ('population_year', 'population_year'),
                           ('area_km2', 'official_area_km2'), ('density', 'registered_density_input')]:
            if d['facts'][field] != b[key] or signals['districts'][d['slug']]['facts'][field] != b[key]:
                raise ValueError(f'Baseline facts changed: {d["slug"]}.{field}')
    populations, summary = load_population(json.loads((APP / 'geometry.json').read_text()), slugs)
    rows = compare(baseline['districts'], populations)
    weights = json.loads((ROOT / 'packages/schema/constants.json').read_text())['default_weights']
    validate_crowd_state(baseline, districts, signals, meta, rows, weights)
    registered = sum(b['registered_population'] for b in baseline['districts'].values())
    summary.update(registered_population=registered, population_ratio=summary['population'] / registered,
                   registered_shortfall_pct_of_model=100 * (1 - registered / summary['population']),
                   changed_ratings=sum(r['rating_delta'] != 0 for r in rows.values()))
    source = json.loads((DATA / 'population-source.json').read_text())
    comparison = {'source': source, 'baseline': baseline['_meta'], 'summary': summary, 'districts': rows}
    for d in districts['districts']:
        row = rows[d['slug']]
        d['ratings']['crowd'] = row['worldpop_rating']
        d['sources']['crowd'] = ['worldpop_2020', 'overture']
        signals['districts'][d['slug']]['ratings']['crowd'] = row['worldpop_rating']
        signals['districts'][d['slug']]['raw']['crowd'] = round(row['worldpop_raw'], 4)
    meta['medians']['crowd'] = R.median_int([d['ratings']['crowd'] for d in districts['districts']])
    meta['default_anchors'] = R.anchors([R.composite(d['ratings'], weights) for d in districts['districts']])
    # Separate population epoch/provenance; do not relabel stale POIs as fresh.
    population_meta = population_metadata()
    districts['_meta']['population'] = population_meta
    signals['_meta']['population'] = population_meta
    district_text = (APP / 'districts.json').read_text()
    district_indent = None if '\n' not in district_text.rstrip('\n') else 1
    for path, doc, indent in [(APP / 'districts.json', districts, district_indent), (DATA / 'signals.json', signals, 1),
                              (APP / 'meta.json', meta, 2), (DATA / 'population-comparison.json', comparison, 2)]:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=indent,
                                  separators=(',', ':') if indent is None else None) + '\n')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=['slug', *next(iter(rows.values()))])
    writer.writeheader()
    writer.writerows({'slug': slug, **row} for slug, row in rows.items())
    (DATA / 'population-comparison.csv').write_text(stream.getvalue())
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
