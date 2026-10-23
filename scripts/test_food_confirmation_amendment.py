"""Offline controls for the prospective V22 confirmation-only amendment."""
import copy
import hashlib
import json
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from food_pilot import bounded, manifest as manifest_contract, run
from food_pilot.acquire_osm import encoded
from food_pilot.bounded import AcquisitionStopped


HEAD = 'a' * 40
V21_HEAD = 'b' * 40
EXECUTION_INTENT_SHA256 = 'e' * 64


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(value):
    return value.isoformat().replace('+00:00', 'Z')


def physical_regular_bytes(root):
    total = 0
    for path in Path(root).rglob('*'):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if not path.is_symlink() and path.is_file():
            total += info.st_size
    return total


def synthetic_handoff(tmp_path, monkeypatch, checkpoint_edit=None, total_retained_bytes=2*1024**3):
    artifact_root = tmp_path/'v20-artifacts'
    manifest_dir = artifact_root/'amended-v1'
    phase_dir = artifact_root/'hp_prescreen'
    manifest_dir.mkdir(parents=True)
    phase_dir.mkdir(parents=True)
    code_map = {'scripts/food_pilot/old.py': '0'*64}
    source = {
        'state': 'frozen',
        'code_sha256': code_map,
        'source_window': {'core_hp_complete_before': manifest_contract.CORE_SOURCE_CUTOFF},
        'core': {'stations': []},
        'budgets': {'hp_confirmation': copy.deepcopy(manifest_contract.CONFIRMATION_BUDGET),
                    'overture_metadata': {'attempts': 80},
                    'total_retained_bytes': total_retained_bytes},
        'challenge': {
            'order': [],
            'confirmed_goal_per_group': 8,
            'confirmation_stop': 'V20 predecessor control text',
        },
        'reviewed_execution_scope': ['old_scope'],
        'later_phase_gate': 'old gate contract',
    }
    expected = manifest_contract.confirmation_candidate_bindings()
    candidate_ids = [row['slug'] for row in expected]
    for index in range(32):
        source['challenge']['order'].append({'slug': f'rich-{index}', 'challenge_group': 'rich'})
        source['challenge']['order'].append({
            'slug': candidate_ids[index] if index < len(candidate_ids) else f'sparse-{index}',
            'challenge_group': 'sparse',
        })
    source_raw = manifest_contract.canonical_manifest_bytes(source)
    archive_raw = b'synthetic immutable V20 archive bytes\n'
    prescreen_raw = b'opaque synthetic V20 prescreen envelope; never parse this payload\n'
    checkpoint = {
        'manifest_sha256': sha(source_raw),
        'prescreen_result_sha256': sha(prescreen_raw),
        'zero_confirmation': {
            'status': 'pending_real_time',
            'candidates': [{
                'slug': row['slug'],
                'first_status': 'complete_provider_zero' if i % 2 == 0 else 'complete_800m_zero',
                'first_complete_at': row['first_complete_at'].replace('Z', '+00:00'),
                'eligible_from': row['eligible_from'].replace('Z', '+00:00'),
                'eligible_until': row['eligible_until'].replace('Z', '+00:00'),
            } for i, row in enumerate(expected)],
            'batch_eligible_from': manifest_contract.V20_BATCH_ELIGIBLE_FROM.replace('Z', '+00:00'),
            'batch_eligible_until': manifest_contract.V20_BATCH_ELIGIBLE_UNTIL.replace('Z', '+00:00'),
        },
    }
    if checkpoint_edit:
        checkpoint_edit(checkpoint)
    checkpoint_raw = manifest_contract.canonical_manifest_bytes(checkpoint)

    monkeypatch.setattr(manifest_contract, 'V20_MANIFEST_SHA256', sha(source_raw))
    monkeypatch.setattr(manifest_contract, 'V20_ARCHIVE_SHA256', sha(archive_raw))
    monkeypatch.setattr(manifest_contract, 'V20_CODE_MAP_SHA256',
                        manifest_contract.canonical_code_map_sha256(code_map))
    monkeypatch.setattr(manifest_contract, 'V20_PRESCREEN_SHA256', sha(prescreen_raw))
    monkeypatch.setattr(manifest_contract, 'V20_CHECKPOINT_SHA256', sha(checkpoint_raw))

    source_path = manifest_dir/'final-manifest-v20.json'
    archive_path = manifest_dir/'final-manifest-v20.archive.json'
    prescreen_path = phase_dir/'result-69217f88ac70d677a816fc3e31ec2fbcbe2868f4bfd60c56f0e3d6c5de1b44ff.json'
    checkpoint_path = phase_dir/'result-277cfbd918553cb5bd9caaf6878ab04ade46dfd713a02f067223a8a16962789d.json'
    source_path.write_bytes(source_raw)
    archive_path.write_bytes(archive_raw)
    prescreen_path.write_bytes(prescreen_raw)
    checkpoint_path.write_bytes(checkpoint_raw)
    v21 = manifest_contract.make_v21_test_predecessor(
        source_raw, artifact_root=artifact_root, runtime_root=run.ROOT, code_head=V21_HEAD)
    v21_raw = manifest_contract.canonical_manifest_bytes(v21)
    v21_archive_raw = v21_raw
    v21_artifact_root = tmp_path/'v21-artifacts'
    v21_artifact_root.mkdir()
    v21_manifest_path = v21_artifact_root/'final-manifest-v21.json'
    v21_archive_path = v21_artifact_root/'final-manifest-v21.archive.json'
    v21_manifest_path.write_bytes(v21_raw)
    v21_archive_path.write_bytes(v21_archive_raw)
    monkeypatch.setattr(manifest_contract, 'V21_MANIFEST_SHA256', sha(v21_raw))
    monkeypatch.setattr(manifest_contract, 'V21_ARCHIVE_SHA256', sha(v21_archive_raw))
    monkeypatch.setattr(manifest_contract, 'V21_CODE_MAP_SHA256',
                        manifest_contract.canonical_code_map_sha256(v21['code_sha256']))
    monkeypatch.setattr(manifest_contract, 'V21_AMENDMENT_SHA256',
                        manifest_contract.canonical_compact_sha256(v21['confirmation_amendment']))
    monkeypatch.setattr(manifest_contract, 'V21_GIT_HEAD', V21_HEAD)
    successor = manifest_contract.make_confirmation_successor_v22(
        v21_raw, v21_archive_raw, artifact_root=v21_artifact_root,
        runtime_root=run.ROOT, code_head=HEAD)
    successor_path = tmp_path/'successor-manifest.json'
    successor_raw = manifest_contract.canonical_manifest_bytes(successor)
    successor_path.write_bytes(successor_raw)
    return SimpleNamespace(
        artifact_root=artifact_root, source=source, source_raw=source_raw,
        source_path=source_path, archive_path=archive_path, archive_raw=archive_raw,
        prescreen_path=prescreen_path, prescreen_raw=prescreen_raw,
        checkpoint_path=checkpoint_path, checkpoint=checkpoint,
        v21=v21, v21_raw=v21_raw, v21_archive_raw=v21_archive_raw,
        v21_artifact_root=v21_artifact_root,
        v21_manifest_path=v21_manifest_path, v21_archive_path=v21_archive_path,
        checkpoint_raw=checkpoint_raw, successor=successor,
        successor_path=successor_path, successor_raw=successor_raw,
        successor_sha=sha(successor_raw), candidate_ids=candidate_ids,
    )


def authorization_files(f, tmp_path, output_root, now, *, head=HEAD):
    map_sha = manifest_contract.canonical_code_map_sha256(f.successor['code_sha256'])
    activation_id = 'synthetic-activation-1'
    run_id = 'synthetic-run-1'
    pool = run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, head, output_root, activation_id, run_id,
        EXECUTION_INTENT_SHA256)
    real_datetime = run.datetime

    class FixtureDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz) if tz else now

    run.datetime = FixtureDateTime
    try:
        pool = run._issue_confirmation_preparation_intents_at(
            f.successor, f.successor_sha, head, output_root, activation_id, run_id, now,
            EXECUTION_INTENT_SHA256)
        pool = run._commit_confirmation_burn_claim_at(
            f.successor, f.successor_sha, head, output_root, activation_id, run_id, now,
            EXECUTION_INTENT_SHA256)
    finally:
        run.datetime = real_datetime
    started, deadline = run._intent_window(pool['slots']['preparation_owner_intent'])
    chain_fields = {
        'allocation_descriptor_sha256': pool['descriptor_sha256'],
        'preparation_owner_intent_sha256': pool['slot_sha256']['preparation_owner_intent'],
        'preparation_root_intent_sha256': pool['slot_sha256']['preparation_root_intent'],
        'execution_intent_sha256': EXECUTION_INTENT_SHA256,
        'burn_claim_commitment_sha256': pool['slots']['burn_claim']['claim_commitment_sha256'],
        'window_started_at': stamp(started),
        'absolute_deadline': stamp(deadline),
    }
    owner = {
        **run._control_slot_reservation(
            pool['descriptor'], pool['descriptor_sha256'], 'final_owner_execution_receipt'),
        'kind': 'owner_hp_confirmation_activation',
        'slot_state': 'issued',
        'phase': 'hp_confirmation',
        'allowed_phases': ['hp_confirmation'],
        'single_use': True,
        'manifest_sha256': f.successor_sha,
        'git_head': head,
        'code_map_sha256': map_sha,
        'output_root': str(output_root.resolve()),
        'source_manifest_sha256': manifest_contract.V20_MANIFEST_SHA256,
        'source_archive_sha256': manifest_contract.V20_ARCHIVE_SHA256,
        'source_code_map_sha256': manifest_contract.V20_CODE_MAP_SHA256,
        'prescreen_envelope_sha256': manifest_contract.V20_PRESCREEN_SHA256,
        'control_checkpoint_sha256': manifest_contract.V20_CHECKPOINT_SHA256,
        'candidate_count': 13,
        'group_counts': {'rich': 0, 'sparse': 13},
        'budget': f.successor['budgets']['hp_confirmation'],
        'activation_id': activation_id,
        'run_id': run_id,
        'created_at': stamp(now),
        'expires_at': stamp(deadline),
        **chain_fields,
    }
    owner_raw = run._padded_control_slot(owner)
    owner_sha = sha(owner_raw)
    root_check = {
        'manifest_sha256': f.successor_sha,
        'git_head': head,
        'code_map_sha256': map_sha,
        'allowed_phases': ['hp_confirmation'],
        'output_root': str(output_root.resolve()),
        'owner_activation_sha256': owner_sha,
        **chain_fields,
    }
    gate = {
        **run._control_slot_reservation(
            pool['descriptor'], pool['descriptor_sha256'], 'final_root_release_receipt'),
        'kind': 'root_hp_confirmation_release',
        'slot_state': 'issued',
        'phase': 'hp_confirmation',
        'allowed_phases': ['hp_confirmation'],
        'manifest_sha256': f.successor_sha,
        'git_head': head,
        'code_map_sha256': map_sha,
        'output_root': str(output_root.resolve()),
        'native_review_approved_head': head,
        'owner_activation_sha256': owner_sha,
        'root_manifest_check': root_check,
        'released_at': stamp(now),
        'expires_at': stamp(deadline),
        **chain_fields,
    }
    real_datetime = run.datetime

    class FixtureDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz) if tz else now

    run.datetime = FixtureDateTime
    try:
        pool = run.publish_confirmation_execution_receipts(
            f.successor, f.successor_sha, head, output_root,
            activation_id, run_id, EXECUTION_INTENT_SHA256, owner, gate)
    finally:
        run.datetime = real_datetime
    owner_path = pool['paths']['final_owner_execution_receipt']
    gate_path = pool['paths']['final_root_release_receipt']
    return owner_path, gate_path, owner, gate


