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
from contextlib import contextmanager
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
    historical_v21 = amendment.get('historical_v21') if isinstance(amendment, dict) else None
    if (manifest.get('version') != 'v22'
            or manifest.get('supersedes_manifest_sha256') != manifest_contract.V21_MANIFEST_SHA256
            or not isinstance(amendment, dict)
            or amendment.get('schema_version') != 1
            or amendment.get('source_cutoff') != manifest_contract.CORE_SOURCE_CUTOFF
            or amendment.get('confirmation_completion_before') != manifest_contract.CONFIRMATION_COMPLETION_BEFORE
            or amendment.get('predecessor_operational_authority_reusable') is not False
            or not isinstance(historical_v21, dict)
            or historical_v21.get('manifest_sha256') != manifest_contract.V21_MANIFEST_SHA256
            or historical_v21.get('archive_sha256') != manifest_contract.V21_ARCHIVE_SHA256
            or historical_v21.get('code_map_sha256') != manifest_contract.V21_CODE_MAP_SHA256
            or historical_v21.get('amendment_sha256') != manifest_contract.V21_AMENDMENT_SHA256
            or historical_v21.get('git_head') != manifest_contract.V21_GIT_HEAD
            or amendment.get('allowed_phases') != ['hp_confirmation']
            or amendment.get('requires_fresh_exact_head_manifest_code_owner_root_release') is not True
            or amendment.get('v20_remains_insufficient') is not True
            or amendment.get('control_pool_contract') != manifest_contract.CONFIRMATION_CONTROL_POOL_CONTRACT
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


_CONTROL_ROLE_PREFIX = {
    'allocation_descriptor': '.hp_confirmation_allocation-',
    'preparation_owner_intent': '.hp_confirmation_preparation_owner-',
    'preparation_root_intent': '.hp_confirmation_preparation_root-',
    'burn_claim': '.hp_confirmation_claim-',
    'final_owner_execution_receipt': '.hp_confirmation_final_owner-',
    'final_root_release_receipt': '.hp_confirmation_final_root-',
}


def _control_identity(activation_id, run_id):
    return hashlib.sha256(encoded({'activation_id': activation_id, 'run_id': run_id})).hexdigest()


def _control_pool_paths(output_root, activation_id, run_id):
    root = Path(output_root).resolve()
    suffix = _control_identity(activation_id, run_id)
    return {role: root/f'{prefix}{suffix}.json'
            for role, prefix in _CONTROL_ROLE_PREFIX.items()}


def _padded_control_slot(value):
    raw = encoded(value)
    size = manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES
    if len(raw) >= size:
        raise AcquisitionStopped('confirmation_control_slot_payload_too_large')
    return raw+b' '*(size-len(raw))


def _read_fixed_control_file(path):
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size != manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES):
            raise AcquisitionStopped('confirmation_control_slot_invalid')
        chunks = []
        while True:
            chunk = os.read(descriptor, 8192)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b''.join(chunks)
    except AcquisitionStopped:
        raise
    except OSError:
        raise AcquisitionStopped('confirmation_control_slot_missing_or_unreadable') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(raw) != manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES:
        raise AcquisitionStopped('confirmation_control_slot_invalid')
    return raw


def _confirmation_control_files(output_root):
    root = Path(output_root).resolve(strict=True)
    files = []
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                if not any(entry.name.startswith(prefix) and entry.name.endswith('.json')
                           for prefix in _CONTROL_ROLE_PREFIX.values()):
                    continue
                info = entry.stat(follow_symlinks=False)
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or info.st_size != manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES):
                    raise AcquisitionStopped('confirmation_control_slot_invalid')
                files.append((root/entry.name, info.st_size))
    except AcquisitionStopped:
        raise
    except OSError:
        raise AcquisitionStopped('confirmation_control_slot_unreadable') from None
    return files


def _confirmation_control_bytes(output_root):
    return sum(size for _path, size in _confirmation_control_files(output_root))


def _confirmation_consumer_started_locked(root_fd, root):
    """Return whether any reserved confirmation pool has entered consumption."""
    for path, _size in _confirmation_control_files(root):
        if not path.name.startswith(_CONTROL_ROLE_PREFIX['burn_claim']):
            continue
        _raw, claim = _read_control_slot_locked(root_fd, path.name)
        if (claim.get('kind') == 'hp_confirmation_activation_claim'
                and claim.get('claim_state') == 'consumer_started'):
            return True
    return False


def _confirmation_phase_bytes(root, *, allow_unsafe_path=False):
    phase_dir = Path(root).resolve()/'hp_confirmation'
    if phase_dir.is_symlink() or (phase_dir.exists() and not phase_dir.is_dir()):
        if allow_unsafe_path:
            try:
                return phase_dir.lstat().st_size
            except OSError:
                raise AcquisitionStopped('confirmation_phase_directory_invalid') from None
        raise AcquisitionStopped('confirmation_phase_directory_invalid')
    if not phase_dir.exists():
        return 0
    return _physical_retained_bytes(phase_dir)


def _control_pool_descriptor(manifest, manifest_hash, head, output_root,
                             activation_id, run_id, execution_intent_sha256):
    execution_intent_sha256 = _checked_approval_sha256(execution_intent_sha256)
    root = Path(output_root).resolve()
    paths = _control_pool_paths(root, activation_id, run_id)
    return {
        'kind': 'hp_confirmation_control_pool',
        'schema_version': 1,
        'phase': 'hp_confirmation',
        'activation_id': activation_id,
        'run_id': run_id,
        'git_head': head,
        'execution_intent_sha256': execution_intent_sha256,
        'manifest_sha256': manifest_hash,
        'code_map_sha256': manifest_contract.canonical_code_map_sha256(manifest.get('code_sha256')),
        'output_root': str(root),
        'phase_retained_bytes': manifest['budgets']['hp_confirmation']['retained_bytes'],
        'total_retained_bytes': manifest['budgets']['total_retained_bytes'],
        'slot_bytes': manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES,
        'total_slot_bytes': manifest_contract.CONFIRMATION_CONTROL_POOL_BYTES,
        'slot_state': 'reserved',
        'role': 'allocation_descriptor',
        'slots': {role: {'path': str(path), 'bytes': manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES}
                  for role, path in paths.items()},
    }


def _control_slot_reservation(descriptor, allocation_sha256, role):
    return {
        'kind': 'hp_confirmation_control_slot_reservation',
        'schema_version': 1,
        'role': role,
        'allocation_descriptor_sha256': allocation_sha256,
        'activation_id': descriptor['activation_id'],
        'run_id': descriptor['run_id'],
        'phase': descriptor['phase'],
        'git_head': descriptor['git_head'],
        'execution_intent_sha256': descriptor['execution_intent_sha256'],
        'manifest_sha256': descriptor['manifest_sha256'],
        'code_map_sha256': descriptor['code_map_sha256'],
        'output_root': descriptor['output_root'],
        'phase_retained_bytes': descriptor['phase_retained_bytes'],
        'total_retained_bytes': descriptor['total_retained_bytes'],
        'slot_bytes': descriptor['slot_bytes'],
        'slot_state': 'reserved',
    }


