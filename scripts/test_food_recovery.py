"""Offline regressions for the explicitly gated cache-only recovery adapter."""
import hashlib
import json
import copy
from pathlib import Path

import pytest
from types import SimpleNamespace

from food_pilot import recovery
from food_pilot.acquire_osm import encoded
from food_pilot.bounded import AcquisitionStopped
from food_pilot.run import overture_metadata_input


STARTED = '2026-10-16T11:37:07.610699+00:00'
FINISHED = '2026-10-16T11:38:01.834534+00:00'
DEADLINE = '2026-10-16T11:47:07.610699+00:00'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(tmp_path, monkeypatch):
    phase = tmp_path / 'target-v4' / 'overture_metadata'
    phase.mkdir(parents=True)
    (phase / '.reader.lock').touch()
    urls = [f'https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/r/part-{i}.parquet'
            for i in range(16)]
    source = {'state': 'frozen', 'overture': {'release': 'r', 'objects': urls},
              'budgets': {'overture_metadata': {'attempts': 80, 'retained_bytes': 64 * 1024 * 1024,
                  'wall_seconds': 600, 'response_body_bytes': 64 * 1024 * 1024}},
              'source_window': {'core_hp_complete_before': '2026-10-22T00:00:00Z'}}
    source_path = tmp_path / 'source-v4.json'
    source_raw = encoded(source)
    source_path.write_bytes(source_raw)
    downstream = {'state': 'frozen', 'supersedes_manifest_sha256': recovery.V8_MANIFEST_SHA256,
                  'supersession_reason': 'reviewed code-only child fixture', 'budgets': source['budgets'],
                  'source_window': source['source_window'], 'code_sha256': {}}
    root = Path(__file__).resolve().parents[1]
    downstream['code_sha256'] = {
        str(p.relative_to(root)): sha(p.read_bytes())
        for p in sorted((root / 'scripts' / 'food_pilot').glob('*.py'))
    }
    downstream_path = tmp_path / 'downstream-v8.json'
    downstream_raw = encoded(downstream)
    downstream_path.write_bytes(downstream_raw)
    contract = {key: value for key, value in downstream.items()
                if key not in {'code_sha256', 'supersedes_manifest_sha256', 'supersession_reason'}}
    monkeypatch.setattr(recovery, 'V8_NONCODE_CONTRACT_SHA256', recovery.canonical_sha(contract))

    attempts, objects = [], []
    for i in range(33):
        name = f'response-{i + 1:05d}.json'
        raw = encoded({'body_b64': f'fixture-{i}'})
        (phase / name).write_bytes(raw)
        identity = f'fixture:{i}'
        attempts.append({'identity': identity, 'status': 'complete', 'cache': name,
                         'cache_sha256': sha(raw), 'response_sha256': sha(identity.encode())})
    for i, url in enumerate(urls):
        attempt = attempts[i + 1]
        ref = {'identity': attempt['identity'], 'cache': attempt['cache'],
               'cache_sha256': attempt['cache_sha256'], 'response_sha256': attempt['response_sha256']}
        objects.append({'url': url, 'etag': f'etag-{i}', 'size': 1000,
                        'footer_ref': ref,
                        'groups': [{'index': g, 'rows': 1, 'bounds': [None] * 4}
                                   for g in range(304)]})
    ledger = {'manifest_sha256': sha(source_raw), 'limits': source['budgets']['overture_metadata'],
              'started_at': STARTED, 'finished_at': FINISHED, 'status': 'incomplete',
              'attempts': attempts, 'charged_bytes': 30_147_627, 'row_groups': []}
    ledger_raw = encoded(ledger)
    (phase / 'ledger.json').write_bytes(ledger_raw)
    result = {'release': 'r', 'objects': objects, 'complete': True}
    diagnostic = {'artifact_type': 'offline_lossless_metadata_derivative',
        'phase_completion_claim': False, 'source_phase_status': 'incomplete',
        'source_ledger_sha256': sha(ledger_raw), 'source_phase_started_at': STARTED,
        'source_phase_finished_at': FINISHED, 'source_phase_original_deadline': DEADLINE,
        'source_attempts': 33, 'source_charged_response_body_bytes': 30_147_627,
        'result': result}
    diagnostic_path = phase / recovery.SOURCE_DIAGNOSTIC_NAME
    diagnostic_raw = encoded(diagnostic)
    diagnostic_path.write_bytes(diagnostic_raw)

    monkeypatch.setattr(recovery, 'SOURCE_PHASE_DIR', phase)
    monkeypatch.setattr(recovery, 'SOURCE_V4_MANIFEST_SHA256', sha(source_raw))
    monkeypatch.setattr(recovery, 'SOURCE_V4_LEDGER_SHA256', sha(ledger_raw))
    monkeypatch.setattr(recovery, 'SOURCE_DIAGNOSTIC_SHA256', sha(diagnostic_raw))

    def offline_metadata(manifest, budget):
        # Exercise the same ledger lookup and response hash checks as ReplayBudget
        # while keeping the fixture independent of parquet/provider libraries.
        for record in budget.ledger['attempts']:
            raw = (budget.directory / record['cache']).read_bytes()
            if sha(raw) != record['cache_sha256']:
                raise AcquisitionStopped('cached_response_hash')
        for obj in result['objects']:
            budget.resolve_reference(obj['footer_ref'])
        return result
    monkeypatch.setattr(recovery, 'metadata', offline_metadata)

    bindings = recovery._bindings(source_manifest=source, source_manifest_sha=sha(source_raw),
        ledger=ledger, ledger_sha=sha(ledger_raw), diagnostic=diagnostic,
        diagnostic_sha=sha(diagnostic_raw), downstream_manifest=downstream,
        downstream_manifest_sha=sha(downstream_raw), phase_dir=phase)
    owner = {'receipt_type': recovery.OWNER_EXCEPTION_TYPE,
        'decision': 'allow_cache_only_metadata_downstream_admission', 'owner_exception_id': 'test-only',
        'recorded_at_utc': '2026-10-16T12:00:00Z', 'scope': [recovery.DOWNSTREAM_PHASE],
        'metadata_requests_permitted': False, 'source_phase_completion_permitted': False, **bindings}
    owner_path = tmp_path / 'mock-owner.json'
    owner_raw = encoded(owner); owner_path.write_bytes(owner_raw)
    root_receipt = {'receipt_type': recovery.ROOT_RELEASE_TYPE, 'operation': 'write_cache_only_admission_receipt',
        'root_release_id': 'test-only-root', 'released_at_utc': '2026-10-16T12:01:00Z',
        'owner_exception_sha256': sha(owner_raw), 'metadata_requests_permitted': False,
        'source_phase_completion_permitted': False, 'downstream_phase_execution_permitted': False,
        **bindings}
    root_path = tmp_path / 'mock-root.json'; root_path.write_bytes(encoded(root_receipt))
    return {'phase': phase, 'source': source, 'source_path': source_path,
        'downstream': downstream, 'downstream_path': downstream_path,
        'diagnostic_path': diagnostic_path, 'owner_path': owner_path, 'root_path': root_path,
        'ledger_before': ledger_raw, 'result': result}