def replace_control_slot(f, role, value, *, head=HEAD):
    owner = value if role == 'final_owner_execution_receipt' else None
    identity = (owner or {}).get('activation_id', 'synthetic-activation-1')
    run_id = (owner or {}).get('run_id', 'synthetic-run-1')
    with run._confirmation_control_lock(f.artifact_root) as (root, root_fd):
        pool = run._read_control_pool_locked(
            root_fd, root, f.successor, f.successor_sha, head, identity, run_id,
            EXECUTION_INTENT_SHA256)
        raw = run._rewrite_control_slot_locked(
            root_fd, pool['paths'][role].name, pool['raws'][role], value)
    return raw


def force_replace_control_slot(path, value):
    root = Path(path).parent
    with run._confirmation_control_lock(root) as (_root, root_fd):
        old_raw = run._read_fixed_control_file(path)
        return run._rewrite_control_slot_locked(
            root_fd, Path(path).name, old_raw, value)


def replace_authorization_pair(f, owner_path, gate_path, owner, gate):
    owner_raw = replace_control_slot(f, 'final_owner_execution_receipt', owner)
    owner_sha = sha(owner_raw)
    gate = copy.deepcopy(gate)
    gate['owner_activation_sha256'] = owner_sha
    gate['root_manifest_check']['owner_activation_sha256'] = owner_sha
    gate_raw = replace_control_slot(f, 'final_root_release_receipt', gate)
    return owner_raw, gate_raw, gate


def test_successor_is_confirmation_only_and_preserves_v20_budgets(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    assert f.successor['version'] == 'v22'
    assert f.successor['supersedes_manifest_sha256'] == sha(f.v21_raw)
    assert f.successor['source_window']['core_hp_complete_before'] == '2026-10-22T00:00:00Z'
    assert f.successor['confirmation_amendment']['confirmation_completion_before'] == '2026-10-24T00:00:00Z'
    assert f.successor['reviewed_execution_scope'] == ['hp_confirmation']
    assert f.successor['budgets'] == f.source['budgets']
    assert f.successor['budgets']['hp_confirmation'] == {
        'attempts': 200, 'successful_pages': 160, 'pages_per_station': 50,
        'response_bytes': 1024**2, 'response_body_bytes': 64*1024**2,
        'retained_bytes': 64*1024**2, 'wall_seconds': 1800, 'socket_seconds': 20,
        'concurrency': 1, 'minimum_request_interval_seconds': .6,
        'maximum_attempts_per_page': 2,
    }
    v20 = f.successor['confirmation_amendment']['historical_v20']
    assert v20['group_counts'] == {'rich': 0, 'sparse': 13}
    assert [row['slug'] for row in v20['candidate_bindings']] == f.candidate_ids
    assert v20['batch_window'] == {
        'start_inclusive': '2026-10-22T08:37:46.527802Z',
        'end_exclusive': '2026-10-24T08:34:49.296391Z',
    }
    assert f.successor['confirmation_amendment']['v20_remains_insufficient'] is True
    assert f.successor['confirmation_amendment']['authority']['implementation_approval_is_not_activation'] is True
    assert f.successor['confirmation_amendment']['control_pool_contract']['slot_bytes'] == 4096
    assert f.successor['confirmation_amendment']['control_pool_contract']['total_bytes'] == 24576
    v21 = f.successor['confirmation_amendment']['historical_v21']
    assert v21['manifest_sha256'] == sha(f.v21_raw)
    assert v21['archive_sha256'] == sha(f.v21_archive_raw)
    assert v21['code_map_sha256'] == manifest_contract.V21_CODE_MAP_SHA256
    assert f.successor['confirmation_amendment']['historical_v20'] == f.v21['confirmation_amendment']['historical_v20']
    assert f.successor['confirmation_amendment']['predecessor_operational_authority_reusable'] is False


def test_v22_accepts_only_exact_direct_v21_lineage_and_rejects_v21_authority(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    amendment = run.checked_confirmation_amendment(f.successor)
    assert amendment['confirmation_completion_before'] == '2026-10-24T00:00:00Z'
    assert f.successor['supersedes_manifest_sha256'] == sha(f.v21_raw)
    with pytest.raises(AcquisitionStopped, match='confirmation_amendment_required_or_invalid'):
        run.checked_confirmation_amendment(f.v21)
    with pytest.raises(AcquisitionStopped, match='confirmation_amendment_required_or_invalid'):
        run.checked_confirmation_gate(
            tmp_path/'old-v21-gate.json', tmp_path/'old-v21-owner.json', f.v21,
            sha(f.v21_raw), V21_HEAD, f.artifact_root,
            datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc))

    changed_archive = f.v21_archive_raw+b'changed'
    f.v21_archive_path.write_bytes(changed_archive)
    with pytest.raises(AcquisitionStopped, match='confirmation_v21_predecessor_hash'):
        run.checked_confirmation_handoff(
            f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path,
            f.v21_manifest_path, f.v21_archive_path, HEAD)

    changed_successor = copy.deepcopy(f.successor)
    changed_successor['supersedes_manifest_sha256'] = sha(f.source_raw)
    with pytest.raises(AcquisitionStopped, match='confirmation_amendment_required_or_invalid'):
        run.checked_confirmation_amendment(changed_successor)


def test_control_pool_pre_reserves_all_bytes_and_pins_exact_execution_intent(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    before = physical_regular_bytes(f.artifact_root)
    pool = run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        'synthetic-activation-1', 'synthetic-run-1', EXECUTION_INTENT_SHA256)
    assert physical_regular_bytes(f.artifact_root)-before == 24576
    assert run._confirmation_control_bytes(f.artifact_root) == 24576
    assert pool['descriptor']['execution_intent_sha256'] == EXECUTION_INTENT_SHA256
    assert set(pool['paths']) == set(manifest_contract.CONFIRMATION_CONTROL_SLOT_ROLES)
    for role, path in pool['paths'].items():
        assert path.stat().st_size == 4096
        value = run._control_json(path.read_bytes())
        assert value.get('execution_intent_sha256') == EXECUTION_INTENT_SHA256
    with pytest.raises(AcquisitionStopped, match='confirmation_control_pool_binding'):
        run.issue_confirmation_preparation_intents(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            'synthetic-activation-1', 'synthetic-run-1', 'f'*64)
    owner_intent = run._control_json(
        pool['paths']['preparation_owner_intent'].read_bytes())
    assert owner_intent['slot_state'] == 'reserved'


def test_issuer_live_deadline_after_lock_wait_publishes_no_owner_intent(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    activation_id, run_id = 'delay-activation', 'delay-run'
    run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, EXECUTION_INTENT_SHA256)
    start = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    now = [start]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    real_lock = run._confirmation_control_lock
    real_rewrite = run._rewrite_control_slot_locked
    owner_name = run._control_pool_paths(
        f.artifact_root, activation_id, run_id)['preparation_owner_intent'].name

    @contextmanager
    def delay_lock(root):
        now[0] = start+timedelta(minutes=29)
        with real_lock(root) as locked:
            yield locked

    def delay_owner_write(root_fd, name, expected_raw, value, *, pre_write_guard=None):
        if name == owner_name:
            now[0] = start+timedelta(seconds=1800)
        return real_rewrite(root_fd, name, expected_raw, value,
                            pre_write_guard=pre_write_guard)

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, '_confirmation_control_lock', delay_lock)
    monkeypatch.setattr(run, '_rewrite_control_slot_locked', delay_owner_write)
    with pytest.raises(AcquisitionStopped, match='confirmation_completion_deadline_expired'):
        run.issue_confirmation_preparation_intents(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            activation_id, run_id, EXECUTION_INTENT_SHA256)
    monkeypatch.setattr(run, '_confirmation_control_lock', real_lock)
    monkeypatch.setattr(run, '_rewrite_control_slot_locked', real_rewrite)
    paths = run._control_pool_paths(f.artifact_root, activation_id, run_id)
    for role in ('preparation_owner_intent', 'preparation_root_intent', 'burn_claim',
                 'final_owner_execution_receipt', 'final_root_release_receipt'):
        value = run._control_json(paths[role].read_bytes())
        assert value['slot_state'] == 'reserved'