def _control_capacity_preflight(root, manifest, additional_bytes=0, *,
                                allow_unsafe_phase_path=False):
    root = Path(root).resolve(strict=True)
    phase_bytes = _confirmation_phase_bytes(
        root, allow_unsafe_path=allow_unsafe_phase_path)
    control_bytes = _confirmation_control_bytes(root)
    retained = _physical_retained_bytes(root)
    phase_limit = manifest['budgets']['hp_confirmation']['retained_bytes']
    total_limit = manifest['budgets']['total_retained_bytes']
    if phase_bytes+control_bytes+additional_bytes > phase_limit:
        raise AcquisitionStopped('retained_control_pool_budget')
    # The phase cap, including all controls, remains reserved in the global tree.
    if retained-phase_bytes-control_bytes+phase_limit > total_limit:
        raise AcquisitionStopped('total_retained_budget')


def _write_new_fixed_control_file(root_fd, name, raw):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor = os.open(name, flags, 0o600, dir_fd=root_fd)
    except FileExistsError:
        return False
    except OSError:
        raise AcquisitionStopped('confirmation_control_slot_persist_failed') from None
    try:
        written = 0
        while written < len(raw):
            amount = os.write(descriptor, raw[written:])
            if amount <= 0:
                raise OSError('short control slot write')
            written += amount
        os.fsync(descriptor)
    except OSError:
        raise AcquisitionStopped('confirmation_control_slot_persist_failed') from None
    finally:
        os.close(descriptor)
    return True


_CONTROL_INTEGER_KEYS = {
    'schema_version', 'phase_retained_bytes', 'total_retained_bytes', 'slot_bytes',
    'total_slot_bytes', 'candidate_count', 'attempts', 'successful_pages',
    'pages_per_station', 'response_bytes', 'response_body_bytes', 'retained_bytes',
    'wall_seconds', 'socket_seconds', 'concurrency', 'maximum_attempts_per_page',
    'bytes', 'rich', 'sparse',
}
_CONTROL_BOOLEAN_KEYS = {'single_use'}
_CONTROL_FLOAT_KEYS = {'minimum_request_interval_seconds'}


def _validate_control_integer_types(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _CONTROL_INTEGER_KEYS and type(item) is not int:
                raise AcquisitionStopped('confirmation_control_slot_integer_type')
            if key in _CONTROL_BOOLEAN_KEYS and type(item) is not bool:
                raise AcquisitionStopped('confirmation_control_slot_boolean_type')
            if key in _CONTROL_FLOAT_KEYS and type(item) is not float:
                raise AcquisitionStopped('confirmation_control_slot_float_type')
            _validate_control_integer_types(item)
    elif isinstance(value, list):
        for item in value:
            _validate_control_integer_types(item)


def _control_json(raw):
    if len(raw) != manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES:
        raise AcquisitionStopped('confirmation_control_slot_invalid')
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        raise AcquisitionStopped('confirmation_control_slot_invalid') from None
    if (not isinstance(value, dict)
            or type(value.get('schema_version')) is not int
            or value.get('schema_version') != 1):
        raise AcquisitionStopped('confirmation_control_slot_schema')
    _validate_control_integer_types(value)
    if not isinstance(value, dict) or _padded_control_slot(value) != raw:
        raise AcquisitionStopped('confirmation_control_slot_noncanonical')
    return value


def _checked_approval_sha256(value):
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in '0123456789abcdef' for character in value)):
        raise AcquisitionStopped('confirmation_execution_intent_approval_binding')
    return value


@contextmanager
def _confirmation_control_lock(root):
    root = Path(root).resolve(strict=True)
    descriptor = None
    try:
        descriptor = os.open(root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
                             | getattr(os, 'O_NOFOLLOW', 0))
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise AcquisitionStopped('confirmation_artifact_root_invalid')
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield root, descriptor
    except AcquisitionStopped:
        raise
    except OSError:
        raise AcquisitionStopped('confirmation_control_pool_unavailable') from None
    finally:
        if descriptor is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def _read_control_slot_locked(root_fd, name):
    descriptor = None
    try:
        descriptor = os.open(name, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0),
                             dir_fd=root_fd)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size != manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES):
            raise AcquisitionStopped('confirmation_control_slot_invalid')
        chunks = []
        while True:
            chunk = os.read(descriptor, 8192)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b''.join(chunks)
    except AcquisitionStopped:
        raise
    except OSError:
        raise AcquisitionStopped('confirmation_control_slot_missing_or_unreadable') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return raw, _control_json(raw)


def _rewrite_control_slot_locked(root_fd, name, expected_raw, value, *, pre_write_guard=None):
    raw = _padded_control_slot(value)
    descriptor = None
    try:
        descriptor = os.open(name, os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0),
                             dir_fd=root_fd)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size != manifest_contract.CONFIRMATION_CONTROL_SLOT_BYTES):
            raise AcquisitionStopped('confirmation_control_slot_invalid')
        chunks = []
        while True:
            chunk = os.read(descriptor, 8192)
            if not chunk:
                break
            chunks.append(chunk)
        if b''.join(chunks) != expected_raw:
            raise AcquisitionStopped('confirmation_control_slot_concurrent_change')
        if pre_write_guard is not None:
            pre_write_guard()
        written = 0
        while written < len(raw):
            amount = os.pwrite(descriptor, raw[written:], written)
            if amount <= 0:
                raise OSError('short fixed-slot rewrite')
            written += amount
        os.fsync(descriptor)
        os.fsync(root_fd)
    except AcquisitionStopped:
        raise
    except OSError:
        raise AcquisitionStopped('confirmation_control_slot_persist_failed') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return raw


def _read_control_pool_locked(root_fd, root, manifest, manifest_hash, head,
                              activation_id, run_id, execution_intent_sha256):
    descriptor = _control_pool_descriptor(
        manifest, manifest_hash, head, root, activation_id, run_id,
        execution_intent_sha256)
    paths = _control_pool_paths(root, activation_id, run_id)
    allocation_raw, allocation = _read_control_slot_locked(
        root_fd, paths['allocation_descriptor'].name)
    expected_allocation = _padded_control_slot(descriptor)
    if allocation_raw != expected_allocation:
        raise AcquisitionStopped('confirmation_control_pool_binding')
    allocation_sha = hashlib.sha256(allocation_raw).hexdigest()
    slots = {}
    raws = {'allocation_descriptor': allocation_raw}
    for role in manifest_contract.CONFIRMATION_CONTROL_POOL_CONTRACT['slot_roles']:
        if role == 'allocation_descriptor':
            continue
        raw, value = _read_control_slot_locked(root_fd, paths[role].name)
        reservation = _control_slot_reservation(descriptor, allocation_sha, role)
        if any(value.get(key) != expected for key, expected in reservation.items()
               if key not in ('kind', 'slot_state')):
            raise AcquisitionStopped('confirmation_control_slot_binding')
        if value != reservation:
            expected_kinds = {
                'preparation_owner_intent': ('hp_confirmation_preparation_owner_intent', 'issued'),
                'preparation_root_intent': ('hp_confirmation_preparation_root_intent', 'issued'),
                'burn_claim': ('hp_confirmation_activation_claim',
                               ('committed', 'consumer_started', 'terminal_rejected')),
                'final_owner_execution_receipt': ('owner_hp_confirmation_activation', 'issued'),
                'final_root_release_receipt': ('root_hp_confirmation_release', 'issued'),
            }
            expected_kind, expected_state = expected_kinds[role]
            actual_state = value.get('claim_state') if role == 'burn_claim' else value.get('slot_state')
            if (value.get('kind') != expected_kind
                    or (actual_state not in expected_state if isinstance(expected_state, tuple)
                        else actual_state != expected_state)):
                raise AcquisitionStopped('confirmation_control_slot_state_invalid')
        slots[role] = value
        raws[role] = raw
    return {
        'descriptor': descriptor,
        'descriptor_sha256': allocation_sha,
        'paths': paths,
        'slots': slots,
        'raws': raws,
        'slot_sha256': {role: hashlib.sha256(raw).hexdigest() for role, raw in raws.items()},
    }