def test_pinned_v5_v18_chain_and_only_reviewed_direct_successors_are_accepted(monkeypatch):
    chain = {
        recovery.V5_MANIFEST_SHA256: recovery.SOURCE_V4_MANIFEST_SHA256,
        recovery.V6_MANIFEST_SHA256: recovery.V5_MANIFEST_SHA256,
        recovery.V7_MANIFEST_SHA256: recovery.V6_MANIFEST_SHA256,
        recovery.V8_MANIFEST_SHA256: recovery.V7_MANIFEST_SHA256,
        recovery.V9_MANIFEST_SHA256: recovery.V8_MANIFEST_SHA256,
        recovery.V10_MANIFEST_SHA256: recovery.V9_MANIFEST_SHA256,
        recovery.V11_MANIFEST_SHA256: recovery.V10_MANIFEST_SHA256,
        recovery.V12_MANIFEST_SHA256: recovery.V11_MANIFEST_SHA256,
        recovery.V13_MANIFEST_SHA256: recovery.V12_MANIFEST_SHA256,
        recovery.V14_MANIFEST_SHA256: recovery.V13_MANIFEST_SHA256,
        recovery.V15_MANIFEST_SHA256: recovery.V14_MANIFEST_SHA256,
        recovery.V16_MANIFEST_SHA256: recovery.V15_MANIFEST_SHA256,
        recovery.V17_MANIFEST_SHA256: recovery.V16_MANIFEST_SHA256,
        recovery.V18_MANIFEST_SHA256: recovery.V17_MANIFEST_SHA256,
    }
    for manifest_sha, parent_sha in chain.items():
        assert recovery._check_successor_lineage(
            {'supersedes_manifest_sha256': parent_sha}, manifest_sha) is None

    # The next code-only manifest is eligible only as a direct child of v8;
    # its exact hash is additionally bound by the new owner/root receipts.
    contract = {'state': 'frozen', 'budgets': {'total_retained_bytes': 2048}}
    monkeypatch.setattr(recovery, 'V8_NONCODE_CONTRACT_SHA256', recovery.canonical_sha(contract))
    assert recovery._check_successor_lineage(
        {**contract, 'supersedes_manifest_sha256': recovery.V8_MANIFEST_SHA256}, 'new-v9-hash') is None


