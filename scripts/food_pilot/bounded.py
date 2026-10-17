"""Durable, single-reader request budgets for internal shadow acquisition.

No credentials, URLs, response headers or exception messages enter the ledger.
Callers supply validated requests and project safe response fields before caching.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import re
import signal
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .acquire_osm import encoded, save_ledger


class AcquisitionStopped(RuntimeError):
    pass


class RequestRejected(AcquisitionStopped):
    def __init__(self, error_type, diagnostic=None):
        super().__init__('request_or_contract_rejected')
        self.error_type = error_type
        self.diagnostic = diagnostic


_DIAGNOSTIC_TYPES = {'null', 'boolean', 'integer', 'number', 'string', 'array', 'object', 'other'}
_DIAGNOSTIC_PAGINATION = {'results_available', 'results_start', 'results_returned'}
_DIAGNOSTIC_PROVIDER_CODES = {'1000', '2000', '3000'}


def safe_diagnostic(value):
    """Copy only bounded structural diagnostics; never persist arbitrary parser data."""
    if not isinstance(value, dict):
        return None
    result = {}
    status = value.get('http_status')
    if type(status) is int and 100 <= status <= 599:
        result['http_status'] = status
    reason = value.get('parser_reason')
    if isinstance(reason, str) and re.fullmatch(r'[a-z][a-z0-9_]{0,63}', reason):
        result['parser_reason'] = reason
    body_bytes = value.get('body_bytes')
    if type(body_bytes) is int and 0 <= body_bytes <= 1_048_576:
        result['body_bytes'] = body_bytes
    payload_type = value.get('payload_type')
    if isinstance(payload_type, str) and payload_type in _DIAGNOSTIC_TYPES | {'invalid_json'}:
        result['payload_type'] = payload_type
    for key in ('pagination_types', 'pagination_counts'):
        fields = value.get(key)
        if isinstance(fields, dict):
            if key == 'pagination_types':
                clean = {name: kind for name, kind in fields.items()
                         if name in _DIAGNOSTIC_PAGINATION and isinstance(kind, str) and kind in _DIAGNOSTIC_TYPES}
            else:
                clean = {name: count for name, count in fields.items()
                         if name in _DIAGNOSTIC_PAGINATION and type(count) is int and 0 <= count <= 1_000_000}
            if clean:
                result[key] = clean
    shop_type = value.get('shop_type')
    if isinstance(shop_type, str) and shop_type in _DIAGNOSTIC_TYPES:
        result['shop_type'] = shop_type
    shop_count = value.get('shop_count')
    if type(shop_count) is int and 0 <= shop_count <= 1000:
        result['shop_count'] = shop_count
    if type(value.get('provider_error_present')) is bool:
        result['provider_error_present'] = value['provider_error_present']
    codes = value.get('provider_error_codes')
    if isinstance(codes, list):
        clean_codes = sorted({code for code in codes
                              if isinstance(code, str) and code in _DIAGNOSTIC_PROVIDER_CODES})
        if clean_codes:
            result['provider_error_codes'] = clean_codes
    return result or None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcquisitionStopped('redirect_rejected')


class Budget:
    def __init__(self, directory, limits, manifest_hash, *, resume=False, opener=None,
                 absolute_deadline=None, identity_windows=None, completion_window=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.limits = limits
        self.absolute_deadline = self._utc(absolute_deadline) if absolute_deadline else None
        self.identity_windows = {key: tuple(self._utc(v) for v in value)
                                 for key, value in (identity_windows or {}).items()}
        self.completion_window = tuple(self._utc(v) for v in completion_window) if completion_window else None
        self.window_contract = {
            'absolute_deadline': self.absolute_deadline.isoformat() if self.absolute_deadline else None,
            'identity_windows': {key: [v.isoformat() for v in value]
                                 for key, value in sorted(self.identity_windows.items())},
            'completion_window': [v.isoformat() for v in self.completion_window] if self.completion_window else None,
        }
        self.path = self.directory / 'ledger.json'
        self.lock = (self.directory / '.reader.lock').open('a')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open
        anchor = time.monotonic()
        now = datetime.now(timezone.utc)
        if self.path.exists():
            if not resume:
                self.close()
                raise AcquisitionStopped('ledger_exists_no_reset')
            self.ledger = json.loads(self.path.read_text())
            if self.ledger['manifest_sha256'] != manifest_hash or self.ledger['limits'] != limits:
                self.close()
                raise AcquisitionStopped('frozen_budget_changed')
            if self.ledger.get('window_contract', self.window_contract) != self.window_contract:
                self.close()
                raise AcquisitionStopped('frozen_acquisition_window_changed')
            self.ledger.setdefault('window_contract', self.window_contract)
            elapsed = (now - datetime.fromisoformat(self.ledger['started_at'])).total_seconds()
            if elapsed < 0:
                self.close()
                raise AcquisitionStopped('clock_precedes_original_start')
            for attempt in self.ledger['attempts']:
                if attempt['status'] == 'pending':
                    attempt['status'] = 'interrupted'
                    attempt['retry_disposition'] = 'retryable'
                elif attempt['status'] == 'failed' and 'retry_disposition' not in attempt:
                    # Older receipts did not persist this decision. Fail closed:
                    # a resumed invocation must not infer permission to retry.
                    attempt['retry_disposition'] = 'terminal'
        else:
            self.ledger = {'manifest_sha256': manifest_hash, 'limits': limits,
                           'started_at': now.isoformat(), 'attempts': [], 'charged_bytes': 0,
                           'successful_pages': 0, 'row_groups': [], 'status': 'in_progress',
                           'window_contract': self.window_contract}
            elapsed = 0
        self.deadline = anchor + limits['wall_seconds'] - elapsed
        last_at = self.ledger['attempts'][-1]['at'] if self.ledger['attempts'] else None
        self.last_request = anchor-(now-datetime.fromisoformat(last_at)).total_seconds() if last_at else None
        self.previous_handler = None
        try:
            self.remaining()
            self.persist()
        except BaseException:
            self.close()
            raise

    def close(self):
        if not self.lock.closed:
            self.lock.close()

    def __enter__(self):
        self.previous_handler = signal.signal(signal.SIGALRM, self._alarm)
        signal.setitimer(signal.ITIMER_REAL, self.remaining())
        return self

    def __exit__(self, kind, value, trace):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self.previous_handler)
        self.ledger['status'] = 'complete' if kind is None else 'incomplete'
        self.ledger['finished_at'] = datetime.now(timezone.utc).isoformat()
        try:
            self.persist()
        finally:
            self.close()

    @staticmethod
    def _alarm(_signum, _frame):
        raise AcquisitionStopped('original_wall_deadline')

    @staticmethod
    def _utc(value):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
        if parsed.tzinfo is None:
            raise AcquisitionStopped('naive_acquisition_window')
        return parsed.astimezone(timezone.utc)

    def check_window(self, identity=None, *, completion=False):
        now = datetime.now(timezone.utc)
        if self.absolute_deadline is not None and now >= self.absolute_deadline:
            raise AcquisitionStopped('absolute_source_deadline')
        if completion and self.completion_window is not None:
            earliest, latest = self.completion_window
            if now < earliest or now >= latest:
                raise AcquisitionStopped('confirmation_completion_window')
        if identity is not None:
            for prefix, (earliest, latest) in self.identity_windows.items():
                if identity.startswith(prefix) and (now < earliest or now >= latest):
                    raise AcquisitionStopped('confirmation_request_window')

    def remaining(self, identity=None):
        self.check_window(identity)
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AcquisitionStopped('original_wall_deadline')
        if self.absolute_deadline is not None:
            remaining = min(remaining, (self.absolute_deadline-datetime.now(timezone.utc)).total_seconds())
        if identity is not None:
            for prefix, (_earliest, latest) in self.identity_windows.items():
                if identity.startswith(prefix):
                    remaining = min(remaining, (latest-datetime.now(timezone.utc)).total_seconds())
        if remaining <= 0:
            raise AcquisitionStopped('absolute_acquisition_window')
        return remaining

    def check_completion(self):
        self.check_window(completion=True)
        self.remaining()

    def persist(self):
        if self.retained()+len(encoded(self.ledger)) > self.limits['retained_bytes']:
            raise AcquisitionStopped('retained_ledger_budget')
        save_ledger(self.path, self.ledger)

    def retained(self):
        return sum(p.stat().st_size for p in self.directory.rglob('*') if p.is_file())

    def group(self, identity):
        self.remaining()
        if identity in self.ledger['row_groups']:
            return
        if len(self.ledger['row_groups']) >= self.limits['row_groups']:
            raise AcquisitionStopped('row_group_budget')
        self.ledger['row_groups'].append(identity)
        self.persist()

    def fetch(self, identity, request, project, *, response_bytes=None, kind='range'):
        """Return projected/cached safe data; bounded unknown attempts stay charged."""
        self.remaining(identity)
        previous = [a for a in self.ledger['attempts'] if a['identity'] == identity]
        terminal = [a for a in previous if a.get('retry_disposition') == 'terminal' or
                    a.get('status') == 'failed' and a.get('retry_disposition') not in ('transient', 'retryable')]
        if terminal:
            raise RequestRejected(terminal[-1].get('error_type', 'TerminalRequestHistory'))
        complete = [a for a in previous if a['status'] == 'complete']
        if complete:
            if len(complete) != 1:
                raise AcquisitionStopped('ambiguous_cached_receipt')
            raw = (self.directory / complete[0]['cache']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != complete[0]['cache_sha256']:
                raise AcquisitionStopped('cached_response_hash')
            return json.loads(raw)
        maximum = self.limits.get('maximum_attempts_per_page', self.limits.get('maximum_attempts_per_range', 2))
        if previous and len(previous) < maximum:
            # A resumed interrupted retry also observes the frozen backoff.
            time.sleep(min(2, self.remaining(identity)))
        while len(previous) < maximum:
            self.remaining(identity)
            if len(self.ledger['attempts']) >= self.limits['attempts']:
                raise AcquisitionStopped('attempt_budget')
            if kind == 'page' and self.ledger['successful_pages'] >= self.limits['successful_pages']:
                raise AcquisitionStopped('page_budget')
            reservation = response_bytes or self.limits['response_bytes']
            if reservation > self.limits['response_bytes'] or self.ledger['charged_bytes'] + reservation > self.limits['response_body_bytes']:
                raise AcquisitionStopped('response_byte_budget')
            if self.retained() + reservation > self.limits['retained_bytes']:
                raise AcquisitionStopped('retained_byte_budget')
            if self.last_request is not None:
                wait = self.limits['minimum_request_interval_seconds'] - (time.monotonic() - self.last_request)
                if wait > 0:
                    time.sleep(min(wait, self.remaining(identity)))
            attempt = {'identity': identity, 'status': 'pending', 'reserved_bytes': reservation,
                       'at': datetime.now(timezone.utc).isoformat(), 'accounting': 'conservative_reservation',
                       'retry_disposition': 'pending'}
            self.ledger['attempts'].append(attempt)
            previous.append(attempt)
            self.ledger['charged_bytes'] += reservation
            self.persist()  # durable before opening a socket
            received, eof, retry = 0, False, False
            try:
                timeout = min(self.limits['socket_seconds'], self.remaining(identity))
                self.last_request = time.monotonic()
                with self.opener(request, timeout=timeout) as response:
                    chunks = []
                    while True:
                        self.remaining(identity)
                        if received == reservation:
                            # Exact-length range callers can validate this using
                            # Content-Range; ordinary pages require EOF below cap.
                            if response_bytes is None:
                                raise AcquisitionStopped('response_at_cap')
                            break
                        chunk = response.read(min(65536, reservation-received))
                        received += len(chunk)
                        if not chunk:
                            eof = True
                            break
                        chunks.append(chunk)
                    raw = b''.join(chunks)
                    result = project(raw, response)
                    self.remaining(identity)
                cached = encoded(result)
                if self.retained() + len(cached) > self.limits['retained_bytes']:
                    raise AcquisitionStopped('retained_byte_budget')
                cache = f'response-{len(self.ledger["attempts"]):05d}.json'
                with (self.directory / cache).open('xb') as stream:
                    stream.write(cached)
                    stream.flush()
                    import os
                    os.fsync(stream.fileno())
                self.remaining(identity)
                attempt.update(status='complete', cache=cache,
                               cache_sha256=hashlib.sha256(cached).hexdigest(),
                               response_sha256=hashlib.sha256(raw).hexdigest(),
                               retry_disposition='none')
                if kind == 'page':
                    self.ledger['successful_pages'] += 1
                # Successful exact-range projection establishes complete bytes.
                eof = True
            except urllib.error.HTTPError as exc:
                status = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else None
                retry = status is not None and 500 <= status <= 599
                attempt.update(status='failed', error_type='HTTPError',
                               retry_disposition='transient' if retry else 'terminal',
                               diagnostic=safe_diagnostic({'http_status': status, 'parser_reason': 'http_error'}))
                if status is not None:
                    attempt['http_status'] = status
            except (urllib.error.URLError, TimeoutError) as exc:
                retry = True
                attempt.update(status='failed', error_type=type(exc).__name__, retry_disposition='transient')
            except Exception as exc:
                attempt.update(status='failed', error_type=type(exc).__name__, retry_disposition='terminal')
                diagnostic = getattr(exc, 'safe_diagnostic', None)
                diagnostic = safe_diagnostic(diagnostic)
                if diagnostic:
                    attempt['diagnostic'] = diagnostic
            except BaseException as exc:
                attempt.update(status='interrupted', error_type=type(exc).__name__, retry_disposition='retryable')
                raise
            finally:
                attempt['observed_bytes'] = received
                if eof and attempt['status'] != 'interrupted':
                    self.ledger['charged_bytes'] -= reservation-received
                    attempt['accounting'] = 'observed_complete_body'
                self.persist()
            if attempt['status'] == 'complete':
                return result
            if not retry:
                raise RequestRejected(attempt.get('error_type', 'UnknownRequestError'),
                                      attempt.get('diagnostic'))
            if len(previous) < maximum:
                time.sleep(min(2, self.remaining(identity)))
        raise AcquisitionStopped('logical_request_attempt_budget')

    def cache_reference(self, identity):
        """Return a compact, ledger-bound reference to one completed projection."""
        records = [a for a in self.ledger['attempts']
                   if a['identity'] == identity and a['status'] == 'complete']
        if len(records) != 1:
            raise AcquisitionStopped('missing_unique_cached_response')
        record = records[0]
        raw = (self.directory / record['cache']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['cache_sha256']:
            raise AcquisitionStopped('cached_response_hash')
        return {'identity': identity, 'cache': record['cache'],
                'cache_sha256': record['cache_sha256'],
                'response_sha256': record['response_sha256']}


class ReplayBudget:
    """Read verified completed projections/ranges only; no network or new budget."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.ledger = json.loads((self.directory/'ledger.json').read_text())
        self.limits = self.ledger['limits']

    def remaining(self):
        return float('inf')

    def group(self, identity):
        if identity not in self.ledger['row_groups']:
            raise AcquisitionStopped('row_group_not_acquired')

    def fetch(self, identity, request, project, **kwargs):
        records = [a for a in self.ledger['attempts'] if a['identity']==identity and a['status']=='complete']
        if len(records) != 1:
            raise AcquisitionStopped('missing_complete_cached_response')
        raw = (self.directory/records[0]['cache']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != records[0]['cache_sha256']:
            raise AcquisitionStopped('cached_response_hash')
        return json.loads(raw)

    def cache_reference(self, identity):
        records = [a for a in self.ledger['attempts']
                   if a['identity'] == identity and a['status'] == 'complete']
        if len(records) != 1:
            raise AcquisitionStopped('missing_unique_cached_response')
        record = records[0]
        reference = {'identity': identity, 'cache': record['cache'],
                     'cache_sha256': record['cache_sha256'],
                     'response_sha256': record['response_sha256']}
        self.resolve_reference(reference)
        return reference

    def resolve_reference(self, reference):
        """Resolve a content-addressed projection without network or new budget."""
        if not isinstance(reference, dict) or set(reference) != {
                'identity', 'cache', 'cache_sha256', 'response_sha256'}:
            raise AcquisitionStopped('invalid_cache_reference')
        if not isinstance(reference['cache'], str) or Path(reference['cache']).name != reference['cache']:
            raise AcquisitionStopped('invalid_cache_reference')
        records = [a for a in self.ledger['attempts']
                   if a['identity'] == reference['identity'] and a['status'] == 'complete']
        if len(records) != 1:
            raise AcquisitionStopped('missing_complete_cached_response')
        record = records[0]
        if any(record.get(key) != reference[key]
               for key in ('cache', 'cache_sha256', 'response_sha256')):
            raise AcquisitionStopped('cache_reference_mismatch')
        raw = (self.directory / record['cache']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['cache_sha256']:
            raise AcquisitionStopped('cached_response_hash')
        return json.loads(raw)