def _intent_window(owner_intent):
    try:
        started = _utc(owner_intent['window_started_at'])
        deadline = _utc(owner_intent['absolute_deadline'])
    except (KeyError, TypeError):
        raise AcquisitionStopped('confirmation_preparation_intent_window') from None
    expected = min(started+timedelta(seconds=1800),
                   _utc(manifest_contract.CONFIRMATION_COMPLETION_BEFORE))
    if deadline != expected:
        raise AcquisitionStopped('confirmation_preparation_intent_window')
    return started, deadline


def _publish_confirmation_intents_locked(root_fd, root, pool, invocation_started,
                                         execution_intent_sha256):
    slots = pool['slots']
    descriptor = pool['descriptor']
    paths = pool['paths']
    owner = slots['preparation_owner_intent']
    root_intent = slots['preparation_root_intent']
    if owner.get('slot_state') == 'reserved':
        if root_intent.get('slot_state') != 'reserved':
            raise AcquisitionStopped('confirmation_preparation_partial_corrupt')
        started = invocation_started
        deadline = min(started+timedelta(seconds=1800),
                       _utc(manifest_contract.CONFIRMATION_COMPLETION_BEFORE))
        if started >= deadline:
            raise AcquisitionStopped('confirmation_completion_deadline_expired')
        live_now = datetime.now(timezone.utc)
        if live_now < started:
            raise AcquisitionStopped('confirmation_clock_moved_backwards')
        if live_now >= deadline:
            raise AcquisitionStopped('confirmation_completion_deadline_expired')

        def check_owner_publication_deadline():
            publish_now = datetime.now(timezone.utc)
            if publish_now < started:
                raise AcquisitionStopped('confirmation_clock_moved_backwards')
            if publish_now >= deadline:
                raise AcquisitionStopped('confirmation_completion_deadline_expired')

        owner_value = {
            **_control_slot_reservation(descriptor, pool['descriptor_sha256'],
                                        'preparation_owner_intent'),
            'kind': 'hp_confirmation_preparation_owner_intent',
            'slot_state': 'issued',
            'window_started_at': started.isoformat().replace('+00:00', 'Z'),
            'absolute_deadline': deadline.isoformat().replace('+00:00', 'Z'),
            'issued_at': started.isoformat().replace('+00:00', 'Z'),
            'execution_intent_sha256': execution_intent_sha256,
        }
        owner_raw = _rewrite_control_slot_locked(
            root_fd, paths['preparation_owner_intent'].name,
            pool['raws']['preparation_owner_intent'], owner_value,
            pre_write_guard=check_owner_publication_deadline)
        owner = owner_value
        pool['raws']['preparation_owner_intent'] = owner_raw
        pool['slot_sha256']['preparation_owner_intent'] = hashlib.sha256(owner_raw).hexdigest()
        slots['preparation_owner_intent'] = owner
    else:
        started, deadline = _intent_window(owner)
        if owner.get('execution_intent_sha256') != execution_intent_sha256:
            raise AcquisitionStopped('confirmation_execution_intent_approval_binding')

    if root_intent.get('slot_state') == 'reserved':
        root_now = datetime.now(timezone.utc)
        if root_now < started:
            raise AcquisitionStopped('confirmation_clock_moved_backwards')
        if root_now >= deadline:
            raise AcquisitionStopped('confirmation_completion_deadline_expired')

        def check_root_publication_deadline():
            publish_now = datetime.now(timezone.utc)
            if publish_now < started:
                raise AcquisitionStopped('confirmation_clock_moved_backwards')
            if publish_now >= deadline:
                raise AcquisitionStopped('confirmation_completion_deadline_expired')

        root_value = {
            **_control_slot_reservation(descriptor, pool['descriptor_sha256'],
                                        'preparation_root_intent'),
            'kind': 'hp_confirmation_preparation_root_intent',
            'slot_state': 'issued',
            'window_started_at': started.isoformat().replace('+00:00', 'Z'),
            'absolute_deadline': deadline.isoformat().replace('+00:00', 'Z'),
            'preparation_owner_intent_sha256': pool['slot_sha256']['preparation_owner_intent'],
            'execution_intent_sha256': execution_intent_sha256,
        }
        root_raw = _rewrite_control_slot_locked(
            root_fd, paths['preparation_root_intent'].name,
            pool['raws']['preparation_root_intent'], root_value,
            pre_write_guard=check_root_publication_deadline)
        root_intent = root_value
        pool['raws']['preparation_root_intent'] = root_raw
        pool['slot_sha256']['preparation_root_intent'] = hashlib.sha256(root_raw).hexdigest()
        slots['preparation_root_intent'] = root_intent
    elif (root_intent.get('window_started_at') != started.isoformat().replace('+00:00', 'Z')
          or root_intent.get('absolute_deadline') != deadline.isoformat().replace('+00:00', 'Z')
          or root_intent.get('preparation_owner_intent_sha256')
          != pool['slot_sha256']['preparation_owner_intent']
          or root_intent.get('execution_intent_sha256') != execution_intent_sha256):
        raise AcquisitionStopped('confirmation_preparation_partial_corrupt')
    return pool


def issue_confirmation_preparation_intents(manifest, manifest_hash, head, output_root,
                                           activation_id, run_id,
                                           execution_intent_sha256):
    """Anchor T0/D in the first durable owner intent; retries reuse that window."""
    invocation_started = datetime.now(timezone.utc).astimezone(timezone.utc)
    return _issue_confirmation_preparation_intents_at(
        manifest, manifest_hash, head, output_root, activation_id, run_id,
        invocation_started, execution_intent_sha256)


def _issue_confirmation_preparation_intents_at(manifest, manifest_hash, head, output_root,
                                                activation_id, run_id, invocation_started,
                                                execution_intent_sha256):
    execution_intent_sha256 = _checked_approval_sha256(execution_intent_sha256)
    root = Path(output_root).resolve(strict=True)
    if root != _confirmation_artifact_root(manifest):
        raise AcquisitionStopped('confirmation_artifact_root_mismatch')
    with _confirmation_control_lock(root) as (locked_root, root_fd):
        pool = _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                         head, activation_id, run_id, execution_intent_sha256)
        _control_capacity_preflight(root, manifest)
        pool = _publish_confirmation_intents_locked(
            root_fd, locked_root, pool, invocation_started, execution_intent_sha256)
        return pool


def commit_confirmation_burn_claim(manifest, manifest_hash, head, output_root,
                                   activation_id, run_id, execution_intent_sha256):
    """Commit the fixed preparation window into the reserved burn-claim slot."""
    now = datetime.now(timezone.utc)
    return _commit_confirmation_burn_claim_at(
        manifest, manifest_hash, head, output_root, activation_id, run_id, now,
        execution_intent_sha256)


