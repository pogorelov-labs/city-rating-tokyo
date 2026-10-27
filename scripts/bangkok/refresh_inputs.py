"""Frozen-input capture/verification for the October 2026 Bangkok refresh."""
import hashlib
import json
from pathlib import Path

OSM = ('boundaries', 'province', 'green', 'pois_culture', 'pois_essentials', 'pois_food',
       'pois_nightlife', 'pois_sports', 'pois_transit_other', 'rail_routes', 'rail_stations', 'rail_stops')
API = ('wikidata', 'commons', 'station_wikidata', 'station_commons')
RAW_FILES = ([f'data/bangkok/raw/{name}.json' for name in (*OSM, *API)] +
             [f'data/bangkok/raw/{name}' for name in
              ('thailand.osm.pbf', 'thailand.osm.pbf.source.json', 'geofabrik-source.json',
               'overture_places.parquet', 'overture-source.json', 'tha_ppp_2020_constrained.tif', 'thaifloodrisk.zip')])
BUILD_FILES = ['data/bangkok/editorial.json', 'data/bangkok/rent-overrides.json',
               'data/bangkok/flood.json', 'data/bangkok/population-source.json',
               'data/bangkok/enrichments-baseline.json', 'data/tourism/proximity.json',
               'data/michelin/proximity.json', 'data/institutions/district-institutions.json',
               'data/institutions/station-institutions.json', 'packages/schema/constants.json']


def digest(path: Path) -> dict:
    with path.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': sha}


def required_files(root: Path) -> set[str]:
    return set(RAW_FILES + BUILD_FILES +
               [str(p.relative_to(root)) for p in (root / 'data/bangkok/descriptions').glob('*.json')] +
               [str(p.relative_to(root)) for p in (root / 'app/public/data/bangkok/licenses').glob('*.txt')] +
               [str(p.relative_to(root)) for p in (root / 'data/bangkok/raw/review').glob('*.json')])


def verify_inputs(root: Path, path: Path) -> dict:
    doc = json.loads(path.read_text())
    if doc['schema_version'] != 1 or set(doc['files']) != required_files(root):
        raise ValueError('Frozen input manifest file set mismatch')
    for name, expected in doc['files'].items():
        if digest(root / name) != expected:
            raise ValueError(f'Frozen input mismatch: {name}')
    return doc


def capture(root: Path, build_date: str) -> dict:
    import duckdb
    raw = root / 'data/bangkok/raw'
    source = json.loads((raw / 'geofabrik-source.json').read_text())
    expected_pbf = {'bytes': 329280467, 'sha256': 'e8373240cf0be47cc641f2c8627e674064d8c47f4ff2a11f6a33fcbfc9a50949'}
    if digest(raw / 'thailand.osm.pbf') != expected_pbf:
        raise ValueError('PBF does not match authorized frozen snapshot')
    if source['timestamp_osm_base'] != '2026-10-24T20:20:51Z':
        raise ValueError('Unexpected OSM replication timestamp')
    revisions = {}
    for name in API:
        payload = json.loads((raw / f'{name}.json').read_text())
        entries = {}
        for key, row in payload.get('entities', payload.get('pages', {})).items():
            if key == '_normalized':
                continue
            if 'wikidata' in name:
                entries[key] = {'revision_id': row['lastrevid'], 'timestamp': row['modified']}
            else:
                revision = row['revisions'][0]
                info = row['imageinfo'][0]
                entries[key] = {'title': row['title'], 'revision_id': revision['revid'],
                                'timestamp': revision['timestamp'], 'image_timestamp': info['timestamp'],
                                'image_sha1': info['sha1']}
        revisions[f'{name}.json'] = {'fetched_at': payload['_fetched_at'], 'records': entries}
    con = duckdb.connect()
    parquet = str(raw / 'overture_places.parquet')
    licenses = con.execute('SELECT dataset, license, count(*) FROM read_parquet(?) GROUP BY ALL ORDER BY 1', [parquet]).fetchall()
    return {
        'schema_version': 1, 'build_date': build_date,
        'base_commit': 'd7e2ddf5c5d906e155e0f310015f45441360fa06',
        'files': {p: digest(root / p) for p in sorted(required_files(root))},
        'geofabrik': source,
        'overture': {'release': '2026-09-23.1', 'path': 'data/bangkok/raw/overture_places.parquet',
                     'acquisition': json.loads((raw / 'overture-source.json').read_text()),
                     'rows': sum(row[2] for row in licenses),
                     'source_licenses': [{'dataset': ds, 'license': lic, 'rows': n} for ds, lic, n in licenses],
                     'attribution': 'Overture Maps Foundation; Meta, Microsoft, PinMeTo, DAC (CDLA-Permissive-2.0); Foursquare (Apache-2.0); AllThePlaces (CC0-1.0)',
                     'license_review': 'research/bangkok/notes/2026-10-26-frozen-refresh.md'},
        'wikimedia': {'mode': 'live API acquisition; exact payload hashes and response revision IDs frozen, not revision-pinned HTTP replay',
                      'limitation': 'Commons extmetadata can include transcluded templates; a page revision alone cannot reproduce it. Retain the hashed raw payloads for exact rebuilds. Thumbnail bytes are not vendored.',
                      'payloads': revisions},
        'retained_enrichments': json.loads((root / 'data/bangkok/enrichments-baseline.json').read_text())['_meta'],
        'retained_population': json.loads((root / 'data/bangkok/population-source.json').read_text()),
        'retained_flood': {'cache': 'data/bangkok/raw/thaifloodrisk.zip', 'license': 'CC-BY-4.0',
                           'doi': '10.5281/zenodo.23260465', 'build_reads': 'data/bangkok/flood.json'},
        'environment': {'duckdb': duckdb.__version__},
    }
