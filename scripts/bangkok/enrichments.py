"""Compose retained enrichment snapshots after the spatial build.

These are observations from their own dates, not fresh PBF observations.
Validate all sources/joins before mutating either output document.
"""
import hashlib
import json
from pathlib import Path


def read_source(root: Path, path: str, expected: dict) -> dict:
    payload = (root / path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected['sha256']:
        raise ValueError(f'Enrichment source checksum mismatch: {path}')
    return json.loads(payload)


def apply_enrichments(root: Path, districts: list[dict], areas: list[dict]) -> None:
    baseline = json.loads((root / 'data/bangkok/enrichments-baseline.json').read_text())
    sources = baseline['_meta']['sources']
    tourism = read_source(root, 'data/tourism/proximity.json', sources['tourism'])['stations']['bangkok']
    michelin = read_source(root, 'data/michelin/proximity.json', sources['michelin'])['districts']
    district_ids = [d['slug'] for d in districts]
    area_ids = [a['id'] for a in areas]
    if (len(district_ids) != 50 or len(set(district_ids)) != 50
            or set(district_ids) != set(baseline['district_ids'])):
        raise ValueError('Enrichment district join mismatch (requires all 50 districts)')
    if (len(area_ids) != 133 or len(set(area_ids)) != 133
            or set(area_ids) != set(tourism) or set(area_ids) != set(baseline['area_ids'])):
        raise ValueError('Tourism area join mismatch (requires all 133 areas)')
    if set(michelin) != set(baseline['michelin_districts']) or not set(michelin) <= set(district_ids):
        raise ValueError('Michelin district join mismatch')
    if not set(baseline['embassies_800m']) <= set(district_ids):
        raise ValueError('Embassy district join mismatch')
    # Resolve every required field before mutation, including zero observations.
    area_fields = {}
    for area_id, row in tourism.items():
        hotels, attractions = row['hotels_800m'], row['attractions_800m']
        if any(type(v) is not int or v < 0 for v in (hotels, attractions)):
            raise ValueError(f'Invalid tourism counts: {area_id}')
        area_fields[area_id] = dict(hotels_800m=hotels, attractions_800m=attractions,
                                    tourist_badge=hotels >= 50 or attractions >= 8)
    district_fields = {}
    for slug, row in michelin.items():
        stars, bib = row['stars'], row['bib_gourmand']
        if any(type(v) is not int or v < 0 for v in (stars, bib)):
            raise ValueError(f'Invalid Michelin counts: {slug}')
        district_fields[slug] = dict(michelin_stars=stars, michelin_bib=bib)
    for slug, value in baseline['embassies_800m'].items():
        if type(value) is not int or value < 0:
            raise ValueError(f'Invalid preserved embassy count: {slug}')
        district_fields.setdefault(slug, {})['embassies_800m'] = value
    for area in areas:
        area.update(area_fields[area['id']])
    for district in districts:
        district['facts'].update(district_fields.get(district['slug'], {}))
