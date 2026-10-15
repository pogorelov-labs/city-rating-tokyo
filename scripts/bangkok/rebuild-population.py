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
        poi_term = b['crowd_raw'] - 0.5 * math.log(max(b['registered_density_input'], 1))
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


def main():
    baseline = json.loads((DATA / 'population-baseline.json').read_text())
    if sha256(APP / 'geometry.json') != baseline['_meta']['geometry_sha256']:
        raise ValueError('Adoption replay requires the pinned baseline district geometry')
    districts = json.loads((APP / 'districts.json').read_text())
    signals = json.loads((DATA / 'signals.json').read_text())
    meta = json.loads((APP / 'meta.json').read_text())
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
    weights = json.loads((ROOT / 'packages/schema/constants.json').read_text())['default_weights']
    meta['medians']['crowd'] = R.median_int([d['ratings']['crowd'] for d in districts['districts']])
    meta['default_anchors'] = R.anchors([R.composite(d['ratings'], weights) for d in districts['districts']])
    # Separate population epoch/provenance; do not relabel stale POIs as fresh.
    population_meta = population_metadata()
    districts['_meta']['population'] = population_meta
    signals['_meta']['population'] = population_meta
    for path, doc, indent in [(APP / 'districts.json', districts, None), (DATA / 'signals.json', signals, 1),
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
