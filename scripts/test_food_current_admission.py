"""Synthetic V20 create→load tests: source cache stays immutable, receipt is external."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from food_pilot import historical_handoff, recovery, run, supplemental
from food_pilot.acquire_osm import encoded
from food_pilot.bounded import AcquisitionStopped
from test_food_historical_handoff import fixture as historical_fixture


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def current_fixture(tmp_path, monkeypatch):
    artifact_root, downstream, _historical = historical_fixture(tmp_path, monkeypatch)
    target_root = artifact_root / 'target-v4'
    phase = target_root / 'overture_metadata'
    phase.mkdir(parents=True, exist_ok=True)
    (phase / '.reader.lock').write_bytes(b'')
    urls = [f'https://objects.example/release/r/part-{i}.parquet' for i in range(16)]
    metadata_budget = {'attempts': 80, 'retained_bytes': 64 * 1024**2,
                       'wall_seconds': 600, 'response_body_bytes': 64 * 1024**2}
    budgets = {'overture_metadata': metadata_budget,
        'overture_development': {'attempts': 2048, 'retained_bytes': 512 * 1024**2},
        'total_retained_bytes': 2 * 1024**3}
    source = {'state': 'frozen', 'overture': {'release': 'r', 'objects': urls},
              'budgets': budgets, 'source_window': {'core_hp_complete_before': '2026-10-22T00:00:00Z'}}
    source_path = artifact_root / 'amended-v1' / 'final-manifest-v4.json'
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_raw = encoded(source)
    source_path.write_bytes(source_raw)
    source_sha = sha(source_raw)

    attempts, objects = [], []
    for i in range(33):
        name = f'response-{i + 1:05d}.json'
        cache_raw = encoded({'body_b64': f'cache-fixture-{i}'})
        (phase / name).write_bytes(cache_raw)
        identity = f'fixture:{i}'
        attempts.append({'identity': identity, 'status': 'complete', 'cache': name,
            'cache_sha256': sha(cache_raw), 'response_sha256': sha(identity.encode())})
    for i, url in enumerate(urls):
        attempt = attempts[i + 1]
        footer = {'identity': attempt['identity'], 'cache': attempt['cache'],
            'cache_sha256': attempt['cache_sha256'], 'response_sha256': attempt['response_sha256']}
        objects.append({'url': url, 'etag': f'etag-{i}', 'size': 1000,
            'footer_ref': footer,
            'groups': [{'index': g, 'rows': 1, 'bounds': [None, None, None, None]}
                       for g in range(304)]})
    ledger = {'manifest_sha256': source_sha, 'limits': metadata_budget,
        'started_at': recovery.EXPECTED_STARTED_AT, 'finished_at': recovery.EXPECTED_FINISHED_AT,
        'status': 'incomplete', 'attempts': attempts,
        'charged_bytes': recovery.EXPECTED_CHARGED_BYTES, 'row_groups': []}
    ledger_raw = encoded(ledger)
    (phase / 'ledger.json').write_bytes(ledger_raw)
    result = {'release': 'r', 'objects': objects, 'complete': True}
    diagnostic = {'artifact_type': 'offline_lossless_metadata_derivative',
        'phase_completion_claim': False, 'source_phase_status': 'incomplete',
        'source_ledger_sha256': sha(ledger_raw), 'source_phase_started_at': ledger['started_at'],
        'source_phase_finished_at': ledger['finished_at'],
        'source_phase_original_deadline': recovery.EXPECTED_DEADLINE,
        'source_attempts': 33, 'source_charged_response_body_bytes': recovery.EXPECTED_CHARGED_BYTES,
        'result': result}
    diagnostic_path = phase / recovery.SOURCE_DIAGNOSTIC_NAME
    diagnostic_raw = encoded(diagnostic)
    diagnostic_path.write_bytes(diagnostic_raw)

    # These test-local pins represent a synthetic copy of V4; no real source file is changed.
    monkeypatch.setattr(recovery, 'SOURCE_PHASE_DIR', phase)
    monkeypatch.setattr(recovery, 'SOURCE_V4_MANIFEST_SHA256', source_sha)
    monkeypatch.setattr(recovery, 'SOURCE_V4_LEDGER_SHA256', sha(ledger_raw))
    monkeypatch.setattr(recovery, 'SOURCE_DIAGNOSTIC_SHA256', sha(diagnostic_raw))

    def offline_metadata(manifest, cache):
        for attempt in cache.ledger['attempts']:
            raw = (cache.directory / attempt['cache']).read_bytes()
            if sha(raw) != attempt['cache_sha256']:
                raise AcquisitionStopped('cached_response_hash')
        for item in result['objects']:
            cache.resolve_reference(item['footer_ref'])
        return result
    monkeypatch.setattr(recovery, 'metadata', offline_metadata)

    # Finalize the synthetic target-v4 fixture before binding it into the run handoff.
    tree_sha, target_bytes, file_count = supplemental.tree_digest(target_root)
    subset_sha, _subset_bytes, subset_count = supplemental.tree_digest(
        target_root, excluded=supplemental.PRE_RECEIPT_EXCLUSIONS)
    run_root = artifact_root / downstream['historical_supplemental_hp_run']['run_directory']
    auth_root = artifact_root / downstream['historical_supplemental_hp_run']['authorization_directory']
    run_bytes, auth_bytes = supplemental.file_size(run_root), supplemental.file_size(auth_root)
    hp_bytes = supplemental.file_size(target_root / 'hp_development') + run_bytes + auth_bytes
    global_bytes = target_bytes + run_bytes + auth_bytes
    hp_contract = downstream['supplemental_hp_development']
    hp_contract.update(target_v4_tree_sha256=tree_sha, pre_receipt_tree_sha256=subset_sha,
        target_v4_file_count=file_count, pre_receipt_file_count=subset_count,
        original_evidence_sha256=supplemental.EXPECTED_EVIDENCE)
    handoff = downstream['historical_supplemental_hp_run']
    handoff.update(target_v4_tree_sha256=tree_sha, pre_receipt_tree_sha256=subset_sha,
        target_v4_file_count=file_count, pre_receipt_file_count=subset_count)
    handoff.update(run_retained_bytes=run_bytes, authorization_retained_bytes=auth_bytes,
        hp_retained_bytes=hp_bytes, global_retained_bytes=global_bytes)
    handoff['metadata_source_phase'] = {
        'manifest_sha256': source_sha, 'ledger_sha256': sha(ledger_raw),
        'diagnostic_sha256': sha(diagnostic_raw), 'status': 'incomplete'}
    monkeypatch.setattr(historical_handoff, 'TARGET_V4_TREE_SHA256', tree_sha)
    monkeypatch.setattr(historical_handoff, 'PRE_RECEIPT_TREE_SHA256', subset_sha)
    monkeypatch.setattr(historical_handoff, 'EXPECTED_HANDOFF_CONTRACT_SHA256',
                        historical_handoff.canonical_sha(handoff))

    current_admission = {
        'schema_version': 1,
        'state': 'disabled_current_manifest_cache_admission_destination',
        'downstream_phase': recovery.DOWNSTREAM_PHASE,
        'source_manifest_sha256': source_sha,
        'source_ledger_sha256': sha(ledger_raw),
        'source_diagnostic_sha256': sha(diagnostic_raw),
        'historical_supplemental_hp_run_sha256': historical_handoff.canonical_sha(handoff),
        'protocol_sha256': 'synthetic-current-protocol',
        'decision_sha256': 'synthetic-governing-decision',
        'source_cache_directory': 'target-v4/overture_metadata',
        'admission_directory': 'v20-overture-metadata-admissions',
        'authorization_subdirectory': 'authorizations',
        'owner_file': 'owner-exception.json', 'root_file': 'root-release.json',
        'metadata_retention_limit': metadata_budget['retained_bytes'],
        'global_retention_limit': budgets['total_retained_bytes'],
        'baseline_metadata_source_bytes': supplemental.file_size(phase),
        'baseline_global_bytes': global_bytes,
        'metadata_retention_roots': ['target-v4/overture_metadata', 'v20-overture-metadata-admissions'],
        'global_retention_roots': ['target-v4', 'supplemental-hp-v18-001',
            'supplemental-hp-v18-001-authorizations', 'v20-overture-metadata-admissions'],
        'fresh_owner_root_required': True,
        'metadata_requests_permitted': False,
        'source_phase_completion_claim': False,
        'admission_is_not_phase_completion': True,
        'downstream_phase_execution_permitted': False,
    }
    downstream.update({'state': 'frozen', 'version': 'v20-test',
        'supersedes_manifest_sha256': recovery.V19_MANIFEST_SHA256,
        'supersession_reason': 'test external current-manifest admission root',
        'budgets': budgets, 'source_window': source['source_window'],
        'current_manifest_cache_admission': current_admission})
    downstream['code_sha256'] = {
        str(path.relative_to(recovery.Path(__file__).resolve().parents[1])): sha(path.read_bytes())
        for path in sorted((recovery.Path(__file__).resolve().parents[1] / 'scripts' / 'food_pilot').glob('*.py'))}
    base_noncode = {key: value for key, value in downstream.items()
        if key not in {'code_sha256', 'supersedes_manifest_sha256', 'supersession_reason',
                       'version', 'current_manifest_cache_admission'}}
    monkeypatch.setattr(recovery, 'V19_NONCODE_CONTRACT_SHA256', recovery.canonical_sha(base_noncode))
    monkeypatch.setattr(recovery, 'EXPECTED_CURRENT_ADMISSION_CONTRACT_SHA256',
                        recovery.canonical_sha(current_admission))
    downstream_path = artifact_root / 'amended-v1' / 'manifest-v20-test.json'
    downstream_path.write_bytes(encoded(downstream))
    admission_root = artifact_root / current_admission['admission_directory']
    authorization_root = admission_root / current_admission['authorization_subdirectory']
    authorization_root.mkdir(parents=True)
    return {'artifact_root': artifact_root, 'target_root': target_root,
        'phase': phase, 'source_manifest': source, 'source_path': source_path,
        'ledger': ledger, 'ledger_sha': sha(ledger_raw), 'ledger_raw': ledger_raw,
        'diagnostic': diagnostic, 'diagnostic_path': diagnostic_path,
        'downstream': downstream, 'downstream_path': downstream_path,
        'admission_root': admission_root, 'authorization_root': authorization_root,
        'owner_path': authorization_root / current_admission['owner_file'],
        'root_path': authorization_root / current_admission['root_file'],
        'current_contract': current_admission, 'metadata_result': result}


def bind_fresh_test_receipts(f):
    downstream_sha = sha(f['downstream_path'].read_bytes())
    bindings = recovery._bindings(source_manifest=f['source_manifest'],
        source_manifest_sha=sha(f['source_path'].read_bytes()),
        ledger=f['ledger'], ledger_sha=f['ledger_sha'], diagnostic=f['diagnostic'],
        diagnostic_sha=sha(f['diagnostic_path'].read_bytes()),
        downstream_manifest=f['downstream'], downstream_manifest_sha=downstream_sha,
        phase_dir=f['phase'], admission_root=f['admission_root'], require_admission_root=True)
    owner = {'receipt_type': recovery.OWNER_EXCEPTION_TYPE,
        'decision': 'allow_cache_only_metadata_downstream_admission',
        'owner_exception_id': 'synthetic-v20-owner', 'recorded_at_utc': '2026-10-18T00:00:00Z',
        'scope': [recovery.DOWNSTREAM_PHASE], 'metadata_requests_permitted': False,
        'source_phase_completion_permitted': False, **bindings}
    owner_raw = encoded(owner)
    f['owner_path'].write_bytes(owner_raw)
    root = {'receipt_type': recovery.ROOT_RELEASE_TYPE,
        'operation': 'write_cache_only_admission_receipt',
        'root_release_id': 'synthetic-v20-root', 'released_at_utc': '2026-10-18T00:01:00Z',
        'owner_exception_sha256': sha(owner_raw), 'metadata_requests_permitted': False,
        'source_phase_completion_permitted': False, 'downstream_phase_execution_permitted': False,
        **bindings}
    f['root_path'].write_bytes(encoded(root))
    return bindings


def test_v20_create_load_replays_v4_footer_from_external_admission_root(tmp_path, monkeypatch):
    f = current_fixture(tmp_path, monkeypatch)
    bind_fresh_test_receipts(f)
    usage = recovery._current_retention_usage(source_phase_dir=f['phase'],
        admission_root=f['admission_root'], downstream_manifest=f['downstream'],
        source_manifest=f['source_manifest'])
    assert usage['metadata_used'] == supplemental.file_size(f['phase']) + supplemental.file_size(f['admission_root'])
    assert usage['global_used'] == (supplemental.file_size(f['target_root'])
        + supplemental.file_size(f['artifact_root'] / 'supplemental-hp-v18-001')
        + supplemental.file_size(f['artifact_root'] / 'supplemental-hp-v18-001-authorizations')
        + supplemental.file_size(f['admission_root']))
    before = supplemental.tree_digest(f['target_root'])
    output, _digest = recovery.make_admission(
        source_manifest_path=f['source_path'], downstream_manifest_path=f['downstream_path'],
        phase_dir=f['phase'], diagnostic_path=f['diagnostic_path'],
        owner_exception_path=f['owner_path'], root_release_path=f['root_path'],
        admission_root=f['admission_root'])
    assert output.parent == f['admission_root']
    assert (f['phase'] / 'ledger.json').read_bytes() == f['ledger_raw']
    loaded, cache = recovery.load_admitted_metadata(
        admission_path=output, source_manifest_path=f['source_path'],
        downstream_manifest=f['downstream'], downstream_manifest_sha=sha(f['downstream_path'].read_bytes()),
        owner_exception_path=f['owner_path'], root_release_path=f['root_path'],
        source_phase_dir=f['phase'], admission_root=f['admission_root'])
    assert loaded == f['metadata_result']
    footer = loaded['objects'][0]['footer_ref']
    assert cache.resolve_reference(footer)['body_b64']
    runner_args = SimpleNamespace(phase='overture_development',
        cache_only_admission=output, cache_only_source_manifest=f['source_path'],
        cache_only_owner_exception=f['owner_path'], cache_only_root_release=f['root_path'],
        cache_only_source_phase_dir=f['phase'], cache_only_admission_root=f['admission_root'],
        overture_metadata=None)
    runner_loaded, runner_cache = run.overture_metadata_input(
        runner_args, f['downstream'], sha(f['downstream_path'].read_bytes()))
    assert runner_loaded == f['metadata_result']
    assert runner_cache.resolve_reference(footer)['body_b64']
    assert supplemental.tree_digest(f['target_root']) == before


def test_v20_run_main_routes_current_roots_through_cache_admission(tmp_path, monkeypatch, capsys):
    f = current_fixture(tmp_path, monkeypatch)
    bind_fresh_test_receipts(f)
    before = supplemental.tree_digest(f['target_root'])
    admission, _digest = recovery.make_admission(
        source_manifest_path=f['source_path'], downstream_manifest_path=f['downstream_path'],
        phase_dir=f['phase'], diagnostic_path=f['diagnostic_path'],
        owner_exception_path=f['owner_path'], root_release_path=f['root_path'],
        admission_root=f['admission_root'])
    manifest_sha = sha(f['downstream_path'].read_bytes())
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f['downstream'], manifest_sha))
    monkeypatch.setattr(run, 'checked_gate', lambda *_args: None)
    monkeypatch.setattr(run, 'phase_sites', lambda *_args: [])

    class OfflineBudget:
        def __init__(self, *_args, **_kwargs):
            self.limits = {'retained_bytes': 1024 * 1024}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def check_completion(self):
            return None

    def fake_extract(_manifest, _sites, result, _budget, cache):
        assert result == f['metadata_result']
        assert cache.resolve_reference(result['objects'][0]['footer_ref'])['body_b64']
        return {'status': 'complete'}

    monkeypatch.setattr(run, 'Budget', OfflineBudget)
    monkeypatch.setattr(run, 'extract', fake_extract)
    monkeypatch.setattr(run, 'immutable_result', lambda *_args: (tmp_path / 'result.json', 'result-digest'))
    monkeypatch.setattr('sys.argv', ['food-pilot-run', '--manifest', str(f['downstream_path']),
        '--execution-gate', str(tmp_path / 'gate.json'), '--phase', 'overture_development',
        '--output-root', str(tmp_path / 'run-output'), '--cache-only-admission', str(admission),
        '--cache-only-source-manifest', str(f['source_path']),
        '--cache-only-owner-exception', str(f['owner_path']),
        '--cache-only-root-release', str(f['root_path']),
        '--cache-only-source-phase-dir', str(f['phase']),
        '--cache-only-admission-root', str(f['admission_root'])])
    run.main()
    assert json.loads(capsys.readouterr().out)['status'] == 'complete'
    assert supplemental.tree_digest(f['target_root']) == before


def test_v20_wrong_source_or_output_path_rejected_without_source_mutation(tmp_path, monkeypatch):
    f = current_fixture(tmp_path, monkeypatch)
    bind_fresh_test_receipts(f)
    before = supplemental.tree_digest(f['target_root'])
    wrong_output = f['artifact_root'] / 'wrong-admissions'
    with pytest.raises(AcquisitionStopped, match='recovery_admission_root_mismatch'):
        recovery.make_admission(source_manifest_path=f['source_path'],
            downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
            diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
            root_release_path=f['root_path'], admission_root=wrong_output)
    wrong_source = f['artifact_root'] / 'target-v4-copy' / 'overture_metadata'
    wrong_source.mkdir(parents=True)
    admission = f['admission_root'] / 'nonexistent.json'
    with pytest.raises(AcquisitionStopped, match='recovery_not_original_v4_phase'):
        recovery.load_admitted_metadata(admission_path=admission,
            source_manifest_path=f['source_path'], downstream_manifest=f['downstream'],
            downstream_manifest_sha=sha(f['downstream_path'].read_bytes()),
            owner_exception_path=f['owner_path'], root_release_path=f['root_path'],
            source_phase_dir=wrong_source, admission_root=f['admission_root'])
    assert not wrong_output.exists()
    assert supplemental.tree_digest(f['target_root']) == before


def test_v20_external_admission_root_symlink_and_escape_rejected(tmp_path, monkeypatch):
    f = current_fixture(tmp_path, monkeypatch)
    expected = f['admission_root']
    import shutil
    shutil.rmtree(expected)
    outside = tmp_path / 'outside'
    outside.mkdir()
    expected.symlink_to(outside, target_is_directory=True)
    with pytest.raises(AcquisitionStopped, match='recovery_admission_root_symlink'):
        recovery._resolve_admission_roots(f['downstream'], f['phase'], expected,
                                          require_admission_root=True)
    expected.unlink()
    with pytest.raises(AcquisitionStopped, match='recovery_admission_root_mismatch'):
        recovery._resolve_admission_roots(f['downstream'], f['phase'], f['artifact_root'] / 'other-admissions',
                                          require_admission_root=True)


def test_v20_combined_retention_counts_source_and_external_output_once(tmp_path, monkeypatch):
    f = current_fixture(tmp_path, monkeypatch)
    current = f['current_contract']
    current['metadata_retention_limit'] = 200
    current['global_retention_limit'] = 820
    current['baseline_metadata_source_bytes'] = 100
    current['baseline_global_bytes'] = 800
    f['source_manifest']['budgets']['overture_metadata']['retained_bytes'] = 200
    f['downstream']['budgets']['total_retained_bytes'] = 820

    values = {
        f['phase'].resolve(): 100,
        f['admission_root'].resolve(): 20,
        (f['target_root']).resolve(): 500,
        (f['artifact_root'] / 'supplemental-hp-v18-001').resolve(): 200,
        (f['artifact_root'] / 'supplemental-hp-v18-001-authorizations').resolve(): 100,
    }
    from food_pilot import supplemental as supplemental_module
    monkeypatch.setattr(supplemental_module, 'file_size', lambda path: values[Path(path).resolve()])
    usage = recovery._current_retention_usage(source_phase_dir=f['phase'],
        admission_root=f['admission_root'], downstream_manifest=f['downstream'],
        source_manifest=f['source_manifest'])
    assert usage['metadata_used'] == 120
    assert usage['global_used'] == 820
    values[f['admission_root'].resolve()] = 21
    with pytest.raises(AcquisitionStopped, match='combined_current_admission_retention_budget'):
        recovery._current_retention_usage(source_phase_dir=f['phase'],
            admission_root=f['admission_root'], downstream_manifest=f['downstream'],
            source_manifest=f['source_manifest'])


def test_v20_missing_source_lock_fails_without_creating_inside_frozen_tree(tmp_path, monkeypatch):
    f = current_fixture(tmp_path, monkeypatch)
    bind_fresh_test_receipts(f)
    lock = f['phase'] / '.reader.lock'
    lock.unlink()
    before = supplemental.tree_digest(f['target_root'])
    with pytest.raises(AcquisitionStopped, match='metadata_cache_lock_unavailable'):
        recovery.make_admission(source_manifest_path=f['source_path'],
            downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
            diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
            root_release_path=f['root_path'], admission_root=f['admission_root'])
    assert not lock.exists()
    assert supplemental.tree_digest(f['target_root']) == before


def test_v20_make_rejects_prewrite_retention_exhaustion(tmp_path, monkeypatch):
    f = current_fixture(tmp_path, monkeypatch)
    bind_fresh_test_receipts(f)
    before = supplemental.tree_digest(f['target_root'])
    real_file_size = supplemental.file_size
    output_limit = (f['current_contract']['metadata_retention_limit']
                    - real_file_size(f['phase']) + 1)

    def charged_size(path):
        if Path(path).resolve() == f['admission_root'].resolve():
            return output_limit
        return real_file_size(path)

    monkeypatch.setattr(supplemental, 'file_size', charged_size)
    with pytest.raises(AcquisitionStopped, match='combined_current_admission_retention_budget'):
        recovery.make_admission(source_manifest_path=f['source_path'],
            downstream_manifest_path=f['downstream_path'], phase_dir=f['phase'],
            diagnostic_path=f['diagnostic_path'], owner_exception_path=f['owner_path'],
            root_release_path=f['root_path'], admission_root=f['admission_root'])
    assert sorted(path.name for path in f['authorization_root'].iterdir()) == [
        'owner-exception.json', 'root-release.json']
    assert supplemental.tree_digest(f['target_root']) == before