def _commit_confirmation_burn_claim_at(manifest, manifest_hash, head, output_root,
                                       activation_id, run_id, now,
                                       execution_intent_sha256):
    execution_intent_sha256 = _checked_approval_sha256(execution_intent_sha256)
    root = Path(output_root).resolve(strict=True)
    if root != _confirmation_artifact_root(manifest):
        raise AcquisitionStopped('confirmation_artifact_root_mismatch')
    with _confirmation_control_lock(root) as (locked_root, root_fd):
        pool = _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                         head, activation_id, run_id, execution_intent_sha256)
        owner = pool['slots']['preparation_owner_intent']
        root_intent = pool['slots']['preparation_root_intent']
        if owner.get('slot_state') != 'issued' or root_intent.get('slot_state') != 'issued':
            raise AcquisitionStopped('confirmation_preparation_intents_required')
        if (pool['slots']['final_owner_execution_receipt'].get('slot_state') != 'reserved'
                or pool['slots']['final_root_release_receipt'].get('slot_state') != 'reserved'):
            raise AcquisitionStopped('confirmation_final_receipt_order')
        _control_capacity_preflight(root, manifest)
        started, deadline = _intent_window(owner)
        if (root_intent.get('window_started_at') != owner.get('window_started_at')
                or root_intent.get('absolute_deadline') != owner.get('absolute_deadline')
                or root_intent.get('preparation_owner_intent_sha256')
                != pool['slot_sha256']['preparation_owner_intent']
                or owner.get('execution_intent_sha256') != execution_intent_sha256
                or root_intent.get('execution_intent_sha256') != execution_intent_sha256):
            raise AcquisitionStopped('confirmation_preparation_intent_mismatch')
        claim = pool['slots']['burn_claim']
        if claim.get('slot_state') == 'reserved':
            if not started <= now < deadline:
                raise AcquisitionStopped('confirmation_completion_deadline_expired')

            def check_claim_commit_deadline():
                commit_now = datetime.now(timezone.utc)
                if commit_now < started:
                    raise AcquisitionStopped('confirmation_clock_moved_backwards')
                if commit_now >= deadline:
                    raise AcquisitionStopped('confirmation_completion_deadline_expired')

            commitment = {
                'phase': 'hp_confirmation',
                'activation_id': activation_id,
                'run_id': run_id,
                'git_head': head,
                'manifest_sha256': manifest_hash,
                'code_map_sha256': pool['descriptor']['code_map_sha256'],
                'output_root': str(root),
                'allocation_descriptor_sha256': pool['descriptor_sha256'],
                'preparation_owner_intent_sha256': pool['slot_sha256']['preparation_owner_intent'],
                'preparation_root_intent_sha256': pool['slot_sha256']['preparation_root_intent'],
                'execution_intent_sha256': execution_intent_sha256,
                'window_started_at': owner['window_started_at'],
                'absolute_deadline': owner['absolute_deadline'],
                'phase_retained_bytes': pool['descriptor']['phase_retained_bytes'],
                'total_retained_bytes': pool['descriptor']['total_retained_bytes'],
            }
            claim_value = {
                **_control_slot_reservation(pool['descriptor'], pool['descriptor_sha256'],
                                            'burn_claim'),
                'kind': 'hp_confirmation_activation_claim',
                'claim_state': 'committed',
                **commitment,
                'claimed_at': now.isoformat().replace('+00:00', 'Z'),
                'claim_commitment_sha256': hashlib.sha256(encoded(commitment)).hexdigest(),
            }
            claim_raw = _rewrite_control_slot_locked(
                root_fd, pool['paths']['burn_claim'].name,
                pool['raws']['burn_claim'], claim_value,
                pre_write_guard=check_claim_commit_deadline)
            pool['slots']['burn_claim'] = claim_value
            pool['raws']['burn_claim'] = claim_raw
            pool['slot_sha256']['burn_claim'] = hashlib.sha256(claim_raw).hexdigest()
            claim = claim_value
        elif claim.get('claim_state') not in ('committed', 'consumer_started'):
            raise AcquisitionStopped('confirmation_claim_state_invalid')
        if (claim.get('window_started_at') != owner.get('window_started_at')
                or claim.get('absolute_deadline') != owner.get('absolute_deadline')):
            raise AcquisitionStopped('confirmation_activation_claim_window')
        return pool


def publish_confirmation_execution_receipts(manifest, manifest_hash, head, output_root,
                                            activation_id, run_id,
                                            execution_intent_sha256,
                                            owner_receipt, root_release_receipt):
    """Persist externally approved final receipts into their already charged slots."""
    execution_intent_sha256 = _checked_approval_sha256(execution_intent_sha256)
    root = Path(output_root).resolve(strict=True)
    if root != _confirmation_artifact_root(manifest):
        raise AcquisitionStopped('confirmation_artifact_root_mismatch')
    if not isinstance(owner_receipt, dict) or not isinstance(root_release_receipt, dict):
        raise AcquisitionStopped('confirmation_final_execution_receipts_required')
    with _confirmation_control_lock(root) as (locked_root, root_fd):
        pool = _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                         head, activation_id, run_id,
                                         execution_intent_sha256)
        _control_capacity_preflight(root, manifest)
        pool = _validate_control_chain(pool)
        claim = pool['slots']['burn_claim']
        if claim.get('claim_state') != 'committed':
            raise AcquisitionStopped('confirmation_final_receipt_order')
        owner_intent = pool['slots']['preparation_owner_intent']
        started, deadline = _intent_window(owner_intent)
        now = datetime.now(timezone.utc)
        if not started <= now < deadline:
            raise AcquisitionStopped('confirmation_completion_deadline_expired')
        chain_fields = {
            'allocation_descriptor_sha256': pool['descriptor_sha256'],
            'preparation_owner_intent_sha256': pool['slot_sha256']['preparation_owner_intent'],
            'preparation_root_intent_sha256': pool['slot_sha256']['preparation_root_intent'],
            'execution_intent_sha256': execution_intent_sha256,
            'burn_claim_commitment_sha256': claim['claim_commitment_sha256'],
            'window_started_at': owner_intent['window_started_at'],
            'absolute_deadline': owner_intent['absolute_deadline'],
        }
        owner_reservation = _control_slot_reservation(
            pool['descriptor'], pool['descriptor_sha256'], 'final_owner_execution_receipt')
        root_reservation = _control_slot_reservation(
            pool['descriptor'], pool['descriptor_sha256'], 'final_root_release_receipt')
        for role, value, reservation, kind in (
                ('final_owner_execution_receipt', owner_receipt, owner_reservation,
                 'owner_hp_confirmation_activation'),
                ('final_root_release_receipt', root_release_receipt, root_reservation,
                 'root_hp_confirmation_release')):
            if (value.get('kind') != kind or value.get('slot_state') != 'issued'
                    or any(value.get(key) != expected for key, expected in reservation.items()
                           if key not in ('kind', 'slot_state'))
                    or any(value.get(key) != expected for key, expected in chain_fields.items())):
                raise AcquisitionStopped('confirmation_final_receipt_binding')
            _padded_control_slot(value)
        owner_raw = _padded_control_slot(owner_receipt)
        owner_sha = hashlib.sha256(owner_raw).hexdigest()
        if (root_release_receipt.get('owner_activation_sha256') != owner_sha
                or not isinstance(root_release_receipt.get('root_manifest_check'), dict)
                or root_release_receipt['root_manifest_check'].get('owner_activation_sha256')
                != owner_sha):
            raise AcquisitionStopped('confirmation_final_receipt_binding')
        owner_slot = pool['slots']['final_owner_execution_receipt']
        root_slot = pool['slots']['final_root_release_receipt']
        if owner_slot.get('slot_state') not in ('reserved', 'issued'):
            raise AcquisitionStopped('confirmation_final_receipt_order')
        if root_slot.get('slot_state') not in ('reserved', 'issued'):
            raise AcquisitionStopped('confirmation_final_receipt_order')
        if owner_slot.get('slot_state') == 'reserved':
            def check_owner_receipt_deadline():
                if datetime.now(timezone.utc) >= deadline:
                    raise AcquisitionStopped('confirmation_completion_deadline_expired')

            _rewrite_control_slot_locked(
                root_fd, pool['paths']['final_owner_execution_receipt'].name,
                pool['raws']['final_owner_execution_receipt'], owner_receipt,
                pre_write_guard=check_owner_receipt_deadline)
            pool = _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                             head, activation_id, run_id,
                                             execution_intent_sha256)
        elif pool['raws']['final_owner_execution_receipt'] != owner_raw:
            raise AcquisitionStopped('confirmation_final_receipt_already_issued')
        root_raw = _padded_control_slot(root_release_receipt)
        if root_slot.get('slot_state') == 'reserved':
            def check_root_release_deadline():
                if datetime.now(timezone.utc) >= deadline:
                    raise AcquisitionStopped('confirmation_completion_deadline_expired')

            _rewrite_control_slot_locked(
                root_fd, pool['paths']['final_root_release_receipt'].name,
                pool['raws']['final_root_release_receipt'], root_release_receipt,
                pre_write_guard=check_root_release_deadline)
            pool = _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                             head, activation_id, run_id,
                                             execution_intent_sha256)
        elif pool['raws']['final_root_release_receipt'] != root_raw:
            raise AcquisitionStopped('confirmation_final_receipt_already_issued')
        return _validate_control_chain(pool, require_final=True)