def test_pre_owner_intent_storage_failure_publishes_no_usable_window(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    activation_id, run_id = 'prewrite-activation', 'prewrite-run'
    pool = run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, EXECUTION_INTENT_SHA256)
    start = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    real_datetime = run.datetime
    real_rewrite = run._rewrite_control_slot_locked
    owner_name = pool['paths']['preparation_owner_intent'].name

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return start.astimezone(tz) if tz else start

    def fail_before_owner_mutation(root_fd, name, expected_raw, value, *, pre_write_guard=None):
        if name == owner_name:
            raise AcquisitionStopped('synthetic_owner_slot_open_failure')
        return real_rewrite(root_fd, name, expected_raw, value,
                            pre_write_guard=pre_write_guard)

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, '_rewrite_control_slot_locked', fail_before_owner_mutation)
    with pytest.raises(AcquisitionStopped, match='synthetic_owner_slot_open_failure'):
        run.issue_confirmation_preparation_intents(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            activation_id, run_id, EXECUTION_INTENT_SHA256)
    monkeypatch.setattr(run, '_rewrite_control_slot_locked', real_rewrite)
    paths = run._control_pool_paths(f.artifact_root, activation_id, run_id)
    for role in ('preparation_owner_intent', 'preparation_root_intent', 'burn_claim',
                 'final_owner_execution_receipt', 'final_root_release_receipt'):
        assert run._control_json(paths[role].read_bytes())['slot_state'] == 'reserved'
    with pytest.raises(AcquisitionStopped, match='confirmation_preparation_owner_intent_missing'):
        run._confirmation_control_chain(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            activation_id, run_id, EXECUTION_INTENT_SHA256)

    start = start+timedelta(minutes=1)
    issued = run._issue_confirmation_preparation_intents_at(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, start, EXECUTION_INTENT_SHA256)
    assert issued['slots']['preparation_owner_intent']['window_started_at'] == stamp(start)
    assert issued['slots']['preparation_root_intent']['slot_state'] == 'issued'


def test_preparation_intents_alone_are_not_runnable_by_actual_cli(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz) if tz else now

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    activation_id, run_id = 'prep-only-activation', 'prep-only-run'
    pool = run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, EXECUTION_INTENT_SHA256)
    pool = run._issue_confirmation_preparation_intents_at(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, now, EXECUTION_INTENT_SHA256)
    calls = []
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr(run, 'acquire_sites', lambda *_args: calls.append('source'))
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(pool['paths']['final_root_release_receipt']),
        '--owner-activation', str(pool['paths']['final_owner_execution_receipt']),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ])
    with pytest.raises(AcquisitionStopped, match='confirmation_activation_claim_missing'):
        run.main()
    assert pool['slots']['preparation_owner_intent']['slot_state'] == 'issued'
    assert pool['slots']['preparation_root_intent']['slot_state'] == 'issued'
    assert pool['slots']['burn_claim']['slot_state'] == 'reserved'
    assert calls == []


def test_issuer_owner_first_prefix_retry_reuses_fixed_t0_and_approval(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    activation_id, run_id = 'prefix-activation', 'prefix-run'
    pool = run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, EXECUTION_INTENT_SHA256)
    start = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    now = [start]
    real_datetime = run.datetime
    real_rewrite = run._rewrite_control_slot_locked
    root_name = pool['paths']['preparation_root_intent'].name

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    fail_root = [True]

    def fail_after_owner(root_fd, name, expected_raw, value, *, pre_write_guard=None):
        if name == root_name and fail_root[0]:
            fail_root[0] = False
            raise AcquisitionStopped('synthetic_root_intent_persist_failure')
        return real_rewrite(root_fd, name, expected_raw, value,
                            pre_write_guard=pre_write_guard)

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, '_rewrite_control_slot_locked', fail_after_owner)
    with pytest.raises(AcquisitionStopped, match='synthetic_root_intent_persist_failure'):
        run.issue_confirmation_preparation_intents(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            activation_id, run_id, EXECUTION_INTENT_SHA256)
    monkeypatch.setattr(run, '_rewrite_control_slot_locked', real_rewrite)
    paths = run._control_pool_paths(f.artifact_root, activation_id, run_id)
    owner_intent = run._control_json(paths['preparation_owner_intent'].read_bytes())
    assert owner_intent['window_started_at'] == stamp(start)
    assert run._control_json(paths['preparation_root_intent'].read_bytes())['slot_state'] == 'reserved'
    with pytest.raises(AcquisitionStopped, match='confirmation_control_pool_binding'):
        run.issue_confirmation_preparation_intents(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            activation_id, run_id, 'f'*64)

    now[0] += timedelta(minutes=5)
    retried = run.issue_confirmation_preparation_intents(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, EXECUTION_INTENT_SHA256)
    assert retried['slots']['preparation_owner_intent']['window_started_at'] == stamp(start)
    assert retried['slots']['preparation_root_intent']['window_started_at'] == stamp(start)
    assert retried['slots']['preparation_root_intent']['absolute_deadline'] == stamp(
        start+timedelta(seconds=1800))
    assert retried['slots']['preparation_root_intent']['execution_intent_sha256'] == EXECUTION_INTENT_SHA256


def test_concurrent_issuers_reload_owner_window_under_art_lock(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    activation_id, run_id = 'concurrent-activation', 'concurrent-run'
    run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, EXECUTION_INTENT_SHA256)
    start = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    clock_values = {
        'issuer-early': start,
        'issuer-late': start+timedelta(minutes=5),
    }
    real_datetime = run.datetime
    real_lock = run._confirmation_control_lock
    barrier = threading.Barrier(2)

    class ConcurrentDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            value = clock_values[threading.current_thread().name]
            return value.astimezone(tz) if tz else value

    @contextmanager
    def simultaneous_lock(root):
        barrier.wait(timeout=5)
        with real_lock(root) as locked:
            yield locked

    monkeypatch.setattr(run, 'datetime', ConcurrentDateTime)
    monkeypatch.setattr(run, '_confirmation_control_lock', simultaneous_lock)
    results, errors = {}, []

    def issue():
        name = threading.current_thread().name
        try:
            results[name] = run.issue_confirmation_preparation_intents(
                f.successor, f.successor_sha, HEAD, f.artifact_root,
                activation_id, run_id, EXECUTION_INTENT_SHA256)
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=issue, name=name)
               for name in ('issuer-early', 'issuer-late')]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    assert errors == []
    windows = {result['slots']['preparation_owner_intent']['window_started_at']
               for result in results.values()}
    assert len(windows) == 1
    pool = next(iter(results.values()))
    assert pool['slots']['preparation_root_intent']['window_started_at'] == next(iter(windows))
    assert pool['slots']['preparation_root_intent']['preparation_owner_intent_sha256'] == \
        pool['slot_sha256']['preparation_owner_intent']
    assert pool['descriptor']['execution_intent_sha256'] == EXECUTION_INTENT_SHA256


@pytest.mark.parametrize('wrong_version', [True, 1.0])
def test_control_slot_schema_version_rejects_bool_and_float(tmp_path, monkeypatch, wrong_version):
    f = synthetic_handoff(tmp_path, monkeypatch)
    activation_id, run_id = 'typed-activation', 'typed-run'
    pool = run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        activation_id, run_id, EXECUTION_INTENT_SHA256)
    slot = pool['paths']['preparation_owner_intent']
    value = run._control_json(slot.read_bytes())
    value['schema_version'] = wrong_version
    force_replace_control_slot(slot, value)
    with pytest.raises(AcquisitionStopped, match='confirmation_control_slot_schema'):
        run.issue_confirmation_preparation_intents(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            activation_id, run_id, EXECUTION_INTENT_SHA256)