def test_v18_child_requires_exact_handoff_and_unchanged_noncode_contract(monkeypatch):
    from food_pilot import historical_handoff

    v18_contract = {'state': 'frozen', 'budgets': {'metadata': 64},
                    'source_window': {'cutoff': '2026-10-22T00:00:00Z'}}
    monkeypatch.setattr(recovery, 'V18_NONCODE_CONTRACT_SHA256', recovery.canonical_sha(v18_contract))
    handoff = {'state': 'historical_development_evidence_only', 'run_id': 'fixture'}
    monkeypatch.setattr(historical_handoff, 'EXPECTED_HANDOFF_CONTRACT_SHA256',
                        historical_handoff.canonical_sha(handoff))
    child = {**v18_contract, 'version': 'v19', 'code_sha256': {'runtime.py': 'fixed'},
             'supersedes_manifest_sha256': recovery.V18_MANIFEST_SHA256,
             'supersession_reason': 'bind historical HP development evidence',
             'historical_supplemental_hp_run': handoff}
    assert recovery._check_successor_lineage(child, 'new-v19-hash') is None

    changed_contract = {**child, 'budgets': {'metadata': 65}}
    with pytest.raises(AcquisitionStopped, match='recovery_manifest_noncode_contract_changed'):
        recovery._check_successor_lineage(changed_contract, 'new-v19-hash')

    changed_handoff = {**child, 'historical_supplemental_hp_run': {**handoff, 'run_id': 'other'}}
    with pytest.raises(AcquisitionStopped, match='recovery_historical_hp_handoff_contract_changed'):
        recovery._check_successor_lineage(changed_handoff, 'new-v19-hash')

    skipped = {**child, 'supersedes_manifest_sha256': recovery.V17_MANIFEST_SHA256}
    with pytest.raises(AcquisitionStopped, match='recovery_manifest_lineage_mismatch'):
        recovery._check_successor_lineage(skipped, 'new-v19-hash')


@pytest.mark.parametrize(('manifest_sha', 'parent_sha'), [
    (recovery.V7_MANIFEST_SHA256, recovery.V5_MANIFEST_SHA256),
    ('new-v9-hash', recovery.V7_MANIFEST_SHA256),
    ('unknown-manifest-hash', recovery.V5_MANIFEST_SHA256),
])
def test_broken_or_skipped_successor_lineage_is_rejected(manifest_sha, parent_sha):
    with pytest.raises(AcquisitionStopped, match='recovery_manifest_lineage_mismatch'):
        recovery._check_successor_lineage({'supersedes_manifest_sha256': parent_sha}, manifest_sha)


