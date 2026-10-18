"""Offline tests for the read-only completed-development handoff."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from food_pilot import historical_handoff as handoff
from food_pilot import supplemental
from food_pilot.acquire_osm import encoded
from food_pilot.bounded import AcquisitionStopped
from food_pilot.supplemental import development_fingerprints


V18 = handoff.V18_MANIFEST_SHA256
RUN_ID = handoff.EXPECTED_RUN_ID
ACTIVATION_ID = handoff.EXPECTED_ACTIVATION_ID
T0 = datetime.fromisoformat('2026-10-17T22:00:00+00:00')
DEADLINE = T0 + timedelta(seconds=1800)


class Clock:
    def __init__(self):
        self.step = 0

    def now(self):
        return T0 + timedelta(seconds=self.step / 1000)

    def mono(self):
        return 1000 + self.step / 1000

    def tick(self):
        self.step += 1


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(tmp_path, monkeypatch):
    artifact_root = tmp_path / 'artifacts'
    run_dir = artifact_root / 'supplemental-hp-v18-001'
    auth_dir = artifact_root / 'supplemental-hp-v18-001-authorizations'
    artifact_root.mkdir()
    auth_dir.mkdir()
    target_root = artifact_root / 'target-v4'
    evidence_paths = {
        'diagnostic_outcome': 'hp_development/hp-diagnostic-outcome-v1.json',
        'diagnostic_reservation': 'hp_development/hp-diagnostic-reservation-v1.json',
        'hp_ledger': 'hp_development/ledger.json',
        'hp_result': 'hp_development/result-original.json',
    }
    evidence_hashes = {}
    for key, relative in evidence_paths.items():
        path = target_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = f'fixture-{key}'.encode()
        path.write_bytes(raw)
        evidence_hashes[key] = digest(raw)
    monkeypatch.setattr(supplemental, 'EXPECTED_EVIDENCE', evidence_hashes)
    (target_root / 'overture_metadata').mkdir(parents=True)
    (target_root / 'overture_metadata' / '.reader.lock').write_bytes(b'')
    for relative in (
        'hp_development/diagnostic-authorization-provenance.json',
        'hp_development/hp-diagnostic-outcome-v1.json',
        'hp_development/hp-diagnostic-reservation-v1.json',
        'hp_development/owner-diagnostic-exception.json',
        'hp_development/root-diagnostic-gate.json',
    ):
        path = target_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(b'fixture-receipt')
    target_tree_sha, target_bytes, target_count = supplemental.tree_digest(target_root)
    subset_sha, _, subset_count = supplemental.tree_digest(target_root,
        excluded=supplemental.PRE_RECEIPT_EXCLUSIONS)
    monkeypatch.setattr(handoff, 'TARGET_V4_TREE_SHA256', target_tree_sha)
    monkeypatch.setattr(handoff, 'PRE_RECEIPT_TREE_SHA256', subset_sha)
    stations = [{'slug': f'site-{index:02d}', 'lat': f'{35.0 + index/1000:.6f}',
                 'lng': f'{139.0 + index/1000:.6f}', 'split': 'development'}
                for index in range(32)]
    manifest = {'core': {'stations': stations}, 'supplemental_hp_development': {
        'protocol_sha256': 'protocol', 'decision_sha256': 'decision',
        'original_evidence_sha256': evidence_hashes,
        'original_evidence_paths': evidence_paths,
        'target_v4_tree_sha256': target_tree_sha,
        'pre_receipt_tree_sha256': subset_sha,
        'target_v4_file_count': target_count,
        'pre_receipt_file_count': subset_count,
        'budget_snapshot': {'attempts_used': 2}}}
    sample_sha, query_sha, ordered = development_fingerprints(manifest)
    manifest['supplemental_hp_development'].update(
        development_sample_sha256=sample_sha, query_fingerprint_sha256=query_sha)

    received_at = []
    rows = []
    for index, station in enumerate(ordered):
        stamp = (T0 + timedelta(milliseconds=5 + index / 10)).isoformat()
        zero = index < 5
        params = {'lat': station['lat'], 'lng': station['lng'], 'range': 3,
                  'count': 100, 'start': 1, 'format': 'json', 'order': 1}
        query = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        if index == 0:
            monkeypatch.setattr(supplemental, 'EXCEPTIONAL_IDENTITY',
                                f"hp:{station['slug']}:1:{query}")
        page = {'start': 1, 'results_start': 0 if zero else 1, 'returned': 0 if zero else 1,
                'query_sha256': query, 'received_at': stamp}
        received_at.append(stamp)
        rows.append({'slug': station['slug'],
                     'status': 'complete_provider_zero' if zero else 'complete_positive',
                     'results_available_1000m': 0 if zero else 1,
                     'unique_fetched': 0 if zero else 1,
                     'count_800m': 0 if zero else 1,
                     'first_received_at': stamp, 'finished_at': stamp, 'pages': [page]})
    envelope = {'phase': 'supplemental_hp_development', 'manifest_sha256': V18,
                'activation_id': ACTIVATION_ID, 'run_id': RUN_ID,
                'started_at': T0.isoformat(), 'deadline': DEADLINE.isoformat(),
                'result': {'status': 'complete', 'stations': rows}}
    result_raw = encoded(envelope)
    result_name = 'result-fixture.json'

    owner = {'kind': 'owner_supplemental_hp_activation', 'activation_id': ACTIVATION_ID,
        'run_id': RUN_ID, 'manifest_sha256': V18, 'git_head': handoff.V18_HEAD,
        'code_map_sha256': handoff.V18_CODE_MAP_SHA256, 'sample_sha256': sample_sha,
        'query_fingerprint_sha256': query_sha, 'protocol_sha256': 'protocol',
        'decision_sha256': 'decision', 'evidence_sha256': evidence_hashes,
        'allowed_operation': 'supplemental_hp_development',
        'target_root': str(target_root.resolve()), 'supplemental_root': str(run_dir.resolve()),
        'accounted_roots': [str(target_root.resolve()), str(run_dir.resolve())],
        'budget_snapshot': {'attempts_used': 2}, 'single_use': True}
    owner_raw = encoded(owner)
    owner_name = 'owner-activation.json'
    (auth_dir / owner_name).write_bytes(owner_raw)
    owner_sha = digest(owner_raw)
    root_release = {'kind': 'root_supplemental_hp_release', 'activation_id': ACTIVATION_ID,
        'run_id': RUN_ID, 'manifest_sha256': V18, 'git_head': handoff.V18_HEAD,
        'code_map_sha256': handoff.V18_CODE_MAP_SHA256, 'sample_sha256': sample_sha,
        'query_fingerprint_sha256': query_sha, 'protocol_sha256': 'protocol',
        'decision_sha256': 'decision', 'evidence_sha256': evidence_hashes,
        'allowed_operation': 'supplemental_hp_development',
        'target_root': str(target_root.resolve()), 'supplemental_root': str(run_dir.resolve()),
        'accounted_roots': [str(target_root.resolve()), str(run_dir.resolve())],
        'budget_snapshot': {'attempts_used': 2}, 'single_use': True,
        'owner_activation_sha256': owner_sha, 'root_manifest_check': True,
        'native_review_approved_head': handoff.V18_HEAD,
        'downstream_phase_execution_permitted': False}
    root_raw = encoded(root_release)
    root_name = 'root-release.json'
    (auth_dir / root_name).write_bytes(root_raw)
    root_sha = digest(root_raw)

    clock = Clock()
    journal = supplemental.Journal(run_dir, resume=False, now=clock.now,
        monotonic=clock.mono, start_utc=T0, start_mono=1000,
        start_fields={'activation_claim_state': 'pending'})
    (run_dir / result_name).write_bytes(result_raw)
    owner_sha, root_sha = digest(owner_raw), digest(root_raw)
    clock.tick()
    journal.append('activation_preflight_started', {
        'owner_activation_sha256': owner_sha, 'root_release_sha256': root_sha})
    clock.tick()
    claim = {'activation_id': ACTIVATION_ID, 'run_id': RUN_ID,
             'owner_activation_sha256': owner_sha, 'root_release_sha256': root_sha}
    journal.append('activation_consumed', claim)
    clock.tick()
    journal.append('activation_claim_ready', claim)
    clock.tick()
    journal.append('activation_bound', {**claim, 'manifest_sha256': V18,
        'git_head': handoff.V18_HEAD, 'code_map_sha256': handoff.V18_CODE_MAP_SHA256})
    for index, row in enumerate(rows):
        clock.tick()
        identity = f"hp:{row['slug']}:1:{row['pages'][0]['query_sha256']}"
        attempt_id = f'fixture-{index:02d}'
        slot_id = f'fixture-slot-{index:02d}'
        journal.append('attempt_reserved', {'attempt_id': attempt_id, 'identity': identity,
            'reserved_body_bytes': 1024, 'retry_disposition': 'none'})
        clock.tick()
        journal.append('response_complete', {'attempt_id': attempt_id, 'identity': identity,
            'eof': True, 'observed_body_bytes': 10})
        clock.tick()
        journal.append('attempt_settled', {'attempt_id': attempt_id, 'identity': identity,
            'status': 'complete', 'charged_body_bytes': 10, 'retry_disposition': 'none'})
        clock.tick()
        journal.append('page_slot_reserved', {'identity': identity, 'slot_id': slot_id,
            'slot_state': 'pending'})
        clock.tick()
        journal.append('page_slot_admitted', {'identity': identity, 'slot_id': slot_id,
            'slot_state': 'admitted'})
    clock.tick()
    finalized_at = clock.now().isoformat()
    journal.append('run_finalized', {'status': 'complete', 'result': result_name,
        'result_sha256': digest(result_raw)})
    journal_raw = (run_dir / 'journal.jsonl').read_bytes()
    journal_sha = digest(journal_raw)
    windows = handoff.informational_zero_windows(rows, [s['slug'] for s in ordered])
    run_retained = supplemental.file_size(run_dir)
    authorization_retained = supplemental.file_size(auth_dir)
    hp_retained = supplemental.file_size(target_root / 'hp_development') + run_retained + authorization_retained
    global_retained = target_bytes + run_retained + authorization_retained
    contract = {
        'state': 'historical_development_evidence_only',
        'phase_execution_authorized': False,
        'confirmation_phase_eligible': False,
        'source_manifest_sha256': V18, 'source_git_head': handoff.V18_HEAD,
        'source_code_map_sha256': handoff.V18_CODE_MAP_SHA256,
        'run_id': RUN_ID, 'activation_id': ACTIVATION_ID,
        'owner_activation_sha256': owner_sha, 'root_release_sha256': root_sha,
        'sample_sha256': sample_sha, 'query_fingerprint_sha256': query_sha,
        'protocol_sha256': 'protocol', 'decision_sha256': 'decision',
        'target_v4_tree_sha256': target_tree_sha,
        'pre_receipt_tree_sha256': subset_sha,
        'target_v4_file_count': target_count,
        'pre_receipt_file_count': subset_count,
        'run_directory': 'supplemental-hp-v18-001',
        'authorization_directory': 'supplemental-hp-v18-001-authorizations',
        'owner_file': owner_name, 'root_file': root_name,
        'journal_file': 'journal.jsonl', 'result_file': result_name,
        'journal_sha256': journal_sha, 'result_sha256': digest(result_raw),
        'started_at': T0.isoformat(), 'deadline': DEADLINE.isoformat(),
        'finalized_at': finalized_at, 'source_cutoff': handoff.SOURCE_CUTOFF,
        'status': 'complete', 'station_count': len(rows), 'attempt_count': len(rows),
        'page_count': len(rows),
        'station_status_counts': {'complete_provider_zero': 5, 'complete_positive': 27},
        'settled_count': len(rows), 'unknown_count': 0,
        'complete_response_count': len(rows), 'admitted_page_slots': len(rows),
        'body_bytes': 10 * len(rows), 'informational_confirmation_windows': windows,
        'historically_admitted_pages': 0, 'held_diagnostic_page_slots': 1,
        'cumulative_attempts': 2 + len(rows), 'cumulative_body_bytes': 214 + 10 * len(rows),
        'occupied_page_slots': len(rows) + 1, 'page_slot_limit': 320,
        'attempt_limit': 400, 'body_byte_limit': 134217728,
        'run_retained_bytes': run_retained,
        'authorization_retained_bytes': authorization_retained,
        'hp_retained_bytes': hp_retained, 'global_retained_bytes': global_retained,
    }
    monkeypatch.setattr(handoff, 'EXPECTED_HANDOFF_CONTRACT_SHA256',
                        handoff.canonical_sha(contract))
    manifest['historical_supplemental_hp_run'] = contract
    return artifact_root, manifest, contract


def test_completed_run_is_verified_as_historical_dev_input_with_informational_windows(tmp_path, monkeypatch):
    artifact_root, manifest, contract = fixture(tmp_path, monkeypatch)
    verified = handoff.verify_historical_supplemental_run(manifest, artifact_root=artifact_root)
    assert verified['state'] == 'verified_historical_development_input_only'
    assert verified['phase_execution_authorized'] is False
    assert verified['confirmation_phase_eligible'] is False
    assert verified['station_count'] == 32
    assert verified['attempt_count'] == verified['body_bytes'] // 10 == 32
    assert len(verified['informational_confirmation_windows']) == 5
    assert all(row['phase_eligible_under_current_policy'] is False
               for row in verified['informational_confirmation_windows'])


@pytest.mark.parametrize('file_name', ['result-fixture.json', 'journal.jsonl', 'owner-activation.json', 'root-release.json'])
def test_modified_historical_run_evidence_fails_closed(tmp_path, monkeypatch, file_name):
    artifact_root, manifest, _ = fixture(tmp_path, monkeypatch)
    base = artifact_root / ('supplemental-hp-v18-001-authorizations'
                            if file_name.endswith('activation.json') or file_name == 'root-release.json'
                            else 'supplemental-hp-v18-001')
    path = base / file_name
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(AcquisitionStopped, match='historical_handoff_file_hash_mismatch'):
        handoff.verify_historical_supplemental_run(manifest, artifact_root=artifact_root)


def test_modified_original_v4_tree_blocks_historical_handoff(tmp_path, monkeypatch):
    artifact_root, manifest, _ = fixture(tmp_path, monkeypatch)
    old_ledger = artifact_root / 'target-v4' / 'hp_development' / 'ledger.json'
    old_ledger.write_bytes(old_ledger.read_bytes() + b'changed')
    with pytest.raises(AcquisitionStopped, match='historical_handoff_source_tree_changed'):
        handoff.verify_historical_supplemental_run(manifest, artifact_root=artifact_root)


def test_confirmation_window_over_cutoff_is_not_emitted():
    row = {'slug': 'late-zero', 'status': 'complete_provider_zero',
           'finished_at': '2026-10-21T01:00:00Z'}
    with pytest.raises(AcquisitionStopped, match='confirmation_window_after_cutoff'):
        handoff.informational_zero_windows([row], ['late-zero'])
