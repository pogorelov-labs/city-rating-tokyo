"""Durable, single-reader request budgets for internal shadow acquisition.

No credentials, URLs, response headers or exception messages enter the ledger.
Callers supply validated requests and project safe response fields before caching.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
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
    def __init__(self, error_type):
        super().__init__('request_or_contract_rejected')
        self.error_type = error_type


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcquisitionStopped('redirect_rejected')


class Budget:
    def __init__(self, directory, limits, manifest_hash, *, resume=False, opener=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.limits = limits
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
            elapsed = (now - datetime.fromisoformat(self.ledger['started_at'])).total_seconds()
            if elapsed < 0:
                self.close()
                raise AcquisitionStopped('clock_precedes_original_start')
            for attempt in self.ledger['attempts']:
                if attempt['status'] == 'pending':
                    attempt['status'] = 'interrupted'
        else:
            self.ledger = {'manifest_sha256': manifest_hash, 'limits': limits,
                           'started_at': now.isoformat(), 'attempts': [], 'charged_bytes': 0,
                           'successful_pages': 0, 'row_groups': [], 'status': 'in_progress'}
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

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AcquisitionStopped('original_wall_deadline')
        return remaining

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
        self.remaining()
        previous = [a for a in self.ledger['attempts'] if a['identity'] == identity]
        complete = [a for a in previous if a['status'] == 'complete']
        if complete:
            if len(complete) != 1:
                raise AcquisitionStopped('ambiguous_cached_receipt')
            raw = (self.directory / complete[0]['cache']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != complete[0]['cache_sha256']:
                raise AcquisitionStopped('cached_response_hash')
            return json.loads(raw)
        maximum = self.limits.get('maximum_attempts_per_page', self.limits.get('maximum_attempts_per_range', 2))
        while len(previous) < maximum:
            self.remaining()
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
                    time.sleep(min(wait, self.remaining()))
            attempt = {'identity': identity, 'status': 'pending', 'reserved_bytes': reservation,
                       'at': datetime.now(timezone.utc).isoformat(), 'accounting': 'conservative_reservation'}
            self.ledger['attempts'].append(attempt)
            previous.append(attempt)
            self.ledger['charged_bytes'] += reservation
            self.persist()  # durable before opening a socket
            received, eof, retry = 0, False, False
            try:
                timeout = min(self.limits['socket_seconds'], self.remaining())
                self.last_request = time.monotonic()
                with self.opener(request, timeout=timeout) as response:
                    chunks = []
                    while True:
                        self.remaining()
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
                    self.remaining()
                cached = encoded(result)
                if self.retained() + len(cached) > self.limits['retained_bytes']:
                    raise AcquisitionStopped('retained_byte_budget')
                cache = f'response-{len(self.ledger["attempts"]):05d}.json'
                with (self.directory / cache).open('xb') as stream:
                    stream.write(cached)
                    stream.flush()
                    import os
                    os.fsync(stream.fileno())
                self.remaining()
                attempt.update(status='complete', cache=cache,
                               cache_sha256=hashlib.sha256(cached).hexdigest(),
                               response_sha256=hashlib.sha256(raw).hexdigest())
                if kind == 'page':
                    self.ledger['successful_pages'] += 1
                # Successful exact-range projection establishes complete bytes.
                eof = True
            except urllib.error.HTTPError as exc:
                attempt.update(status='failed', http_status=exc.code, error_type='HTTPError')
                retry = 500 <= exc.code <= 599
            except (urllib.error.URLError, TimeoutError) as exc:
                attempt.update(status='failed', error_type=type(exc).__name__)
                retry = True
            except Exception as exc:
                attempt.update(status='failed', error_type=type(exc).__name__)
            except BaseException as exc:
                attempt.update(status='interrupted', error_type=type(exc).__name__)
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
                raise RequestRejected(attempt.get('error_type', 'UnknownRequestError'))
            if len(previous) < maximum:
                time.sleep(min(2, self.remaining()))
        raise AcquisitionStopped('logical_request_attempt_budget')


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
