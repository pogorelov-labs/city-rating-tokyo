"""Explicitly gated acquisition phases; never run at import time."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import stat
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
        gate_raw = Path(gate_path).read_bytes()
        owner = json.loads(owner_raw)
        gate = json.loads(gate_raw)
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
    return owner, gate, owner_sha, hashlib.sha256(gate_raw).hexdigest()


def _confirmation_phase_directory(root):
    """Create/check only the real confirmation child beneath the pinned ART root."""
    root = Path(root).resolve()
    phase_dir = root/'hp_confirmation'
    if phase_dir.is_symlink():
        raise AcquisitionStopped('confirmation_phase_directory_invalid')
    try:
        phase_dir.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError:
        pass
    except OSError:
        raise AcquisitionStopped('confirmation_phase_directory_invalid') from None
    try:
        if (phase_dir.is_symlink() or not phase_dir.is_dir()
                or phase_dir.resolve(strict=True) != phase_dir.absolute()
                or not phase_dir.resolve(strict=True).is_relative_to(root)):
            raise AcquisitionStopped('confirmation_phase_directory_invalid')
    except (OSError, RuntimeError, ValueError):
        raise AcquisitionStopped('confirmation_phase_directory_invalid') from None
    return phase_dir


def _write_confirmation_receipt(path, value, conflict_reason):
    """Create one durable confirmation receipt without following an existing path."""
    raw = encoded(value)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise AcquisitionStopped(conflict_reason) from None
    except OSError:
        raise AcquisitionStopped('confirmation_activation_claim_persist_failed') from None
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:
        # Leave any partial receipt in place. A later invocation must fail closed.
        raise AcquisitionStopped('confirmation_activation_claim_persist_failed') from None
    return raw


def _confirmation_claim_binding(owner, owner_sha, gate_sha, manifest, manifest_hash,
                                head, output_root):
    return {
        'kind': 'hp_confirmation_activation_claim',
        'schema_version': 1,
        'phase': 'hp_confirmation',
        'manifest_sha256': manifest_hash,
        'git_head': head,
        'code_map_sha256': manifest_contract.canonical_code_map_sha256(manifest.get('code_sha256')),
        'output_root': str(Path(output_root).resolve()),
        'owner_activation_sha256': owner_sha,
        'root_release_sha256': gate_sha,
        'activation_id': owner['activation_id'],
        'run_id': owner['run_id'],
    }


def _confirmation_claim_path(output_root, binding):
    identity = encoded({'activation_id': binding['activation_id'], 'run_id': binding['run_id']})
    suffix = hashlib.sha256(identity).hexdigest()
    return Path(output_root).resolve()/f'.hp_confirmation_claim-{suffix}.json'


def _confirmation_claim_files(output_root):
    root = Path(output_root).resolve(strict=True)
    claims = []
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                if not (entry.name.startswith('.hp_confirmation_claim-')
                        and entry.name.endswith('.json')):
                    continue
                info = entry.stat(follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise AcquisitionStopped('confirmation_activation_claim_invalid')
                claims.append((root/entry.name, info.st_size))
    except AcquisitionStopped:
        raise
    except OSError:
        raise AcquisitionStopped('confirmation_activation_claim_unreadable') from None
    return claims


def _confirmation_claim_bytes(output_root):
    return sum(size for _path, size in _confirmation_claim_files(output_root))


def _physical_retained_bytes(directory):
    """Count bytes beneath a root without following any symlink target."""
    total = 0

    def raise_walk_error(error):
        raise error

    try:
        for current, directories, files in os.walk(
                directory, topdown=True, followlinks=False, onerror=raise_walk_error):
            kept_directories = []
            for name in directories:
                path = Path(current)/name
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode):
                    total += info.st_size
                else:
                    kept_directories.append(name)
            directories[:] = kept_directories
            for name in files:
                info = (Path(current)/name).lstat()
                if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                    total += info.st_size
    except OSError:
        raise AcquisitionStopped('retention_preflight_unreadable') from None
    return total


def _persist_confirmation_claim(output_root, claim_path, raw, manifest):
    root = Path(output_root).resolve(strict=True)
    claim_path = Path(claim_path)
    if claim_path.parent != root or claim_path.name != _confirmation_claim_path(
            root, json.loads(raw)).name:
        raise AcquisitionStopped('confirmation_activation_claim_path')
    directory_fd = None
    rejected_reason = None
    try:
        directory_fd = os.open(
            root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        if not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
            raise AcquisitionStopped('confirmation_artifact_root_invalid')
        fcntl.flock(directory_fd, fcntl.LOCK_EX)
        try:
            try:
                os.stat(claim_path.name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise AcquisitionStopped('confirmation_activation_already_claimed')
            claims = _confirmation_claim_files(root)
            prior_claim_bytes = sum(size for _path, size in claims)
            phase_dir = root/'hp_confirmation'
            phase_bytes = 0
            if not phase_dir.is_symlink() and phase_dir.is_dir():
                phase_bytes = _physical_retained_bytes(phase_dir)
            phase_limit = manifest['budgets']['hp_confirmation']['retained_bytes']
            total_limit = manifest['budgets']['total_retained_bytes']
            retained = _physical_retained_bytes(root)
            reason = None
            if phase_bytes+prior_claim_bytes+len(raw) > phase_limit:
                reason = 'retained_claim_budget'
            # Claims and phase outputs share the confirmation allowance; reserve
            # that full allowance in ART before publishing a runnable claim.
            elif retained-phase_bytes-prior_claim_bytes+phase_limit > total_limit:
                reason = 'total_retained_budget'
            if reason is not None:
                rejected_reason = reason
                claim = json.loads(raw)
                terminal = {
                    'kind': 'hp_confirmation_activation_claim_rejected',
                    'schema_version': 1,
                    'phase': 'hp_confirmation',
                    'manifest_sha256': claim['manifest_sha256'],
                    'owner_activation_sha256': claim['owner_activation_sha256'],
                    'root_release_sha256': claim['root_release_sha256'],
                    'activation_id': claim['activation_id'],
                    'run_id': claim['run_id'],
                    'window_started_at': claim['window_started_at'],
                    'absolute_deadline': claim['absolute_deadline'],
                    'rejected_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    'reason': reason,
                }
                terminal_raw = encoded(terminal)
                if (phase_bytes+prior_claim_bytes+len(terminal_raw) > phase_limit
                        or retained+len(terminal_raw) > total_limit):
                    raise AcquisitionStopped(reason)
                raw = terminal_raw
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
            try:
                descriptor = os.open(claim_path.name, flags, 0o600, dir_fd=directory_fd)
            except FileExistsError:
                raise AcquisitionStopped('confirmation_activation_already_claimed') from None
            except OSError:
                raise AcquisitionStopped('confirmation_activation_claim_persist_failed') from None
            try:
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.fsync(directory_fd)
            except OSError:
                # A partial or uncertain claim remains evidence and blocks reuse.
                raise AcquisitionStopped('confirmation_activation_claim_persist_failed') from None
        finally:
            fcntl.flock(directory_fd, fcntl.LOCK_UN)
    except AcquisitionStopped:
        raise
    except (OSError, KeyError, TypeError, ValueError):
        raise AcquisitionStopped('retention_preflight_unreadable') from None
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
    if rejected_reason is not None:
        raise AcquisitionStopped(rejected_reason)


def _read_confirmation_claim(claim_path, binding):
    path = Path(claim_path)
    expected_path = _confirmation_claim_path(binding['output_root'], binding)
    if path != expected_path:
        raise AcquisitionStopped('confirmation_activation_claim_path')
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AcquisitionStopped('confirmation_activation_claim_invalid')
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None
            raw = stream.read()
        claim = json.loads(raw)
    except AcquisitionStopped:
        raise
    except (OSError, ValueError, TypeError):
        raise AcquisitionStopped('confirmation_activation_claim_missing') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    expected_keys = set(binding) | {
        'claim_state', 'window_started_at', 'absolute_deadline', 'claimed_at'}
    if (not isinstance(claim, dict) or set(claim) != expected_keys
            or claim.get('claim_state') != 'preflight_claimed'
            or any(claim.get(key) != value for key, value in binding.items())):
        raise AcquisitionStopped('confirmation_activation_claim_binding')
    try:
        started = _utc(claim['window_started_at'])
        deadline = _utc(claim['absolute_deadline'])
        claimed = _utc(claim['claimed_at'])
    except AcquisitionStopped:
        raise AcquisitionStopped('confirmation_activation_claim_invalid') from None
    expected_deadline = min(
        started+timedelta(seconds=1800), _utc(manifest_contract.CONFIRMATION_COMPLETION_BEFORE))
    if claimed != started or deadline != expected_deadline:
        raise AcquisitionStopped('confirmation_activation_claim_window')
    return claim, hashlib.sha256(raw).hexdigest(), started, deadline


def _prepare_confirmation_claim(claim_path, binding, started, deadline, *, resume,
                                manifest=None):
    if resume:
        claim, claim_sha, claim_started, claim_deadline = _read_confirmation_claim(claim_path, binding)
        if claim_started != started or claim_deadline != deadline:
            raise AcquisitionStopped('confirmation_activation_claim_window')
        return claim, claim_sha
    claim = {
        **binding,
        'claim_state': 'preflight_claimed',
        'window_started_at': started.isoformat().replace('+00:00', 'Z'),
        'absolute_deadline': deadline.isoformat().replace('+00:00', 'Z'),
        'claimed_at': started.isoformat().replace('+00:00', 'Z'),
    }
    if manifest is None:
        raise AcquisitionStopped('confirmation_activation_claim_manifest_missing')
    raw = encoded(claim)
    _persist_confirmation_claim(binding['output_root'], claim_path, raw, manifest)
    return claim, hashlib.sha256(raw).hexdigest()


def _read_confirmation_budget_marker(phase_dir, claim_sha):
    path = Path(phase_dir)/'activation-budget-started.json'
    try:
        if path.is_symlink():
            raise AcquisitionStopped('confirmation_activation_marker_invalid')
        marker = json.loads(path.read_bytes())
    except AcquisitionStopped:
        raise
    except (OSError, ValueError, TypeError):
        raise AcquisitionStopped('confirmation_activation_marker_missing') from None
    expected = {
        'kind': 'hp_confirmation_budget_started',
        'schema_version': 1,
        'claim_sha256': claim_sha,
    }
    if marker != expected:
        raise AcquisitionStopped('confirmation_activation_marker_binding')
    return marker


def _mark_confirmation_budget_started(phase_dir, claim_sha, *, retained_limit=None,
                                      claim_root=None):
    path = Path(phase_dir)/'activation-budget-started.json'
    if path.exists() or path.is_symlink():
        return _read_confirmation_budget_marker(phase_dir, claim_sha)
    marker = {
        'kind': 'hp_confirmation_budget_started',
        'schema_version': 1,
        'claim_sha256': claim_sha,
    }
    if retained_limit is not None:
        phase_bytes = _physical_retained_bytes(phase_dir)
        claim_bytes = _confirmation_claim_bytes(claim_root)
        if phase_bytes+claim_bytes+len(encoded(marker)) > retained_limit:
            raise AcquisitionStopped('retained_activation_marker_budget')
    _write_confirmation_receipt(
        path, marker, 'confirmation_activation_marker_already_recorded')
    return marker


def _confirmation_run_window(args, manifest_hash, invocation_utc, *,
                             phase_dir=None, claim_binding=None, claim_path=None):
    cutoff = _utc(manifest_contract.CONFIRMATION_COMPLETION_BEFORE)
    phase_dir = Path(phase_dir or (args.output_root/'hp_confirmation'))
    ledger_path = phase_dir/'ledger.json'
    marker_path = phase_dir/'activation-budget-started.json'
    claim = claim_started = claim_deadline = claim_sha = None
    if claim_binding is not None:
        if claim_path is None:
            claim_path = _confirmation_claim_path(claim_binding['output_root'], claim_binding)
        claim, claim_sha, claim_started, claim_deadline = _read_confirmation_claim(
            claim_path, claim_binding)
    if args.resume:
        if ledger_path.is_symlink():
            raise AcquisitionStopped('confirmation_ledger_path_invalid')
        if ledger_path.exists():
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
            if claim_binding is not None:
                if claim_started != started or claim_deadline != deadline:
                    raise AcquisitionStopped('confirmation_activation_claim_window')
                _read_confirmation_budget_marker(phase_dir, claim_sha)
            if ledger.get('status') == 'complete':
                raise AcquisitionStopped('confirmation_run_already_finalized')
            if ledger.get('finalization_rejections'):
                raise AcquisitionStopped('confirmation_late_finalization_not_admissible')
        else:
            if claim_binding is None:
                raise AcquisitionStopped('confirmation_resume_window_missing')
            if marker_path.exists() or marker_path.is_symlink():
                raise AcquisitionStopped('confirmation_resume_ledger_missing')
            try:
                entries = {path.name for path in phase_dir.iterdir()}
            except OSError:
                raise AcquisitionStopped('confirmation_resume_window_missing') from None
            if entries:
                raise AcquisitionStopped('confirmation_resume_ledger_missing')
            started, deadline = claim_started, claim_deadline
    else:
        if claim_binding is not None:
            try:
                if any(phase_dir.iterdir()):
                    raise AcquisitionStopped('confirmation_activation_already_claimed')
            except OSError:
                raise AcquisitionStopped('confirmation_phase_directory_invalid') from None
        started = invocation_utc
        deadline = min(started+timedelta(seconds=1800), cutoff)
        if claim_binding is not None and (claim_started != started or claim_deadline != deadline):
            raise AcquisitionStopped('confirmation_activation_claim_window')
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


def immutable_result(directory, value, retained_limit, *, commit_guard=None,
                     retained_extra_bytes=0):
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
    if used+retained_extra_bytes+len(raw)>retained_limit:
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
    confirmation_phase_dir = None
    confirmation_claim_binding = None
    confirmation_claim_sha = None
    confirmation_resume_from_claim = False
    historical_checkpoint = None
    if args.phase == 'hp_confirmation':
        checked_confirmation_amendment(manifest)
        head = confirmation_git_head()
        confirmation_owner, confirmation_gate, owner_sha, gate_sha = checked_confirmation_gate(
            args.execution_gate, args.owner_activation, manifest, manifest_hash, head, root, invocation_utc)
        confirmation_claim_binding = _confirmation_claim_binding(
            confirmation_owner, owner_sha, gate_sha, manifest, manifest_hash, head, root)
        claim_path = _confirmation_claim_path(root, confirmation_claim_binding)
        if args.resume:
            _claim, _claim_sha, confirmation_started, confirmation_deadline = _read_confirmation_claim(
                claim_path, confirmation_claim_binding)
        else:
            confirmation_started = invocation_utc
            confirmation_deadline = min(
                confirmation_started+timedelta(seconds=1800),
                _utc(manifest_contract.CONFIRMATION_COMPLETION_BEFORE))
            if confirmation_started >= confirmation_deadline:
                raise AcquisitionStopped('confirmation_completion_deadline_expired')
        _claim, confirmation_claim_sha = _prepare_confirmation_claim(
            claim_path, confirmation_claim_binding, confirmation_started,
            confirmation_deadline, resume=args.resume, manifest=manifest)
        # The claim is durably bound to this ART root before checking the phase
        # destination; an unsafe phase path therefore cannot reset its window.
        confirmation_phase_dir = _confirmation_phase_directory(root)
        ledger_path = confirmation_phase_dir/'ledger.json'
        marker_path = confirmation_phase_dir/'activation-budget-started.json'
        confirmation_resume_from_claim = (
            args.resume and not ledger_path.exists() and not marker_path.exists()
            and not ledger_path.is_symlink() and not marker_path.is_symlink())
        confirmation_started, confirmation_deadline, confirmation_monotonic_remaining = _confirmation_run_window(
            args, manifest_hash, invocation_utc, phase_dir=confirmation_phase_dir,
            claim_binding=confirmation_claim_binding, claim_path=claim_path)
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
    phase_dir = confirmation_phase_dir or root/args.phase
    if args.phase == 'hp_confirmation':
        retained = _physical_retained_bytes(root)
        already = _physical_retained_bytes(phase_dir)
    else:
        phase_dir.mkdir(parents=True, exist_ok=True)
        retained = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
        already = sum(p.stat().st_size for p in phase_dir.rglob('*') if p.is_file())
    claim_bytes = (_confirmation_claim_bytes(root)
                   if args.phase == 'hp_confirmation' else 0)
    if (retained-already-claim_bytes+manifest['budgets'][args.phase]['retained_bytes']
            > manifest['budgets']['total_retained_bytes']):
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
    if args.phase == 'hp_confirmation':
        _mark_confirmation_budget_started(
            phase_dir, confirmation_claim_sha,
            retained_limit=manifest['budgets'][args.phase]['retained_bytes'],
            claim_root=root)
    with Budget(phase_dir, manifest['budgets'][args.phase], manifest_hash, resume=args.resume,
                confirmation_lock_guard=args.phase == 'hp_confirmation',
                confirmation_claim_sha=confirmation_claim_sha,
                confirmation_claim_path=(claim_path if args.phase == 'hp_confirmation' else None),
                confirmation_claim_root=(root if args.phase == 'hp_confirmation' else None),
                allow_resume_without_ledger=confirmation_resume_from_claim,
                require_real_directory=args.phase == 'hp_confirmation',
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
                    commit_guard=confirmation_commit_guard,
                    retained_extra_bytes=_confirmation_claim_bytes(root))
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