def _confirmation_claim_commitment(claim):
    keys = (
        'phase', 'activation_id', 'run_id', 'git_head', 'manifest_sha256',
        'code_map_sha256', 'output_root', 'allocation_descriptor_sha256',
        'preparation_owner_intent_sha256', 'preparation_root_intent_sha256',
        'execution_intent_sha256',
        'window_started_at', 'absolute_deadline', 'phase_retained_bytes',
        'total_retained_bytes',
    )
    try:
        return {key: claim[key] for key in keys}
    except (KeyError, TypeError):
        raise AcquisitionStopped('confirmation_activation_claim_invalid') from None


def _validate_control_chain(pool, *, require_final=False):
    slots = pool['slots']
    owner_intent = slots['preparation_owner_intent']
    root_intent = slots['preparation_root_intent']
    claim = slots['burn_claim']
    if owner_intent.get('slot_state') != 'issued':
        raise AcquisitionStopped('confirmation_preparation_owner_intent_missing')
    started, deadline = _intent_window(owner_intent)
    expected_started = owner_intent['window_started_at']
    expected_deadline = owner_intent['absolute_deadline']
    if (owner_intent.get('issued_at') != expected_started
            or _checked_approval_sha256(owner_intent.get('execution_intent_sha256'))
            != root_intent.get('execution_intent_sha256')
            or root_intent.get('slot_state') != 'issued'
            or root_intent.get('window_started_at') != expected_started
            or root_intent.get('absolute_deadline') != expected_deadline
            or root_intent.get('preparation_owner_intent_sha256')
            != pool['slot_sha256']['preparation_owner_intent']):
        raise AcquisitionStopped('confirmation_preparation_intent_mismatch')
    if claim.get('claim_state') not in ('committed', 'consumer_started', 'terminal_rejected'):
        if require_final:
            raise AcquisitionStopped('confirmation_activation_claim_missing')
        return pool
    commitment = _confirmation_claim_commitment(claim)
    try:
        claimed_at = _utc(claim.get('claimed_at'))
    except AcquisitionStopped:
        raise AcquisitionStopped('confirmation_activation_claim_invalid') from None
    if (claim.get('claim_commitment_sha256') != hashlib.sha256(encoded(commitment)).hexdigest()
            or claim.get('allocation_descriptor_sha256') != pool['descriptor_sha256']
            or claim.get('preparation_owner_intent_sha256')
            != pool['slot_sha256']['preparation_owner_intent']
            or claim.get('preparation_root_intent_sha256')
            != pool['slot_sha256']['preparation_root_intent']
            or claim.get('execution_intent_sha256') != owner_intent.get('execution_intent_sha256')
            or claim.get('window_started_at') != expected_started
            or claim.get('absolute_deadline') != expected_deadline
            or not started <= claimed_at < deadline):
        raise AcquisitionStopped('confirmation_activation_claim_binding')
    if require_final:
        owner = slots['final_owner_execution_receipt']
        root_release = slots['final_root_release_receipt']
        if (owner.get('slot_state') != 'issued'
                or root_release.get('slot_state') != 'issued'):
            raise AcquisitionStopped('confirmation_final_execution_receipts_required')
        receipt_bindings = {
            'allocation_descriptor_sha256': pool['descriptor_sha256'],
            'preparation_owner_intent_sha256': pool['slot_sha256']['preparation_owner_intent'],
            'preparation_root_intent_sha256': pool['slot_sha256']['preparation_root_intent'],
            'execution_intent_sha256': claim['execution_intent_sha256'],
            'burn_claim_commitment_sha256': claim['claim_commitment_sha256'],
            'window_started_at': expected_started,
            'absolute_deadline': expected_deadline,
        }
        if any(owner.get(key) != value or root_release.get(key) != value
               for key, value in receipt_bindings.items()):
            raise AcquisitionStopped('confirmation_final_receipt_binding')
        owner_sha = pool['slot_sha256']['final_owner_execution_receipt']
        if root_release.get('owner_activation_sha256') != owner_sha:
            raise AcquisitionStopped('confirmation_final_receipt_binding')
    return pool


def reserve_confirmation_control_pool(manifest, manifest_hash, head, output_root,
                                      activation_id, run_id, execution_intent_sha256):
    """Reserve all six fixed-size ART slots; run.main never creates a pool."""
    root = Path(output_root).resolve(strict=True)
    if root != _confirmation_artifact_root(manifest):
        raise AcquisitionStopped('confirmation_artifact_root_mismatch')
    descriptor = _control_pool_descriptor(
        manifest, manifest_hash, head, root, activation_id, run_id,
        execution_intent_sha256)
    descriptor_raw = _padded_control_slot(descriptor)
    descriptor_sha = hashlib.sha256(descriptor_raw).hexdigest()
    expected = {'allocation_descriptor': descriptor_raw}
    for role in manifest_contract.CONFIRMATION_CONTROL_POOL_CONTRACT['slot_roles']:
        if role != 'allocation_descriptor':
            expected[role] = _padded_control_slot(
                _control_slot_reservation(descriptor, descriptor_sha, role))
    paths = _control_pool_paths(root, activation_id, run_id)
    with _confirmation_control_lock(root) as (locked_root, root_fd):
        try:
            existing = {path.name: size for path, size in _confirmation_control_files(locked_root)}
            missing_bytes = sum(len(raw) for role, raw in expected.items()
                                if paths[role].name not in existing)
            if missing_bytes:
                # Budget writes phase bytes while holding hp_confirmation/.reader.lock.
                # Its authority guard marks consumer_started under this ART lock first;
                # once that state is visible, no new allocation may race a later check.
                if _confirmation_consumer_started_locked(root_fd, locked_root):
                    raise AcquisitionStopped('confirmation_control_pool_frozen')
                _control_capacity_preflight(root, manifest, missing_bytes)
            for role, raw in expected.items():
                name = paths[role].name
                if name in existing:
                    current_raw, _current = _read_control_slot_locked(root_fd, name)
                    if role == 'allocation_descriptor' and current_raw != raw:
                        raise AcquisitionStopped('confirmation_control_pool_binding')
                    if role != 'allocation_descriptor':
                        current = _control_json(current_raw)
                        if (current.get('allocation_descriptor_sha256') != descriptor_sha
                                or current.get('role') != role):
                            raise AcquisitionStopped('confirmation_control_pool_binding')
                else:
                    _write_new_fixed_control_file(root_fd, name, raw)
            os.fsync(root_fd)
            return _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                             head, activation_id, run_id,
                                             execution_intent_sha256)
        except AcquisitionStopped:
            raise
        except OSError:
            raise AcquisitionStopped('confirmation_control_pool_unavailable') from None