def test_historical_handoff_uses_checkpoint_and_opaque_result_hash(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    prior, checkpoint = run.checked_confirmation_handoff(
        f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path,
        f.v21_manifest_path, f.v21_archive_path, HEAD)
    assert f.prescreen_raw.startswith(b'opaque')
    assert [row['slug'] for row in prior['stations']] == f.candidate_ids
    assert run.confirmation_checkpoint(prior) == checkpoint['zero_confirmation']


def test_historical_handoff_rejects_current_prior_path_and_changed_checkpoint(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    with pytest.raises(AcquisitionStopped, match='confirmation_v20_prescreen_path'):
        run.checked_confirmation_handoff(
            f.successor, f.successor_path, f.checkpoint_path, f.source_path, f.archive_path,
            f.v21_manifest_path, f.v21_archive_path, HEAD)
    f.checkpoint_path.write_bytes(f.checkpoint_raw+b'changed')
    with pytest.raises(AcquisitionStopped, match='confirmation_v20_checkpoint_hash'):
        run.checked_confirmation_handoff(
            f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path,
            f.v21_manifest_path, f.v21_archive_path, HEAD)


def test_historical_handoff_rejects_checkpoint_order_even_with_matching_pinned_hash(tmp_path, monkeypatch):
    def reverse_candidates(checkpoint):
        checkpoint['zero_confirmation']['candidates'][0:2] = reversed(
            checkpoint['zero_confirmation']['candidates'][0:2])

    f = synthetic_handoff(tmp_path, monkeypatch, checkpoint_edit=reverse_candidates)
    with pytest.raises(AcquisitionStopped, match='confirmation_checkpoint_order_or_status'):
        run.checked_confirmation_handoff(
            f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path,
            f.v21_manifest_path, f.v21_archive_path, HEAD)


def test_confirmation_gate_requires_exact_head_manifest_map_and_single_phase(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    owner_path, gate_path, _owner, gate = authorization_files(f, tmp_path, f.artifact_root, now)
    owner, root, _owner_sha, _gate_sha = run.checked_confirmation_gate(
        gate_path, owner_path, f.successor, f.successor_sha, HEAD, f.artifact_root, now)
    assert owner['activation_id'] == 'synthetic-activation-1'
    assert root['allowed_phases'] == ['hp_confirmation']

    with pytest.raises(AcquisitionStopped, match='confirmation_owner_activation_binding'):
        run.checked_confirmation_gate(
            gate_path, owner_path, f.successor, 'f'*64, HEAD, f.artifact_root, now)
    with pytest.raises(AcquisitionStopped, match='confirmation_owner_activation_binding'):
        run.checked_confirmation_gate(
            gate_path, owner_path, f.successor, f.successor_sha, 'b'*40, f.artifact_root, now)
    with pytest.raises(AcquisitionStopped, match='confirmation_artifact_root_mismatch'):
        run.checked_confirmation_gate(
            gate_path, owner_path, f.successor, f.successor_sha, HEAD, tmp_path/'arbitrary-sibling', now)

    for changes in (
        {'allowed_phases': ['hp_confirmation', 'hp_holdout']},
        {'manifest_sha256': 'f'*64},
        {'git_head': 'b'*40},
        {'code_map_sha256': 'f'*64},
        {'output_root': str((tmp_path/'arbitrary-sibling').resolve())},
        {'native_review_approved_head': 'b'*40},
        {'kind': 'stale_v20_gate'},
        {'root_manifest_check': True},
    ):
        changed = {**gate, **changes}
        force_replace_control_slot(gate_path, changed)
        if changes.get('kind') == 'stale_v20_gate':
            expected_error = 'confirmation_control_slot_state_invalid'
        elif any(key in changes for key in (
                'manifest_sha256', 'git_head', 'code_map_sha256', 'output_root')):
            expected_error = 'confirmation_control_slot_binding'
        else:
            expected_error = 'confirmation_root_gate_binding'
        with pytest.raises(AcquisitionStopped, match=expected_error):
            run.checked_confirmation_gate(
                gate_path, owner_path, f.successor, f.successor_sha, HEAD, f.artifact_root, now)
        force_replace_control_slot(gate_path, gate)


def test_confirmation_gate_rejects_missing_and_expired_owner_root_receipts(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    owner_path, gate_path, owner, gate = authorization_files(f, tmp_path, f.artifact_root, now)
    with pytest.raises(AcquisitionStopped, match='confirmation_final_receipt_path'):
        run.checked_confirmation_gate(
            gate_path, tmp_path/'missing-owner.json', f.successor,
            f.successor_sha, HEAD, f.artifact_root, now)
    owner['expires_at'] = stamp(now)
    _owner_raw, _gate_raw, gate = replace_authorization_pair(
        f, owner_path, gate_path, owner, gate)
    with pytest.raises(AcquisitionStopped, match='confirmation_owner_activation_not_fresh'):
        run.checked_confirmation_gate(
            gate_path, owner_path, f.successor, f.successor_sha, HEAD, f.artifact_root, now)


def test_confirmation_t0_uses_minimum_of_wall_and_absolute_deadline(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    start = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, start)
    phase = run._confirmation_phase_directory(f.artifact_root)
    _owner, _root, owner_sha, gate_sha = run.checked_confirmation_gate(
        gate_path, owner_path, f.successor, f.successor_sha, HEAD, f.artifact_root, start)
    pool = run._confirmation_control_chain(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        owner['activation_id'], owner['run_id'], EXECUTION_INTENT_SHA256,
        require_final=True)
    binding = run._confirmation_claim_binding(
        owner, owner_sha, gate_sha, f.successor, f.successor_sha, HEAD,
        f.artifact_root, control_pool=pool)
    claim_path = run._confirmation_claim_path(f.artifact_root, binding)
    args = SimpleNamespace(resume=False, output_root=f.artifact_root)
    started, deadline, remaining = run._confirmation_run_window(
        args, f.successor_sha, start, phase_dir=phase, claim_binding=binding,
        claim_path=claim_path)
    assert started == start
    assert deadline == start+timedelta(seconds=1800)
    assert remaining == 1800

    near_tmp = tmp_path/'near-cutoff'
    f_near = synthetic_handoff(near_tmp, monkeypatch)
    near_cutoff = datetime(2026, 10, 23, 23, 50, tzinfo=timezone.utc)
    near_owner_path, near_gate_path, near_owner, _ = authorization_files(
        f_near, near_tmp, f_near.artifact_root, near_cutoff)
    near_phase = run._confirmation_phase_directory(f_near.artifact_root)
    _owner, _root, near_owner_sha, near_gate_sha = run.checked_confirmation_gate(
        near_gate_path, near_owner_path, f_near.successor, f_near.successor_sha,
        HEAD, f_near.artifact_root, near_cutoff)
    near_pool = run._confirmation_control_chain(
        f_near.successor, f_near.successor_sha, HEAD, f_near.artifact_root,
        near_owner['activation_id'], near_owner['run_id'], EXECUTION_INTENT_SHA256,
        require_final=True)
    near_binding = run._confirmation_claim_binding(
        near_owner, near_owner_sha, near_gate_sha, f_near.successor,
        f_near.successor_sha, HEAD, f_near.artifact_root, control_pool=near_pool)
    near_claim = run._confirmation_claim_path(f_near.artifact_root, near_binding)
    near_args = SimpleNamespace(resume=False, output_root=f_near.artifact_root)
    _started, deadline, remaining = run._confirmation_run_window(
        near_args, f_near.successor_sha, near_cutoff, phase_dir=near_phase,
        claim_binding=near_binding, claim_path=near_claim)
    assert deadline == datetime(2026, 10, 24, 0, 0, tzinfo=timezone.utc)
    assert remaining == 600
    _started, _deadline, remaining = run._confirmation_run_window(
        near_args, f_near.successor_sha, deadline-timedelta(microseconds=1),
        phase_dir=near_phase, claim_binding=near_binding, claim_path=near_claim)
    assert remaining == pytest.approx(0.000001)
    for expired in (deadline, deadline+timedelta(minutes=1)):
        with pytest.raises(AcquisitionStopped, match='confirmation_completion_deadline_expired'):
            run._confirmation_run_window(
                near_args, f_near.successor_sha, expired, phase_dir=near_phase,
                claim_binding=near_binding, claim_path=near_claim)


def test_confirmation_resume_retains_original_t0_and_deadline(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    start = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    deadline = start+timedelta(seconds=1800)
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, start)
    phase = run._confirmation_phase_directory(f.artifact_root)
    _owner, _root, owner_sha, gate_sha = run.checked_confirmation_gate(
        gate_path, owner_path, f.successor, f.successor_sha, HEAD, f.artifact_root, start)
    pool = run._confirmation_control_chain(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        owner['activation_id'], owner['run_id'], EXECUTION_INTENT_SHA256,
        require_final=True)
    binding = run._confirmation_claim_binding(
        owner, owner_sha, gate_sha, f.successor, f.successor_sha, HEAD,
        f.artifact_root, control_pool=pool)
    claim_path = run._confirmation_claim_path(f.artifact_root, binding)
    _claim, claim_sha, _claim_started, _claim_deadline = run._read_confirmation_claim(
        claim_path, binding)
    run._mark_confirmation_budget_started(
        phase, claim_sha, retained_limit=f.successor['budgets']['hp_confirmation']['retained_bytes'],
        claim_root=f.artifact_root)
    ledger = {
        'manifest_sha256': f.successor_sha,
        'limits': f.successor['budgets']['hp_confirmation'],
        'started_at': stamp(start),
        'window_contract': {
            'absolute_deadline': stamp(deadline),
            'window_started_at': stamp(start),
        },
    }
    (phase/'ledger.json').write_bytes(encoded(ledger))
    args = SimpleNamespace(resume=True, output_root=f.artifact_root)
    resumed_start, resumed_deadline, remaining = run._confirmation_run_window(
        args, f.successor_sha, start+timedelta(minutes=5), phase_dir=phase,
        claim_binding=binding, claim_path=claim_path)
    assert resumed_start == start
    assert resumed_deadline == deadline
    assert remaining == 1500
    with pytest.raises(AcquisitionStopped, match='confirmation_completion_deadline_expired'):
        run._confirmation_run_window(
            args, f.successor_sha, deadline, phase_dir=phase,
            claim_binding=binding, claim_path=claim_path)
    ledger['finalization_rejections'] = [{'result_sha256': 'late-result'}]
    (phase/'ledger.json').write_bytes(encoded(ledger))
    with pytest.raises(AcquisitionStopped, match='confirmation_late_finalization_not_admissible'):
        run._confirmation_run_window(args, f.successor_sha, start+timedelta(minutes=5),
                                     phase_dir=phase, claim_binding=binding,
                                     claim_path=claim_path)


def test_failed_confirmation_preflight_cannot_reset_activation_t0(tmp_path, monkeypatch, capsys):
    f = synthetic_handoff(tmp_path, monkeypatch)
    started = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    now = [started]
    real_run_datetime = run.datetime
    real_budget_datetime = bounded.datetime

    class ControlledRunDateTime(real_run_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    class ControlledBudgetDateTime(real_budget_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    monkeypatch.setattr(run, 'datetime', ControlledRunDateTime)
    monkeypatch.setattr(bounded, 'datetime', ControlledBudgetDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setenv('HOTPEPPER_API_KEY', 'offline-test-only')
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, started)
    phase_dir = f.artifact_root/'hp_confirmation'
    claim_path = run._confirmation_claim_path(
        f.artifact_root,
        run._confirmation_claim_binding(
            owner, sha(owner_path.read_bytes()), sha(gate_path.read_bytes()),
            f.successor, f.successor_sha, HEAD, f.artifact_root))
    marker_path = phase_dir/'activation-budget-started.json'
    ledger_path = phase_dir/'ledger.json'
    source_calls = []

    def offline_acquire(sites, _budget, _key):
        source_calls.append('mocked_hotpepper_adapter')
        finish = stamp(now[0]+timedelta(minutes=1))
        return {'status': 'complete', 'stations': [
            {'slug': row['slug'], 'status': 'complete_provider_zero',
             'finished_at': finish, 'pages': []} for row in sites
        ]}

    monkeypatch.setattr(run, 'acquire_sites', offline_acquire)

    def argv(*, resume=False, prior_checkpoint=None):
        values = [
            'food-pilot-run', '--manifest', str(f.successor_path),
            '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
            '--prior-prescreen', str(f.prescreen_path),
            '--prior-checkpoint', str(prior_checkpoint or f.checkpoint_path),
            '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
            '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
            '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
        ]
        if resume:
            values.append('--resume')
        return values

    monkeypatch.setattr('sys.argv', argv(prior_checkpoint=tmp_path/'wrong-checkpoint.json'))
    with pytest.raises(AcquisitionStopped, match='confirmation_v20_checkpoint_path'):
        run.main()
    original_claim_raw = claim_path.read_bytes()
    claim = json.loads(original_claim_raw)
    assert claim['claim_state'] == 'committed'
    assert claim['activation_id'] == owner['activation_id']
    assert claim['run_id'] == owner['run_id']
    assert claim['window_started_at'] == stamp(started)
    assert claim['absolute_deadline'] == stamp(started+timedelta(seconds=1800))
    assert claim['execution_intent_sha256'] == EXECUTION_INTENT_SHA256
    assert claim['preparation_owner_intent_sha256']
    assert not marker_path.exists()
    assert not ledger_path.exists()

    now[0] = started+timedelta(minutes=5)
    monkeypatch.setattr('sys.argv', argv())
    run.main()
    output = json.loads(capsys.readouterr().out)
    assert output['status'] == 'complete'
    assert source_calls == ['mocked_hotpepper_adapter']
    ledger = json.loads(ledger_path.read_bytes())
    assert ledger['started_at'] == started.isoformat()
    assert ledger['window_contract']['window_started_at'] == started.isoformat()
    assert ledger['window_contract']['absolute_deadline'] == (started+timedelta(seconds=1800)).isoformat()
    claim_after = json.loads(claim_path.read_bytes())
    assert claim_after['claim_state'] == 'consumer_started'
    assert claim_after['window_started_at'] == stamp(started)
    assert claim_after['absolute_deadline'] == stamp(started+timedelta(seconds=1800))
    assert claim_after['claim_commitment_sha256'] == json.loads(marker_path.read_bytes())['claim_sha256']
    assert original_claim_raw != claim_path.read_bytes()


@pytest.mark.parametrize('terminal_state', ['complete', 'finalization_rejected'])
def test_confirmation_resume_rechecks_terminal_ledger_under_lock(
        tmp_path, monkeypatch, capsys, terminal_state):
    f = synthetic_handoff(tmp_path, monkeypatch)
    started = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    now = [started]
    real_run_datetime = run.datetime
    real_budget_datetime = bounded.datetime

    class ControlledRunDateTime(real_run_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    class ControlledBudgetDateTime(real_budget_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    monkeypatch.setattr(run, 'datetime', ControlledRunDateTime)
    monkeypatch.setattr(bounded, 'datetime', ControlledBudgetDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, started)
    phase_dir = run._confirmation_phase_directory(f.artifact_root)
    _owner, _gate, owner_sha, gate_sha = run.checked_confirmation_gate(
        gate_path, owner_path, f.successor, f.successor_sha, HEAD, f.artifact_root, started)
    pool = run._confirmation_control_chain(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        owner['activation_id'], owner['run_id'], EXECUTION_INTENT_SHA256,
        require_final=True)
    binding = run._confirmation_claim_binding(
        owner, owner_sha, gate_sha, f.successor, f.successor_sha, HEAD,
        f.artifact_root, control_pool=pool)
    claim_path = run._confirmation_claim_path(f.artifact_root, binding)
    _claim, claim_sha, started, deadline = run._read_confirmation_claim(claim_path, binding)
    run._mark_confirmation_budget_started(
        phase_dir, claim_sha, retained_limit=f.successor['budgets']['hp_confirmation']['retained_bytes'],
        claim_root=f.artifact_root)

    prior, checkpoint = run.checked_confirmation_handoff(
        f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path,
        f.v21_manifest_path, f.v21_archive_path, HEAD)
    windows = {f"hp:{row['slug']}:": (row['eligible_from'], row['eligible_until'])
               for row in checkpoint['zero_confirmation']['candidates']}
    completion_window = (checkpoint['zero_confirmation']['batch_eligible_from'],
                         checkpoint['zero_confirmation']['batch_eligible_until'])
    initial_budget = bounded.Budget(
        phase_dir, f.successor['budgets']['hp_confirmation'], f.successor_sha,
        absolute_deadline=deadline, identity_windows=windows,
        completion_window=completion_window, window_started_at=started,
        confirmation_lock_guard=True, confirmation_claim_sha=claim_sha,
        confirmation_claim_path=claim_path, confirmation_claim_root=f.artifact_root,
        confirmation_authority_guard=lambda: run._consume_confirmation_control_claim(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            owner['activation_id'], owner['run_id'], EXECUTION_INTENT_SHA256, resume=False),
        require_real_directory=True)
    initial_budget.close()
    ledger_path = phase_dir/'ledger.json'

    real_handoff = run.checked_confirmation_handoff

    def finish_between_precheck_and_budget(*args):
        result = real_handoff(*args)
        ledger = json.loads(ledger_path.read_bytes())
        if terminal_state == 'complete':
            ledger['status'] = 'complete'
        else:
            ledger['status'] = 'incomplete'
            ledger['finalization_rejections'] = [{'result_sha256': 'synthetic-late-result'}]
        bounded.save_ledger(ledger_path, ledger)
        return result

    monkeypatch.setattr(run, 'checked_confirmation_handoff', finish_between_precheck_and_budget)
    monkeypatch.setenv('HOTPEPPER_API_KEY', 'offline-test-only')
    source_calls = []
    monkeypatch.setattr(run, 'acquire_sites', lambda *_args: source_calls.append('called'))
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root), '--resume',
    ])
    reason = ('confirmation_run_already_finalized' if terminal_state == 'complete'
              else 'confirmation_late_finalization_not_admissible')
    with pytest.raises(AcquisitionStopped, match=reason):
        run.main()
    assert capsys.readouterr().out == ''
    assert source_calls == []


def test_confirmation_candidate_and_batch_windows_are_half_open(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    prior, _ = run.checked_confirmation_handoff(
        f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path,
        f.v21_manifest_path, f.v21_archive_path, HEAD)
    challenge = f.successor['challenge']['order']
    batch_start = datetime.fromisoformat('2026-10-22T08:37:46.527802+00:00')
    batch_end = datetime.fromisoformat('2026-10-24T08:34:49.296391+00:00')
    assert [row['slug'] for row in run.phase_sites(
        f.successor, 'hp_confirmation', prior, now=batch_start)] == f.candidate_ids
    with pytest.raises(AcquisitionStopped, match='outside_real_24_72_hour_confirmation_window'):
        run.phase_sites(f.successor, 'hp_confirmation', prior, now=batch_start-timedelta(microseconds=1))
    with pytest.raises(AcquisitionStopped, match='outside_real_24_72_hour_confirmation_window'):
        run.phase_sites(f.successor, 'hp_confirmation', prior, now=batch_end)
    assert len(challenge) == 64


def test_budget_enforces_confirmation_completion_end_and_absolute_deadline(monkeypatch, tmp_path):
    now = [datetime(2026, 10, 22, 8, 37, 46, 527802, tzinfo=timezone.utc)]
    mono = [100.0]
    real_datetime = bounded.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    monkeypatch.setattr(bounded, 'datetime', ControlledDateTime)
    monkeypatch.setattr(bounded, 'time', SimpleNamespace(monotonic=lambda: mono[0]))
    budget = bounded.Budget.__new__(bounded.Budget)
    budget.absolute_deadline = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
    budget.completion_window = (
        datetime(2026, 10, 22, 8, 37, 46, 527802, tzinfo=timezone.utc),
        datetime(2026, 10, 24, 8, 34, 49, 296391, tzinfo=timezone.utc),
    )
    budget.identity_windows = {
        'hp:emi:': (datetime(2026, 10, 22, 8, 34, 49, 296391, tzinfo=timezone.utc),
                    datetime(2026, 10, 24, 8, 34, 49, 296391, tzinfo=timezone.utc))
    }
    budget.deadline = 200.0
    budget.check_completion()
    now[0] = budget.completion_window[1]
    with pytest.raises(AcquisitionStopped, match='confirmation_completion_window'):
        budget.check_completion()
    now[0] = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    budget.check_window('hp:emi:page1')
    budget.identity_windows = {}
    budget.completion_window = None
    budget.absolute_deadline = datetime(2026, 10, 24, 0, 0, tzinfo=timezone.utc)
    now[0] = budget.absolute_deadline-timedelta(microseconds=1)
    budget.check_window()
    budget.check_completion()
    assert budget.remaining() > 0
    now[0] = budget.absolute_deadline
    with pytest.raises(AcquisitionStopped, match='absolute_source_deadline'):
        budget.check_window()
    with pytest.raises(AcquisitionStopped, match='absolute_source_deadline'):
        budget.check_completion()
    now[0] += timedelta(microseconds=1)
    with pytest.raises(AcquisitionStopped, match='absolute_source_deadline'):
        budget.check_completion()


def test_budget_persists_command_t0_and_refuses_resume_window_reset(monkeypatch, tmp_path):
    now = [datetime(2026, 10, 22, 9, 0, 5, tzinfo=timezone.utc)]
    mono = [100.0]
    real_datetime = bounded.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    monkeypatch.setattr(bounded, 'datetime', ControlledDateTime)
    monkeypatch.setattr(bounded, 'time', SimpleNamespace(monotonic=lambda: mono[0]))
    started = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    deadline = started+timedelta(seconds=1800)
    directory = tmp_path/'confirmation-budget'
    limits = copy.deepcopy(manifest_contract.CONFIRMATION_BUDGET)

    first = bounded.Budget(directory, limits, 'manifest-hash', absolute_deadline=deadline,
                           window_started_at=started)
    assert first.ledger['started_at'] == started.isoformat()
    assert first.ledger['window_contract']['window_started_at'] == started.isoformat()
    assert first.deadline == 1895.0
    first.close()

    now[0] = started+timedelta(minutes=5, seconds=5)
    mono[0] = 500.0
    resumed = bounded.Budget(directory, limits, 'manifest-hash', resume=True,
                             absolute_deadline=deadline, window_started_at=started)
    assert resumed.deadline == 1995.0
    resumed.close()
    with pytest.raises(AcquisitionStopped, match='frozen_acquisition_window_changed'):
        bounded.Budget(directory, limits, 'manifest-hash', resume=True,
                       absolute_deadline=deadline, window_started_at=started+timedelta(seconds=1))


def test_budget_final_ledger_commit_at_v22_cutoff_persists_rejection(monkeypatch, tmp_path):
    now = [datetime(2026, 10, 23, 23, 30, 5, tzinfo=timezone.utc)]
    mono = [100.0]
    real_datetime = bounded.datetime
    real_save_ledger = bounded.save_ledger
    save_calls = []

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    def save_ledger_advancing_on_final_write(path, ledger):
        save_calls.append('save')
        if len(save_calls) == 2:
            now[0] = datetime(2026, 10, 24, 0, 0, tzinfo=timezone.utc)
        return real_save_ledger(path, ledger)

    monkeypatch.setattr(bounded, 'datetime', ControlledDateTime)
    monkeypatch.setattr(bounded, 'time', SimpleNamespace(monotonic=lambda: mono[0]))
    monkeypatch.setattr(bounded, 'save_ledger', save_ledger_advancing_on_final_write)
    started = datetime(2026, 10, 23, 23, 30, tzinfo=timezone.utc)
    deadline = started+timedelta(seconds=1800)
    directory = tmp_path/'budget-final-ledger'
    budget = bounded.Budget(directory, copy.deepcopy(manifest_contract.CONFIRMATION_BUDGET),
                            'manifest-hash', absolute_deadline=deadline,
                            window_started_at=started)
    budget.finalization_guard = budget.check_completion
    budget.finalization_rejection_callback = lambda exc: budget.ledger.setdefault(
        'finalization_rejections', []).append({'reason_type': type(exc).__name__})
    with pytest.raises(AcquisitionStopped, match='absolute_source_deadline'):
        with budget:
            pass
    ledger = json.loads((directory/'ledger.json').read_text())
    assert ledger['status'] == 'incomplete'
    assert ledger['finalization_rejections'] == [{'reason_type': 'AcquisitionStopped'}]
    assert len(save_calls) >= 3


def test_confirmation_budget_rejects_reader_lock_symlink_before_open_or_flock(
        monkeypatch, tmp_path):
    phase_dir = tmp_path/'art'/'hp_confirmation'
    phase_dir.mkdir(parents=True)
    outside_target = tmp_path/'outside'/'lock-target'
    outside_target.parent.mkdir()
    lock_path = phase_dir/'.reader.lock'
    lock_path.symlink_to(outside_target)
    flock_calls = []
    real_flock = bounded.fcntl.flock

    def track_flock(*args):
        flock_calls.append(args)
        return real_flock(*args)

    monkeypatch.setattr(bounded.fcntl, 'flock', track_flock)
    with pytest.raises(AcquisitionStopped, match='confirmation_lock_path_invalid'):
        bounded.Budget(
            phase_dir, copy.deepcopy(manifest_contract.CONFIRMATION_BUDGET),
            'manifest-hash', confirmation_lock_guard=True,
            confirmation_claim_sha='a'*64, require_real_directory=True)

    assert lock_path.is_symlink()
    assert not outside_target.exists()
    assert flock_calls == []
    assert not (phase_dir/'ledger.json').exists()


def test_real_cli_art_lock_delay_past_does_not_start_consumer_or_dispatch(
        tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    started = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    deadline = started+timedelta(seconds=1800)
    now = [started]
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, started)
    real_run_datetime = run.datetime
    real_budget_datetime = bounded.datetime
    real_control_lock = run._confirmation_control_lock

    class ControlledRunDateTime(real_run_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    class ControlledBudgetDateTime(real_budget_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    lock_calls = []

    @contextmanager
    def delay_consumer_lock(root):
        lock_calls.append(root)
        if len(lock_calls) == 4:
            now[0] = deadline
        with real_control_lock(root) as locked:
            yield locked

    monkeypatch.setattr(run, 'datetime', ControlledRunDateTime)
    monkeypatch.setattr(bounded, 'datetime', ControlledBudgetDateTime)
    monkeypatch.setattr(run, '_confirmation_control_lock', delay_consumer_lock)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setenv('HOTPEPPER_API_KEY', 'offline-test-only')
    source_calls = []
    monkeypatch.setattr(run, 'acquire_sites', lambda *_args: source_calls.append('source'))
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ])
    with pytest.raises(AcquisitionStopped, match='confirmation_completion_deadline_expired'):
        run.main()

    claim_path = run._control_pool_paths(
        f.artifact_root, owner['activation_id'], owner['run_id'])['burn_claim']
    claim = run._control_json(claim_path.read_bytes())
    assert len(lock_calls) == 4
    assert claim['claim_state'] == 'committed'
    assert claim['window_started_at'] == stamp(started)
    assert (f.artifact_root/'hp_confirmation'/'activation-budget-started.json').exists()
    assert not (f.artifact_root/'hp_confirmation'/'ledger.json').exists()
    assert source_calls == []


def test_budget_counts_art_root_claims_against_confirmation_retention(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    output_root = f.artifact_root
    run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, output_root,
        'synthetic-activation-1', 'synthetic-run-1', EXECUTION_INTENT_SHA256)
    phase_dir = output_root/'hp_confirmation'
    phase_dir.mkdir()
    assert run._confirmation_control_bytes(output_root) == manifest_contract.CONFIRMATION_CONTROL_POOL_BYTES
    limits = copy.deepcopy(manifest_contract.CONFIRMATION_BUDGET)
    limits['retained_bytes'] = manifest_contract.CONFIRMATION_CONTROL_POOL_BYTES

    with pytest.raises(AcquisitionStopped, match='retained_ledger_budget'):
        bounded.Budget(
            phase_dir, limits, 'manifest-hash', confirmation_claim_root=output_root,
            require_real_directory=True)
    assert not (phase_dir/'ledger.json').exists()


def test_second_pool_is_frozen_during_consumer_result_write(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    started = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)

    class ControlledDateTime(run.datetime):
        @classmethod
        def now(cls, tz=None):
            return started.astimezone(tz) if tz else started

    class ControlledBudgetDateTime(bounded.datetime):
        @classmethod
        def now(cls, tz=None):
            return started.astimezone(tz) if tz else started

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(bounded, 'datetime', ControlledBudgetDateTime)
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, started)
    phase_dir = run._confirmation_phase_directory(f.artifact_root)
    _owner, _gate, owner_sha, gate_sha = run.checked_confirmation_gate(
        gate_path, owner_path, f.successor, f.successor_sha, HEAD,
        f.artifact_root, started)
    pool = run._confirmation_control_chain(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        owner['activation_id'], owner['run_id'], EXECUTION_INTENT_SHA256,
        require_final=True)
    binding = run._confirmation_claim_binding(
        owner, owner_sha, gate_sha, f.successor, f.successor_sha, HEAD,
        f.artifact_root, control_pool=pool)
    claim_path = run._confirmation_claim_path(f.artifact_root, binding)
    _claim, claim_sha, _started, deadline = run._read_confirmation_claim(
        claim_path, binding)
    run._mark_confirmation_budget_started(
        phase_dir, claim_sha, retained_limit=f.successor['budgets']['hp_confirmation']['retained_bytes'],
        claim_root=f.artifact_root)
    budget = bounded.Budget(
        phase_dir, f.successor['budgets']['hp_confirmation'], f.successor_sha,
        absolute_deadline=deadline, window_started_at=started,
        confirmation_lock_guard=True, confirmation_claim_sha=claim_sha,
        confirmation_claim_path=claim_path, confirmation_claim_root=f.artifact_root,
        confirmation_authority_guard=lambda: run._consume_confirmation_control_claim(
            f.successor, f.successor_sha, HEAD, f.artifact_root,
            owner['activation_id'], owner['run_id'], EXECUTION_INTENT_SHA256,
            resume=False),
        require_real_directory=True)

    retained_limit = f.successor['budgets']['hp_confirmation']['retained_bytes']
    pool_bytes = manifest_contract.CONFIRMATION_CONTROL_POOL_BYTES
    control_bytes = run._confirmation_control_bytes(f.artifact_root)
    phase_bytes = run._physical_retained_bytes(phase_dir)
    filler_size = retained_limit-control_bytes-pool_bytes-phase_bytes
    value = {'payload': 'x'*10_000}
    result_raw = encoded(value)
    assert 0 < len(result_raw) < pool_bytes
    assert filler_size > 0
    with (phase_dir/'.synthetic-retention-fill.bin').open('wb') as stream:
        stream.truncate(filler_size)

    at_result_open = threading.Event()
    allow_result_write = threading.Event()
    original_open = Path.open

    def pause_result_open(path, mode='r', *args, **kwargs):
        if path.parent == phase_dir and path.name.startswith('result-') and mode == 'xb':
            at_result_open.set()
            if not allow_result_write.wait(5):
                raise TimeoutError('result write interleaving timed out')
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', pause_result_open)
    outcome, errors = {}, []

    def publish_result():
        try:
            outcome['result'] = run.immutable_result(
                phase_dir, value, retained_limit,
                retained_extra_bytes=control_bytes)
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=publish_result, name='result-writer')
    try:
        thread.start()
        assert at_result_open.wait(5), 'result did not reach the post-check write boundary'
        with pytest.raises(AcquisitionStopped, match='confirmation_control_pool_frozen'):
            run.reserve_confirmation_control_pool(
                f.successor, f.successor_sha, HEAD, f.artifact_root,
                'second-synthetic-activation', 'second-synthetic-run',
                EXECUTION_INTENT_SHA256)
    finally:
        allow_result_write.set()
        thread.join(timeout=10)
        budget.close()

    assert not thread.is_alive(), 'result writer deadlocked with ART reservation'
    assert errors == []
    result_path, result_sha = outcome['result']
    assert result_path.read_bytes() == result_raw
    assert sha(result_raw) == result_sha
    assert run._confirmation_control_bytes(f.artifact_root) == pool_bytes
    assert (run._physical_retained_bytes(phase_dir)+pool_bytes
            == retained_limit-pool_bytes+len(result_raw))
    assert physical_regular_bytes(f.artifact_root) <= f.successor['budgets']['total_retained_bytes']
    assert not list(phase_dir.glob('*.pending'))


def test_preconsumer_marker_write_serializes_with_pool_capacity_check(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    run.reserve_confirmation_control_pool(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        'first-synthetic-activation', 'first-synthetic-run', EXECUTION_INTENT_SHA256)
    phase_dir = run._confirmation_phase_directory(f.artifact_root)
    retained_limit = f.successor['budgets']['hp_confirmation']['retained_bytes']
    pool_bytes = manifest_contract.CONFIRMATION_CONTROL_POOL_BYTES
    control_bytes = run._confirmation_control_bytes(f.artifact_root)
    filler_size = retained_limit-control_bytes-pool_bytes
    assert filler_size > 0
    with (phase_dir/'.synthetic-retention-fill.bin').open('wb') as stream:
        stream.truncate(filler_size)

    at_marker_check = threading.Event()
    allow_marker_check = threading.Event()
    original_physical_retained_bytes = run._physical_retained_bytes

    def pause_marker_capacity_check(directory):
        if (threading.current_thread().name == 'marker-writer'
                and Path(directory) == phase_dir):
            at_marker_check.set()
            if not allow_marker_check.wait(5):
                raise TimeoutError('marker capacity interleaving timed out')
        return original_physical_retained_bytes(directory)

    monkeypatch.setattr(run, '_physical_retained_bytes', pause_marker_capacity_check)
    outcomes, errors = {}, []
    reserve_attempted = threading.Event()

    def write_marker():
        try:
            outcomes['marker'] = run._mark_confirmation_budget_started(
                phase_dir, 'a'*64, retained_limit=retained_limit,
                claim_root=f.artifact_root)
        except BaseException as exc:
            errors.append(exc)

    def reserve_second_pool():
        reserve_attempted.set()
        try:
            outcomes['pool'] = run.reserve_confirmation_control_pool(
                f.successor, f.successor_sha, HEAD, f.artifact_root,
                'second-synthetic-activation', 'second-synthetic-run',
                EXECUTION_INTENT_SHA256)
        except BaseException as exc:
            outcomes['pool_error'] = exc

    marker_thread = threading.Thread(target=write_marker, name='marker-writer')
    pool_thread = threading.Thread(target=reserve_second_pool, name='pool-reserver')
    try:
        marker_thread.start()
        assert at_marker_check.wait(5), 'marker did not reach its capacity snapshot'
        pool_thread.start()
        assert reserve_attempted.wait(5)
    finally:
        allow_marker_check.set()
        marker_thread.join(timeout=10)
        pool_thread.join(timeout=10)

    assert not marker_thread.is_alive() and not pool_thread.is_alive(), 'ART lock order deadlocked'
    assert errors == []
    assert outcomes['marker']['kind'] == 'hp_confirmation_budget_started'
    assert isinstance(outcomes.get('pool_error'), AcquisitionStopped)
    assert outcomes['pool_error'].args == ('retained_control_pool_budget',)
    assert (phase_dir/'activation-budget-started.json').exists()
    assert run._confirmation_control_bytes(f.artifact_root) == pool_bytes
    assert run._physical_retained_bytes(phase_dir)+pool_bytes <= retained_limit
    assert physical_regular_bytes(f.artifact_root) <= f.successor['budgets']['total_retained_bytes']


def test_run_main_uses_all_thirteen_and_confirmation_deadline_without_network(
        tmp_path, monkeypatch, capsys):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = [datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    output_root = f.artifact_root
    owner_path, gate_path, _owner, _gate = authorization_files(f, tmp_path, output_root, now[0])
    captured = {}
    source_calls = []

    class OfflineBudget:
        def __init__(self, directory, limits, manifest_hash, **kwargs):
            captured.update(directory=directory, limits=limits, manifest_hash=manifest_hash, **kwargs)
            self.limits = limits
            self.ledger = {}
            self.finalization_guard = None
            self.finalization_rejection_callback = None
            self.finalization_guard = None
            self.finalization_rejection_callback = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, *_args):
            if exc_type:
                self.ledger['status'] = 'incomplete'
                captured['ledger'] = self.ledger
                return False
            try:
                if self.finalization_guard:
                    self.finalization_guard()
                self.ledger['status'] = 'complete'
                if self.finalization_guard:
                    self.finalization_guard()
            except BaseException as exc:
                if self.finalization_rejection_callback:
                    self.finalization_rejection_callback(exc)
                self.ledger['status'] = 'incomplete'
                captured['ledger'] = self.ledger
                raise
            captured['ledger'] = self.ledger
            return False

        def check_completion(self):
            deadline = datetime.fromisoformat(captured['absolute_deadline'].replace('Z', '+00:00'))
            if now[0] >= deadline:
                raise AcquisitionStopped('offline_deadline_guard')

    def offline_acquire(sites, _budget, _key):
        source_calls.append('mocked_hotpepper_adapter')
        assert [row['slug'] for row in sites] == f.candidate_ids
        finish = stamp(now[0]+timedelta(minutes=1))
        return {'status': 'complete', 'stations': [
            {'slug': row['slug'], 'status': 'complete_provider_zero',
             'finished_at': finish, 'pages': []} for row in sites
        ]}

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr(run, 'Budget', OfflineBudget)
    monkeypatch.setattr(run, 'acquire_sites', offline_acquire)
    def offline_immutable(_directory, _value, _limit, *, commit_guard=None,
                          retained_extra_bytes=0):
        assert retained_extra_bytes > 0
        if commit_guard:
            commit_guard()
        return tmp_path/'result.json', 'result-hash'

    monkeypatch.setattr(run, 'immutable_result', offline_immutable)
    monkeypatch.setenv('HOTPEPPER_API_KEY', 'offline-test-only')
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(output_root),
    ])
    run.main()
    response = json.loads(capsys.readouterr().out)
    assert response['status'] == 'complete'
    assert source_calls == ['mocked_hotpepper_adapter']
    assert captured['absolute_deadline'] == '2026-10-22T09:30:00Z'
    assert captured['window_started_at'] == '2026-10-22T09:00:00Z'
    assert captured['limits'] == manifest_contract.CONFIRMATION_BUDGET
    assert len(captured['identity_windows']) == 13
    assert captured['completion_window'] == (
        '2026-10-22T08:37:46.527802+00:00', '2026-10-24T08:34:49.296391+00:00')
    assert captured['ledger']['status'] == 'complete'
    assert not captured['ledger'].get('finalization_rejections')


def test_immutable_result_preserves_late_published_envelope_as_failure_evidence(tmp_path):
    directory = tmp_path/'hp_confirmation'
    directory.mkdir()
    value = {'phase': 'hp_confirmation', 'result': {'status': 'complete'}}
    raw = encoded(value)
    expected = directory/f'result-{sha(raw)}.json'
    guard_calls = []

    def fail_after_publish():
        guard_calls.append('guard')
        if len(guard_calls) == 2:
            raise AcquisitionStopped('deadline_after_publish')

    with pytest.raises(AcquisitionStopped, match='deadline_after_publish'):
        run.immutable_result(directory, value, 1024*1024, commit_guard=fail_after_publish)
    assert expected.read_bytes() == raw
    assert list(directory.glob('*.pending')) == []


@pytest.mark.parametrize('deadline_stage', ['immutable_result', 'final_ledger_persist'])
def test_run_main_finalization_crossing_deadline_never_reports_complete(
        deadline_stage, tmp_path, monkeypatch, capsys):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = [datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    output_root = f.artifact_root
    owner_path, gate_path, _owner, _gate = authorization_files(f, tmp_path, output_root, now[0])
    captured = {}
    source_calls = []

    class OfflineBudget:
        def __init__(self, directory, limits, manifest_hash, **kwargs):
            captured.update(directory=directory, limits=limits, manifest_hash=manifest_hash, **kwargs)
            self.limits = limits
            self.ledger = {}
            self.finalization_guard = None
            self.finalization_rejection_callback = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, *_args):
            if exc_type:
                self.ledger['status'] = 'incomplete'
                captured['ledger'] = self.ledger
                return False
            try:
                if self.finalization_guard:
                    self.finalization_guard()
                self.ledger['status'] = 'complete'
                if deadline_stage == 'final_ledger_persist':
                    now[0] = datetime.fromisoformat(
                        captured['absolute_deadline'].replace('Z', '+00:00'))
                if self.finalization_guard:
                    self.finalization_guard()
            except BaseException:
                self.ledger['status'] = 'incomplete'
                captured['ledger'] = self.ledger
                raise
            return False

        def check_completion(self):
            deadline = datetime.fromisoformat(captured['absolute_deadline'].replace('Z', '+00:00'))
            if now[0] >= deadline:
                raise AcquisitionStopped('offline_deadline_guard')

    def offline_acquire(sites, _budget, _key):
        source_calls.append('mocked_hotpepper_adapter')
        finish = stamp(now[0]+timedelta(minutes=1))
        return {'status': 'complete', 'stations': [
            {'slug': row['slug'], 'status': 'complete_provider_zero', 'finished_at': finish, 'pages': []}
            for row in sites
        ]}

    def late_immutable(_directory, _value, _limit, *, commit_guard=None,
                       retained_extra_bytes=0):
        assert retained_extra_bytes > 0
        if commit_guard:
            commit_guard()
        if deadline_stage == 'immutable_result':
            now[0] = datetime.fromisoformat(captured['absolute_deadline'].replace('Z', '+00:00'))
        return tmp_path/'late-result.json', 'late-result-sha'

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr(run, 'Budget', OfflineBudget)
    monkeypatch.setattr(run, 'acquire_sites', offline_acquire)
    monkeypatch.setattr(run, 'immutable_result', late_immutable)
    monkeypatch.setenv('HOTPEPPER_API_KEY', 'offline-test-only')
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(output_root),
    ])
    with pytest.raises(AcquisitionStopped):
        run.main()
    assert capsys.readouterr().out == ''
    assert source_calls == ['mocked_hotpepper_adapter']
    assert captured['ledger']['status'] == 'incomplete'
    rejection = captured['ledger']['finalization_rejections'][0]
    assert len(rejection['result_sha256']) == 64
    assert all(char in '0123456789abcdef' for char in rejection['result_sha256'])
    assert rejection['reason_type'] == 'AcquisitionStopped'


def test_real_cli_rejects_late_final_ledger_commit_and_resume(tmp_path, monkeypatch, capsys):
    f = synthetic_handoff(tmp_path, monkeypatch)
    started = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    now = [started]
    mono = [100.0]
    real_run_datetime = run.datetime
    real_budget_datetime = bounded.datetime
    real_save_ledger = bounded.save_ledger
    save_calls = []

    class ControlledRunDateTime(real_run_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    class ControlledBudgetDateTime(real_budget_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    deadline = started+timedelta(seconds=1800)

    def advance_on_final_ledger_write(path, ledger):
        save_calls.append('persist')
        if len(save_calls) == 2:
            now[0] = deadline
        return real_save_ledger(path, ledger)

    monkeypatch.setattr(run, 'datetime', ControlledRunDateTime)
    monkeypatch.setattr(bounded, 'datetime', ControlledBudgetDateTime)
    monkeypatch.setattr(run.time, 'monotonic', lambda: mono[0])
    monkeypatch.setattr(bounded, 'save_ledger', advance_on_final_ledger_write)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setenv('HOTPEPPER_API_KEY', 'offline-test-only')
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, started)

    source_calls = []

    def offline_acquire(sites, _budget, _key):
        source_calls.append('mocked_hotpepper_adapter')
        finish = stamp(started+timedelta(minutes=1))
        return {'status': 'complete', 'stations': [
            {'slug': row['slug'], 'status': 'complete_provider_zero', 'finished_at': finish, 'pages': []}
            for row in sites
        ]}

    monkeypatch.setattr(run, 'acquire_sites', offline_acquire)
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ])
    with pytest.raises(AcquisitionStopped, match='absolute_source_deadline'):
        run.main()

    assert capsys.readouterr().out == ''
    assert source_calls == ['mocked_hotpepper_adapter']
    phase_dir = f.artifact_root/'hp_confirmation'
    result_paths = list(phase_dir.glob('result-*.json'))
    assert len(result_paths) == 1
    result_path = result_paths[0]
    assert json.loads(result_path.read_bytes())['result']['status'] == 'complete'
    ledger = json.loads((phase_dir/'ledger.json').read_bytes())
    assert ledger['status'] == 'incomplete'
    rejection = ledger['finalization_rejections'][0]
    assert rejection['result_sha256'] == sha(result_path.read_bytes())
    assert rejection['reason_type'] == 'AcquisitionStopped'
    assert len(save_calls) >= 3

    pool = run._confirmation_control_chain(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        owner['activation_id'], owner['run_id'], EXECUTION_INTENT_SHA256,
        require_final=True)
    binding = run._confirmation_claim_binding(
        owner, sha(owner_path.read_bytes()), sha(gate_path.read_bytes()),
        f.successor, f.successor_sha, HEAD, f.artifact_root, control_pool=pool)
    claim_path = run._confirmation_claim_path(f.artifact_root, binding)
    resume_args = SimpleNamespace(resume=True, output_root=f.artifact_root)
    with pytest.raises(AcquisitionStopped, match='confirmation_late_finalization_not_admissible'):
        run._confirmation_run_window(
            resume_args, f.successor_sha, deadline-timedelta(seconds=1),
            phase_dir=phase_dir, claim_binding=binding, claim_path=claim_path)


