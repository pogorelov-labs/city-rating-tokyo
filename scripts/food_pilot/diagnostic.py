"""One-shot, separately gated HP response diagnostic; never a pilot phase.

This command exists so an owner can review a narrow exception. It is disabled
unless a fresh owner exception and root gate bind the exact frozen manifest,
code map and Git head. It does not resume or rewrite the original HP phase.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .acquire_osm import encoded
from .bounded import AcquisitionStopped, NoRedirect, safe_diagnostic
from .hotpepper import BadCoordinates, HPApiError, PaginationChanged, page_projection
from .run import ROOT, checked_manifest


OWNER_EXCEPTION_TYPE = 'crtky194-hp-diagnostic-owner-exception-v1'
ROOT_GATE_TYPE = 'crtky194-hp-diagnostic-root-gate-v1'
RESERVATION_TYPE = 'crtky194-hp-diagnostic-reservation-v1'
OUTCOME_TYPE = 'crtky194-hp-diagnostic-outcome-v1'
HP_PHASE_DIR = Path('/Users/ruslan/.ao/data/artifacts/city-rating-3/overture-food-shadow/target-v4/hp_development')
ORIGINAL_MANIFEST_SHA256 = '7a6f996f2324a3158407e8b8e4ef63c2670cdd05d33ce6230171bee1f84e0c00'
ORIGINAL_LEDGER_SHA256 = '73385ba0be0f8e98f12a66e2bf0f7fa5711e77864598ce774c35294de59ef4df'
ORIGINAL_RESULT_SHA256 = '0c4301b5d98b406b43a6688866c1671a5b6ad0dd13a61b801ecd9a343cde1267'
ORIGINAL_PHASE_STARTED = '2026-10-16T13:25:29.181380+00:00'
ORIGINAL_PHASE_FINISHED = '2026-10-16T13:25:31.024097+00:00'
ORIGINAL_PHASE_DEADLINE = '2026-10-16T13:55:29.181380+00:00'
FIRST_STATION_SLUG = 'gun-hatake'
FIRST_REQUEST_IDENTITY = 'hp:gun-hatake:1:c0f76ffdde068ca75e23685291e70029d28758efb37f14b4800709d6d88cb3c9'
FIRST_QUERY_SHA256 = 'c0f76ffdde068ca75e23685291e70029d28758efb37f14b4800709d6d88cb3c9'
SOURCE_CUTOFF = '2026-10-22T00:00:00Z'
MAX_REQUESTS = 1
MAX_BODY_BYTES = 1_048_576
SOCKET_TIMEOUT_SECONDS = 20
HARD_WINDOW_SECONDS = 60
MAX_RECEIPT_BYTES = 16 * 1024
MAX_RESERVATION_FILE_BYTES = MAX_RECEIPT_BYTES // 2
MAX_OUTCOME_FILE_BYTES = MAX_RECEIPT_BYTES // 2
RESERVATION_NAME = 'hp-diagnostic-reservation-v1.json'
OUTCOME_NAME = 'hp-diagnostic-outcome-v1.json'
HTTP_ENDPOINT = 'https://webservice.recruit.co.jp/hotpepper/gourmet/v1/'


class DiagnosticWindowExpired(RuntimeError):
    pass


class _StatusResponse:
    def __init__(self, status):
        self.status = status


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _encoded_map_sha(code_map):
    return _sha((json.dumps(code_map, sort_keys=True, indent=2) + '\n').encode())


def _read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise AcquisitionStopped('diagnostic_gate_file_missing_or_symlinked')
    if path.stat().st_size > MAX_RECEIPT_BYTES:
        raise AcquisitionStopped('diagnostic_gate_file_too_large')
    raw = path.read_bytes()
    if len(raw) > MAX_RECEIPT_BYTES:
        raise AcquisitionStopped('diagnostic_gate_file_too_large')
    try:
        return json.loads(raw), raw
    except (ValueError, TypeError):
        raise AcquisitionStopped('diagnostic_gate_json_invalid') from None


def _current_head():
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, check=True, timeout=2)
        head = result.stdout.strip()
    except Exception:
        raise AcquisitionStopped('diagnostic_git_head_unavailable') from None
    if len(head) != 40 or any(c not in '0123456789abcdef' for c in head):
        raise AcquisitionStopped('diagnostic_git_head_invalid')
    return head


def _utc(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    except (ValueError, TypeError, AttributeError):
        raise AcquisitionStopped('diagnostic_timestamp_invalid') from None
    if parsed.tzinfo is None:
        raise AcquisitionStopped('diagnostic_timestamp_naive')
    return parsed.astimezone(timezone.utc)


def _now():
    return datetime.now(timezone.utc)


def _check_deadlines(started_mono):
    now = _now()
    cutoff = _utc(SOURCE_CUTOFF)
    if now >= cutoff:
        raise AcquisitionStopped('diagnostic_source_cutoff')
    if time.monotonic() - started_mono >= HARD_WINDOW_SECONDS:
        raise DiagnosticWindowExpired()
    return now


@contextmanager
def _hard_alarm(seconds):
    def expire(_signum, _frame):
        raise DiagnosticWindowExpired()

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _write_exclusive(path, raw, maximum):
    if len(raw) > maximum:
        raise AcquisitionStopped('diagnostic_receipt_size')
    path = Path(path)
    try:
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError:
        raise AcquisitionStopped('diagnostic_already_attempted') from None
    return _sha(raw)


def _tree_bytes(root):
    total = 0
    for path in Path(root).rglob('*'):
        if path.is_symlink():
            raise AcquisitionStopped('diagnostic_symlink_in_accounting_tree')
        if path.is_file():
            total += path.stat().st_size
    return total


def _require_under(path, root):
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_relative_to(Path(root).resolve(strict=True)):
        raise AcquisitionStopped('diagnostic_receipt_outside_accounted_root')
    return resolved


def _fixed_request(manifest, api_key):
    stations = [row for row in manifest['core']['stations'] if row['split'] == 'development']
    if not stations or stations[0].get('slug') != FIRST_STATION_SLUG:
        raise AcquisitionStopped('diagnostic_station_identity_mismatch')
    station = stations[0]
    params = {'lat': station['lat'], 'lng': station['lng'], 'range': 3,
              'count': 100, 'start': 1, 'format': 'json', 'order': 1}
    query_sha = _sha(json.dumps(params, sort_keys=True).encode())
    if query_sha != FIRST_QUERY_SHA256:
        raise AcquisitionStopped('diagnostic_request_identity_mismatch')
    request_params = {**params, 'key': api_key}
    request = urllib.request.Request(HTTP_ENDPOINT + '?' + urllib.parse.urlencode(request_params),
                                     headers={'User-Agent': 'city-rating-food-shadow/2.0',
                                              'Accept-Encoding': 'identity'})
    return request, query_sha


def _original_inputs(phase_dir, manifest):
    phase_dir = Path(phase_dir)
    if phase_dir.is_symlink():
        raise AcquisitionStopped('diagnostic_phase_dir_symlink')
    phase_dir = phase_dir.resolve(strict=True)
    ledger_path = phase_dir / 'ledger.json'
    result_path = phase_dir / f'result-{ORIGINAL_RESULT_SHA256}.json'
    ledger_raw = ledger_path.read_bytes()
    result_raw = result_path.read_bytes()
    if _sha(ledger_raw) != ORIGINAL_LEDGER_SHA256 or _sha(result_raw) != ORIGINAL_RESULT_SHA256:
        raise AcquisitionStopped('diagnostic_original_evidence_changed')
    ledger = json.loads(ledger_raw)
    if (ledger.get('manifest_sha256') != ORIGINAL_MANIFEST_SHA256
            or ledger.get('status') != 'incomplete'
            or ledger.get('started_at') != ORIGINAL_PHASE_STARTED
            or ledger.get('finished_at') != ORIGINAL_PHASE_FINISHED
            or ledger.get('charged_bytes') != 107
            or ledger.get('successful_pages') != 0
            or len(ledger.get('attempts', [])) != 1
            or ledger['attempts'][0].get('identity') != FIRST_REQUEST_IDENTITY
            or ledger['attempts'][0].get('status') != 'failed'
            or ledger['attempts'][0].get('retry_disposition') != 'terminal'
            or ledger['attempts'][0].get('observed_bytes') != 107):
        raise AcquisitionStopped('diagnostic_original_ledger_contract')
    if ledger.get('limits') != manifest['budgets'].get('hp_development'):
        raise AcquisitionStopped('diagnostic_original_budget_mismatch')
    original_deadline = _utc(ledger['started_at']) + timedelta(seconds=ledger['limits']['wall_seconds'])
    if original_deadline.isoformat() != ORIGINAL_PHASE_DEADLINE:
        raise AcquisitionStopped('diagnostic_original_deadline_mismatch')
    result = json.loads(result_raw)
    station_rows = result.get('result', {}).get('stations', [])
    if (result.get('phase') != 'hp_development'
            or result.get('manifest_sha256') != ORIGINAL_MANIFEST_SHA256
            or result.get('result', {}).get('status') != 'incomplete'
            or not station_rows or station_rows[0].get('slug') != FIRST_STATION_SLUG
            or station_rows[0].get('status') != 'truncated'
            or station_rows[0].get('count_800m') is not None):
        raise AcquisitionStopped('diagnostic_original_result_contract')
    return ledger, ledger_raw, result_raw


def _validate_gates(manifest_path, owner_path, root_path):
    manifest, manifest_sha = checked_manifest(Path(manifest_path))
    from . import recovery
    recovery._check_successor_lineage(manifest, manifest_sha)
    if manifest.get('supersedes_manifest_sha256') != recovery.V8_MANIFEST_SHA256:
        raise AcquisitionStopped('diagnostic_manifest_not_v8_successor')
    head = _current_head()
    code_sha = _encoded_map_sha(manifest['code_sha256'])
    owner, owner_raw = _read_json(owner_path)
    root_gate, root_raw = _read_json(root_path)
    owner_fields = {
        'type', 'decision', 'owner_exception_id', 'recorded_at_utc', 'manifest_sha256',
        'code_head_sha256', 'code_map_sha256', 'original_ledger_sha256',
        'original_result_sha256', 'request_identity', 'query_sha256', 'source_cutoff_utc',
        'max_requests', 'max_body_bytes', 'socket_timeout_seconds', 'hard_window_seconds',
        'max_receipt_bytes', 'allow_retry', 'allow_redirect', 'pilot_count_permitted',
        'phase_completion_permitted', 'next_request_permitted',
    }
    root_fields = {
        'type', 'root_release_id', 'released_at_utc', 'root_session', 'delivery_handle', 'root_manifest_check',
        'diagnostic_only', 'allowed_operation', 'manifest_sha256', 'code_head_sha256',
        'code_map_sha256', 'native_review_approved_head', 'owner_exception_sha256',
        'ci_all_green', 'ci_run_id', 'max_requests', 'max_body_bytes', 'max_receipt_bytes',
        'socket_timeout_seconds', 'hard_window_seconds', 'source_cutoff_utc',
        'allow_retry', 'allow_redirect', 'metadata_requests_permitted', 'phase_completion_permitted',
        'pilot_count_permitted', 'next_request_permitted',
    }
    if set(owner) != owner_fields or set(root_gate) != root_fields:
        raise AcquisitionStopped('diagnostic_gate_schema_mismatch')
    if (owner.get('type') != OWNER_EXCEPTION_TYPE
            or owner.get('decision') != 'allow_one_hp_diagnostic_only'
            or owner.get('manifest_sha256') != manifest_sha
            or owner.get('code_head_sha256') != head
            or owner.get('code_map_sha256') != code_sha
            or owner.get('original_ledger_sha256') != ORIGINAL_LEDGER_SHA256
            or owner.get('original_result_sha256') != ORIGINAL_RESULT_SHA256
            or owner.get('request_identity') != FIRST_REQUEST_IDENTITY
            or owner.get('query_sha256') != FIRST_QUERY_SHA256
            or owner.get('source_cutoff_utc') != SOURCE_CUTOFF
            or owner.get('max_requests') != MAX_REQUESTS
            or owner.get('max_body_bytes') != MAX_BODY_BYTES
            or owner.get('socket_timeout_seconds') != SOCKET_TIMEOUT_SECONDS
            or owner.get('hard_window_seconds') != HARD_WINDOW_SECONDS
            or owner.get('max_receipt_bytes') != MAX_RECEIPT_BYTES
            or not isinstance(owner.get('owner_exception_id'), str)
            or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,96}', owner['owner_exception_id'])
            or not isinstance(owner.get('recorded_at_utc'), str)
            or _utc(owner['recorded_at_utc']) > _now()
            or owner.get('allow_retry') is not False
            or owner.get('allow_redirect') is not False
            or owner.get('pilot_count_permitted') is not False
            or owner.get('phase_completion_permitted') is not False
            or owner.get('next_request_permitted') is not False):
        raise AcquisitionStopped('diagnostic_owner_exception_mismatch')
    if (root_gate.get('type') != ROOT_GATE_TYPE
            or root_gate.get('root_manifest_check') is not True
            or root_gate.get('diagnostic_only') is not True
            or root_gate.get('allowed_operation') != 'one_hp_diagnostic_request'
            or root_gate.get('manifest_sha256') != manifest_sha
            or root_gate.get('code_head_sha256') != head
            or root_gate.get('code_map_sha256') != code_sha
            or root_gate.get('native_review_approved_head') != head
            or root_gate.get('owner_exception_sha256') != _sha(owner_raw)
            or root_gate.get('root_session') != 'city-rating-1'
            or not isinstance(root_gate.get('root_release_id'), str)
            or not root_gate.get('root_release_id')
            or not isinstance(root_gate.get('released_at_utc'), str)
            or _utc(root_gate['released_at_utc']) > _now()
            or not isinstance(root_gate.get('delivery_handle'), str)
            or not root_gate.get('delivery_handle')
            or root_gate.get('ci_all_green') is not True
            or not isinstance(root_gate.get('ci_run_id'), str)
            or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,96}', root_gate['ci_run_id'])
            or root_gate.get('max_receipt_bytes') != MAX_RECEIPT_BYTES
            or root_gate.get('socket_timeout_seconds') != SOCKET_TIMEOUT_SECONDS
            or root_gate.get('hard_window_seconds') != HARD_WINDOW_SECONDS
            or root_gate.get('allow_retry') is not False
            or root_gate.get('allow_redirect') is not False
            or root_gate.get('metadata_requests_permitted') is not False
            or root_gate.get('phase_completion_permitted') is not False
            or root_gate.get('pilot_count_permitted') is not False
            or root_gate.get('next_request_permitted') is not False
            or root_gate.get('max_requests') != MAX_REQUESTS
            or root_gate.get('max_body_bytes') != MAX_BODY_BYTES
            or root_gate.get('source_cutoff_utc') != SOURCE_CUTOFF):
        raise AcquisitionStopped('diagnostic_root_gate_mismatch')
    _utc(owner['recorded_at_utc'])
    return manifest, manifest_sha, head, code_sha, owner_raw, root_raw


def _read_response(response, started_mono):
    status = getattr(response, 'status', None)
    received = 0
    chunks = []
    eof = False
    while received < MAX_BODY_BYTES:
        _check_deadlines(started_mono)
        chunk = response.read(min(64 * 1024, MAX_BODY_BYTES - received))
        if not chunk:
            eof = True
            break
        received += len(chunk)
        chunks.append(chunk)
    return status, b''.join(chunks), received, eof


def _project(raw, status):
    try:
        projected = page_projection(raw, _StatusResponse(status))
        return 'response_contract_valid', safe_diagnostic(projected.get('diagnostic'))
    except (HPApiError, BadCoordinates, PaginationChanged) as exc:
        return 'parser_rejected', safe_diagnostic(getattr(exc, 'safe_diagnostic', None))
    except Exception:
        return 'diagnostic_processing_error', None


def _build_reservation(*, manifest_sha, head, code_sha, owner_sha, root_sha,
                       ledger_sha, result_sha, ledger, limits, phase_retained,
                       total_retained, started_at, deadline):
    return {
        'artifact_type': RESERVATION_TYPE,
        'state': 'reserved_before_io',
        'manifest_sha256': manifest_sha,
        'code_head_sha256': head,
        'code_map_sha256': code_sha,
        'owner_exception_sha256': owner_sha,
        'root_gate_sha256': root_sha,
        'original_ledger_sha256': ledger_sha,
        'original_result_sha256': result_sha,
        'original_phase_status_remains': 'incomplete',
        'original_phase_started_at_utc': ORIGINAL_PHASE_STARTED,
        'original_phase_finished_at_utc': ORIGINAL_PHASE_FINISHED,
        'original_phase_deadline_utc': ORIGINAL_PHASE_DEADLINE,
        'request_identity': FIRST_REQUEST_IDENTITY,
        'query_sha256': FIRST_QUERY_SHA256,
        'request_attempts_reserved': 1,
        'phase_attempts_used_before': len(ledger['attempts']),
        'phase_attempt_cap': limits['attempts'],
        'same_page_attempts_used_before': sum(
            attempt['identity'] == FIRST_REQUEST_IDENTITY for attempt in ledger['attempts']),
        'same_page_attempt_cap': limits['maximum_attempts_per_page'],
        'response_body_bytes_charged_before': ledger['charged_bytes'],
        'response_body_bytes_reserved': MAX_BODY_BYTES,
        'response_body_bytes_cap': limits['response_body_bytes'],
        'successful_page_slots_used_before': ledger['successful_pages'],
        'successful_page_slots_reserved': 1,
        'successful_page_slots_cap': limits['successful_pages'],
        'body_bytes_reserved': MAX_BODY_BYTES,
        'retained_bytes_reserved': MAX_RECEIPT_BYTES,
        'phase_retained_bytes_before': phase_retained,
        'phase_retained_bytes_cap': limits['retained_bytes'],
        'total_retained_bytes_before': total_retained,
        'total_retained_bytes_cap': 2 * 1024**3,
        'started_at_utc': started_at.isoformat(),
        'diagnostic_deadline_utc': deadline.isoformat(),
        'socket_timeout_seconds': SOCKET_TIMEOUT_SECONDS,
        'source_cutoff_utc': SOURCE_CUTOFF,
        'retry_permitted': False,
        'redirect_permitted': False,
        'pilot_count_created': False,
        'phase_completion_claim': False,
        'next_request_permitted': False,
    }


def _build_outcome(*, reservation_sha, status, started_at, finished_at,
                   body_bytes, body_charge, eof, diagnostic):
    return {
        'artifact_type': OUTCOME_TYPE,
        'state': 'diagnostic_only',
        'reservation_sha256': reservation_sha,
        'request_identity': FIRST_REQUEST_IDENTITY,
        'query_sha256': FIRST_QUERY_SHA256,
        'diagnostic_status': status,
        'started_at_utc': started_at.isoformat(),
        'finished_at_utc': finished_at.isoformat(),
        'observed_body_bytes': body_bytes,
        'body_bytes_charged': body_charge,
        'eof_observed': eof,
        'diagnostic': safe_diagnostic(diagnostic),
        'pilot_count_created': False,
        'hp_zero_confirmed': False,
        'phase_completion_claim': False,
        'next_request_permitted': False,
    }


def _retention_preflight(phase_dir, target_root, limits, total_limit, owner_path, root_path):
    # Keep authorization and both diagnostic records under the existing frozen
    # target-v4 root so they are included in the same global accounting tree.
    _require_under(owner_path, target_root)
    _require_under(root_path, target_root)
    used_phase = _tree_bytes(phase_dir)
    used_total = _tree_bytes(target_root)
    if used_phase + MAX_RECEIPT_BYTES > limits['retained_bytes']:
        raise AcquisitionStopped('diagnostic_phase_retention_budget')
    if used_total + MAX_RECEIPT_BYTES > total_limit:
        raise AcquisitionStopped('diagnostic_global_retention_budget')
    return used_phase, used_total


def run_diagnostic(manifest_path, owner_exception_path, root_gate_path, *,
                   api_key=None, opener=None):
    """Run the one diagnostic only after fresh exact-bound receipts are supplied.

    This function is not called by the ordinary phase runner. It does not reuse
    the expired HP phase clock and does not alter that phase; its own one-shot
    diagnostic clock and byte/attempt reservations are separately accounted.
    """
    started_mono = time.monotonic()
    started_at = _now()
    deadline = started_at + timedelta(seconds=HARD_WINDOW_SECONDS)
    _check_deadlines(started_mono)
    manifest, manifest_sha, head, code_sha, owner_raw, root_raw = _validate_gates(
        manifest_path, owner_exception_path, root_gate_path)
    phase_dir = Path(HP_PHASE_DIR)
    lock_path = phase_dir / '.reader.lock'
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise AcquisitionStopped('hp_phase_busy') from None
        return _run_locked(manifest=manifest, manifest_sha=manifest_sha, head=head,
            code_sha=code_sha, owner_raw=owner_raw, root_raw=root_raw,
            owner_path=owner_exception_path, root_path=root_gate_path,
            phase_dir=phase_dir, started_mono=started_mono,
            started_at=started_at, deadline=deadline, api_key=api_key, opener=opener)


def _run_locked(*, manifest, manifest_sha, head, code_sha, owner_raw, root_raw,
                owner_path, root_path, phase_dir, started_mono, started_at,
                deadline, api_key, opener):
    target_root = phase_dir.parent
    limits = manifest['budgets']['hp_development']
    # Re-read immutable approvals under the same single-reader lock as the
    # original HP ledger, preventing a validation/write race before I/O.
    _owner, owner_check = _read_json(owner_path)
    _root_gate, root_check = _read_json(root_path)
    if _sha(owner_check) != _sha(owner_raw) or _sha(root_check) != _sha(root_raw):
        raise AcquisitionStopped('diagnostic_gate_changed_after_validation')
    ledger, ledger_raw, result_raw = _original_inputs(phase_dir, manifest)
    if (manifest['source_window'].get('core_hp_complete_before') != SOURCE_CUTOFF
            or manifest['budgets'].get('total_retained_bytes') != 2 * 1024**3):
        raise AcquisitionStopped('diagnostic_frozen_contract_changed')
    if (len(ledger['attempts']) >= limits['attempts']
            or ledger['charged_bytes'] + MAX_BODY_BYTES > limits['response_body_bytes']
            or ledger['successful_pages'] + 1 > limits['successful_pages']
            or sum(a['identity'] == FIRST_REQUEST_IDENTITY for a in ledger['attempts']) + 1
                > limits['maximum_attempts_per_page']):
        raise AcquisitionStopped('diagnostic_original_budget_exhausted')
    reservation_path = phase_dir / RESERVATION_NAME
    outcome_path = phase_dir / OUTCOME_NAME
    if reservation_path.exists() or outcome_path.exists():
        raise AcquisitionStopped('diagnostic_already_attempted')
    if api_key is None:
        api_key = os.environ.get('HOTPEPPER_API_KEY')
    if not isinstance(api_key, str) or not api_key:
        raise AcquisitionStopped('scoped_hp_credential_unavailable')
    _check_deadlines(started_mono)
    request, _ = _fixed_request(manifest, api_key)
    phase_retained, total_retained = _retention_preflight(phase_dir, target_root,
        limits, manifest['budgets']['total_retained_bytes'], owner_path, root_path)
    _check_deadlines(started_mono)
    reservation = _build_reservation(manifest_sha=manifest_sha, head=head,
        code_sha=code_sha, owner_sha=_sha(owner_raw), root_sha=_sha(root_raw),
        ledger_sha=_sha(ledger_raw), result_sha=_sha(result_raw), ledger=ledger,
        limits=limits, phase_retained=phase_retained, total_retained=total_retained,
        started_at=started_at, deadline=deadline)
    reservation_raw = encoded(reservation)
    reservation_sha = _write_exclusive(reservation_path, reservation_raw,
                                       MAX_RESERVATION_FILE_BYTES)
    # From this durable point onward, a crash consumes the whole reserved
    # attempt/body allowance and the fixed path prevents any retry.
    outcome_status, diag, observed, eof, status = 'unknown_outcome', None, 0, False, None
    body_charge = MAX_BODY_BYTES
    request_opener = opener or urllib.request.build_opener(NoRedirect()).open
    try:
        remaining = HARD_WINDOW_SECONDS - (time.monotonic() - started_mono)
        if remaining <= 0:
            raise DiagnosticWindowExpired()
        with _hard_alarm(remaining):
            _check_deadlines(started_mono)
            try:
                response_context = request_opener(request, timeout=SOCKET_TIMEOUT_SECONDS)
            except urllib.error.HTTPError as exc:
                status = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else None
                outcome_status = 'http_error'
                diag = safe_diagnostic({'http_status': status, 'parser_reason':
                                        'redirect_rejected' if status in (301,302,303,307,308) else 'http_error'})
                # Do not read or retain an HTTP error body. The complete
                # reservation is charged because body consumption is unknown.
                response_context = None
            if response_context is not None:
                with response_context as response:
                    status, raw, observed, eof = _read_response(response, started_mono)
                if eof:
                    outcome_status, diag = _project(raw, status)
                    body_charge = observed
                else:
                    outcome_status = 'response_limit_or_eof_unknown'
                    diag = safe_diagnostic({'http_status': status, 'body_bytes': observed,
                                            'parser_reason': 'response_not_complete'})
            _check_deadlines(started_mono)
    except DiagnosticWindowExpired:
        outcome_status = 'diagnostic_window_expired'
    except (urllib.error.URLError, TimeoutError, OSError):
        outcome_status = 'transport_unknown'
    except AcquisitionStopped as exc:
        if str(exc) == 'redirect_rejected':
            outcome_status = 'http_error'
            diag = safe_diagnostic({'parser_reason': 'redirect_rejected'})
        else:
            outcome_status = 'diagnostic_window_or_cutoff_rejected'
    except Exception as exc:
        if isinstance(exc, (HPApiError, BadCoordinates, PaginationChanged)):
            outcome_status = 'parser_rejected'
            diag = safe_diagnostic(getattr(exc, 'safe_diagnostic', None))
        else:
            outcome_status = 'diagnostic_processing_error'
    finished_at = _now()
    if (finished_at >= _utc(SOURCE_CUTOFF)
            and outcome_status not in ('diagnostic_window_expired', 'diagnostic_window_or_cutoff_rejected')):
        outcome_status = 'outcome_outside_diagnostic_window'
        body_charge = MAX_BODY_BYTES
    if (time.monotonic() - started_mono >= HARD_WINDOW_SECONDS
            and outcome_status not in ('diagnostic_window_expired', 'diagnostic_window_or_cutoff_rejected')):
        outcome_status = 'outcome_outside_diagnostic_window'
        body_charge = MAX_BODY_BYTES
    if not eof:
        body_charge = MAX_BODY_BYTES
    outcome = _build_outcome(reservation_sha=reservation_sha, status=outcome_status,
        started_at=started_at, finished_at=finished_at, body_bytes=observed,
        body_charge=body_charge, eof=eof, diagnostic=diag)
    outcome_raw = encoded(outcome)
    if len(reservation_raw) + len(outcome_raw) > MAX_RECEIPT_BYTES:
        # The reservation remains and consumes the complete cap; never
        # overwrite it or issue another request to recover the outcome.
        raise AcquisitionStopped('diagnostic_receipt_combined_size')
    if (_tree_bytes(phase_dir) + len(outcome_raw) > limits['retained_bytes']
            or _tree_bytes(target_root) + len(outcome_raw) > manifest['budgets']['total_retained_bytes']):
        raise AcquisitionStopped('diagnostic_retention_after_request')
    _write_exclusive(outcome_path, outcome_raw, MAX_OUTCOME_FILE_BYTES)
    return {'state': 'diagnostic_only', 'outcome_path': str(outcome_path),
            'sha256': _sha(outcome_raw), 'diagnostic_status': outcome_status,
            'body_bytes_charged': body_charge}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--owner-exception', type=Path, required=True)
    parser.add_argument('--root-gate', type=Path, required=True)
    args = parser.parse_args()
    result = run_diagnostic(args.manifest, args.owner_exception, args.root_gate)
    print(json.dumps({key: result[key] for key in
                      ('state', 'sha256', 'diagnostic_status', 'body_bytes_charged')}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Never print exception messages, request URLs, headers or credentials.
        print(json.dumps({'state': 'stopped', 'error_type': type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