def _confirmation_control_chain(manifest, manifest_hash, head, output_root,
                                 activation_id, run_id, execution_intent_sha256,
                                 *, require_final=False):
    root = Path(output_root).resolve(strict=True)
    if root != _confirmation_artifact_root(manifest):
        raise AcquisitionStopped('confirmation_artifact_root_mismatch')
    with _confirmation_control_lock(root) as (locked_root, root_fd):
        pool = _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                         head, activation_id, run_id,
                                         execution_intent_sha256)
        _control_capacity_preflight(root, manifest, allow_unsafe_phase_path=True)
        return _validate_control_chain(pool, require_final=require_final)


def _terminal_reject_confirmation_claim(manifest, manifest_hash, head, output_root,
                                        activation_id, run_id, execution_intent_sha256,
                                        reason):
    """Persist a fixed-size terminal rejection in the pre-reserved claim slot."""
    root = Path(output_root).resolve(strict=True)
    with _confirmation_control_lock(root) as (locked_root, root_fd):
        pool = _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                         head, activation_id, run_id,
                                         execution_intent_sha256)
        pool = _validate_control_chain(pool, require_final=True)
        claim = pool['slots']['burn_claim']
        if claim.get('claim_state') == 'terminal_rejected':
            return pool
        terminal = dict(claim)
        terminal['claim_state'] = 'terminal_rejected'
        terminal['terminal_reason'] = reason
        terminal['terminal_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        raw = _rewrite_control_slot_locked(
            root_fd, pool['paths']['burn_claim'].name,
            pool['raws']['burn_claim'], terminal)
        pool['slots']['burn_claim'] = terminal
        pool['raws']['burn_claim'] = raw
        pool['slot_sha256']['burn_claim'] = hashlib.sha256(raw).hexdigest()
        return pool