def test_run_main_rejects_arbitrary_confirmation_root_before_output(
        tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = [datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    sibling = tmp_path/'arbitrary-sibling'
    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(tmp_path/'unused-gate.json'),
        '--owner-activation', str(tmp_path/'unused-owner.json'),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(sibling),
    ])
    with pytest.raises(AcquisitionStopped, match='confirmation_artifact_root_mismatch'):
        run.main()
    assert not sibling.exists()


def test_run_main_rejects_confirmation_phase_symlink_before_ledger_or_budget(
        tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = [datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    owner_path, gate_path, _owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, now[0])
    frozen_dir = f.artifact_root/'target-v4'
    frozen_dir.mkdir()
    frozen_marker = frozen_dir/'preserved.bin'
    frozen_marker.write_bytes(b'frozen synthetic evidence')
    poisoned_ledger = frozen_dir/'ledger.json'
    poisoned_ledger.write_bytes(b'must not be read through the symlink')
    phase_dir = f.artifact_root/'hp_confirmation'
    phase_dir.symlink_to(frozen_dir, target_is_directory=True)
    owner_sha = sha(owner_path.read_bytes())
    gate_sha = sha(gate_path.read_bytes())
    binding = run._confirmation_claim_binding(
        _owner, owner_sha, gate_sha, f.successor, f.successor_sha, HEAD,
        f.artifact_root)
    claim_path = run._confirmation_claim_path(f.artifact_root, binding)
    source_calls = []
    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr(run, 'acquire_sites', lambda *_args: source_calls.append('called'))
    argv = [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ]
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(AcquisitionStopped, match='confirmation_phase_directory_invalid'):
        run.main()

    assert phase_dir.is_symlink()
    assert frozen_marker.read_bytes() == b'frozen synthetic evidence'
    assert poisoned_ledger.read_bytes() == b'must not be read through the symlink'
    assert not (frozen_dir/'.reader.lock').exists()
    assert not (frozen_dir/'activation-budget-started.json').exists()
    claim = json.loads(claim_path.read_bytes())
    assert claim['window_started_at'] == stamp(now[0])
    assert claim['absolute_deadline'] == stamp(now[0]+timedelta(seconds=1800))
    assert claim['claim_state'] == 'terminal_rejected'
    assert claim['terminal_reason'] == 'confirmation_phase_directory_invalid'
    original_claim = claim_path.read_bytes()
    assert source_calls == []

    phase_dir.unlink()
    now[0] += timedelta(minutes=5)
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(AcquisitionStopped, match='confirmation_activation_terminal_rejection'):
        run.main()
    assert claim_path.read_bytes() == original_claim
    assert source_calls == []


def test_run_main_terminalizes_non_directory_phase_path_in_art_control_slot(
        tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    started = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    now = [started]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, started)
    phase_path = f.artifact_root/'hp_confirmation'
    phase_path.write_bytes(b'unsafe synthetic phase file')
    source_calls = []
    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr(run, 'acquire_sites', lambda *_args: source_calls.append('source'))
    argv = [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ]
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(AcquisitionStopped, match='confirmation_phase_directory_invalid'):
        run.main()
    assert phase_path.read_bytes() == b'unsafe synthetic phase file'
    claim_path = run._control_pool_paths(
        f.artifact_root, owner['activation_id'], owner['run_id'])['burn_claim']
    claim = run._control_json(claim_path.read_bytes())
    assert claim['claim_state'] == 'terminal_rejected'
    assert claim['terminal_reason'] == 'confirmation_phase_directory_invalid'
    phase_path.unlink()
    now[0] += timedelta(minutes=5)
    with pytest.raises(AcquisitionStopped, match='confirmation_activation_terminal_rejection'):
        run.main()
    assert source_calls == []


def create_global_retention_pressure(f):
    root = f.artifact_root
    phase_bytes = run._confirmation_phase_bytes(root)
    control_bytes = run._confirmation_control_bytes(root)
    retained = run._physical_retained_bytes(root)
    projected = retained-phase_bytes-control_bytes+f.successor['budgets']['hp_confirmation']['retained_bytes']
    filler_size = f.successor['budgets']['total_retained_bytes']-projected+1
    assert filler_size > 0
    filler = root/'.synthetic-global-retention-pressure.bin'
    with filler.open('wb') as stream:
        stream.truncate(filler_size)
    return filler


def test_run_main_global_retention_counts_common_art_root_files(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = [datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    owner_path, gate_path, _owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, now[0])
    filler = create_global_retention_pressure(f)

    class MustNotStartBudget:
        def __init__(self, *_args, **_kwargs):
            pytest.fail('global retention preflight should reject before Budget or acquisition')

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr(run, 'Budget', MustNotStartBudget)
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ])
    with pytest.raises(AcquisitionStopped, match='total_retained_budget'):
        run.main()
    assert filler.stat().st_size > 0
    controls = run._confirmation_control_files(f.artifact_root)
    assert len(controls) == 6
    assert all(size == manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES
               for _path, size in controls)
    assert physical_regular_bytes(f.artifact_root) <= f.successor['budgets']['total_retained_bytes']


