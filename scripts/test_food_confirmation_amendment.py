"""Offline controls for the prospective V20 confirmation-only amendment."""
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from food_pilot import bounded, manifest as manifest_contract, run
from food_pilot.acquire_osm import encoded
from food_pilot.bounded import AcquisitionStopped


HEAD = 'a' * 40


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
    successor = manifest_contract.make_confirmation_successor(
        source_raw, artifact_root=artifact_root, runtime_root=run.ROOT, code_head=HEAD)
    successor_path = tmp_path/'successor-manifest.json'
    successor_raw = manifest_contract.canonical_manifest_bytes(successor)
    successor_path.write_bytes(successor_raw)
    return SimpleNamespace(
        artifact_root=artifact_root, source=source, source_raw=source_raw,
        source_path=source_path, archive_path=archive_path, archive_raw=archive_raw,
        prescreen_path=prescreen_path, prescreen_raw=prescreen_raw,
        checkpoint_path=checkpoint_path, checkpoint=checkpoint,
        checkpoint_raw=checkpoint_raw, successor=successor,
        successor_path=successor_path, successor_raw=successor_raw,
        successor_sha=sha(successor_raw), candidate_ids=candidate_ids,
    )


def authorization_files(f, tmp_path, output_root, now, *, head=HEAD):
    auth_dir = tmp_path/'authorization'
    auth_dir.mkdir(exist_ok=True)
    owner_path = auth_dir/'owner-activation.json'
    gate_path = auth_dir/'root-release.json'
    map_sha = manifest_contract.canonical_code_map_sha256(f.successor['code_sha256'])
    owner = {
        'kind': 'owner_hp_confirmation_activation',
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
        'activation_id': 'synthetic-activation-1',
        'run_id': 'synthetic-run-1',
        'created_at': stamp(now-timedelta(minutes=1)),
        'expires_at': stamp(now+timedelta(hours=1)),
    }
    owner_raw = encoded(owner)
    owner_sha = sha(owner_raw)
    root_check = {
        'manifest_sha256': f.successor_sha,
        'git_head': head,
        'code_map_sha256': map_sha,
        'allowed_phases': ['hp_confirmation'],
        'output_root': str(output_root.resolve()),
        'owner_activation_sha256': owner_sha,
    }
    gate = {
        'kind': 'root_hp_confirmation_release',
        'phase': 'hp_confirmation',
        'allowed_phases': ['hp_confirmation'],
        'manifest_sha256': f.successor_sha,
        'git_head': head,
        'code_map_sha256': map_sha,
        'output_root': str(output_root.resolve()),
        'native_review_approved_head': head,
        'owner_activation_sha256': owner_sha,
        'root_manifest_check': root_check,
        'released_at': stamp(now-timedelta(minutes=1)),
        'expires_at': stamp(now+timedelta(hours=1)),
    }
    owner_path.write_bytes(owner_raw)
    gate_path.write_bytes(encoded(gate))
    return owner_path, gate_path, owner, gate


