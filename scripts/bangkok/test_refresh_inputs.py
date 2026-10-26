"""Offline provenance checks; raw downloads are deliberately absent in CI."""
import json
from pathlib import Path

import pytest

from refresh_inputs import digest, verify_inputs

ROOT = Path(__file__).resolve().parents[2]


def test_committed_frozen_input_manifest():
    doc = json.loads((ROOT / 'data/bangkok/refresh-inputs.json').read_text())
    baseline = json.loads((ROOT / 'data/bangkok/population-baseline-refresh-2026-10-24.json').read_text())
    assert baseline['_meta']['inputs_manifest_sha256'] == digest(ROOT / 'data/bangkok/refresh-inputs.json')['sha256']
    pbf = doc['files']['data/bangkok/raw/thailand.osm.pbf']
    assert pbf == dict(bytes=329280467, sha256='e8373240cf0be47cc641f2c8627e674064d8c47f4ff2a11f6a33fcbfc9a50949')
    assert doc['geofabrik']['requested_url'].endswith('thailand-261024.osm.pbf')
    assert doc['geofabrik']['timestamp_osm_base'] == '2026-10-24T20:20:51Z'
    assert doc['overture']['release'] == '2026-09-23.1'
    assert doc['overture']['rows'] == 309704
    assert {r['license'] for r in doc['overture']['acquisition']['source_entry_licenses']} == {'CDLA-Permissive-2.0', 'Apache-2.0', 'CC0-1.0'}
    for name, count in [('wikidata.json', 50), ('commons.json', 50),
                        ('station_wikidata.json', 232), ('station_commons.json', 215)]:
        payload = doc['wikimedia']['payloads'][name]
        assert len(payload['records']) == count
        assert all(row['revision_id'] > 0 and row['timestamp'].endswith('Z') for row in payload['records'].values())
        assert doc['files']['data/bangkok/raw/' + name]['bytes'] > 0
    for name, expected in [('tha_ppp_2020_constrained.tif', '400dc5435e15e78ce6b5e510327ec863c62d209011ce1b03cad4445773753d42'),
                           ('thaifloodrisk.zip', '8ce4a1c95771f56204d979dafcb61df44f4f2aee4e19fbf40adc75ebbb8b8ddf')]:
        assert doc['files']['data/bangkok/raw/' + name]['sha256'] == expected
    # Every distributable build input (including notices) is available offline.
    for name, expected in doc['files'].items():
        if '/raw/' not in name:
            assert digest(ROOT / name) == expected


def test_input_drift_or_missing_file_is_rejected_before_build(tmp_path, monkeypatch):
    import refresh_inputs
    source = tmp_path / 'source.json'
    source.write_text('{}')
    manifest = tmp_path / 'manifest.json'
    doc = {'schema_version': 1, 'files': {'source.json': digest(source)}}
    manifest.write_text(json.dumps(doc))
    monkeypatch.setattr(refresh_inputs, 'required_files', lambda root: {'source.json'})
    assert verify_inputs(tmp_path, manifest) == doc
    source.write_text('{"changed": true}')
    with pytest.raises(ValueError, match='Frozen input mismatch'):
        verify_inputs(tmp_path, manifest)
    source.unlink()
    with pytest.raises(FileNotFoundError):
        verify_inputs(tmp_path, manifest)


def test_cross_city_outputs_only_change_authorized_bangkok_provenance_hashes():
    import hashlib
    frozen = json.loads((ROOT / 'scripts/fixtures/bangkok-population/provenance-only.json').read_text())
    allowed = set(frozen['allowed_input_paths'])
    def exclude_authorized_hashes(doc):
        if isinstance(doc, dict):
            for key, value in doc.items():
                if key == 'input_sha256':
                    for path in allowed:
                        if path in value:
                            value[path] = '<authorized Bangkok provenance hash>'
                elif key == 'inputs' and isinstance(value, list):
                    for row in value:
                        if row.get('path') in allowed:
                            row['sha256'] = '<authorized Bangkok provenance hash>'
                else:
                    exclude_authorized_hashes(value)
        elif isinstance(doc, list):
            for value in doc:
                exclude_authorized_hashes(value)
    for name, expected in frozen['files'].items():
        doc = json.loads((ROOT / name).read_text())
        exclude_authorized_hashes(doc)
        actual = hashlib.sha256(json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert actual == expected['excluding_allowed_hash_fields_sha256'], name
