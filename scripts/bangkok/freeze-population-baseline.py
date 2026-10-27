#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=2", "shapely>=2.1", "rasterio>=1.4,<2"]
# ///
"""Freeze the refresh population replay baseline once, after the full build.

The historical adoption baseline is never modified. Precise POI terms come
from the spatial builder, not from reverse engineering rounded crowd signals.
"""
import importlib.util
import json
import math
from pathlib import Path

import ratings as R
from population import crowd_raw, sha256

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/bangkok'
APP = ROOT / 'app/src/data/bangkok'


def main():
    spec = importlib.util.spec_from_file_location('rebuild_population', Path(__file__).with_name('rebuild-population.py'))
    rebuild = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rebuild)
    path = DATA / rebuild.BASELINES['refresh-2026-10-24']
    if path.exists():
        raise ValueError('Refusing to overwrite immutable refresh baseline')
    districts = json.loads((APP / 'districts.json').read_text())
    signals = json.loads((DATA / 'signals.json').read_text())
    meta = json.loads((APP / 'meta.json').read_text())
    rows = {}
    for d in districts['districts']:
        facts = d['facts']
        term = signals['districts'][d['slug']]['crowd_input']['poi_log_term']
        rows[d['slug']] = {'registered_population': facts['population'],
                           'population_year': facts['population_year'],
                           'official_area_km2': facts['area_km2'],
                           'registered_density_input': facts['density'],
                           'poi_log_term': term,
                           'crowd_raw': crowd_raw(facts['density'], term)}
        current = crowd_raw(signals['districts'][d['slug']]['crowd_input']['population'] / facts['area_km2'], term)
        if round(current, 4) != signals['districts'][d['slug']]['raw']['crowd'] or not math.isfinite(term):
            raise ValueError(f'Crowd input mismatch: {d["slug"]}')
    before = R.percentile_normalize({s: b['crowd_raw'] for s, b in rows.items()}, invert=True)
    for slug, row in rows.items():
        row['crowd_rating'] = before[slug]
    baseline = {'_meta': {
        'id': 'refresh-2026-10-24', 'inputs_manifest': 'data/bangkok/refresh-inputs.json',
        'inputs_manifest_sha256': sha256(DATA / 'refresh-inputs.json'),
        'geometry_sha256': sha256(APP / 'geometry.json'),
        'note': 'October refresh replay. Exact POI log terms and new published district geometry. Registered raw/rating is a counterfactual comparison, not a new DOPA observation. Historical adoption baseline is retained separately.',
        'unchanged_signatures': {name: rebuild.snapshot_signature(doc, name)
                                 for name, doc in [('districts', districts), ('signals', signals), ('meta', meta)]},
        }, 'districts': rows}
    # Freeze the exact synthetic pre-adoption state accepted by the same strict
    # original checksum guard as the historical replay; nothing is published.
    for doc in (districts, signals):
        doc['_meta'].pop('population')
    for d in districts['districts']:
        b = rows[d['slug']]
        d['ratings']['crowd'] = b['crowd_rating']
        d['sources']['crowd'] = ['dopa_population', 'overture']
        signals['districts'][d['slug']]['ratings']['crowd'] = b['crowd_rating']
        signals['districts'][d['slug']]['raw']['crowd'] = b['crowd_raw']
    import hashlib
    baseline['_meta']['signals_sha256'] = hashlib.sha256(
        (json.dumps(signals, ensure_ascii=False, indent=1) + '\n').encode()).hexdigest()
    path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + '\n')
    print(f'Frozen {len(rows)} refresh district inputs: {path}')


if __name__ == '__main__':
    main()