def _consume_confirmation_control_claim(manifest, manifest_hash, head, output_root,
                                        activation_id, run_id, execution_intent_sha256,
                                        *, resume):
    """Mark the reserved claim in place under the ART lock after phase lock acquisition."""
    root = Path(output_root).resolve(strict=True)
    with _confirmation_control_lock(root) as (locked_root, root_fd):
        pool = _read_control_pool_locked(root_fd, locked_root, manifest, manifest_hash,
                                         head, activation_id, run_id,
                                         execution_intent_sha256)
        _control_capacity_preflight(root, manifest)
        pool = _validate_control_chain(pool, require_final=True)
        claim = pool['slots']['burn_claim']
        started, deadline = _intent_window(pool['slots']['preparation_owner_intent'])
        now = datetime.now(timezone.utc)
        if now < started:
            raise AcquisitionStopped('confirmation_clock_precedes_start')
        if now >= deadline:
            raise AcquisitionStopped('confirmation_completion_deadline_expired')
        if claim.get('claim_state') == 'committed':
            claim_value = dict(claim)
            claim_value['claim_state'] = 'consumer_started'
            claim_value['consumer_started_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            def check_consumer_start_deadline():
                commit_now = datetime.now(timezone.utc)
                if commit_now < started:
                    raise AcquisitionStopped('confirmation_clock_precedes_start')
                if commit_now >= deadline:
                    raise AcquisitionStopped('confirmation_completion_deadline_expired')

            claim_raw = _rewrite_control_slot_locked(
                root_fd, pool['paths']['burn_claim'].name,
                pool['raws']['burn_claim'], claim_value,
                pre_write_guard=check_consumer_start_deadline)
            pool['slots']['burn_claim'] = claim_value
            pool['raws']['burn_claim'] = claim_raw
            pool['slot_sha256']['burn_claim'] = hashlib.sha256(claim_raw).hexdigest()
        elif claim.get('claim_state') == 'consumer_started':
            if not resume:
                raise AcquisitionStopped('confirmation_activation_already_claimed')
        else:
            raise AcquisitionStopped('confirmation_activation_claim_state_invalid')
        return pool


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
                                 prior_v20_manifest_path, prior_v20_archive_path,
                                 prior_v21_manifest_path, prior_v21_archive_path, head):
    """Validate the direct V21 predecessor and preserved historical V20 handoff."""
    amendment = checked_confirmation_amendment(manifest)
    handoff = amendment.get('historical_v20')
    handoff_v21 = amendment.get('historical_v21')
    if not isinstance(handoff, dict):
        raise AcquisitionStopped('confirmation_historical_handoff_missing')
    if not isinstance(handoff_v21, dict):
        raise AcquisitionStopped('confirmation_v21_historical_handoff_missing')
    v21_manifest_path = _bound_file(
        prior_v21_manifest_path, handoff_v21.get('manifest_path'),
        'confirmation_v21_manifest_path')
    v21_archive_path = _bound_file(
        prior_v21_archive_path, handoff_v21.get('archive_path'),
        'confirmation_v21_archive_path')
    manifest_path = _bound_file(prior_v20_manifest_path, handoff.get('manifest_path'),
                                'confirmation_v20_manifest_path')
    archive_path = _bound_file(prior_v20_archive_path, handoff.get('archive_path'),
                               'confirmation_v20_archive_path')
    prescreen_path = _bound_file(prior_prescreen_path, handoff.get('prescreen_envelope_path'),
                                 'confirmation_v20_prescreen_path')
    checkpoint_path = _bound_file(prior_checkpoint_path, handoff.get('control_checkpoint_path'),
                                  'confirmation_v20_checkpoint_path')
    try:
        v21_manifest_raw = v21_manifest_path.read_bytes()
        v21_archive_raw = v21_archive_path.read_bytes()
        if (hashlib.sha256(v21_manifest_raw).hexdigest() != manifest_contract.V21_MANIFEST_SHA256
                or hashlib.sha256(v21_archive_raw).hexdigest() != manifest_contract.V21_ARCHIVE_SHA256
                or v21_manifest_raw != v21_archive_raw):
            raise AcquisitionStopped('confirmation_v21_predecessor_hash')
        v21_predecessor = json.loads(v21_manifest_raw)
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
        expected_successor = manifest_contract.make_confirmation_successor_v22(
            v21_manifest_raw, v21_archive_raw,
            artifact_root=handoff_v21.get('artifact_root'), runtime_root=ROOT,
            code_head=head)
    except (ValueError, OSError, TypeError):
        raise AcquisitionStopped('confirmation_successor_binding_invalid') from None
    if (manifest != expected_successor
            or handoff != expected_successor['confirmation_amendment']['historical_v20']
            or handoff_v21 != expected_successor['confirmation_amendment']['historical_v21']
            or v21_predecessor.get('supersedes_manifest_sha256') != manifest_contract.V20_MANIFEST_SHA256):
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
        owner_candidate = Path(owner_path)
        gate_candidate = Path(gate_path)
        if (owner_candidate.is_symlink() or gate_candidate.is_symlink()
                or owner_candidate.parent.resolve() != bound_output_root
                or gate_candidate.parent.resolve() != bound_output_root
                or not owner_candidate.name.startswith(_CONTROL_ROLE_PREFIX['final_owner_execution_receipt'])
                or not gate_candidate.name.startswith(_CONTROL_ROLE_PREFIX['final_root_release_receipt'])
                or not owner_candidate.name.endswith('.json')
                or not gate_candidate.name.endswith('.json')):
            raise AcquisitionStopped('confirmation_final_receipt_path')
        owner_candidate = owner_candidate.parent.resolve()/owner_candidate.name
        gate_candidate = gate_candidate.parent.resolve()/gate_candidate.name
        owner_raw = _read_fixed_control_file(owner_candidate)
        owner = _control_json(owner_raw)
    except AcquisitionStopped:
        raise
    except (OSError, ValueError, TypeError):
        raise AcquisitionStopped('confirmation_owner_or_root_release_unreadable') from None
    activation_id, run_id = owner.get('activation_id'), owner.get('run_id')
    if not isinstance(activation_id, str) or not activation_id or not isinstance(run_id, str) or not run_id:
        raise AcquisitionStopped('confirmation_owner_activation_binding')
    if (owner.get('manifest_sha256') != manifest_hash
            or owner.get('git_head') != head
            or owner.get('code_map_sha256')
            != manifest_contract.canonical_code_map_sha256(manifest.get('code_sha256'))
            or owner.get('output_root') != str(bound_output_root)):
        raise AcquisitionStopped('confirmation_owner_activation_binding')
    execution_intent_sha256 = _checked_approval_sha256(owner.get('execution_intent_sha256'))
    pool = _confirmation_control_chain(
        manifest, manifest_hash, head, bound_output_root, activation_id, run_id,
        execution_intent_sha256, require_final=True)
    if (owner_candidate != pool['paths']['final_owner_execution_receipt']
            or gate_candidate != pool['paths']['final_root_release_receipt']
            or owner_raw != pool['raws']['final_owner_execution_receipt']):
        raise AcquisitionStopped('confirmation_final_receipt_path')
    gate_raw = pool['raws']['final_root_release_receipt']
    gate = pool['slots']['final_root_release_receipt']
    if pool['slots']['burn_claim'].get('claim_state') == 'terminal_rejected':
        raise AcquisitionStopped('confirmation_activation_terminal_rejection')
    checked_confirmation_amendment(manifest)
    map_sha = manifest_contract.canonical_code_map_sha256(manifest.get('code_sha256'))
    owner_sha = pool['slot_sha256']['final_owner_execution_receipt']
    claim = pool['slots']['burn_claim']
    owner_intent = pool['slots']['preparation_owner_intent']
    root_intent = pool['slots']['preparation_root_intent']
    claim_commitment_sha = claim['claim_commitment_sha256']
    started, deadline = _intent_window(owner_intent)
    chain_fields = {
        'allocation_descriptor_sha256': pool['descriptor_sha256'],
        'preparation_owner_intent_sha256': pool['slot_sha256']['preparation_owner_intent'],
        'preparation_root_intent_sha256': pool['slot_sha256']['preparation_root_intent'],
        'burn_claim_commitment_sha256': claim_commitment_sha,
        'execution_intent_sha256': owner_intent['execution_intent_sha256'],
        'window_started_at': started.isoformat().replace('+00:00', 'Z'),
        'absolute_deadline': deadline.isoformat().replace('+00:00', 'Z'),
    }
    allowed = ['hp_confirmation']
    expected_owner = {
        'kind': 'owner_hp_confirmation_activation',
        'slot_state': 'issued',
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
        **chain_fields,
    }
    if (not isinstance(owner, dict)
            or any(owner.get(key) != value for key, value in expected_owner.items())
            or owner.get('activation_id') != activation_id
            or owner.get('run_id') != run_id):
        raise AcquisitionStopped('confirmation_owner_activation_binding')
    if manifest.get('confirmation_amendment', {}).get('git_head') != head:
        raise AcquisitionStopped('confirmation_manifest_head_mismatch')
    try:
        created = _utc(owner.get('created_at'))
        owner_expires = _utc(owner.get('expires_at'))
    except AcquisitionStopped:
        raise AcquisitionStopped('confirmation_owner_activation_time') from None
    if (created < started or created > invocation_utc or owner_expires <= invocation_utc
            or owner_expires > deadline):
        raise AcquisitionStopped('confirmation_owner_activation_not_fresh')

    expected_root_check = {
        'manifest_sha256': manifest_hash,
        'git_head': head,
        'code_map_sha256': map_sha,
        'allowed_phases': allowed,
        'output_root': str(bound_output_root),
        'owner_activation_sha256': owner_sha,
        **chain_fields,
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
            or any(gate.get(key) != value for key, value in chain_fields.items())
            or gate.get('root_manifest_check') != expected_root_check):
        raise AcquisitionStopped('confirmation_root_gate_binding')
    try:
        released = _utc(gate.get('released_at'))
        root_expires = _utc(gate.get('expires_at'))
    except AcquisitionStopped:
        raise AcquisitionStopped('confirmation_root_gate_time') from None
    if (released < started or released > invocation_utc or root_expires <= invocation_utc
            or root_expires > deadline):
        raise AcquisitionStopped('confirmation_root_gate_not_fresh')
    if manifest.get('confirmation_amendment', {}).get('allowed_phases') != allowed:
        raise AcquisitionStopped('confirmation_scope_not_single_phase')
    if (released < created or claim.get('window_started_at') != chain_fields['window_started_at']
            or claim.get('absolute_deadline') != chain_fields['absolute_deadline']
            or root_intent.get('window_started_at') != chain_fields['window_started_at']):
        raise AcquisitionStopped('confirmation_final_receipt_window')
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
                                head, output_root, control_pool=None):
    if control_pool is None:
        control_pool = _confirmation_control_chain(
            manifest, manifest_hash, head, output_root,
            owner['activation_id'], owner['run_id'], owner['execution_intent_sha256'],
            require_final=True)
    claim = control_pool['slots']['burn_claim']
    return {
        'kind': 'hp_confirmation_activation_claim',
        'schema_version': 1,
        'phase': 'hp_confirmation',
        'manifest_sha256': manifest_hash,
        'git_head': head,
        'code_map_sha256': manifest_contract.canonical_code_map_sha256(manifest.get('code_sha256')),
        'output_root': str(Path(output_root).resolve()),
        'activation_id': owner['activation_id'],
        'run_id': owner['run_id'],
        'allocation_descriptor_sha256': control_pool['descriptor_sha256'],
        'preparation_owner_intent_sha256': control_pool['slot_sha256']['preparation_owner_intent'],
        'preparation_root_intent_sha256': control_pool['slot_sha256']['preparation_root_intent'],
        'execution_intent_sha256': claim.get('execution_intent_sha256'),
        'claim_commitment_sha256': claim.get('claim_commitment_sha256'),
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


def _read_confirmation_claim(claim_path, binding):
    path = Path(claim_path)
    expected_path = _confirmation_claim_path(binding['output_root'], binding)
    if path != expected_path:
        raise AcquisitionStopped('confirmation_activation_claim_path')
    try:
        raw = _read_fixed_control_file(path)
        claim = _control_json(raw)
    except AcquisitionStopped:
        raise
    except (OSError, ValueError, TypeError):
        raise AcquisitionStopped('confirmation_activation_claim_missing') from None
    if (claim.get('kind') != 'hp_confirmation_activation_claim'
            or claim.get('claim_state') not in ('committed', 'consumer_started')
            or any(claim.get(key) != value for key, value in binding.items())):
        raise AcquisitionStopped('confirmation_activation_claim_binding')
    try:
        started = _utc(claim['window_started_at'])
        deadline = _utc(claim['absolute_deadline'])
    except AcquisitionStopped:
        raise AcquisitionStopped('confirmation_activation_claim_invalid') from None
    commitment = _confirmation_claim_commitment(claim)
    if (claim.get('claim_commitment_sha256') != hashlib.sha256(encoded(commitment)).hexdigest()
            or deadline != min(started+timedelta(seconds=1800),
                               _utc(manifest_contract.CONFIRMATION_COMPLETION_BEFORE))):
        raise AcquisitionStopped('confirmation_activation_claim_window')
    return claim, claim['claim_commitment_sha256'], started, deadline


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
    phase_dir = Path(phase_dir)
    if claim_root is None:
        raise AcquisitionStopped('confirmation_artifact_root_invalid')
    root = Path(claim_root).resolve(strict=True)
    if (phase_dir.is_symlink() or not phase_dir.is_dir()
            or phase_dir.resolve(strict=True) != root/'hp_confirmation'):
        raise AcquisitionStopped('confirmation_phase_directory_invalid')
    path = phase_dir/'activation-budget-started.json'
    marker = {
        'kind': 'hp_confirmation_budget_started',
        'schema_version': 1,
        'claim_sha256': claim_sha,
    }
    # Keep every preconsumer byte check/write in the same serialization domain as
    # control-pool allocation. Budget later takes .reader.lock then this ART lock;
    # no ART-locked path takes .reader.lock, so the order cannot invert.
    with _confirmation_control_lock(root) as (locked_root, _root_fd):
        if path.exists() or path.is_symlink():
            return _read_confirmation_budget_marker(phase_dir, claim_sha)
        if retained_limit is not None:
            phase_bytes = _physical_retained_bytes(phase_dir)
            claim_bytes = _confirmation_control_bytes(locked_root)
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
    if claim_binding is None:
        raise AcquisitionStopped('confirmation_activation_claim_missing')
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
            if claim_started != started or claim_deadline != deadline:
                raise AcquisitionStopped('confirmation_activation_claim_window')
            _read_confirmation_budget_marker(phase_dir, claim_sha)
            if ledger.get('status') == 'complete':
                raise AcquisitionStopped('confirmation_run_already_finalized')
            if ledger.get('finalization_rejections'):
                raise AcquisitionStopped('confirmation_late_finalization_not_admissible')
        else:
            if marker_path.exists() or marker_path.is_symlink():
                raise AcquisitionStopped('confirmation_resume_ledger_missing')
            try:
                entries = {path.name for path in phase_dir.iterdir()}
            except OSError:
                raise AcquisitionStopped('confirmation_resume_window_missing') from None
            if entries:
                raise AcquisitionStopped('confirmation_resume_ledger_missing')
            if claim.get('claim_state') != 'consumer_started':
                raise AcquisitionStopped('confirmation_resume_before_consumer_start')
            started, deadline = claim_started, claim_deadline
    else:
        try:
            if phase_dir.exists() and any(phase_dir.iterdir()):
                raise AcquisitionStopped('confirmation_activation_already_claimed')
        except OSError:
            raise AcquisitionStopped('confirmation_phase_directory_invalid') from None
        if claim.get('claim_state') != 'committed':
            raise AcquisitionStopped('confirmation_activation_already_claimed')
        started, deadline = claim_started, claim_deadline
    elapsed = (invocation_utc-started).total_seconds()
    remaining = min(1800-elapsed, (deadline-invocation_utc).total_seconds())
    if invocation_utc < started:
        raise AcquisitionStopped('confirmation_clock_precedes_start')
    if remaining <= 0 or invocation_utc >= claim_deadline:
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
    parser.add_argument('--prior-v21-manifest', type=Path)
    parser.add_argument('--prior-v21-archive', type=Path)
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
                          args.prior_v20_archive, args.prior_v21_manifest,
                          args.prior_v21_archive, args.owner_activation)
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
    confirmation_control_pool = None
    confirmation_authority_guard = None
    if args.phase == 'hp_confirmation':
        checked_confirmation_amendment(manifest)
        head = confirmation_git_head()
        confirmation_owner, confirmation_gate, owner_sha, gate_sha = checked_confirmation_gate(
            args.execution_gate, args.owner_activation, manifest, manifest_hash, head, root, invocation_utc)
        confirmation_control_pool = _confirmation_control_chain(
            manifest, manifest_hash, head, root,
            confirmation_owner['activation_id'], confirmation_owner['run_id'],
            confirmation_owner['execution_intent_sha256'], require_final=True)
        confirmation_claim_binding = _confirmation_claim_binding(
            confirmation_owner, owner_sha, gate_sha, manifest, manifest_hash, head, root,
            control_pool=confirmation_control_pool)
        claim_path = _confirmation_claim_path(root, confirmation_claim_binding)
        _claim, confirmation_claim_sha, confirmation_started, confirmation_deadline = _read_confirmation_claim(
            claim_path, confirmation_claim_binding)
        try:
            confirmation_phase_dir = _confirmation_phase_directory(root)
        except AcquisitionStopped as exc:
            if str(exc) == 'confirmation_phase_directory_invalid':
                _terminal_reject_confirmation_claim(
                    manifest, manifest_hash, head, root,
                    confirmation_owner['activation_id'], confirmation_owner['run_id'],
                    confirmation_owner['execution_intent_sha256'],
                    'confirmation_phase_directory_invalid')
            raise
        ledger_path = confirmation_phase_dir/'ledger.json'
        marker_path = confirmation_phase_dir/'activation-budget-started.json'
        confirmation_resume_from_claim = (
            args.resume and not ledger_path.exists() and not marker_path.exists()
            and not ledger_path.is_symlink() and not marker_path.is_symlink())
        if (args.resume and not ledger_path.exists() and _claim.get('claim_state') != 'consumer_started'):
            raise AcquisitionStopped('confirmation_resume_before_consumer_start')
        confirmation_authority_guard = lambda: _consume_confirmation_control_claim(
            manifest, manifest_hash, head, root, confirmation_owner['activation_id'],
            confirmation_owner['run_id'], confirmation_owner['execution_intent_sha256'],
            resume=args.resume)
        confirmation_started, confirmation_deadline, confirmation_monotonic_remaining = _confirmation_run_window(
            args, manifest_hash, invocation_utc, phase_dir=confirmation_phase_dir,
            claim_binding=confirmation_claim_binding, claim_path=claim_path)
        _check_confirmation_run_window(confirmation_started, confirmation_deadline, invocation_utc,
                                       invocation_monotonic, confirmation_monotonic_remaining)
        prior, historical_checkpoint = checked_confirmation_handoff(
            manifest, args.prior_prescreen, args.prior_checkpoint,
            args.prior_v20_manifest, args.prior_v20_archive,
            args.prior_v21_manifest, args.prior_v21_archive, head)
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
    claim_bytes = (_confirmation_control_bytes(root)
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
                confirmation_authority_guard=confirmation_authority_guard,
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
                    retained_extra_bytes=_confirmation_control_bytes(root))
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