@pytest.mark.parametrize('field', ['budgets', 'source_window'])
def test_v9_successor_cannot_change_frozen_budget_or_source_window(tmp_path, monkeypatch, field):
    f = fixture(tmp_path, monkeypatch)
    downstream = copy.deepcopy(f['downstream'])
    if field == 'budgets':
        downstream['budgets']['overture_metadata']['attempts'] += 1
    else:
        downstream['source_window']['core_hp_complete_before'] = '2026-10-23T00:00:00Z'
    source_raw = f['source_path'].read_bytes()
    ledger_raw = (f['phase'] / 'ledger.json').read_bytes()
    diagnostic_raw = f['diagnostic_path'].read_bytes()
    with pytest.raises(AcquisitionStopped, match='recovery_manifest_noncode_contract_changed'):
        recovery._bindings(source_manifest=f['source'], source_manifest_sha=sha(source_raw),
            ledger=json.loads(ledger_raw), ledger_sha=sha(ledger_raw),
            diagnostic=json.loads(diagnostic_raw), diagnostic_sha=sha(diagnostic_raw),
        downstream_manifest=downstream, downstream_manifest_sha='new-v9-hash', phase_dir=f['phase'])


def test_explicit_cache_only_admission_is_distinct_and_ledger_stays_incomplete(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    output, digest = recovery.make_admission(source_manifest_path=f['source_path'],
        downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
        diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
        root_release_path=f['root_path'])
    receipt = json.loads(output.read_bytes())
    assert receipt['state'] == 'downstream_admitted_cache_only'
    assert receipt['phase_completion_claim'] is False
    assert receipt['metadata_requests_performed'] == 0
    assert output.name == f'cache-only-admission-{digest}.json'
    assert (f['phase'] / 'ledger.json').read_bytes() == f['ledger_before']
    assert json.loads((f['phase'] / 'ledger.json').read_bytes())['status'] == 'incomplete'
    loaded, _cache = recovery.load_admitted_metadata(admission_path=output,
        source_manifest_path=f['source_path'], downstream_manifest=f['downstream'],
        downstream_manifest_sha=sha(f['downstream_path'].read_bytes()),
        owner_exception_path=f['owner_path'], root_release_path=f['root_path'])
    assert loaded == f['result']


@pytest.mark.parametrize('missing', ['owner', 'root'])
def test_missing_owner_or_root_never_writes_admission(tmp_path, monkeypatch, missing):
    f = fixture(tmp_path, monkeypatch)
    f[f'{missing}_path'].unlink()
    with pytest.raises(AcquisitionStopped, match='invalid_owner_or_root_receipt'):
        recovery.make_admission(source_manifest_path=f['source_path'],
            downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
            diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
            root_release_path=f['root_path'])
    assert not list(f['phase'].glob('cache-only-admission-*.json'))


def test_modified_actual_cache_hash_blocks_admission(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    cache = f['phase'] / 'response-00008.json'
    cache.write_bytes(cache.read_bytes() + b'changed')
    with pytest.raises(AcquisitionStopped, match='cached_response_hash'):
        recovery.make_admission(source_manifest_path=f['source_path'],
            downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
            diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
            root_release_path=f['root_path'])
    assert not list(f['phase'].glob('cache-only-admission-*.json'))


def test_total_original_metadata_retention_includes_derivative_and_admission(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    # Sparse logical padding exercises the frozen cap without writing a 64 MiB blob.
    cap = f['source']['budgets']['overture_metadata']['retained_bytes']
    pad = f['phase'] / 'retention-boundary.bin'
    pad.touch()
    used = sum(p.stat().st_size for p in f['phase'].rglob('*') if p.is_file())
    with pad.open('r+b') as stream:
        stream.truncate(cap - used + 1)
    with pytest.raises(AcquisitionStopped, match='combined_metadata_retention_budget'):
        recovery.make_admission(source_manifest_path=f['source_path'],
            downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
            diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
            root_release_path=f['root_path'])
    assert not list(f['phase'].glob('cache-only-admission-*.json'))


def test_consumption_rechecks_combined_metadata_retention(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    output, _ = recovery.make_admission(source_manifest_path=f['source_path'],
        downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
        diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
        root_release_path=f['root_path'])
    cap = f['source']['budgets']['overture_metadata']['retained_bytes']
    pad = f['phase'] / 'post-admission-overflow.bin'
    pad.touch()
    used = sum(p.stat().st_size for p in f['phase'].rglob('*') if p.is_file())
    with pad.open('r+b') as stream:
        stream.truncate(cap - used + 1)
    with pytest.raises(AcquisitionStopped, match='combined_metadata_retention_budget'):
        recovery.load_admitted_metadata(admission_path=output,
            source_manifest_path=f['source_path'], downstream_manifest=f['downstream'],
            downstream_manifest_sha=sha(f['downstream_path'].read_bytes()),
            owner_exception_path=f['owner_path'], root_release_path=f['root_path'])


def test_tampered_admission_receipt_is_rejected(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    output, _ = recovery.make_admission(source_manifest_path=f['source_path'],
        downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
        diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
        root_release_path=f['root_path'])
    receipt = json.loads(output.read_bytes())
    receipt['phase_completion_claim'] = True
    output.write_bytes(encoded(receipt))
    with pytest.raises(AcquisitionStopped, match='invalid_cache_only_admission_hash'):
        recovery.load_admitted_metadata(admission_path=output,
            source_manifest_path=f['source_path'], downstream_manifest=f['downstream'],
            downstream_manifest_sha=sha(f['downstream_path'].read_bytes()),
            owner_exception_path=f['owner_path'], root_release_path=f['root_path'])


def test_historical_v6_admission_cannot_authorize_a_new_current_manifest(tmp_path, monkeypatch):
    phase = tmp_path / 'target-v4' / 'overture_metadata'
    phase.mkdir(parents=True)
    monkeypatch.setattr(recovery, 'SOURCE_PHASE_DIR', phase)
    receipt = {'receipt_type': recovery.ADMISSION_TYPE, 'state': recovery.ADMISSION_STATE,
               'admission_is_not_phase_completion': True,
               'downstream_phase': recovery.DOWNSTREAM_PHASE,
               'downstream_manifest_sha256': recovery.V6_MANIFEST_SHA256}
    path = phase / 'historical-v6-admission.json'
    path.write_bytes(encoded(receipt))
    with pytest.raises(AcquisitionStopped, match='invalid_cache_only_admission'):
        recovery.load_admitted_metadata(admission_path=path,
            source_manifest_path=tmp_path / 'unused-v4.json', downstream_manifest={},
            downstream_manifest_sha='new-current-v19-manifest',
            owner_exception_path=tmp_path / 'old-owner.json',
            root_release_path=tmp_path / 'old-root.json')


def test_runner_cache_only_path_is_opt_in_and_phase_scoped(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    base = {'phase': 'overture_development', 'cache_only_admission': None,
            'cache_only_source_manifest': None, 'cache_only_owner_exception': None,
            'cache_only_root_release': None, 'overture_metadata': None}
    with pytest.raises(AcquisitionStopped, match='missing_pinned_metadata'):
        overture_metadata_input(SimpleNamespace(**base), f['downstream'],
                                sha(f['downstream_path'].read_bytes()))
    recovery_args = {**base, 'cache_only_admission': f['phase'] / 'absent.json',
        'cache_only_source_manifest': f['source_path'],
        'cache_only_owner_exception': f['owner_path'], 'cache_only_root_release': f['root_path']}
    with pytest.raises(AcquisitionStopped, match='invalid_cache_only_admission'):
        overture_metadata_input(SimpleNamespace(**recovery_args), f['downstream'],
                                sha(f['downstream_path'].read_bytes()))
    recovery_args['phase'] = 'hp_development'
    with pytest.raises(AcquisitionStopped, match='invalid_cache_only_recovery_scope'):
        overture_metadata_input(SimpleNamespace(**recovery_args), f['downstream'],
                                sha(f['downstream_path'].read_bytes()))
