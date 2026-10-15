#!/usr/bin/env python3
"""Acquire noise proxies with mirror rotation. Rebuild uses pinned files offline.

python3 scripts/noise/fetch.py [--city tokyo|bangkok] [--refresh]
Successful responses are saved with query, endpoint, timestamp and SHA-256.
No credentials, TLS bypasses or location inference are used.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'scrapers'))
# Keep the mirrors shared with the established tourism acquisition script.
import importlib.util
spec = importlib.util.spec_from_file_location('tourism_fetch', ROOT / 'scripts/scrapers/fetch-tourism-counts.py')
tourism = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tourism)
RAW = ROOT / 'data/noise/raw'


def stations(city):
    if city == 'tokyo':
        return json.loads((ROOT / 'data/stations.json').read_text())
    return json.loads((ROOT / 'app/src/data/bangkok/stations.json').read_text())['areas']


def acquire(city, kind, refresh=False):
    path = RAW / f'{city}-{kind}.json.gz'
    meta = RAW / f'{city}-{kind}.source.json'
    if path.exists() and meta.exists() and not refresh:
        print(f'Cached: {path.name}', flush=True)
        return
    pts = stations(city)
    # >2 km margin even at the northern Tokyo extent; covers every station.
    bbox = [min(p['lat'] for p in pts)-.025, min(p['lng'] for p in pts)-.03,
            max(p['lat'] for p in pts)+.025, max(p['lng'] for p in pts)+.03]
    bb = ','.join(f'{x:.6f}' for x in bbox)
    selector = 'way["highway"~"^(primary|trunk|motorway|motorway_link)$"]' if kind == 'roads' else 'nwr["amenity"~"^(bar|pub|nightclub|karaoke_box)$"]'
    query = f'[out:json][timeout:90];{selector}({bb});out {"geom" if kind == "roads" else "center"};'
    errors = []
    for endpoint in tourism.ENDPOINTS:
        try:
            req = urllib.request.Request(endpoint, data=urllib.parse.urlencode({'data': query}).encode(),
                                         headers={'User-Agent': 'city-rating-noise/1.0', 'Content-Type': 'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req, timeout=110) as response:
                raw = response.read()
            doc = json.loads(raw)
            if doc.get('remark') or not doc.get('elements'):
                raise ValueError('Incomplete or empty Overpass response')
            packed = gzip.compress(raw, mtime=0)
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_bytes(packed)
            meta.write_text(json.dumps({'url': endpoint, 'query': query, 'bbox': bbox,
                'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'osm_base': doc.get('osm3s', {}).get('timestamp_osm_base'),
                'license': 'ODbL-1.0', 'attribution': '© OpenStreetMap contributors',
                'sha256': hashlib.sha256(packed).hexdigest(), 'elements': len(doc['elements'])}, indent=2)+'\n')
            print(f'{city} {kind}: {len(doc["elements"])} via {endpoint}', flush=True)
            return
        except Exception as exc:
            errors.append(f'{endpoint}: {exc}')
            print(errors[-1], flush=True)
    raise RuntimeError('\n'.join(errors))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--city', choices=['tokyo', 'bangkok'])
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    for city in [args.city] if args.city else ['tokyo', 'bangkok']:
        for kind in ['nightlife', 'roads']:
            acquire(city, kind, args.refresh)