def test_successor_is_confirmation_only_and_preserves_v20_budgets(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    assert f.successor['version'] == 'v21'
    assert f.successor['supersedes_manifest_sha256'] == sha(f.source_raw)
    assert f.successor['source_window']['core_hp_complete_before'] == '2026-10-22T00:00:00Z'
    assert f.successor['confirmation_amendment']['confirmation_completion_before'] == '2026-10-23T00:00:00Z'
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


def test_historical_handoff_uses_checkpoint_and_opaque_result_hash(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    prior, checkpoint = run.checked_confirmation_handoff(
        f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path, HEAD)
    assert f.prescreen_raw.startswith(b'opaque')
    assert [row['slug'] for row in prior['stations']] == f.candidate_ids
    assert run.confirmation_checkpoint(prior) == checkpoint['zero_confirmation']


def test_historical_handoff_rejects_current_prior_path_and_changed_checkpoint(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    with pytest.raises(AcquisitionStopped, match='confirmation_v20_prescreen_path'):
        run.checked_confirmation_handoff(
            f.successor, f.successor_path, f.checkpoint_path, f.source_path, f.archive_path, HEAD)
    f.checkpoint_path.write_bytes(f.checkpoint_raw+b'changed')
    with pytest.raises(AcquisitionStopped, match='confirmation_v20_checkpoint_hash'):
        run.checked_confirmation_handoff(
            f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path, HEAD)


def test_historical_handoff_rejects_checkpoint_order_even_with_matching_pinned_hash(tmp_path, monkeypatch):
    def reverse_candidates(checkpoint):
        checkpoint['zero_confirmation']['candidates'][0:2] = reversed(
            checkpoint['zero_confirmation']['candidates'][0:2])

    f = synthetic_handoff(tmp_path, monkeypatch, checkpoint_edit=reverse_candidates)
    with pytest.raises(AcquisitionStopped, match='confirmation_checkpoint_order_or_status'):
        run.checked_confirmation_handoff(
            f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path, HEAD)


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
        gate_path.write_bytes(encoded(changed))
        with pytest.raises(AcquisitionStopped, match='confirmation_root_gate_binding'):
            run.checked_confirmation_gate(
                gate_path, owner_path, f.successor, f.successor_sha, HEAD, f.artifact_root, now)


def test_confirmation_gate_rejects_missing_and_expired_owner_root_receipts(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    owner_path, gate_path, owner, gate = authorization_files(f, tmp_path, f.artifact_root, now)
    with pytest.raises(AcquisitionStopped, match='confirmation_owner_or_root_release_unreadable'):
        run.checked_confirmation_gate(
            gate_path, tmp_path/'missing-owner.json', f.successor,
            f.successor_sha, HEAD, f.artifact_root, now)
    owner['expires_at'] = stamp(now)
    owner_path.write_bytes(encoded(owner))
    gate['owner_activation_sha256'] = sha(owner_path.read_bytes())
    gate['root_manifest_check']['owner_activation_sha256'] = sha(owner_path.read_bytes())
    gate_path.write_bytes(encoded(gate))
    with pytest.raises(AcquisitionStopped, match='confirmation_owner_activation_not_fresh'):
        run.checked_confirmation_gate(
            gate_path, owner_path, f.successor, f.successor_sha, HEAD, f.artifact_root, now)


def test_confirmation_t0_uses_minimum_of_wall_and_absolute_deadline(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    args = SimpleNamespace(resume=False, output_root=tmp_path/'out')
    start = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    started, deadline, remaining = run._confirmation_run_window(args, f.successor_sha, start)
    assert started == start
    assert deadline == start+timedelta(seconds=1800)
    assert remaining == 1800

    near_cutoff = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)-timedelta(minutes=10)
    _started, deadline, remaining = run._confirmation_run_window(args, f.successor_sha, near_cutoff)
    assert deadline == datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
    assert remaining == 600
    for expired in (datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc),
                    datetime(2026, 10, 23, 0, 1, tzinfo=timezone.utc)):
        with pytest.raises(AcquisitionStopped, match='confirmation_completion_deadline_expired'):
            run._confirmation_run_window(args, f.successor_sha, expired)


def test_confirmation_resume_retains_original_t0_and_deadline(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    start = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    deadline = start+timedelta(seconds=1800)
    output = tmp_path/'out'
    phase = output/'hp_confirmation'
    phase.mkdir(parents=True)
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
    args = SimpleNamespace(resume=True, output_root=output)
    resumed_start, resumed_deadline, remaining = run._confirmation_run_window(
        args, f.successor_sha, start+timedelta(minutes=5))
    assert resumed_start == start
    assert resumed_deadline == deadline
    assert remaining == 1500
    with pytest.raises(AcquisitionStopped, match='confirmation_completion_deadline_expired'):
        run._confirmation_run_window(args, f.successor_sha, deadline)
    ledger['finalization_rejections'] = [{'result_sha256': 'late-result'}]
    (phase/'ledger.json').write_bytes(encoded(ledger))
    with pytest.raises(AcquisitionStopped, match='confirmation_late_finalization_not_admissible'):
        run._confirmation_run_window(args, f.successor_sha, start+timedelta(minutes=5))


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
    assert claim['claim_state'] == 'preflight_claimed'
    assert claim['activation_id'] == owner['activation_id']
    assert claim['run_id'] == owner['run_id']
    assert claim['window_started_at'] == stamp(started)
    assert claim['absolute_deadline'] == stamp(started+timedelta(seconds=1800))
    assert claim['owner_activation_sha256'] == sha(owner_path.read_bytes())
    assert not marker_path.exists()
    assert not ledger_path.exists()

    now[0] = started+timedelta(minutes=5)
    monkeypatch.setattr('sys.argv', argv())
    with pytest.raises(AcquisitionStopped, match='confirmation_activation_already_claimed'):
        run.main()
    assert claim_path.read_bytes() == original_claim_raw
    assert source_calls == []

    # A corrected preflight may continue only as the same resume, with original T0/D.
    monkeypatch.setattr('sys.argv', argv(resume=True))
    run.main()
    output = json.loads(capsys.readouterr().out)
    assert output['status'] == 'complete'
    assert source_calls == ['mocked_hotpepper_adapter']
    ledger = json.loads(ledger_path.read_bytes())
    assert ledger['started_at'] == started.isoformat()
    assert ledger['window_contract']['window_started_at'] == started.isoformat()
    assert ledger['window_contract']['absolute_deadline'] == (started+timedelta(seconds=1800)).isoformat()
    assert sha(claim_path.read_bytes()) == json.loads(marker_path.read_bytes())['claim_sha256']


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
    binding = run._confirmation_claim_binding(
        owner, owner_sha, gate_sha, f.successor, f.successor_sha, HEAD, f.artifact_root)
    deadline = started+timedelta(seconds=1800)
    claim_path = run._confirmation_claim_path(f.artifact_root, binding)
    _claim, claim_sha = run._prepare_confirmation_claim(
        claim_path, binding, started, deadline, resume=False, manifest=f.successor)
    run._mark_confirmation_budget_started(phase_dir, claim_sha)

    prior, checkpoint = run.checked_confirmation_handoff(
        f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path, HEAD)
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
        f.successor, f.prescreen_path, f.checkpoint_path, f.source_path, f.archive_path, HEAD)
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
    budget.absolute_deadline = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
    now[0] = budget.absolute_deadline
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


def test_budget_final_ledger_commit_crossing_deadline_persists_rejection(monkeypatch, tmp_path):
    now = [datetime(2026, 10, 22, 9, 0, 5, tzinfo=timezone.utc)]
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
            now[0] = datetime(2026, 10, 22, 9, 30, tzinfo=timezone.utc)
        return real_save_ledger(path, ledger)

    monkeypatch.setattr(bounded, 'datetime', ControlledDateTime)
    monkeypatch.setattr(bounded, 'time', SimpleNamespace(monotonic=lambda: mono[0]))
    monkeypatch.setattr(bounded, 'save_ledger', save_ledger_advancing_on_final_write)
    started = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
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


def test_budget_counts_art_root_claims_against_confirmation_retention(tmp_path):
    output_root = tmp_path/'art'
    phase_dir = output_root/'hp_confirmation'
    phase_dir.mkdir(parents=True)
    (output_root/'.hp_confirmation_claim-prior.json').write_bytes(b'prior claim bytes')
    limits = copy.deepcopy(manifest_contract.CONFIRMATION_BUDGET)
    limits['retained_bytes'] = 8

    with pytest.raises(AcquisitionStopped, match='retained_ledger_budget'):
        bounded.Budget(
            phase_dir, limits, 'manifest-hash', confirmation_claim_root=output_root,
            require_real_directory=True)
    assert not (phase_dir/'ledger.json').exists()


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
    owner_path, gate_path, _owner, _gate = authorization_files(
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

    resume_args = SimpleNamespace(resume=True, output_root=f.artifact_root)
    with pytest.raises(AcquisitionStopped, match='confirmation_late_finalization_not_admissible'):
        run._confirmation_run_window(resume_args, f.successor_sha, deadline-timedelta(seconds=1))


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
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, now[0])
    owner_sha = sha(owner_path.read_bytes())
    gate_sha = sha(gate_path.read_bytes())
    binding = run._confirmation_claim_binding(
        owner, owner_sha, gate_sha, f.successor, f.successor_sha, HEAD, f.artifact_root)
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
    original_claim = claim_path.read_bytes()
    assert source_calls == []

    phase_dir.unlink()
    now[0] += timedelta(minutes=5)
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(AcquisitionStopped, match='confirmation_activation_already_claimed'):
        run.main()
    assert claim_path.read_bytes() == original_claim
    assert source_calls == []


def test_run_main_global_retention_counts_common_art_root_files(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch, total_retained_bytes=64*1024**2)
    now = [datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    owner_path, gate_path, _owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, now[0])

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
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ])
    with pytest.raises(AcquisitionStopped, match='total_retained_budget'):
        run.main()
    assert any(path.is_file() for path in f.artifact_root.rglob('*'))
    claims = list(f.artifact_root.glob('.hp_confirmation_claim-*.json'))
    assert len(claims) == 1
    assert physical_regular_bytes(f.artifact_root) <= 64*1024**2


def test_run_main_near_global_cap_rejects_claim_without_overbudget_write_or_reuse(
        tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    now = [datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)]
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, now[0])
    binding = run._confirmation_claim_binding(
        owner, sha(owner_path.read_bytes()), sha(gate_path.read_bytes()),
        f.successor, f.successor_sha, HEAD, f.artifact_root)
    trial_claim = {
        **binding,
        'claim_state': 'preflight_claimed',
        'window_started_at': stamp(now[0]),
        'absolute_deadline': stamp(now[0]+timedelta(seconds=1800)),
        'claimed_at': stamp(now[0]),
    }
    trial_claim_size = len(encoded(trial_claim))
    physical_before = physical_regular_bytes(f.artifact_root)
    cap = physical_before+trial_claim_size-1
    f.successor['budgets']['total_retained_bytes'] = cap
    f.successor_raw = manifest_contract.canonical_manifest_bytes(f.successor)
    f.successor_sha = sha(f.successor_raw)
    f.successor_path.write_bytes(f.successor_raw)
    owner_path, gate_path, owner, _gate = authorization_files(
        f, tmp_path, f.artifact_root, now[0])
    binding = run._confirmation_claim_binding(
        owner, sha(owner_path.read_bytes()), sha(gate_path.read_bytes()),
        f.successor, f.successor_sha, HEAD, f.artifact_root)
    claim_path = run._confirmation_claim_path(f.artifact_root, binding)
    actual_claim_size = len(encoded({
        **binding,
        'claim_state': 'preflight_claimed',
        'window_started_at': stamp(now[0]),
        'absolute_deadline': stamp(now[0]+timedelta(seconds=1800)),
        'claimed_at': stamp(now[0]),
    }))
    assert actual_claim_size == trial_claim_size
    assert cap-physical_before == actual_claim_size-1

    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    source_calls = []

    class MustNotStartBudget:
        def __init__(self, *_args, **_kwargs):
            pytest.fail('near-cap rejection must precede Budget and source calls')

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (f.successor, f.successor_sha))
    monkeypatch.setattr(run, 'confirmation_git_head', lambda: HEAD)
    monkeypatch.setattr(run, 'Budget', MustNotStartBudget)
    monkeypatch.setattr(run, 'acquire_sites', lambda *_args: source_calls.append('called'))
    argv = [
        'food-pilot-run', '--manifest', str(f.successor_path),
        '--execution-gate', str(gate_path), '--owner-activation', str(owner_path),
        '--prior-prescreen', str(f.prescreen_path), '--prior-checkpoint', str(f.checkpoint_path),
        '--prior-v20-manifest', str(f.source_path), '--prior-v20-archive', str(f.archive_path),
        '--phase', 'hp_confirmation', '--output-root', str(f.artifact_root),
    ]
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(AcquisitionStopped, match='total_retained_budget'):
        run.main()
    terminal_claim = json.loads(claim_path.read_bytes())
    terminal_size = claim_path.stat().st_size
    assert terminal_claim['kind'] == 'hp_confirmation_activation_claim_rejected'
    assert terminal_claim['window_started_at'] == stamp(now[0])
    assert terminal_claim['absolute_deadline'] == stamp(now[0]+timedelta(seconds=1800))
    assert terminal_claim['reason'] == 'total_retained_budget'
    assert terminal_size < actual_claim_size
    assert physical_regular_bytes(f.artifact_root) == physical_before+terminal_size
    assert physical_regular_bytes(f.artifact_root) <= cap
    assert source_calls == []

    # The durable terminal claim blocks reuse and preserves the original T0/D.
    terminal_bytes = claim_path.read_bytes()
    now[0] += timedelta(minutes=5)
    monkeypatch.setattr('sys.argv', argv)
    with pytest.raises(AcquisitionStopped, match='confirmation_activation_already_claimed'):
        run.main()
    assert claim_path.read_bytes() == terminal_bytes
    assert physical_regular_bytes(f.artifact_root) == physical_before+terminal_size
    assert source_calls == []


def test_nonconfirmation_phase_keeps_original_global_cutoff(tmp_path, monkeypatch):
    f = synthetic_handoff(tmp_path, monkeypatch)
    source = f.source
    monkeypatch.setattr(run, 'checked_manifest', lambda _path: (source, sha(f.source_raw)))
    monkeypatch.setattr(run, 'checked_gate', lambda *_args: None)
    now = [datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)]
    real_datetime = run.datetime

    class ControlledDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0].astimezone(tz) if tz else now[0]

    monkeypatch.setattr(run, 'datetime', ControlledDateTime)
    monkeypatch.setattr('sys.argv', [
        'food-pilot-run', '--manifest', str(f.source_path),
        '--execution-gate', str(tmp_path/'old-gate.json'), '--phase', 'overture_metadata',
        '--output-root', str(tmp_path/'non-confirmation-output'),
    ])
    with pytest.raises(AcquisitionStopped, match='frozen_pilot_window_expired'):
        run.main()
