"""Explicitly gated acquisition phases; never run at import time."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .acquire_osm import encoded
from .bounded import AcquisitionStopped, Budget, ReplayBudget
from .hotpepper import acquire_sites, confirmation_checkpoint
from . import manifest as manifest_contract
from .overture import metadata, extract

ROOT = Path(__file__).resolve().parents[2]


def checked_manifest(path):
    raw = path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get('state') != 'frozen' or not manifest.get('code_sha256'):
        raise AcquisitionStopped('manifest_not_final')
    for relative, expected in manifest['code_sha256'].items():
        source = (ROOT/relative).resolve()
        if not source.is_relative_to(ROOT/'scripts'/'food_pilot'):
            raise AcquisitionStopped('unapproved_code_path')
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise AcquisitionStopped('code_changed_after_freeze')
    runtime_files = {str(p.relative_to(ROOT)) for p in (ROOT/'scripts'/'food_pilot').glob('*.py')}
    if set(manifest['code_sha256']) != runtime_files:
        raise AcquisitionStopped('incomplete_runtime_code_hash_map')
    return manifest, hashlib.sha256(raw).hexdigest()


def checked_gate(path, manifest_hash, phase):
    gate = json.loads(path.read_text())
    if gate.get('manifest_sha256') != manifest_hash or phase not in gate.get('allowed_phases',[]):
        raise AcquisitionStopped('missing_root_execution_gate')
    if not gate.get('native_review_approved_head') or not gate.get('root_manifest_check'):
        raise AcquisitionStopped('unreviewed_execution_gate')
    return gate


def primary_gate(path, manifest_hash, manifest):
    receipt = json.loads(path.read_text())
    if receipt.get('manifest_sha256') != manifest_hash or receipt.get('code_sha256') != manifest['code_sha256']:
        raise AcquisitionStopped('primary_candidate_not_frozen')
    if receipt.get('primary_comparison') != manifest['primary_comparison'] or not receipt.get('development_complete'):
        raise AcquisitionStopped('primary_candidate_not_frozen')


def validate_result_windows(result, windows):
    def utc(value):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
        if parsed.tzinfo is None:
            raise AcquisitionStopped('naive_confirmation_result_window')
        return parsed.astimezone(timezone.utc)

    by_slug = {key.removeprefix('hp:').removesuffix(':'): (utc(start), utc(end))
               for key, (start, end) in windows.items()}
    for station in result.get('stations', []):
        window = by_slug.get(station.get('slug'))
        if window is None or station.get('status') == 'missing':
            continue
        earliest, latest = window
        stamps = [station.get('finished_at')]
        stamps.extend(page.get('received_at') for page in station.get('pages', []))
        for stamp in stamps:
            if stamp is None:
                continue
            received = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            if received.tzinfo is None or not earliest <= received.astimezone(timezone.utc) < latest:
                raise AcquisitionStopped('confirmation_result_outside_candidate_window')


def phase_sites(manifest, phase, prior=None, now=None):
    core = manifest['core']['stations']
    if phase.endswith('development'):
        return [s for s in core if s['split']=='development']
    if phase.endswith('holdout'):
        return [s for s in core if s['split']=='holdout']
    challenge = manifest['challenge']['order']
    if phase == 'hp_prescreen':
        return challenge
    if phase == 'hp_confirmation':
        if prior is None:
            raise AcquisitionStopped('missing_prescreen_checkpoint')
        checkpoint = confirmation_checkpoint(prior)
        if not checkpoint['candidates']:
            raise AcquisitionStopped('no_initial_zeros_to_confirm')
        now = now or datetime.now(timezone.utc)
        if not datetime.fromisoformat(checkpoint['batch_eligible_from']) <= now < datetime.fromisoformat(checkpoint['batch_eligible_until']):
            raise AcquisitionStopped('outside_real_24_72_hour_confirmation_window')
        ids = {r['slug'] for r in checkpoint['candidates']}
        return [s for s in challenge if s['slug'] in ids]
    if phase == 'overture_challenge':
        if prior is None:
            raise AcquisitionStopped('missing_prescreen_checkpoint')
        ids = {r['slug'] for r in prior['stations'] if r['status'] in ('complete_provider_zero','complete_800m_zero')}
        return [s for s in challenge if s['slug'] in ids]
    if phase == 'overture_metadata':
        return []
    raise AcquisitionStopped('unknown_phase')


def checked_confirmation_prior(prior, manifest_hash):
    """Only a current-manifest hp_prescreen envelope can seed confirmation."""
    if (not isinstance(prior, dict) or prior.get('manifest_sha256') != manifest_hash
            or prior.get('phase') != 'hp_prescreen' or not isinstance(prior.get('result'), dict)):
        raise AcquisitionStopped('wrong_prescreen_provenance')
    return prior['result']


def _utc(value, reason='confirmation_timestamp_invalid'):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    except (TypeError, ValueError):
        raise AcquisitionStopped(reason) from None
    if not isinstance(parsed, datetime) or parsed.tzinfo is None:
        raise AcquisitionStopped(reason)
    return parsed.astimezone(timezone.utc)


def checked_confirmation_amendment(manifest):
    amendment = manifest.get('confirmation_amendment')
    if (not isinstance(amendment, dict)
            or amendment.get('schema_version') != 1
            or amendment.get('source_cutoff') != manifest_contract.CORE_SOURCE_CUTOFF
            or amendment.get('confirmation_completion_before') != manifest_contract.CONFIRMATION_COMPLETION_BEFORE
            or amendment.get('allowed_phases') != ['hp_confirmation']
            or amendment.get('requires_fresh_exact_head_manifest_code_owner_root_release') is not True
            or amendment.get('v20_remains_insufficient') is not True
            or manifest.get('source_window', {}).get('core_hp_complete_before') != manifest_contract.CORE_SOURCE_CUTOFF
            or manifest.get('reviewed_execution_scope') != ['hp_confirmation']
            or manifest.get('budgets', {}).get('hp_confirmation') != manifest_contract.CONFIRMATION_BUDGET):
        raise AcquisitionStopped('confirmation_amendment_required_or_invalid')
    return amendment


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _confirmation_artifact_root(manifest):
    amendment = checked_confirmation_amendment(manifest)
    handoff = amendment.get('historical_v20')
    try:
        root = Path(handoff['artifact_root'])
        if root.is_symlink() or not root.is_dir():
            raise AcquisitionStopped('confirmation_artifact_root_invalid')
        return root.resolve()
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        raise AcquisitionStopped('confirmation_artifact_root_invalid') from None


def _bound_file(path, expected_path, reason):
    if path is None:
        raise AcquisitionStopped(reason)
    try:
        candidate = Path(path)
        expected = Path(expected_path)
        if (candidate.is_symlink() or candidate.resolve() != expected.resolve()
                or not candidate.is_file()):
            raise AcquisitionStopped(reason)
    except (OSError, RuntimeError, TypeError, ValueError):
        raise AcquisitionStopped(reason) from None
    return candidate


def checked_confirmation_handoff(manifest, prior_prescreen_path, prior_checkpoint_path,
                                 prior_v20_manifest_path, prior_v20_archive_path, head):
    """Validate the pinned historical V20 artifacts without parsing its result payload."""
    amendment = checked_confirmation_amendment(manifest)
    handoff = amendment.get('historical_v20')
    if not isinstance(handoff, dict):
        raise AcquisitionStopped('confirmation_historical_handoff_missing')
    manifest_path = _bound_file(prior_v20_manifest_path, handoff.get('manifest_path'),
                                'confirmation_v20_manifest_path')
    archive_path = _bound_file(prior_v20_archive_path, handoff.get('archive_path'),
                               'confirmation_v20_archive_path')
    prescreen_path = _bound_file(prior_prescreen_path, handoff.get('prescreen_envelope_path'),
                                 'confirmation_v20_prescreen_path')
    checkpoint_path = _bound_file(prior_checkpoint_path, handoff.get('control_checkpoint_path'),
                                  'confirmation_v20_checkpoint_path')
    try:
        manifest_raw = manifest_path.read_bytes()
        if hashlib.sha256(manifest_raw).hexdigest() != manifest_contract.V20_MANIFEST_SHA256:
            raise AcquisitionStopped('confirmation_v20_manifest_hash')
        if _file_sha256(archive_path) != manifest_contract.V20_ARCHIVE_SHA256:
            raise AcquisitionStopped('confirmation_v20_archive_hash')
        if _file_sha256(prescreen_path) != manifest_contract.V20_PRESCREEN_SHA256:
            raise AcquisitionStopped('confirmation_v20_prescreen_hash')
        checkpoint_raw = checkpoint_path.read_bytes()
        if hashlib.sha256(checkpoint_raw).hexdigest() != manifest_contract.V20_CHECKPOINT_SHA256:
            raise AcquisitionStopped('confirmation_v20_checkpoint_hash')
        checkpoint = json.loads(checkpoint_raw)
        predecessor = json.loads(manifest_raw)
    except AcquisitionStopped:
        raise
    except (OSError, ValueError, TypeError):
        raise AcquisitionStopped('confirmation_historical_handoff_unreadable') from None

    if (manifest_contract.canonical_code_map_sha256(predecessor.get('code_sha256'))
            != manifest_contract.V20_CODE_MAP_SHA256):
        raise AcquisitionStopped('confirmation_v20_code_map_hash')
    try:
        expected_successor = manifest_contract.make_confirmation_successor(
            manifest_raw, artifact_root=handoff.get('artifact_root'), runtime_root=ROOT,
            code_head=head)
    except (ValueError, OSError, TypeError):
        raise AcquisitionStopped('confirmation_successor_binding_invalid') from None
    if manifest != expected_successor or handoff != expected_successor['confirmation_amendment']['historical_v20']:
        raise AcquisitionStopped('confirmation_successor_manifest_mismatch')

    zeroes = checkpoint.get('zero_confirmation') if isinstance(checkpoint, dict) else None
    expected_bindings = manifest_contract.confirmation_candidate_bindings()
    if (not isinstance(zeroes, dict)
            or checkpoint.get('manifest_sha256') != manifest_contract.V20_MANIFEST_SHA256
            or checkpoint.get('prescreen_result_sha256') != manifest_contract.V20_PRESCREEN_SHA256
            or zeroes.get('status') != 'pending_real_time'
            or not isinstance(zeroes.get('candidates'), list)
            or len(zeroes['candidates']) != 13
            or zeroes.get('batch_eligible_from') != manifest_contract.V20_BATCH_ELIGIBLE_FROM.replace('Z', '+00:00')
            or zeroes.get('batch_eligible_until') != manifest_contract.V20_BATCH_ELIGIBLE_UNTIL.replace('Z', '+00:00')):
        raise AcquisitionStopped('confirmation_checkpoint_binding')
    candidates = zeroes['candidates']
    for actual, expected in zip(candidates, expected_bindings):
        if (not isinstance(actual, dict)
                or actual.get('slug') != expected['slug']
                or actual.get('first_status') not in ('complete_provider_zero', 'complete_800m_zero')):
            raise AcquisitionStopped('confirmation_checkpoint_order_or_status')
        for field in ('first_complete_at', 'eligible_from', 'eligible_until'):
            if _utc(actual.get(field)).isoformat().replace('+00:00', 'Z') != expected[field]:
                raise AcquisitionStopped('confirmation_checkpoint_timestamp')
        first = _utc(actual['first_complete_at'])
        if (_utc(actual['eligible_from']) != first + timedelta(hours=24)
                or _utc(actual['eligible_until']) != first + timedelta(hours=72)):
            raise AcquisitionStopped('confirmation_checkpoint_window')
    if candidates[-1]['eligible_from'] != zeroes['batch_eligible_from']:
        raise AcquisitionStopped('confirmation_checkpoint_batch_start')
    if min(row['eligible_until'] for row in candidates) != zeroes['batch_eligible_until']:
        raise AcquisitionStopped('confirmation_checkpoint_batch_end')
    return {'stations': [
        {'slug': row['slug'], 'status': row['first_status'], 'finished_at': row['first_complete_at']}
        for row in candidates
    ]}, checkpoint


def confirmation_git_head():
    try:
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        raise AcquisitionStopped('confirmation_git_identity_unavailable') from None
    if len(head) != 40 or any(c not in '0123456789abcdef' for c in head):
        raise AcquisitionStopped('confirmation_git_identity_invalid')
    return head


def checked_confirmation_gate(gate_path, owner_path, manifest, manifest_hash, head,
                              output_root, invocation_utc):
    bound_output_root = _confirmation_artifact_root(manifest)
    if Path(output_root).resolve() != bound_output_root:
        raise AcquisitionStopped('confirmation_artifact_root_mismatch')
    try:
        owner_raw = Path(owner_path).read_bytes()
        owner = json.loads(owner_raw)
        gate = json.loads(Path(gate_path).read_bytes())
    except (OSError, ValueError, TypeError):
        raise AcquisitionStopped('confirmation_owner_or_root_release_unreadable') from None
    checked_confirmation_amendment(manifest)
    map_sha = manifest_contract.canonical_code_map_sha256(manifest.get('code_sha256'))
    owner_sha = hashlib.sha256(owner_raw).hexdigest()
    allowed = ['hp_confirmation']
    expected_owner = {
        'kind': 'owner_hp_confirmation_activation',
        'phase': 'hp_confirmation',
        'allowed_phases': allowed,
        'single_use': True,
        'manifest_sha256': manifest_hash,
        'git_head': head,
        'code_map_sha256': map_sha,
        'output_root': str(bound_output_root),
        'source_manifest_sha256': manifest_contract.V20_MANIFEST_SHA256,
        'source_archive_sha256': manifest_contract.V20_ARCHIVE_SHA256,
        'source_code_map_sha256': manifest_contract.V20_CODE_MAP_SHA256,
        'prescreen_envelope_sha256': manifest_contract.V20_PRESCREEN_SHA256,
        'control_checkpoint_sha256': manifest_contract.V20_CHECKPOINT_SHA256,
        'candidate_count': 13,
        'group_counts': {'rich': 0, 'sparse': 13},
        'budget': manifest['budgets']['hp_confirmation'],
    }
    if (not isinstance(owner, dict)
            or any(owner.get(key) != value for key, value in expected_owner.items())
            or not owner.get('activation_id') or not owner.get('run_id')):
        raise AcquisitionStopped('confirmation_owner_activation_binding')
    if manifest.get('confirmation_amendment', {}).get('git_head') != head:
        raise AcquisitionStopped('confirmation_manifest_head_mismatch')
    try:
        created = _utc(owner.get('created_at'))
        owner_expires = _utc(owner.get('expires_at'))
    except AcquisitionStopped:
        raise AcquisitionStopped('confirmation_owner_activation_time') from None
    if created > invocation_utc or owner_expires <= invocation_utc:
        raise AcquisitionStopped('confirmation_owner_activation_not_fresh')

    expected_root_check = {
        'manifest_sha256': manifest_hash,
        'git_head': head,
        'code_map_sha256': map_sha,
        'allowed_phases': allowed,
        'output_root': str(bound_output_root),
        'owner_activation_sha256': owner_sha,
    }
    if (not isinstance(gate, dict)
            or gate.get('kind') != 'root_hp_confirmation_release'
            or gate.get('phase') != 'hp_confirmation'
            or gate.get('allowed_phases') != allowed
            or gate.get('manifest_sha256') != manifest_hash
            or gate.get('git_head') != head
            or gate.get('code_map_sha256') != map_sha
            or gate.get('output_root') != str(bound_output_root)
            or gate.get('native_review_approved_head') != head
            or gate.get('owner_activation_sha256') != owner_sha
            or gate.get('root_manifest_check') != expected_root_check):
        raise AcquisitionStopped('confirmation_root_gate_binding')
    try:
        released = _utc(gate.get('released_at'))
        root_expires = _utc(gate.get('expires_at'))
    except AcquisitionStopped:
        raise AcquisitionStopped('confirmation_root_gate_time') from None
    if released > invocation_utc or root_expires <= invocation_utc:
        raise AcquisitionStopped('confirmation_root_gate_not_fresh')
    if manifest.get('confirmation_amendment', {}).get('allowed_phases') != allowed:
        raise AcquisitionStopped('confirmation_scope_not_single_phase')
    return owner, gate


def _confirmation_run_window(args, manifest_hash, invocation_utc):
    cutoff = _utc(manifest_contract.CONFIRMATION_COMPLETION_BEFORE)
    if args.resume:
        ledger_path = args.output_root/'hp_confirmation'/'ledger.json'
        try:
            ledger = json.loads(ledger_path.read_text())
            contract = ledger['window_contract']
            started = _utc(contract['window_started_at'])
            deadline = _utc(contract['absolute_deadline'])
        except (OSError, KeyError, TypeError, ValueError):
            raise AcquisitionStopped('confirmation_resume_window_missing') from None
        if (ledger.get('manifest_sha256') != manifest_hash
                or ledger.get('limits') != manifest_contract.CONFIRMATION_BUDGET
                or _utc(ledger.get('started_at')) != started
                or deadline != min(started+timedelta(seconds=1800), cutoff)):
            raise AcquisitionStopped('confirmation_resume_window_mismatch')
        if ledger.get('status') == 'complete':
            raise AcquisitionStopped('confirmation_run_already_finalized')
        if ledger.get('finalization_rejections'):
            raise AcquisitionStopped('confirmation_late_finalization_not_admissible')
    else:
        started = invocation_utc
        deadline = min(started+timedelta(seconds=1800), cutoff)
    elapsed = (invocation_utc-started).total_seconds()
    remaining = min(1800-elapsed, (deadline-invocation_utc).total_seconds())
    if invocation_utc < started:
        raise AcquisitionStopped('confirmation_clock_precedes_start')
    if remaining <= 0 or invocation_utc >= cutoff:
        raise AcquisitionStopped('confirmation_completion_deadline_expired')
    return started, deadline, remaining


def _check_confirmation_run_window(started, deadline, invocation_utc,
                                   invocation_monotonic, monotonic_remaining):
    now = datetime.now(timezone.utc)
    if now < invocation_utc or now < started:
        raise AcquisitionStopped('confirmation_clock_moved_backwards')
    if now >= deadline or (now-started).total_seconds() >= 1800:
        raise AcquisitionStopped('confirmation_completion_deadline_expired')
    if time.monotonic()-invocation_monotonic >= monotonic_remaining:
        raise AcquisitionStopped('confirmation_monotonic_deadline_expired')


def _fsync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def immutable_result(directory, value, retained_limit, *, commit_guard=None):
    raw = encoded(value)
    digest = hashlib.sha256(raw).hexdigest()
    path = directory/f'result-{digest}.json'
    if path.exists():
        if path.read_bytes() != raw:
            raise AcquisitionStopped('immutable_result_conflict')
        if commit_guard is not None:
            commit_guard()
        return path, digest
    used=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())
    if used+len(raw)>retained_limit:
        raise AcquisitionStopped('retained_result_budget')
    if commit_guard is not None:
        temporary = directory/f'.{path.name}.{uuid.uuid4().hex}.pending'
        try:
            with temporary.open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            commit_guard()
            os.replace(temporary, path)
            _fsync_directory(directory)
            commit_guard()
            return path, digest
        except BaseException:
            if temporary.exists():
                temporary.unlink()
                _fsync_directory(directory)
            raise
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return path, digest


def overture_metadata_input(args, manifest, manifest_hash):
    """Read ordinary pinned metadata or explicit cache-only recovery admission."""
    recovery_paths = (args.cache_only_admission, args.cache_only_source_manifest,
                      args.cache_only_owner_exception, args.cache_only_root_release)
    location_paths = (getattr(args, 'cache_only_source_phase_dir', None),
                      getattr(args, 'cache_only_admission_root', None))
    if any(recovery_paths):
        if args.phase != 'overture_development' or not all(recovery_paths):
            raise AcquisitionStopped('invalid_cache_only_recovery_scope')
        if args.overture_metadata is not None:
            raise AcquisitionStopped('conflicting_metadata_inputs')
        current_contract = manifest.get('current_manifest_cache_admission')
        if current_contract is not None and not all(location_paths):
            raise AcquisitionStopped('current_manifest_admission_roots_required')
        if current_contract is None and any(location_paths):
            raise AcquisitionStopped('unbound_current_admission_roots')
        from .recovery import load_admitted_metadata
        return load_admitted_metadata(admission_path=args.cache_only_admission,
            source_manifest_path=args.cache_only_source_manifest,
            downstream_manifest=manifest, downstream_manifest_sha=manifest_hash,
            owner_exception_path=args.cache_only_owner_exception,
            root_release_path=args.cache_only_root_release,
            source_phase_dir=location_paths[0], admission_root=location_paths[1])
    if args.overture_metadata is None:
        raise AcquisitionStopped('missing_pinned_metadata')
    pinned = json.loads(args.overture_metadata.read_text())
    if pinned.get('manifest_sha256') != manifest_hash or pinned.get('phase') != 'overture_metadata':
        raise AcquisitionStopped('metadata_provenance')
    return pinned['result'], ReplayBudget(args.overture_metadata.parent)


def main():
    invocation_utc = datetime.now(timezone.utc)
    invocation_monotonic = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--execution-gate', type=Path, required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--primary-freeze', type=Path)
    parser.add_argument('--prior-prescreen', type=Path)
    parser.add_argument('--prior-checkpoint', type=Path)
    parser.add_argument('--prior-v20-manifest', type=Path)
    parser.add_argument('--prior-v20-archive', type=Path)
    parser.add_argument('--owner-activation', type=Path)
    parser.add_argument('--overture-metadata', type=Path)
    parser.add_argument('--cache-only-admission', type=Path)
    parser.add_argument('--cache-only-source-manifest', type=Path)
    parser.add_argument('--cache-only-owner-exception', type=Path)
    parser.add_argument('--cache-only-root-release', type=Path)
    parser.add_argument('--cache-only-source-phase-dir', type=Path)
    parser.add_argument('--cache-only-admission-root', type=Path)
    args = parser.parse_args()
    recovery_args = (args.cache_only_admission, args.cache_only_source_manifest,
                     args.cache_only_owner_exception, args.cache_only_root_release)
    recovery_location_args = (args.cache_only_source_phase_dir, args.cache_only_admission_root)
    if any(recovery_args) and (args.phase != 'overture_development' or not all(recovery_args)):
        parser.error('cache-only recovery is available only for overture_development with all four receipts/paths')
    if any(recovery_location_args) and (args.phase != 'overture_development'
                                        or not all(recovery_location_args) or not all(recovery_args)):
        parser.error('current cache-only recovery requires source-phase and admission roots plus all four receipts/paths')
    if all(recovery_args) and args.overture_metadata is not None:
        parser.error('choose ordinary pinned metadata or cache-only admission, not both')
    confirmation_inputs = (args.prior_checkpoint, args.prior_v20_manifest,
                          args.prior_v20_archive, args.owner_activation)
    if args.phase == 'hp_confirmation' and (args.prior_prescreen is None or any(p is None for p in confirmation_inputs)):
        raise AcquisitionStopped('confirmation_historical_handoff_and_activation_required')
    if args.phase != 'hp_confirmation' and any(p is not None for p in confirmation_inputs):
        parser.error('confirmation handoff and activation inputs are available only for hp_confirmation')
    root = args.output_root.resolve()
    if root.is_relative_to(ROOT):
        parser.error('Raw pilot data must stay outside git')
    manifest, manifest_hash = checked_manifest(args.manifest)
    if args.phase not in manifest['budgets'] or not isinstance(manifest['budgets'][args.phase],dict):
        raise AcquisitionStopped('unknown_phase')
    confirmation_started = confirmation_deadline = confirmation_monotonic_remaining = None
    confirmation_owner = confirmation_gate = None
    historical_checkpoint = None
    if args.phase == 'hp_confirmation':
        checked_confirmation_amendment(manifest)
        confirmation_started, confirmation_deadline, confirmation_monotonic_remaining = _confirmation_run_window(
            args, manifest_hash, invocation_utc)
        _check_confirmation_run_window(confirmation_started, confirmation_deadline, invocation_utc,
                                       invocation_monotonic, confirmation_monotonic_remaining)
        head = confirmation_git_head()
        confirmation_owner, confirmation_gate = checked_confirmation_gate(
            args.execution_gate, args.owner_activation, manifest, manifest_hash, head, root, invocation_utc)
        _check_confirmation_run_window(confirmation_started, confirmation_deadline, invocation_utc,
                                       invocation_monotonic, confirmation_monotonic_remaining)
        prior, historical_checkpoint = checked_confirmation_handoff(
            manifest, args.prior_prescreen, args.prior_checkpoint,
            args.prior_v20_manifest, args.prior_v20_archive, head)
        checkpoint = confirmation_checkpoint(prior)
        if checkpoint != historical_checkpoint.get('zero_confirmation'):
            raise AcquisitionStopped('confirmation_historical_prior_checkpoint_mismatch')
        _check_confirmation_run_window(confirmation_started, confirmation_deadline, invocation_utc,
                                       invocation_monotonic, confirmation_monotonic_remaining)
    else:
        checked_gate(args.execution_gate, manifest_hash, args.phase)
        if datetime.now(timezone.utc) >= datetime.fromisoformat(manifest['source_window']['core_hp_complete_before'].replace('Z','+00:00')):
            raise AcquisitionStopped('frozen_pilot_window_expired')
        prior = json.loads(args.prior_prescreen.read_text()) if args.prior_prescreen else None
        checkpoint = None
        if prior is not None:
            prior = checked_confirmation_prior(prior, manifest_hash)
    if args.phase.endswith('holdout'):
        if args.primary_freeze is None:
            raise AcquisitionStopped('holdout_locked')
        primary_gate(args.primary_freeze, manifest_hash, manifest)
    sites = phase_sites(manifest, args.phase, prior)
    if args.phase == 'hp_confirmation':
        _check_confirmation_run_window(confirmation_started, confirmation_deadline, invocation_utc,
                                       invocation_monotonic, confirmation_monotonic_remaining)
    phase_dir = root/args.phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    retained = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    already = sum(p.stat().st_size for p in phase_dir.rglob('*') if p.is_file())
    if retained-already+manifest['budgets'][args.phase]['retained_bytes'] > manifest['budgets']['total_retained_bytes']:
        raise AcquisitionStopped('total_retained_budget')
    key = os.environ.get('HOTPEPPER_API_KEY') if args.phase.startswith('hp_') else None
    if args.phase.startswith('hp_') and not key:
        raise AcquisitionStopped('scoped_hp_credential_unavailable')
    windows = {}
    completion_window = None
    if checkpoint and checkpoint['candidates']:
        windows = {f"hp:{row['slug']}:": (row['eligible_from'], row['eligible_until'])
                   for row in checkpoint['candidates']}
        completion_window = (checkpoint['batch_eligible_from'], checkpoint['batch_eligible_until'])
    absolute_deadline = (confirmation_deadline.isoformat().replace('+00:00', 'Z')
                         if args.phase == 'hp_confirmation'
                         else manifest['source_window']['core_hp_complete_before'])
    budget_window = {'absolute_deadline': absolute_deadline,
                     'identity_windows': windows, 'completion_window': completion_window}
    if args.phase == 'hp_confirmation':
        budget_window['window_started_at'] = confirmation_started.isoformat().replace('+00:00', 'Z')
    confirmation_output = None
    with Budget(phase_dir, manifest['budgets'][args.phase], manifest_hash, resume=args.resume,
                **budget_window) as budget:
        try:
            if args.phase.startswith('hp_'):
                result = acquire_sites(sites,budget,key)
            elif args.phase == 'overture_metadata':
                result = metadata(manifest,budget)
                result['status']='complete'
            else:
                pinned_result, metadata_cache = overture_metadata_input(args, manifest, manifest_hash)
                result=extract(manifest,sites,pinned_result,budget,metadata_cache)
            budget.check_completion()
            if checkpoint:
                validate_result_windows(result, windows)
            if args.phase == 'hp_confirmation':
                _check_confirmation_run_window(confirmation_started, confirmation_deadline, invocation_utc,
                                               invocation_monotonic, confirmation_monotonic_remaining)
        except Exception as exc:
            result={'status':'incomplete','error_type':type(exc).__name__}
        envelope={'phase':args.phase,'manifest_sha256':manifest_hash,'result':result}
        if args.phase == 'hp_confirmation':
            envelope_sha = hashlib.sha256(encoded(envelope)).hexdigest()
            rejection_recorded = False

            def record_confirmation_finalization_rejection(exc):
                nonlocal rejection_recorded
                if rejection_recorded:
                    return
                budget.ledger.setdefault('finalization_rejections', []).append({
                    'result_sha256': envelope_sha,
                    'deadline': confirmation_deadline.isoformat().replace('+00:00', 'Z'),
                    'rejected_at': datetime.now(timezone.utc).isoformat(),
                    'reason_type': type(exc).__name__,
                })
                rejection_recorded = True

            def confirmation_commit_guard():
                try:
                    budget.check_completion()
                    _check_confirmation_run_window(
                        confirmation_started, confirmation_deadline, invocation_utc,
                        invocation_monotonic, confirmation_monotonic_remaining)
                except BaseException as exc:
                    record_confirmation_finalization_rejection(exc)
                    raise

            try:
                path, digest = immutable_result(
                    phase_dir, envelope, budget.limits['retained_bytes'],
                    commit_guard=confirmation_commit_guard)
                confirmation_commit_guard()
            except BaseException as exc:
                record_confirmation_finalization_rejection(exc)
                raise
            if result['status'] != 'complete':
                raise AcquisitionStopped('phase_incomplete_no_budget_extension')
            budget.finalization_guard = confirmation_commit_guard
            budget.finalization_rejection_callback = record_confirmation_finalization_rejection
            confirmation_output = {
                'phase': args.phase, 'status': result['status'],
                'result_path': str(path), 'sha256': digest,
            }
        else:
            path,digest=immutable_result(phase_dir,envelope,budget.limits['retained_bytes'])
            if args.phase=='hp_prescreen' and 'stations' in result:
                immutable_result(phase_dir,{'manifest_sha256':manifest_hash,'prescreen_result_sha256':digest,
                                          'zero_confirmation':confirmation_checkpoint(result)},budget.limits['retained_bytes'])
            print(json.dumps({'phase':args.phase,'status':result['status'],'result_path':str(path),'sha256':digest}),flush=True)
            if result['status'] != 'complete':
                raise AcquisitionStopped('phase_incomplete_no_budget_extension')
    if confirmation_output is not None:
        print(json.dumps(confirmation_output), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Never print exception messages, URLs, request headers or credentials.
        print(json.dumps({'status':'stopped','error_type':type(exc).__name__}),flush=True)
        raise SystemExit(1) from None
