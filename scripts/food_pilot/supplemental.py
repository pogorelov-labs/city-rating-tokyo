"""Explicitly gated, append-only supplemental HP development runner.

This module is inert unless invoked directly with a fresh owner activation and
root release. It never changes the original phase ledger or target-v4 tree.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .acquire_osm import encoded
from .bounded import AcquisitionStopped, NoRedirect, RequestRejected, safe_diagnostic
from .hotpepper import acquire_sites
from .run import ROOT

UTC_CUTOFF = datetime.fromisoformat('2026-10-22T00:00:00+00:00')
WALL_SECONDS = 1800
BODY_CAP = 1_048_576
CONTROL_RETENTION_RESERVE = 16_384
HP_BODY_LIMIT = 134_217_728
HP_ATTEMPT_LIMIT = 400
HP_PAGE_LIMIT = 320
HP_RETAINED_LIMIT = 134_217_728
GLOBAL_RETAINED_LIMIT = 2_147_483_648
BASE_ATTEMPTS = 2
BASE_BODY_BYTES = 214
BASE_ADMITTED_PAGES = 0
BASE_HELD_PAGES = 1
DIAGNOSTIC_SLOT_ID = 'historical:hp-diagnostic-reservation-v9'
EXCEPTIONAL_IDENTITY = 'hp:gun-hatake:1:c0f76ffdde068ca75e23685291e70029d28758efb37f14b4800709d6d88cb3c9'
EXPECTED_TARGET_TREE = '49df1e59182bfeb5a3c6eb25f6d53676a96b0cb93c312ff3ccf3d698c5c0af36'
EXPECTED_PRE_RECEIPT_TREE = '68c125c986f388e56b2a23be3f76867ad41bf0c52cc45469c250f49db112d012'
ORIGINAL_HP_LEDGER = '73385ba0be0f8e98f12a66e2bf0f7fa5711e77864598ce774c35294de59ef4df'
ORIGINAL_HP_RESULT = '0c4301b5d98b406b43a6688866c1671a5b6ad0dd13a61b801ecd9a343cde1267'
V10_MANIFEST_SHA256 = 'd753a5d8238b03ab2c0774150794acbdaf3f09bb4f905c487a1ea661b1630f7b'
DIAGNOSTIC_RESERVATION = '873ab477706f5c8560f32d02a8a6950a0e3d5521c9762a84201a1c02d06f8f3c'
DIAGNOSTIC_OUTCOME = '5ed715d376f64170ba91fc67840d8af66c95abd5d4fef470c0b0d88f217b0a9b'
EXPECTED_EVIDENCE = {
    'hp_ledger': ORIGINAL_HP_LEDGER,
    'hp_result': ORIGINAL_HP_RESULT,
    'diagnostic_reservation': DIAGNOSTIC_RESERVATION,
    'diagnostic_outcome': DIAGNOSTIC_OUTCOME,
}
PRE_RECEIPT_EXCLUSIONS = frozenset({
    'hp_development/diagnostic-authorization-provenance.json',
    'hp_development/hp-diagnostic-outcome-v1.json',
    'hp_development/hp-diagnostic-reservation-v1.json',
    'hp_development/owner-diagnostic-exception.json',
    'hp_development/root-diagnostic-gate.json',
})


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    if not isinstance(parsed, datetime) or parsed.tzinfo is None:
        raise AcquisitionStopped('supplemental_naive_timestamp')
    return parsed.astimezone(timezone.utc)


def _read_json(path):
    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise AcquisitionStopped('supplemental_receipt_unreadable') from None
    if not isinstance(value, dict):
        raise AcquisitionStopped('supplemental_receipt_shape')
    return value, raw


def tree_digest(root, *, excluded=()):
    root = Path(root)
    excluded = set(excluded)
    rows = []
    total_bytes = 0
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise AcquisitionStopped('supplemental_tree_symlink_rejected')
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        raw = path.read_bytes()
        rows.append(relative.encode() + b'\0' + sha256(raw).encode() + b'\0' + str(len(raw)).encode() + b'\n')
        total_bytes += len(raw)
    return sha256(b''.join(rows)), total_bytes, len(rows)


def file_size(root):
    total = 0
    for path in Path(root).rglob('*'):
        if path.is_symlink():
            raise AcquisitionStopped('supplemental_retained_symlink_rejected')
        if path.is_file():
            total += path.stat().st_size
    return total


def code_map_digest(code_map):
    return sha256(encoded(code_map))


def git_head(root=ROOT):
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        raise AcquisitionStopped('supplemental_git_identity_unavailable') from None


def check_manifest(path, *, expected_parent=None):
    manifest, raw = _read_json(path)
    if manifest.get('state') != 'frozen' or not isinstance(manifest.get('code_sha256'), dict):
        raise AcquisitionStopped('supplemental_manifest_not_frozen')
    code_map = manifest['code_sha256']
    runtime_files = {str(p.relative_to(ROOT)) for p in (ROOT / 'scripts' / 'food_pilot').glob('*.py')}
    if set(code_map) != runtime_files:
        raise AcquisitionStopped('supplemental_code_map_incomplete')
    for relative, expected in code_map.items():
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT / 'scripts' / 'food_pilot') or sha256(source.read_bytes()) != expected:
            raise AcquisitionStopped('supplemental_code_hash_mismatch')
    contract = manifest.get('supplemental_hp_development')
    if not isinstance(contract, dict):
        raise AcquisitionStopped('supplemental_contract_missing')
    if contract.get('v10_manifest_sha256') != (expected_parent or V10_MANIFEST_SHA256):
        raise AcquisitionStopped('supplemental_parent_manifest_mismatch')
    if contract.get('target_v4_tree_sha256') != EXPECTED_TARGET_TREE or contract.get('pre_receipt_tree_sha256') != EXPECTED_PRE_RECEIPT_TREE:
        raise AcquisitionStopped('supplemental_evidence_tree_contract')
    if contract.get('original_evidence_sha256') != EXPECTED_EVIDENCE:
        raise AcquisitionStopped('supplemental_evidence_contract')
    if contract.get('wall_seconds') != WALL_SECONDS or contract.get('source_cutoff') != UTC_CUTOFF.isoformat().replace('+00:00', 'Z'):
        raise AcquisitionStopped('supplemental_window_contract')
    if contract.get('extra_identity') != EXCEPTIONAL_IDENTITY or contract.get('extra_lifetime_attempt') != 3:
        raise AcquisitionStopped('supplemental_attempt_contract')
    expected_snapshot = {
        'attempts_used': 2, 'attempt_limit': HP_ATTEMPT_LIMIT,
        'body_bytes_used': BASE_BODY_BYTES, 'body_byte_limit': HP_BODY_LIMIT,
        'admitted_pages': BASE_ADMITTED_PAGES, 'held_page_slots': BASE_HELD_PAGES,
        'page_slot_limit': HP_PAGE_LIMIT, 'hp_retained_bytes': 14_579,
        'hp_retained_limit': HP_RETAINED_LIMIT, 'global_retained_bytes': 41_468_376,
        'global_retained_limit': GLOBAL_RETAINED_LIMIT,
    }
    if contract.get('budget_snapshot') != expected_snapshot:
        raise AcquisitionStopped('supplemental_budget_snapshot_contract')
    if contract.get('development_order') != [row.get('slug') for row in manifest.get('core', {}).get('stations', [])
                                              if row.get('split') == 'development']:
        raise AcquisitionStopped('supplemental_development_order_contract')
    limits = manifest.get('budgets', {}).get('hp_development', {})
    expected_limits = {'attempts': HP_ATTEMPT_LIMIT, 'maximum_attempts_per_page': 2,
                       'response_body_bytes': HP_BODY_LIMIT, 'response_bytes': BODY_CAP,
                       'retained_bytes': HP_RETAINED_LIMIT, 'successful_pages': HP_PAGE_LIMIT,
                       'pages_per_station': 50, 'socket_seconds': 20,
                       'minimum_request_interval_seconds': 0.6, 'concurrency': 1}
    if any(limits.get(key) != value for key, value in expected_limits.items()):
        raise AcquisitionStopped('supplemental_inherited_budget_contract')
    for path_field, hash_field in (('protocol_path', 'protocol_sha256'), ('decision_path', 'decision_sha256')):
        relative = contract.get(path_field)
        if not isinstance(relative, str):
            raise AcquisitionStopped('supplemental_source_document_missing')
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT) or not source.is_file() or sha256(source.read_bytes()) != contract.get(hash_field):
            raise AcquisitionStopped('supplemental_source_document_hash_mismatch')
    return manifest, sha256(raw), code_map_digest(code_map)


def _receipt_bindings(manifest, manifest_hash, map_hash, head, owner, root_gate,
                      target_root, supplemental_root):
    contract = manifest['supplemental_hp_development']
    expected = {
        'manifest_sha256': manifest_hash,
        'git_head': head,
        'code_map_sha256': map_hash,
        'protocol_sha256': contract['protocol_sha256'],
        'decision_sha256': contract['decision_sha256'],
        'evidence_sha256': contract['original_evidence_sha256'],
        'sample_sha256': contract['development_sample_sha256'],
        'query_fingerprint_sha256': contract['query_fingerprint_sha256'],
        'target_root': str(Path(target_root).resolve()),
        'supplemental_root': str(Path(supplemental_root).resolve()),
        'budget_snapshot': contract['budget_snapshot'],
        'allowed_operation': 'supplemental_hp_development',
        'accounted_roots': [str(Path(target_root).resolve()), str(Path(supplemental_root).resolve())],
    }
    for record in (owner, root_gate):
        if any(record.get(key) != value for key, value in expected.items()):
            raise AcquisitionStopped('supplemental_activation_binding_mismatch')
        if record.get('single_use') is not True:
            raise AcquisitionStopped('supplemental_activation_not_single_use')
    if owner.get('kind') != 'owner_supplemental_hp_activation' or not owner.get('activation_id') or not owner.get('run_id'):
        raise AcquisitionStopped('supplemental_owner_activation_invalid')
    if root_gate.get('kind') != 'root_supplemental_hp_release' or root_gate.get('owner_activation_sha256') is None:
        raise AcquisitionStopped('supplemental_root_release_invalid')
    if root_gate.get('root_manifest_check') is not True or root_gate.get('native_review_approved_head') != head:
        raise AcquisitionStopped('supplemental_root_review_gate_invalid')
    if owner.get('activation_id') != root_gate.get('activation_id') or owner.get('run_id') != root_gate.get('run_id'):
        raise AcquisitionStopped('supplemental_activation_identity_mismatch')
    return owner['activation_id'], owner['run_id']


def request_identity(station, start):
    params = {'lat': station['lat'], 'lng': station['lng'], 'range': 3,
              'count': 100, 'start': start, 'format': 'json', 'order': 1}
    query_hash = sha256(json.dumps(params, sort_keys=True).encode())
    return f"hp:{station['slug']}:{start}:{query_hash}"


def development_fingerprints(manifest):
    stations = [row for row in manifest['core']['stations'] if row.get('split') == 'development']
    sample = sha256(encoded(stations))
    queries = [{'slug': row['slug'], 'page1_identity': request_identity(row, 1)} for row in stations]
    return sample, sha256(encoded(queries)), stations


def _append_fsynced(path, raw, *, create=False):
    flags = os.O_WRONLY | os.O_APPEND
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, 'ab', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    directory = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class Journal:
    def __init__(self, directory, *, resume, now, monotonic, start_utc=None, start_mono=None):
        self.directory = Path(directory)
        if self.directory.is_symlink():
            raise AcquisitionStopped('supplemental_root_symlink_rejected')
        if self.directory.exists() and not resume:
            raise AcquisitionStopped('supplemental_root_already_exists')
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.directory.is_dir():
            raise AcquisitionStopped('supplemental_root_path_invalid')
        self.path = self.directory / 'journal.jsonl'
        self.now = now
        self.monotonic = monotonic
        self.events = []
        self.last_sha = '0' * 64
        self.last_utc = None
        self.last_mono = None
        self.started_mono = None
        self.started_utc = None
        self.lock_check = None
        self.retention_guard = None
        if self.path.exists():
            if not resume:
                raise AcquisitionStopped('supplemental_root_already_consumed')
            self._load()
        else:
            if resume:
                raise AcquisitionStopped('supplemental_journal_missing')
            self.started_utc = _utc(start_utc if start_utc is not None else now())
            self.started_mono = start_mono if start_mono is not None else monotonic()
            self._check_clock(self.started_utc, self.started_mono)
            self.append('run_started', {'t0_utc': self.started_utc.isoformat(),
                                        'monotonic_anchor': self.started_mono})

    def _check_clock(self, current_utc, current_mono):
        if current_utc >= UTC_CUTOFF:
            raise AcquisitionStopped('supplemental_source_cutoff')
        if self.started_utc is not None and current_utc >= self.deadline:
            raise AcquisitionStopped('supplemental_wall_deadline')
        if self.last_utc is not None and current_utc < self.last_utc:
            raise AcquisitionStopped('supplemental_utc_clock_went_backwards')
        if self.last_mono is not None and current_mono < self.last_mono:
            raise AcquisitionStopped('supplemental_monotonic_clock_reset')
        if self.started_mono is not None and current_mono < self.started_mono:
            raise AcquisitionStopped('supplemental_monotonic_clock_reset')
        if self.started_mono is not None and current_mono >= self.started_mono + WALL_SECONDS:
            raise AcquisitionStopped('supplemental_wall_deadline')

    def _load(self):
        self.events = []
        self.last_sha = '0' * 64
        self.last_utc = None
        self.last_mono = None
        previous = '0' * 64
        try:
            raw = self.path.read_bytes()
        except OSError:
            raise AcquisitionStopped('supplemental_journal_unreadable') from None
        if raw and not raw.endswith(b'\n'):
            raise AcquisitionStopped('supplemental_journal_truncated')
        lines = raw.splitlines()
        for index, line in enumerate(lines):
            try:
                row = json.loads(line)
                digest = row.pop('event_sha256')
                if row.get('seq') != index or row.get('previous_sha256') != previous or sha256(canonical(row)) != digest:
                    raise ValueError()
                previous = digest
                self.events.append({**row, 'event_sha256': digest})
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                raise AcquisitionStopped('supplemental_journal_chain_invalid') from None
        if not self.events or self.events[0].get('event') != 'run_started':
            raise AcquisitionStopped('supplemental_journal_start_missing')
        first = self.events[0]
        self.started_utc = _utc(first['t0_utc'])
        self.started_mono = first['monotonic_anchor']
        self.last_sha = previous
        self.last_utc = _utc(self.events[-1]['utc'])
        self.last_mono = self.events[-1]['monotonic']
        self._check_clock(_utc(self.now()), self.monotonic())

    def reload_under_lock(self):
        if self.lock_check is None:
            raise AcquisitionStopped('supplemental_lock_required_for_reload')
        self.lock_check()
        self._load()
        self.lock_check()
        if any(event['event'] == 'run_finalized' for event in self.events):
            raise AcquisitionStopped('supplemental_run_already_finalized')
        if any(event['event'] == 'launch_terminal' for event in self.events):
            raise AcquisitionStopped('supplemental_launch_terminal')

    def append(self, name, fields=None):
        self._append_event(name, fields, allow_late=False)
        if name == 'run_finalized':
            try:
                self._check_clock(_utc(self.now()), self.monotonic())
            except AcquisitionStopped as exc:
                if str(exc) not in ('supplemental_wall_deadline', 'supplemental_source_cutoff'):
                    raise
                self._append_event('run_late_failure', {
                    'status': 'incomplete', 'reason': 'finalization_not_durable_by_deadline',
                }, allow_late=True)
                raise AcquisitionStopped('supplemental_finalization_after_deadline') from None

    def _append_event(self, name, fields=None, *, allow_late):
        current_utc = _utc(self.now())
        current_mono = self.monotonic()
        if allow_late:
            if current_utc < self.last_utc or (self.last_mono is not None and current_mono < self.last_mono):
                raise AcquisitionStopped('supplemental_clock_went_backwards')
        else:
            self._check_clock(current_utc, current_mono)
        if self.lock_check is not None:
            self.lock_check()
        row = {'seq': len(self.events), 'previous_sha256': self.last_sha,
               'event': name, 'utc': current_utc.isoformat(), 'monotonic': current_mono}
        if fields:
            row.update(fields)
        digest = sha256(canonical(row))
        line = canonical({**row, 'event_sha256': digest}) + b'\n'
        if self.retention_guard is not None:
            self.retention_guard(len(line))
        if not self.events:
            _append_fsynced(self.path, line, create=True)
        else:
            _append_fsynced(self.path, line)
        self.events.append({**row, 'event_sha256': digest})
        self.last_sha = digest
        self.last_utc = current_utc
        self.last_mono = current_mono

    @property
    def deadline(self):
        return min(self.started_utc + timedelta(seconds=WALL_SECONDS), UTC_CUTOFF)

    def remaining(self):
        current_utc = _utc(self.now())
        current_mono = self.monotonic()
        self._check_clock(current_utc, current_mono)
        if self.lock_check is not None:
            self.lock_check()
        return min((self.deadline - current_utc).total_seconds(),
                   self.started_mono + WALL_SECONDS - current_mono)

    def unresolved_attempts(self):
        reserved = {}
        for event in self.events:
            if event['event'] == 'attempt_reserved':
                reserved[event['attempt_id']] = 'pending'
            elif event['event'] == 'response_complete':
                reserved[event['attempt_id']] = 'complete_response'
            elif event['event'] in ('attempt_settled', 'attempt_unknown'):
                reserved[event['attempt_id']] = event['status']
        return [key for key, status in reserved.items() if status in ('pending', 'unknown')]


class ExclusiveAccountingLock:
    """Use the existing HP development lock to serialize both accounting roots."""
    def __init__(self, target_root, journal):
        self.path = Path(target_root) / 'hp_development' / '.reader.lock'
        self.journal = journal
        self.stream = None

    def __enter__(self):
        if not self.path.is_file() or self.path.is_symlink():
            # The activation was already durably consumed in the new run's
            # journal. A missing/unsafe serialization primitive is a known
            # failed launch, so leave a terminal marker; never let a later
            # `--resume` turn it into a valid launch after the environment is
            # changed.
            if self.journal.events:
                try:
                    self.journal.append('launch_terminal', {'error_type': 'AccountingLockUnavailable'})
                except AcquisitionStopped:
                    pass
            raise AcquisitionStopped('supplemental_shared_lock_missing')
        self.stream = self.path.open('rb')
        try:
            while True:
                self.journal.remaining()  # lock wait consumes the original window
                try:
                    fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return self
                except BlockingIOError:
                    time.sleep(min(0.05, self.journal.remaining()))
        except BaseException:
            self.stream.close()
            self.stream = None
            raise

    def assert_held(self):
        if self.stream is None or self.stream.closed:
            raise AcquisitionStopped('supplemental_lock_lost')
        try:
            check = self.path.open('rb')
        except OSError:
            raise AcquisitionStopped('supplemental_lock_unavailable') from None
        try:
            try:
                fcntl.flock(check, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            fcntl.flock(check, fcntl.LOCK_UN)
            raise AcquisitionStopped('supplemental_lock_lost')
        finally:
            check.close()

    def __exit__(self, *_):
        if self.stream:
            fcntl.flock(self.stream, fcntl.LOCK_UN)
            self.stream.close()


class SupplementalBudget:
    """HP fetch adapter with cumulative reservations and immutable cache receipts."""
    def __init__(self, directory, target_root, limits, journal, *, opener=None,
                 sleeper=time.sleep, monotonic=time.monotonic, original_ledger=None,
                 diagnostic_identity=None, lock=None):
        self.directory = Path(directory)
        self.target_root = Path(target_root)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.limits = limits
        self.journal = journal
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open
        self.sleeper = sleeper
        self.monotonic = monotonic
        self.lock = lock
        self.journal.retention_guard = lambda added: self._check_storage(
            added + getattr(self.journal, 'retention_reservation', 0))
        self.journal.retention_reservation = 0
        self.original_ledger = original_ledger or {}
        self.exceptional_identity = diagnostic_identity or EXCEPTIONAL_IDENTITY
        self.historical = list(self.original_ledger.get('attempts', []))
        self.historical.append({'identity': self.exceptional_identity, 'status': 'diagnostic_only'})
        self._historical_cache = {}
        self._historical_cache_origin = set()
        prior_requests = [event['monotonic'] for event in journal.events if event['event'] == 'attempt_reserved']
        self.last_request = prior_requests[-1] if prior_requests else None
        self._assert_no_unknown_replay()

    def _assert_no_unknown_replay(self):
        if self.journal.unresolved_attempts():
            raise AcquisitionStopped('supplemental_unknown_attempt_blocks_resume')

    def _attempts(self, identity):
        historical = sum(1 for attempt in self.historical if attempt.get('identity') == identity)
        current = sum(1 for event in self.journal.events
                      if event.get('event') == 'attempt_reserved' and event.get('identity') == identity)
        return historical + current

    def attempts_used(self):
        return BASE_ATTEMPTS + sum(1 for event in self.journal.events if event.get('event') == 'attempt_reserved')

    def body_used(self):
        total = BASE_BODY_BYTES
        states = {}
        for event in self.journal.events:
            if event['event'] == 'attempt_reserved':
                states[event['attempt_id']] = BODY_CAP
            elif event['event'] == 'response_complete':
                states[event['attempt_id']] = event['observed_body_bytes']
            elif event['event'] == 'attempt_settled':
                states[event['attempt_id']] = event['charged_body_bytes']
            elif event['event'] == 'attempt_unknown':
                states[event['attempt_id']] = BODY_CAP
        return total + sum(states.values())

    def page_occupancy(self):
        # The rejected diagnostic slot is immutable and distinct from the
        # supplemental page that may later use the same request identity.
        slots = {DIAGNOSTIC_SLOT_ID: 'held'}
        for event in self.journal.events:
            if event['event'] == 'page_slot_reserved':
                slots.setdefault(event['slot_id'], 'reserved')
            elif event['event'] == 'page_slot_admitted':
                slots[event['slot_id']] = 'admitted'
            elif event['event'] == 'page_slot_released':
                if event['slot_id'] != DIAGNOSTIC_SLOT_ID:
                    slots.pop(event['slot_id'], None)
        return sum(status in ('held', 'reserved', 'admitted') for status in slots.values())

    def retained(self):
        return file_size(self.target_root) + file_size(self.directory)

    def _check_storage(self, reservation=0):
        hp_used = file_size(self.target_root / 'hp_development') + file_size(self.directory)
        total_used = self.retained()
        if hp_used + reservation + CONTROL_RETENTION_RESERVE > HP_RETAINED_LIMIT:
            raise AcquisitionStopped('supplemental_hp_retained_budget')
        if total_used + reservation + CONTROL_RETENTION_RESERVE > GLOBAL_RETAINED_LIMIT:
            raise AcquisitionStopped('supplemental_global_retained_budget')

    def check_completion(self):
        self.journal.remaining()
        self._assert_no_unknown_replay()
        # A durable projected cache plus EOF receipt is sufficient to settle a
        # crash between response persistence and the ordinary settlement event.
        settled = {e.get('attempt_id') for e in self.journal.events if e['event'] == 'attempt_settled'}
        for event in list(self.journal.events):
            if event['event'] == 'response_complete' and event['attempt_id'] not in settled:
                self.journal.append('attempt_settled', {
                    'attempt_id': event['attempt_id'], 'identity': event['identity'],
                    'status': 'complete', 'charged_body_bytes': event['observed_body_bytes'],
                    'retry_disposition': 'none', 'reconciled_complete_cache': True,
                })

    def _events_for(self, identity, name):
        return [event for event in self.journal.events
                if event.get('event') == name and event.get('identity') == identity]

    def _cache_for(self, identity):
        records = self._events_for(identity, 'response_complete')
        if len(records) > 1:
            raise AcquisitionStopped('supplemental_ambiguous_cache')
        if records:
            record = records[0]
            path = self.directory / record['cache']
            if not path.is_file() or path.is_symlink():
                raise AcquisitionStopped('supplemental_cache_missing')
            raw = path.read_bytes()
            if sha256(raw) != record['cache_sha256']:
                raise AcquisitionStopped('supplemental_cache_hash')
            return json.loads(raw)
        return None

    def _historical_complete(self, identity):
        records = [row for row in self.historical if row.get('identity') == identity and row.get('status') == 'complete']
        if len(records) > 1:
            raise AcquisitionStopped('supplemental_ambiguous_historical_cache')
        if not records:
            return None
        record = records[0]
        cache = record.get('cache')
        base = self.target_root / 'hp_development'
        candidate = base / cache if isinstance(cache, str) else base
        if candidate.is_symlink():
            raise AcquisitionStopped('supplemental_historical_cache_path')
        path = candidate.resolve()
        if not path.is_relative_to(base.resolve()) or not path.is_file():
            raise AcquisitionStopped('supplemental_historical_cache_path')
        raw = path.read_bytes()
        if sha256(raw) != record.get('cache_sha256'):
            raise AcquisitionStopped('supplemental_historical_cache_hash')
        self._historical_cache_origin.add(identity)
        self._historical_cache[identity] = json.loads(raw)
        return self._historical_cache[identity]

    def _slot_reserve(self, identity):
        slot_id = 'supplemental:' + identity
        matching = [event for event in self.journal.events if event.get('slot_id') == slot_id and
                    event['event'] in ('page_slot_reserved', 'page_slot_admitted', 'page_slot_released')]
        if matching and matching[-1]['event'] in ('page_slot_reserved', 'page_slot_admitted'):
            return
        if self.page_occupancy() >= HP_PAGE_LIMIT:
            raise AcquisitionStopped('supplemental_page_slot_budget')
        self.journal.append('page_slot_reserved', {'identity': identity, 'slot_id': slot_id,
                                                   'slot_state': 'reserved'})

    def admit_page(self, identity):
        if identity in self._historical_cache_origin:
            return
        slot_id = 'supplemental:' + identity
        states = [event for event in self.journal.events if event.get('slot_id') == slot_id
                  and event['event'] in ('page_slot_reserved', 'page_slot_admitted', 'page_slot_released')]
        if states and states[-1]['event'] == 'page_slot_admitted':
            return
        if not states or states[-1]['event'] != 'page_slot_reserved':
            raise AcquisitionStopped('supplemental_page_slot_not_reserved')
        self.journal.append('page_slot_admitted', {'identity': identity, 'slot_id': slot_id,
                                                   'slot_state': 'admitted'})

    def reject_page(self, identity):
        if identity in self._historical_cache_origin:
            return
        if self._events_for(identity, 'page_slot_reserved'):
            latest = [e for e in self.journal.events if e.get('slot_id') == 'supplemental:' + identity and
                      e['event'] in ('page_slot_reserved', 'page_slot_admitted', 'page_slot_released')][-1]
            if latest['event'] == 'page_slot_reserved' and not self.journal.unresolved_attempts():
                self.journal.append('page_slot_released', {'identity': identity,
                                                           'slot_id': 'supplemental:' + identity,
                                                           'slot_state': 'released'})

    def fetch(self, identity, request, project, *, response_bytes=None, kind='range'):
        self.journal.remaining()
        if self.lock is not None:
            self.lock.assert_held()
        if kind != 'page':
            raise AcquisitionStopped('supplemental_hp_only_page_requests')
        if self.journal.unresolved_attempts():
            raise AcquisitionStopped('supplemental_unknown_attempt_blocks_resume')
        cached = self._cache_for(identity)
        if cached is not None:
            return cached
        cached = self._historical_complete(identity)
        if cached is not None:
            return cached
        historical = [attempt for attempt in self.historical if attempt.get('identity') == identity]
        prior = [event for event in self.journal.events if event.get('event') == 'attempt_reserved' and event.get('identity') == identity]
        terminal = [event for event in self.journal.events if event.get('event') == 'attempt_settled' and
                    event.get('identity') == identity and event.get('retry_disposition') == 'terminal']
        if terminal:
            raise RequestRejected(terminal[-1].get('error_type', 'TerminalRequestHistory'))
        maximum = 3 if identity == self.exceptional_identity else 2
        used = len(historical) + len(prior)
        if used >= maximum:
            raise RequestRejected('LifetimeAttemptBudget')
        is_exception = identity == self.exceptional_identity
        if identity.startswith('hp:gun-hatake:1:') and not is_exception:
            raise AcquisitionStopped('supplemental_exception_request_identity_mismatch')
        if is_exception and used != 2:
            raise AcquisitionStopped('supplemental_exception_identity_history_mismatch')
        if not is_exception and any(row.get('retry_disposition') not in ('transient', 'retryable')
                                    for row in historical if row.get('identity') == identity and row.get('status') != 'complete'):
            raise RequestRejected('TerminalRequestHistory')
        transient_failures = [event for event in self.journal.events
                              if event.get('event') == 'attempt_settled'
                              and event.get('identity') == identity
                              and event.get('status') == 'failed'
                              and event.get('retry_disposition') in ('transient', 'retryable')]
        if transient_failures and not is_exception:
            # Reapply the ordinary two-second retry delay after a process
            # interruption. Its settlement timestamp is durable and uses the
            # same monotonic clock as this run; the exceptional identity never
            # reaches this retry path.
            settled_at = transient_failures[-1].get('monotonic')
            if type(settled_at) not in (int, float):
                raise AcquisitionStopped('supplemental_retry_clock_missing')
            delay = max(0.0, 2.0 - (self.monotonic() - settled_at))
            if delay:
                self.sleeper(min(delay, self.journal.remaining()))
            self.journal.remaining()
        if self.attempts_used() >= HP_ATTEMPT_LIMIT:
            raise AcquisitionStopped('supplemental_attempt_budget')
        if self.body_used() + BODY_CAP > HP_BODY_LIMIT:
            raise AcquisitionStopped('supplemental_response_byte_budget')
        self._check_storage(BODY_CAP)
        if self.last_request is not None:
            delay = max(0.0, 0.6 - (self.monotonic() - self.last_request))
            if delay:
                self.sleeper(min(delay, self.journal.remaining()))
        self._slot_reserve(identity)
        self.journal.retention_reservation = BODY_CAP
        attempt_id = f"supp-{len([e for e in self.journal.events if e['event']=='attempt_reserved'])+1:04d}"
        self.journal.append('attempt_reserved', {
            'attempt_id': attempt_id, 'identity': identity, 'reserved_body_bytes': BODY_CAP,
            'page_slot_identity': identity, 'retry_disposition': 'none' if is_exception else 'pending',
        })
        self.last_request = self.monotonic()
        received = 0
        eof = False
        try:
            if self.lock is not None:
                self.lock.assert_held()
            timeout = min(20.0, self.journal.remaining())
            with self.opener(request, timeout=timeout) as response:
                chunks = []
                while True:
                    self.journal.remaining()
                    if received == BODY_CAP:
                        # The reservation is a hard read ceiling. Once it is
                        # consumed, EOF cannot be proven without reading an
                        # uncharged byte, so keep the full reservation unknown.
                        raise AcquisitionStopped('supplemental_response_at_cap_eof_unproven')
                    chunk = response.read(min(65536, BODY_CAP - received))
                    if not chunk:
                        eof = True
                        break
                    received += len(chunk)
                    if received > BODY_CAP:
                        raise AcquisitionStopped('supplemental_response_at_cap')
                    chunks.append(chunk)
                raw = b''.join(chunks)
                projected = project(raw, response)
                self.journal.remaining()
            cached_bytes = encoded(projected)
            self._check_storage(len(cached_bytes))
            cache_name = f'response-{attempt_id}.json'
            cache_path = self.directory / cache_name
            with cache_path.open('xb') as stream:
                stream.write(cached_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            self.journal.remaining()
            self.journal.append('response_complete', {
                'attempt_id': attempt_id, 'identity': identity, 'cache': cache_name,
                'cache_sha256': sha256(cached_bytes), 'response_sha256': sha256(raw),
                'observed_body_bytes': received, 'eof': True,
            })
            self.journal.append('attempt_settled', {
                'attempt_id': attempt_id, 'identity': identity, 'status': 'complete',
                'charged_body_bytes': received, 'retry_disposition': 'none',
            })
            self.journal.retention_reservation = 0
            return projected
        except urllib.error.HTTPError as exc:
            status = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else None
            disposition = 'transient' if status is not None and 500 <= status <= 599 and not is_exception else 'terminal'
            self.journal.append('attempt_settled', {
                'attempt_id': attempt_id, 'identity': identity, 'status': 'failed',
                'charged_body_bytes': BODY_CAP, 'retry_disposition': disposition,
                'error_type': 'HTTPError', 'http_status': status,
            })
            self.journal.retention_reservation = 0
            if disposition == 'transient' and used + 1 < maximum:
                return self.fetch(identity, request, project, response_bytes=response_bytes, kind=kind)
            raise RequestRejected('HTTPError', safe_diagnostic({'http_status': status, 'parser_reason': 'http_error'})) from None
        except (urllib.error.URLError, TimeoutError) as exc:
            disposition = 'terminal' if is_exception else 'transient'
            status = 'unknown' if is_exception else 'failed'
            if status == 'unknown':
                self.journal.append('attempt_unknown', {
                    'attempt_id': attempt_id, 'identity': identity, 'status': status,
                    'charged_body_bytes': BODY_CAP, 'error_type': type(exc).__name__,
                })
                self.journal.retention_reservation = 0
                raise AcquisitionStopped('supplemental_exception_attempt_unknown') from None
            self.journal.append('attempt_settled', {
                'attempt_id': attempt_id, 'identity': identity, 'status': status,
                'charged_body_bytes': BODY_CAP, 'retry_disposition': disposition,
                'error_type': type(exc).__name__,
            })
            self.journal.retention_reservation = 0
            if used + 1 < maximum:
                return self.fetch(identity, request, project, response_bytes=response_bytes, kind=kind)
            raise RequestRejected(type(exc).__name__) from None
        except BaseException as exc:
            # A response that reached complete EOF has a known body charge even
            # if projection rejected it. Otherwise retain the full reservation.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)) or not eof:
                self.journal.append('attempt_unknown', {
                    'attempt_id': attempt_id, 'identity': identity, 'status': 'unknown',
                    'charged_body_bytes': BODY_CAP, 'error_type': type(exc).__name__,
                })
                self.journal.retention_reservation = 0
            else:
                safe = safe_diagnostic(getattr(exc, 'safe_diagnostic', None))
                disposition = 'terminal'
                self.journal.append('attempt_settled', {
                    'attempt_id': attempt_id, 'identity': identity, 'status': 'failed',
                    'charged_body_bytes': received, 'retry_disposition': disposition,
                    'error_type': type(exc).__name__, 'diagnostic': safe,
                })
                self.journal.retention_reservation = 0
            raise


def _validate_roots(target_root, supplemental_root):
    try:
        target_path = Path(target_root)
        output_path = Path(supplemental_root)
        if target_path.is_symlink() or output_path.is_symlink():
            raise AcquisitionStopped('supplemental_root_path_invalid')
        target = target_path.resolve(strict=True)
        output = output_path.resolve()
    except AcquisitionStopped:
        raise
    except (OSError, RuntimeError, TypeError, ValueError):
        # Normalize caller-supplied path failures so a valid activation can
        # still be consumed at its receipt-bound destination before rejection.
        raise AcquisitionStopped('supplemental_root_path_invalid') from None
    if not target.is_dir():
        raise AcquisitionStopped('supplemental_root_path_invalid')
    if output.parent != target.parent or output.name == target.name:
        raise AcquisitionStopped('supplemental_root_not_sibling')
    if target.is_relative_to(ROOT) or output.is_relative_to(ROOT):
        raise AcquisitionStopped('supplemental_data_must_stay_outside_repository')
    return target, output


def _activation_context(*, manifest_path, owner_activation_path, root_release_path,
                        invocation_utc, head_provider):
    """Resolve and validate the authoritative output destination from exact receipt bindings."""
    manifest, manifest_hash, map_hash = check_manifest(manifest_path)
    owner, owner_raw = _read_json(owner_activation_path)
    root_gate, root_raw = _read_json(root_release_path)
    contract = manifest['supplemental_hp_development']
    head = head_provider()
    target, output = _validate_roots(owner.get('target_root'), owner.get('supplemental_root'))
    activation_id, run_id = _receipt_bindings(
        manifest, manifest_hash, map_hash, head, owner, root_gate, target, output)
    if root_gate.get('owner_activation_sha256') != sha256(owner_raw):
        raise AcquisitionStopped('supplemental_root_owner_receipt_hash')
    if owner.get('created_at') is None or root_gate.get('released_at') is None:
        raise AcquisitionStopped('supplemental_activation_receipt_time_missing')
    if _utc(owner['created_at']) > invocation_utc or _utc(root_gate['released_at']) > invocation_utc:
        raise AcquisitionStopped('supplemental_activation_not_preexisting')
    if (_utc(owner.get('activation_expires_at', '')) <= invocation_utc or
            _utc(root_gate.get('release_expires_at', '')) <= invocation_utc):
        raise AcquisitionStopped('supplemental_activation_expired')
    return {'manifest': manifest, 'manifest_hash': manifest_hash, 'map_hash': map_hash,
            'contract': contract, 'head': head, 'owner': owner, 'owner_raw': owner_raw,
            'root_gate': root_gate, 'root_raw': root_raw, 'target': target, 'output': output,
            'activation_id': activation_id, 'run_id': run_id}


def _matches_bound_path(supplied, bound):
    try:
        path = Path(supplied)
        return not path.is_symlink() and path.resolve() == bound
    except (OSError, RuntimeError, TypeError, ValueError):
        return False


def _claim_activation(context, *, invocation_utc, invocation_mono, now, monotonic,
                      terminal_reason=None):
    """Durably claim T0 at the receipt-bound root before any lock wait."""
    target, output = context['target'], context['output']

    def retention_guard(added):
        if (file_size(target / 'hp_development') + file_size(output) + added +
                CONTROL_RETENTION_RESERVE > HP_RETAINED_LIMIT):
            raise AcquisitionStopped('supplemental_hp_retained_budget')
        if (file_size(target) + file_size(output) + added +
                CONTROL_RETENTION_RESERVE > GLOBAL_RETAINED_LIMIT):
            raise AcquisitionStopped('supplemental_global_retained_budget')

    retention_guard(0)
    journal = Journal(output, resume=False, now=now, monotonic=monotonic,
                      start_utc=invocation_utc, start_mono=invocation_mono)
    journal.retention_guard = retention_guard
    owner_sha, root_sha = sha256(context['owner_raw']), sha256(context['root_raw'])
    journal.append('activation_preflight_started', {
        'owner_activation_sha256': owner_sha, 'root_release_sha256': root_sha})
    journal.append('activation_consumed', {
        'activation_id': context['activation_id'], 'run_id': context['run_id'],
        'owner_activation_sha256': owner_sha, 'root_release_sha256': root_sha})
    if terminal_reason is not None:
        journal.append('launch_terminal', {'error_type': 'UnsafeOutputRoot',
                                           'reason': terminal_reason})
    return journal


def _verify_evidence(target_root, contract):
    digest, total_size, count = tree_digest(target_root)
    if digest != EXPECTED_TARGET_TREE or count != 49 or total_size != 41_468_376:
        raise AcquisitionStopped('supplemental_target_v4_changed')
    subset, subset_size, subset_count = tree_digest(target_root, excluded=PRE_RECEIPT_EXCLUSIONS)
    if subset != EXPECTED_PRE_RECEIPT_TREE or subset_count != 44 or subset_size != 41_459_467:
        raise AcquisitionStopped('supplemental_pre_receipt_tree_changed')
    if file_size(Path(target_root) / 'hp_development') != 14_579:
        raise AcquisitionStopped('supplemental_hp_retention_baseline_changed')
    paths = contract.get('original_evidence_paths', {})
    hashes = contract['original_evidence_sha256']
    if set(paths) != set(hashes):
        raise AcquisitionStopped('supplemental_evidence_paths_incomplete')
    raw_evidence = {}
    for key, relative in paths.items():
        candidate = Path(target_root) / relative
        if candidate.is_symlink():
            raise AcquisitionStopped('supplemental_evidence_path_invalid')
        path = candidate.resolve()
        if not path.is_relative_to(Path(target_root).resolve()) or not path.is_file():
            raise AcquisitionStopped('supplemental_evidence_path_invalid')
        raw = path.read_bytes()
        if sha256(raw) != hashes[key]:
            raise AcquisitionStopped('supplemental_evidence_hash_mismatch')
        raw_evidence[key] = json.loads(raw)
    ledger = raw_evidence['hp_ledger']
    attempts = ledger.get('attempts')
    if (ledger.get('status') != 'incomplete' or ledger.get('successful_pages') != 0 or
            ledger.get('charged_bytes') != 107 or not isinstance(attempts, list) or len(attempts) != 1 or
            attempts[0].get('identity') != EXCEPTIONAL_IDENTITY):
        raise AcquisitionStopped('supplemental_original_ledger_state_mismatch')
    return ledger


def execute(*, manifest_path, owner_activation_path, root_release_path, target_root,
            supplemental_root, resume=False, now=lambda: datetime.now(timezone.utc), monotonic=time.monotonic,
            opener=None, sleeper=time.sleep, head_provider=git_head, api_key=None):
    """Run the supplemental phase only after exact reviewed receipts exist."""
    # T0 precedes path validation, journal/receipt parsing and lock wait.
    invocation_utc = _utc(now())
    invocation_mono = monotonic()
    if resume:
        # A terminal existing journal can be rejected without depending on
        # later receipt availability. Nonterminal resumes still rebind to the
        # authoritative receipt path before any lock wait or request work.
        target, output = _validate_roots(target_root, supplemental_root)
        journal = Journal(output, resume=True, now=now, monotonic=monotonic)
        if any(event['event'] == 'run_finalized' for event in journal.events):
            raise AcquisitionStopped('supplemental_run_already_finalized')
        if any(event['event'] == 'launch_terminal' for event in journal.events):
            raise AcquisitionStopped('supplemental_launch_terminal')
        context = _activation_context(
            manifest_path=manifest_path, owner_activation_path=owner_activation_path,
            root_release_path=root_release_path, invocation_utc=invocation_utc,
            head_provider=head_provider)
        if target != context['target'] or output != context['output']:
            raise AcquisitionStopped('supplemental_root_not_receipt_bound')
    else:
        # Establish the trusted receipt-bound accounting destination before
        # inspecting caller-controlled paths. Invalid caller paths can then
        # consume a valid activation only at that authoritative destination.
        context = _activation_context(
            manifest_path=manifest_path, owner_activation_path=owner_activation_path,
            root_release_path=root_release_path, invocation_utc=invocation_utc,
            head_provider=head_provider)
        target, output = context['target'], context['output']
        supplied_root_error = None
        try:
            supplied_target, supplied_output = _validate_roots(target_root, supplemental_root)
        except AcquisitionStopped as exc:
            supplied_root_error = exc
            supplied_target = supplied_output = None
        roots_match = (supplied_root_error is None and supplied_target == target and
                       supplied_output == output and
                       _matches_bound_path(target_root, target) and
                       _matches_bound_path(supplemental_root, output))
        if not roots_match:
            reason = (str(supplied_root_error) if supplied_root_error is not None
                      else 'supplemental_root_not_receipt_bound')
            _claim_activation(context, invocation_utc=invocation_utc,
                              invocation_mono=invocation_mono, now=now,
                              monotonic=monotonic, terminal_reason=reason)
            raise AcquisitionStopped(reason)
        # Claim the exact activation/T0 before entering the interruptible lock
        # wait. Contenders cannot append budget events or dispatch until they
        # acquire the shared writer lock and reload this journal.
        journal = _claim_activation(context, invocation_utc=invocation_utc,
                                    invocation_mono=invocation_mono, now=now,
                                    monotonic=monotonic)
    with ExclusiveAccountingLock(target, journal) as accounting_lock:
        journal.lock_check = accounting_lock.assert_held
        # Every launcher, including the original fresh process, may have been
        # descheduled after publishing its claim while a resumer advanced the
        # journal. Never append or dispatch from a pre-lock snapshot.
        journal.reload_under_lock()
        journal.remaining()
        if any(event['event'] == 'run_finalized' for event in journal.events):
            raise AcquisitionStopped('supplemental_run_already_finalized')
        if any(event['event'] in ('launch_terminal', 'run_terminal') for event in journal.events):
            raise AcquisitionStopped('supplemental_launch_terminal')

        def check_initial_retention(added):
            if file_size(target / 'hp_development') + file_size(output) + added + CONTROL_RETENTION_RESERVE > HP_RETAINED_LIMIT:
                raise AcquisitionStopped('supplemental_hp_retained_budget')
            if file_size(target) + file_size(output) + added + CONTROL_RETENTION_RESERVE > GLOBAL_RETAINED_LIMIT:
                raise AcquisitionStopped('supplemental_global_retained_budget')
        try:
            check_initial_retention(0)
        except Exception as exc:
            journal.append('launch_terminal', {'error_type': type(exc).__name__})
            raise
        journal.retention_guard = check_initial_retention

        try:
            owner_raw = Path(owner_activation_path).read_bytes()
        except OSError:
            owner_raw = b''
        try:
            root_raw = Path(root_release_path).read_bytes()
        except OSError:
            root_raw = b''
        owner_sha, root_sha = sha256(owner_raw), sha256(root_raw)
        preflight = [event for event in journal.events if event['event'] == 'activation_preflight_started']
        consumed = [event for event in journal.events if event['event'] == 'activation_consumed']
        if (len(preflight) != 1 or preflight[0].get('owner_activation_sha256') != owner_sha or
              preflight[0].get('root_release_sha256') != root_sha or len(consumed) != 1 or
              consumed[0].get('owner_activation_sha256') != owner_sha or
              consumed[0].get('root_release_sha256') != root_sha):
            journal.append('launch_terminal', {'error_type': 'ActivationReceiptChanged'})
            raise AcquisitionStopped('supplemental_activation_preflight_receipts_changed')
        consumed = [event for event in journal.events if event['event'] == 'activation_consumed']

        try:
            manifest, manifest_hash, map_hash = check_manifest(manifest_path)
            contract = manifest['supplemental_hp_development']
            owner, owner_raw_checked = _read_json(owner_activation_path)
            root_gate, root_raw_checked = _read_json(root_release_path)
            if owner_raw_checked != owner_raw or root_raw_checked != root_raw:
                raise AcquisitionStopped('supplemental_activation_receipt_changed')
            head = head_provider()
            if contract.get('reviewed_git_head') != head:
                raise AcquisitionStopped('supplemental_manifest_git_head_mismatch')
            activation_id, run_id = _receipt_bindings(
                manifest, manifest_hash, map_hash, head, owner, root_gate, target, output)
            if root_gate.get('owner_activation_sha256') != owner_sha:
                raise AcquisitionStopped('supplemental_root_owner_receipt_hash')
            if consumed[0].get('activation_id') not in (None, activation_id) or consumed[0].get('run_id') not in (None, run_id):
                raise AcquisitionStopped('supplemental_activation_not_consumed')
            binding = {'activation_id': activation_id, 'run_id': run_id,
                       'manifest_sha256': manifest_hash, 'code_map_sha256': map_hash,
                       'git_head': head, 'owner_activation_sha256': owner_sha,
                       'root_release_sha256': root_sha}
            bound = [event for event in journal.events if event['event'] == 'activation_bound']
            if len(bound) > 1 or (bound and any(bound[0].get(k) != v for k, v in binding.items())):
                raise AcquisitionStopped('supplemental_activation_binding_changed')
            if not bound:
                journal.append('activation_bound', binding)
            if owner.get('protocol_sha256') != contract['protocol_sha256']:
                raise AcquisitionStopped('supplemental_protocol_binding_mismatch')
            if owner.get('activation_expires_at') is None or _utc(now()) >= _utc(owner['activation_expires_at']):
                raise AcquisitionStopped('supplemental_activation_expired')
            if owner.get('created_at') is None or _utc(owner['created_at']) > journal.started_utc:
                raise AcquisitionStopped('supplemental_activation_not_preexisting')
            if root_gate.get('released_at') is None or _utc(root_gate['released_at']) > journal.started_utc:
                raise AcquisitionStopped('supplemental_root_release_not_preexisting')
            if root_gate.get('release_expires_at') is None or _utc(now()) >= _utc(root_gate['release_expires_at']):
                raise AcquisitionStopped('supplemental_root_release_expired')
            original_ledger = _verify_evidence(target, contract)
            limits = manifest['budgets']['hp_development']
            if (limits.get('attempts') != HP_ATTEMPT_LIMIT or
                    limits.get('response_body_bytes') != HP_BODY_LIMIT or
                    limits.get('successful_pages') != HP_PAGE_LIMIT):
                raise AcquisitionStopped('supplemental_budget_contract_mismatch')
            if not api_key:
                raise AcquisitionStopped('scoped_hp_credential_unavailable')
            if journal.unresolved_attempts():
                raise AcquisitionStopped('supplemental_unknown_attempt_blocks_resume')
            if journal.remaining() <= 0:
                raise AcquisitionStopped('supplemental_wall_deadline')
            sample_hash, query_hash, stations = development_fingerprints(manifest)
            if (len(stations) != 32 or [row['slug'] for row in stations] != contract['development_order'] or
                    sample_hash != contract['development_sample_sha256'] or
                    query_hash != contract['query_fingerprint_sha256']):
                raise AcquisitionStopped('supplemental_development_sample_mismatch')
            exceptional_site = next((row for row in stations if row['slug'] == 'gun-hatake'), None)
            if exceptional_site is None or request_identity(exceptional_site, 1) != EXCEPTIONAL_IDENTITY:
                raise AcquisitionStopped('supplemental_exception_request_identity_mismatch')
            budget = SupplementalBudget(output, target, limits, journal, opener=opener,
                                        sleeper=sleeper, monotonic=monotonic,
                                        original_ledger=original_ledger, lock=accounting_lock)
        except Exception as exc:
            # A known failed preflight consumes this activation permanently.
            journal.append('launch_terminal', {'error_type': type(exc).__name__})
            raise

        try:
            result = acquire_sites(stations, budget, api_key)
            budget.check_completion()
        except Exception as exc:
            journal.append('run_terminal', {'error_type': type(exc).__name__})
            raise
        if result.get('status') != 'complete' or len(result.get('stations', [])) != 32:
            result = {'status': 'incomplete', 'stations': result.get('stations', []),
                      'error_type': 'SupplementalDevelopmentIncomplete'}
        _verify_evidence(target, contract)
        envelope = {'phase': 'supplemental_hp_development', 'activation_id': activation_id,
                    'run_id': run_id, 'manifest_sha256': manifest_hash,
                    'started_at': journal.started_utc.isoformat(),
                    'deadline': journal.deadline.isoformat(), 'result': result}
        raw = encoded(envelope)
        result_hash = sha256(raw)
        result_path = output / f'result-{result_hash}.json'
        accounting_lock.assert_held()
        if result_path.exists():
            if result_path.is_symlink() or result_path.read_bytes() != raw:
                raise AcquisitionStopped('supplemental_result_path_conflict')
        else:
            pending_path = output / f'.pending-result-{result_hash}.tmp'
            if pending_path.exists():
                if pending_path.is_symlink() or pending_path.read_bytes() != raw:
                    raise AcquisitionStopped('supplemental_pending_result_conflict')
            else:
                budget._check_storage(len(raw))
                with pending_path.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                directory_fd = os.open(output, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            journal.remaining()
            os.replace(pending_path, result_path)
        directory_fd = os.open(output, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        journal.remaining()
        journal.append('run_finalized', {'result': result_path.name,
                                         'result_sha256': result_hash,
                                         'status': result['status']})
        if result['status'] != 'complete':
            raise AcquisitionStopped('supplemental_result_incomplete')
        return {'status': result['status'], 'result_sha256': result_hash,
                'result_path': str(result_path), 'journal_sha256': journal.last_sha}

def main():
    # Invocation clocks are captured before argparse parses or validates inputs.
    t0_utc, t0_mono = datetime.now(timezone.utc), time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--owner-activation', type=Path, required=True)
    parser.add_argument('--root-release', type=Path, required=True)
    parser.add_argument('--target-root', type=Path, required=True)
    parser.add_argument('--supplemental-root', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    clock_utc = [t0_utc]
    clock_mono = [t0_mono]

    def current_utc():
        if clock_utc:
            return clock_utc.pop(0)
        return datetime.now(timezone.utc)

    def current_mono():
        if clock_mono:
            return clock_mono.pop(0)
        return time.monotonic()

    try:
        result = execute(manifest_path=args.manifest, owner_activation_path=args.owner_activation,
                         root_release_path=args.root_release, target_root=args.target_root,
                         supplemental_root=args.supplemental_root, resume=args.resume,
                         now=current_utc, monotonic=current_mono,
                         api_key=os.environ.get('HOTPEPPER_API_KEY'))
        print(json.dumps(result), flush=True)
    except Exception as exc:
        print(json.dumps({'status': 'stopped', 'error_type': type(exc).__name__}), flush=True)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