def test_run_main_global_cap_restoration_reuses_original_claim_window(
        tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = [datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)]
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, now[0])
    pool = run._confirmation_control_chain(
        f.successor, f.successor_sha, HEAD, f.artifact_root,
        owner['activation_id'], owner['run_id'], EXECUTION_INTENT_SHA256,
        require_final=True)
    claim_path = pool['paths']['burn_claim']
    original_claim = claim_path.read_bytes()
    create_global_retention_pressure(f)

    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    monkeypatch.setattr(bounded, 'datetime', ControlledDateTime)
    monkeypatch.setenv('HOTPEPPER_API_KEY', 'offline-test-only')
    source_calls = []

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr(run, 'acquire_sites', lambda sites, _budget, _key: (
        source_calls.append('called'), {'status': 'complete', 'stations': [
            {'slug': row['slug'], 'status': 'complete_provider_zero',
             'finished_at': stamp(now[0]+timedelta(minutes=1)), 'pages': []} for row in sites
        ]})[1])
    argv = [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--prior-v21-manifest', str(f.v21_manifest_path), '--prior-v21-archive', str(f.v21_archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ]
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(AcquisitionStopped, match='total_retained_budget'):
        run.main()
    assert claim_path.read_bytes() == original_claim
    assert source_calls == []

    filler = f.artifact_root/'.synthetic-global-retention-pressure.bin'
    filler.unlink()
    now[0] += timedelta(minutes=5)
    monkeypatch.setattr('sys.argv', argv)
    run.main()
    assert source_calls == ['called']
    ledger = json.loads((f.artifact_root/'hp_confirmation'/'ledger.json').read_bytes())
    original_started = now[0]-timedelta(minutes=5)
    assert ledger['started_at'] == original_started.isoformat()
    claim = json.loads(claim_path.read_bytes())
    assert claim['window_started_at'] == stamp(original_started)
    assert claim['claim_state'] == 'consumer_started'


def test_nonconfirmation_phase_keeps_original_global_cutoff(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    source = f.successor
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (source, f.successor_sha))
    monkeypatch.setattr(run, 'checked_gate', lambda *_args: None)
    now = [datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(tmp_path/'old-gate.json'), '--phase', 'overture_metadata',
        '--output-root', str(tmp_path/'non-confirmation-output'),
    ])
    with pytest.raises(AcquisitionStopped, match='frozen_pilot_window_expired'):
        run.main()
