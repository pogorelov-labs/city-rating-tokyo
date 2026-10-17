import hashlib
import json
import threading
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest

from food_pilot import supplemental
from food_pilot.bounded import AcquisitionStopped, RequestRejected
from food_pilot.hotpepper import acquire_sites, page_projection


class Clock:
    def __init__(self, start=None):
        self.start = start or datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
        self.elapsed = 0.0
        self.utc_skew = 0.0

    def now(self):
        return self.start + timedelta(seconds=self.elapsed + self.utc_skew)

    def mono(self):
        return 1000.0 + self.elapsed

    def sleep(self, seconds):
        self.elapsed += seconds

    def advance_utc(self, seconds):
        self.utc_skew += seconds


class Response:
    status = 200

    def __init__(self, payload):
        self.payload = payload
        self.used = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        if self.used:
            return b''
        self.used = True
        return self.payload[:size]


def raw_page(*, total=0, start=1, returned=0, shops=None, returned_value=None):
    data = {'results_available': total, 'results_start': start,
            'results_returned': returned if returned_value is None else returned_value,
            'shop': [] if shops is None else shops}
    return json.dumps({'results': data}, separators=(',', ':')).encode()


def make_budget(tmp_path, monkeypatch, *, identity=None, opener=None, original=None):
    target = tmp_path / 'target-v4'
    phase = target / 'hp_development'
    phase.mkdir(parents=True)
    (phase / '.reader.lock').write_bytes(b'')
    output = tmp_path / 'supplemental-v1'
    clock = Clock()
    identity = identity or 'hp:sample:1:' + 'a' * 64
    journal = supplemental.Journal(output, resume=False, now=clock.now,
                                   monotonic=clock.mono)
    ledger = original or {'attempts': []}
    budget = supplemental.SupplementalBudget(
        output, target,
        {'attempts': 400, 'response_body_bytes': supplemental.HP_BODY_LIMIT,
         'successful_pages': 320, 'pages_per_station': 50,
         'response_bytes': supplemental.BODY_CAP, 'socket_seconds': 20,
         'minimum_request_interval_seconds': 0.6},
        journal, opener=opener, sleeper=clock.sleep, monotonic=clock.mono,
        original_ledger=ledger, diagnostic_identity=supplemental.EXCEPTIONAL_IDENTITY,
    )
    return target, output, clock, journal, budget


def test_special_page_one_has_lifetime_third_attempt_only_and_keeps_held_slot(tmp_path, monkeypatch):
    identity = 'hp:gun-hatake:1:' + 'c' * 64
    monkeypatch.setattr(supplemental, 'EXCEPTIONAL_IDENTITY', identity)
    calls = []

    def opener(request, timeout):
        calls.append(timeout)
        return Response(raw_page(total=0, start=0, returned=0, returned_value='0'))

    target, output, clock, journal, budget = make_budget(
        tmp_path, monkeypatch, identity=identity, opener=opener,
        original={'attempts': [{'identity': identity, 'status': 'failed',
                                'retry_disposition': 'terminal'}]})
    result = budget.fetch(identity, object(),
                          lambda raw, response: page_projection(raw, response,
                                                                allow_empty_start_zero=True),
                          kind='page')
    budget.admit_page(identity)
    assert result['start'] == 0
    assert calls and calls[0] <= 20
    assert budget.attempts_used() == 3
    assert budget.body_used() == 214 + len(raw_page(total=0, start=0, returned=0, returned_value='0'))
    assert budget.page_occupancy() == 2  # immutable diagnostic hold + separate new page
    assert budget.fetch(identity, object(), lambda *_: {}, kind='page') == result
    assert len(calls) == 1


def test_exceptional_third_attempt_never_retries_a_transient_failure(tmp_path, monkeypatch):
    identity = 'hp:gun-hatake:1:' + 'c' * 64
    monkeypatch.setattr(supplemental, 'EXCEPTIONAL_IDENTITY', identity)
    calls = []

    def opener(request, timeout):
        calls.append(request)
        raise urllib.error.HTTPError('https://invalid.example/', 503, 'ignored', {}, None)

    _target, _output, _clock, _journal, budget = make_budget(
        tmp_path, monkeypatch, identity=identity, opener=opener,
        original={'attempts': [{'identity': identity, 'status': 'failed',
                                'retry_disposition': 'terminal'}]})
    with pytest.raises(RequestRejected):
        budget.fetch(identity, object(), lambda *_: {}, kind='page')
    assert len(calls) == 1
    assert budget.attempts_used() == 3
    assert budget.body_used() == 214 + supplemental.BODY_CAP
    assert budget.page_occupancy() == 2  # held diagnostic + unresolved supplemental slot
    with pytest.raises(RequestRejected):
        budget.fetch(identity, object(), lambda *_: {}, kind='page')
    assert len(calls) == 1


def test_unknown_reserved_attempt_blocks_resume_and_is_not_a_cache(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + 'd' * 64
    _target, output, clock, journal, budget = make_budget(tmp_path, monkeypatch, identity=identity)
    calls = []

    def interrupted(request, timeout):
        calls.append(request)
        raise KeyboardInterrupt()

    budget.opener = interrupted
    with pytest.raises(KeyboardInterrupt):
        budget.fetch(identity, object(), lambda *_: {'ok': True}, kind='page')
    assert len(calls) == 1
    assert budget.body_used() == 214 + supplemental.BODY_CAP
    resumed = supplemental.Journal(output, resume=True, now=clock.now, monotonic=clock.mono)
    with pytest.raises(AcquisitionStopped, match='unknown_attempt'):
        supplemental.SupplementalBudget(output, _target, budget.limits, resumed,
                                        original_ledger={'attempts': []})


def test_only_durable_complete_cache_is_reused_without_another_request(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + 'e' * 64
    target, output, clock, journal, budget = make_budget(tmp_path, monkeypatch, identity=identity)
    payload = raw_page()
    calls = []

    def opener(request, timeout):
        calls.append(request)
        return Response(payload)

    budget.opener = opener
    project = lambda raw, _response: json.loads(raw)
    first = budget.fetch(identity, object(), project, kind='page')
    budget.admit_page(identity)
    resumed = supplemental.Journal(output, resume=True, now=clock.now, monotonic=clock.mono)
    no_network = supplemental.SupplementalBudget(output, target, budget.limits, resumed,
                                                 opener=lambda *_: pytest.fail('cached page performed I/O'),
                                                 sleeper=clock.sleep, monotonic=clock.mono,
                                                 original_ledger={'attempts': []},
                                                 diagnostic_identity=budget.exceptional_identity)
    assert no_network.fetch(identity, object(), project, kind='page') == first
    assert len(calls) == 1


def test_resumed_ordinary_transient_retry_keeps_two_second_backoff(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + '7' * 64
    target, output, clock, journal, _budget = make_budget(tmp_path, monkeypatch, identity=identity)
    journal.append('attempt_reserved', {'attempt_id': 'supp-0001', 'identity': identity,
                                        'reserved_body_bytes': supplemental.BODY_CAP})
    journal.append('attempt_settled', {'attempt_id': 'supp-0001', 'identity': identity,
                                       'status': 'failed', 'charged_body_bytes': supplemental.BODY_CAP,
                                       'retry_disposition': 'transient', 'error_type': 'TimeoutError'})
    clock.elapsed = 1.0
    resumed = supplemental.Journal(output, resume=True, now=clock.now, monotonic=clock.mono)
    calls = []
    budget = supplemental.SupplementalBudget(
        output, target, {'attempts': 400, 'response_body_bytes': supplemental.HP_BODY_LIMIT,
                         'successful_pages': 320, 'pages_per_station': 50,
                         'response_bytes': supplemental.BODY_CAP, 'socket_seconds': 20,
                         'minimum_request_interval_seconds': 0.6},
        resumed, opener=lambda *_a, **_k: (calls.append(clock.elapsed) or Response(b'{}')),
        sleeper=clock.sleep, monotonic=clock.mono, original_ledger={'attempts': []})
    budget.fetch(identity, object(), lambda raw, _response: json.loads(raw), kind='page')
    assert calls == [2.0]


def _sample32(monkeypatch):
    stations = []
    for index in range(32):
        slug = 'gun-hatake' if index == 0 else f'site-{index:02d}'
        stations.append({'slug': slug, 'split': 'development',
                         'lat': 35.0 + index * 0.001, 'lng': 139.0 + index * 0.001})
    identity = supplemental.request_identity(stations[0], 1)
    monkeypatch.setattr(supplemental, 'EXCEPTIONAL_IDENTITY', identity)
    return stations, identity


def _empty_page_for(start, *, gun=False):
    if gun:
        return raw_page(total=0, start=0, returned=0, returned_value='0')
    return raw_page(total=0, start=start, returned=0)


def test_actual_hp_caller_continues_full32_and_normal_pagination_under_one_journal(tmp_path, monkeypatch):
    stations, identity = _sample32(monkeypatch)
    target, output, clock, journal, budget = make_budget(
        tmp_path, monkeypatch, identity=identity,
        original={'attempts': [{'identity': identity, 'status': 'failed', 'retry_disposition': 'terminal'}]})
    rows_by_point = {(str(row['lat']), str(row['lng'])): row for row in stations}
    requests = []

    def opener(request, timeout):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        point = (query['lat'][0], query['lng'][0])
        station = rows_by_point[point]
        start = int(query['start'][0])
        requests.append((station['slug'], start, timeout))
        if station['slug'] == 'gun-hatake':
            return Response(_empty_page_for(start, gun=True))
        if station['slug'] == 'site-01':
            first_idx = 0 if start == 1 else 100
            shops = [{'id': f'venue-{idx}', 'lat': str(station['lat']),
                      'lng': str(station['lng']), 'name': 'x', 'genre': {'code': 'g'}}
                     for idx in range(first_idx, first_idx + (100 if start == 1 else 1))]
            return Response(raw_page(total=101, start=start, returned=len(shops), shops=shops))
        return Response(_empty_page_for(start))

    budget.opener = opener
    result = acquire_sites(stations, budget, 'fixture-key')
    budget.check_completion()
    assert result['status'] == 'complete'
    assert [row['slug'] for row in result['stations']] == [row['slug'] for row in stations]
    assert len(requests) == 33
    assert requests[0][:2] == ('gun-hatake', 1)
    assert ('site-01', 101, 20) in requests
    assert budget.attempts_used() == 35  # two historical + 33 actual calls
    assert budget.page_occupancy() == 34  # held diagnostic slot + 33 new pages incl. site-01 page 2
    assert len(journal.unresolved_attempts()) == 0
    assert journal.events[0]['event'] == 'run_started'


def test_lock_loss_fails_before_attempt_reservation(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + 'f' * 64
    target, output, clock, journal, budget = make_budget(tmp_path, monkeypatch, identity=identity)
    lock = supplemental.ExclusiveAccountingLock(target, journal)
    lock.__enter__()
    budget.lock = lock
    lock.__exit__()
    calls = []
    budget.opener = lambda *_: calls.append(1)
    with pytest.raises(AcquisitionStopped, match='lock_lost'):
        budget.fetch(identity, object(), lambda *_: {}, kind='page')
    assert not calls
    assert not any(event['event'] == 'attempt_reserved' for event in journal.events)


def test_resume_reloads_journal_after_waiting_for_writer_lock(tmp_path):
    target = tmp_path / 'target-v4'
    (target / 'hp_development').mkdir(parents=True)
    (target / 'hp_development' / '.reader.lock').write_bytes(b'')
    output = tmp_path / 'supplemental-v1'
    clock = Clock()
    writer = supplemental.Journal(output, resume=False, now=clock.now, monotonic=clock.mono)
    stale_reader = supplemental.Journal(output, resume=True, now=clock.now, monotonic=clock.mono)
    writer_lock = supplemental.ExclusiveAccountingLock(target, writer)
    writer_lock.__enter__()
    writer.lock_check = writer_lock.assert_held
    reader_waiting = threading.Event()
    reader_observed = []
    errors = []

    def resume_after_lock():
        reader = supplemental.Journal(output, resume=True, now=clock.now, monotonic=clock.mono)
        lock = supplemental.ExclusiveAccountingLock(target, reader)
        reader_waiting.set()
        try:
            with lock:
                reader.lock_check = lock.assert_held
                reader.reload_under_lock()
                reader_observed.extend(event for event in reader.events
                                       if event['event'] == 'attempt_reserved')
                with pytest.raises(AcquisitionStopped, match='unknown_attempt'):
                    supplemental.SupplementalBudget(output, target, {}, reader,
                                                   original_ledger={'attempts': []})
        except BaseException as exc:
            errors.append(exc)

    # This explicit stale snapshot models the waiter's pre-lock read.
    assert not any(event['event'] == 'attempt_reserved' for event in stale_reader.events)
    worker = threading.Thread(target=resume_after_lock)
    worker.start()
    assert reader_waiting.wait(1)
    writer.append('attempt_reserved', {'attempt_id': 'supp-0001',
                                       'identity': 'hp:site-01:1:' + 'a' * 64,
                                       'reserved_body_bytes': supplemental.BODY_CAP})
    writer_lock.__exit__()
    worker.join(2)
    assert not worker.is_alive()
    assert not errors
    assert len(reader_observed) == 1


def test_preflight_failure_consumes_activation_and_cannot_be_repaired_by_resume(tmp_path, monkeypatch):
    stations, _identity = _sample32(monkeypatch)
    target = tmp_path / 'target-v4'
    (target / 'hp_development').mkdir(parents=True)
    (target / 'hp_development' / '.reader.lock').write_bytes(b'')
    output = tmp_path / 'failed-supplemental'
    clock = Clock()
    protocol_hash, decision_hash = '1' * 64, '2' * 64
    evidence = {'hp_ledger': '3' * 64, 'hp_result': '4' * 64,
                'diagnostic_reservation': '5' * 64, 'diagnostic_outcome': '6' * 64}
    sample_hash = supplemental.sha256(supplemental.encoded(stations))
    query_hash = supplemental.sha256(supplemental.encoded(
        [{'slug': row['slug'], 'page1_identity': supplemental.request_identity(row, 1)} for row in stations]))
    snapshot = {'attempts_used': 2, 'attempt_limit': 400, 'body_bytes_used': 214,
                'body_byte_limit': supplemental.HP_BODY_LIMIT, 'admitted_pages': 0,
                'held_page_slots': 1, 'page_slot_limit': 320, 'hp_retained_bytes': 14_579,
                'hp_retained_limit': supplemental.HP_RETAINED_LIMIT,
                'global_retained_bytes': 41_468_376,
                'global_retained_limit': supplemental.GLOBAL_RETAINED_LIMIT}
    contract = {'protocol_sha256': protocol_hash, 'decision_sha256': decision_hash,
                'reviewed_git_head': 'incorrect-head',
                'original_evidence_sha256': evidence, 'development_sample_sha256': sample_hash,
                'query_fingerprint_sha256': query_hash,
                'development_order': [row['slug'] for row in stations], 'budget_snapshot': snapshot}
    manifest = {'core': {'stations': stations}, 'budgets': {'hp_development': {
        'attempts': 400, 'response_body_bytes': supplemental.HP_BODY_LIMIT,
        'successful_pages': 320, 'pages_per_station': 50, 'response_bytes': supplemental.BODY_CAP,
        'socket_seconds': 20, 'minimum_request_interval_seconds': 0.6}},
        'supplemental_hp_development': contract}
    monkeypatch.setattr(supplemental, 'check_manifest', lambda *_a, **_k: (manifest, 'a' * 64, 'b' * 64))
    monkeypatch.setattr(supplemental, '_verify_evidence', lambda *_: {
        'attempts': [{'identity': supplemental.EXCEPTIONAL_IDENTITY, 'status': 'failed'}],
        'status': 'incomplete', 'successful_pages': 0, 'charged_bytes': 107})
    roots = [str(target.resolve()), str(output.resolve())]
    owner = {'kind': 'owner_supplemental_hp_activation', 'activation_id': 'activation-1',
             'run_id': 'run-1', 'single_use': True, 'manifest_sha256': 'a' * 64,
             'git_head': 'reviewed-head', 'code_map_sha256': 'b' * 64,
             'protocol_sha256': protocol_hash, 'decision_sha256': decision_hash,
             'evidence_sha256': evidence, 'sample_sha256': sample_hash,
             'query_fingerprint_sha256': query_hash, 'target_root': roots[0],
             'supplemental_root': roots[1], 'accounted_roots': roots,
             'budget_snapshot': snapshot, 'allowed_operation': 'supplemental_hp_development',
             'created_at': (clock.start - timedelta(seconds=10)).isoformat(),
             'activation_expires_at': (clock.start + timedelta(hours=1)).isoformat()}
    owner_raw = json.dumps(owner, sort_keys=True, separators=(',', ':')).encode()
    owner_path = tmp_path / 'owner.json'
    owner_path.write_bytes(owner_raw)
    root_gate = {'kind': 'root_supplemental_hp_release', **{k: v for k, v in owner.items()
                 if k not in ('kind', 'created_at', 'activation_expires_at')},
                 'owner_activation_sha256': hashlib.sha256(owner_raw).hexdigest(),
                 'root_manifest_check': True, 'native_review_approved_head': 'reviewed-head',
                 'released_at': (clock.start - timedelta(seconds=5)).isoformat(),
                 'release_expires_at': (clock.start + timedelta(hours=1)).isoformat()}
    root_path = tmp_path / 'root.json'
    root_path.write_text(json.dumps(root_gate, sort_keys=True, separators=(',', ':')))
    calls = []
    with pytest.raises(AcquisitionStopped, match='manifest_git_head_mismatch'):
        supplemental.execute(manifest_path=tmp_path / 'manifest.json',
                             owner_activation_path=owner_path, root_release_path=root_path,
                             target_root=target, supplemental_root=output,
                             now=clock.now, monotonic=clock.mono,
                             opener=lambda *_a, **_k: calls.append(1),
                             head_provider=lambda: 'reviewed-head', api_key='fixture-only')
    events = [json.loads(line) for line in (output / 'journal.jsonl').read_text().splitlines()]
    assert [row['event'] for row in events][-1] == 'launch_terminal'
    assert any(row['event'] == 'activation_consumed' for row in events)
    contract['reviewed_git_head'] = 'reviewed-head'
    with pytest.raises(AcquisitionStopped, match='launch_terminal'):
        supplemental.execute(manifest_path=tmp_path / 'manifest.json',
                             owner_activation_path=owner_path, root_release_path=root_path,
                             target_root=target, supplemental_root=output, resume=True,
                             now=clock.now, monotonic=clock.mono,
                             opener=lambda *_a, **_k: calls.append(1),
                             head_provider=lambda: 'reviewed-head', api_key='fixture-only')
    assert not calls


def test_missing_lock_is_terminal_even_if_lock_appears_before_resume(tmp_path):
    target = tmp_path / 'target-v4'
    (target / 'hp_development').mkdir(parents=True)
    output = tmp_path / 'supplemental-v1'
    clock = Clock()
    calls = []
    with pytest.raises(AcquisitionStopped, match='shared_lock_missing'):
        supplemental.execute(manifest_path=tmp_path / 'manifest.json',
                             owner_activation_path=tmp_path / 'owner.json',
                             root_release_path=tmp_path / 'root.json',
                             target_root=target, supplemental_root=output,
                             now=clock.now, monotonic=clock.mono,
                             opener=lambda *_a, **_k: calls.append(1),
                             head_provider=lambda: 'head-test', api_key='fixture-only')
    initial = [json.loads(line) for line in (output / 'journal.jsonl').read_text().splitlines()]
    assert [row['event'] for row in initial[:3]] == [
        'run_started', 'activation_preflight_started', 'activation_consumed']
    assert initial[-1]['event'] == 'launch_terminal'

    (target / 'hp_development' / '.reader.lock').write_bytes(b'')
    with pytest.raises(AcquisitionStopped, match='launch_terminal'):
        supplemental.execute(manifest_path=tmp_path / 'manifest.json',
                             owner_activation_path=tmp_path / 'owner.json',
                             root_release_path=tmp_path / 'root.json',
                             target_root=target, supplemental_root=output, resume=True,
                             now=clock.now, monotonic=clock.mono,
                             opener=lambda *_a, **_k: calls.append(1),
                             head_provider=lambda: 'head-test', api_key='fixture-only')
    assert not calls


def test_initial_retention_preflight_failure_is_terminal(tmp_path, monkeypatch):
    target = tmp_path / 'target-v4'
    (target / 'hp_development').mkdir(parents=True)
    (target / 'hp_development' / '.reader.lock').write_bytes(b'')
    output = tmp_path / 'supplemental-v1'
    clock = Clock()
    monkeypatch.setattr(supplemental, 'HP_RETAINED_LIMIT', 1)
    with pytest.raises(AcquisitionStopped, match='hp_retained_budget'):
        supplemental.execute(manifest_path=tmp_path / 'manifest.json',
                             owner_activation_path=tmp_path / 'owner.json',
                             root_release_path=tmp_path / 'root.json',
                             target_root=target, supplemental_root=output,
                             now=clock.now, monotonic=clock.mono,
                             opener=lambda *_a, **_k: pytest.fail('preflight failure dispatched I/O'),
                             api_key='fixture-only')
    events = [json.loads(line) for line in (output / 'journal.jsonl').read_text().splitlines()]
    assert events[-1]['event'] == 'launch_terminal'
    monkeypatch.setattr(supplemental, 'HP_RETAINED_LIMIT', 10_000_000)
    with pytest.raises(AcquisitionStopped, match='launch_terminal'):
        supplemental.execute(manifest_path=tmp_path / 'manifest.json',
                             owner_activation_path=tmp_path / 'owner.json',
                             root_release_path=tmp_path / 'root.json',
                             target_root=target, supplemental_root=output, resume=True,
                             now=clock.now, monotonic=clock.mono,
                             opener=lambda *_a, **_k: pytest.fail('terminal launch resumed into I/O'),
                             api_key='fixture-only')


def test_finalized_partial_journal_is_terminal_before_caller_io(tmp_path):
    target = tmp_path / 'target-v4'
    (target / 'hp_development').mkdir(parents=True)
    (target / 'hp_development' / '.reader.lock').write_bytes(b'')
    output = tmp_path / 'finalized-partial'
    clock = Clock()
    journal = supplemental.Journal(output, resume=False, now=clock.now, monotonic=clock.mono)
    journal.append('run_finalized', {'status': 'incomplete', 'result': 'fixture.json',
                                    'result_sha256': 'f' * 64})
    calls = []
    with pytest.raises(AcquisitionStopped, match='already_finalized'):
        supplemental.execute(manifest_path=tmp_path / 'missing.json',
                             owner_activation_path=tmp_path / 'missing-owner.json',
                             root_release_path=tmp_path / 'missing-root.json',
                             target_root=target, supplemental_root=output, resume=True,
                             now=clock.now, monotonic=clock.mono,
                             opener=lambda *_a, **_k: calls.append(1), api_key='fixture-only')
    assert not calls


def test_body_and_page_caps_stop_before_socket_and_storage_counts_each_copy(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + 'a' * 64
    target, output, _clock, journal, budget = make_budget(tmp_path, monkeypatch, identity=identity)
    copies = output / 'copy-a.bin', output / 'copy-b.bin'
    copies[0].write_bytes(b'x' * 37)
    copies[1].write_bytes(b'x' * 37)
    assert budget.retained() >= 74
    calls = []
    budget.opener = lambda *_a, **_k: calls.append(1)
    monkeypatch.setattr(supplemental, 'HP_ATTEMPT_LIMIT', 2)
    with pytest.raises(AcquisitionStopped, match='attempt_budget'):
        budget.fetch(identity, object(), lambda *_: {}, kind='page')
    assert not calls


def test_retained_cap_reserves_full_response_before_socket(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + 'b' * 64
    target, output, _clock, _journal, budget = make_budget(tmp_path, monkeypatch, identity=identity)
    hp_used = supplemental.file_size(target / 'hp_development') + supplemental.file_size(output)
    global_used = supplemental.file_size(target) + supplemental.file_size(output)
    monkeypatch.setattr(supplemental, 'HP_RETAINED_LIMIT', hp_used + supplemental.BODY_CAP +
                        supplemental.CONTROL_RETENTION_RESERVE - 1)
    monkeypatch.setattr(supplemental, 'GLOBAL_RETAINED_LIMIT', global_used + supplemental.BODY_CAP +
                        supplemental.CONTROL_RETENTION_RESERVE - 1)
    calls = []
    budget.opener = lambda *_a, **_k: calls.append(1)
    with pytest.raises(AcquisitionStopped, match='retained_budget'):
        budget.fetch(identity, object(), lambda *_: {}, kind='page')
    assert not calls


def test_response_reader_never_consumes_beyond_reserved_body_cap(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + 'c' * 64
    _target, output, _clock, journal, budget = make_budget(tmp_path, monkeypatch, identity=identity)

    class OversizeStream:
        status = 200

        def __init__(self):
            self.total_read = 0
            self.remaining = supplemental.BODY_CAP + 1

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size=-1):
            requested = min(size, self.remaining)
            self.total_read += requested
            self.remaining -= requested
            return b'x' * requested

    stream = OversizeStream()
    budget.opener = lambda *_a, **_k: stream
    with pytest.raises(AcquisitionStopped, match='response_at_cap_eof_unproven'):
        budget.fetch(identity, object(), lambda *_: {}, kind='page')
    assert stream.total_read == supplemental.BODY_CAP
    assert stream.remaining == 1
    assert budget.body_used() == 214 + supplemental.BODY_CAP
    assert len(journal.unresolved_attempts()) == 1
    assert not list(output.glob('response-*'))


def test_truncated_journal_is_not_silently_resumed(tmp_path):
    clock = Clock()
    output = tmp_path / 'truncated'
    journal = supplemental.Journal(output, resume=False, now=clock.now, monotonic=clock.mono)
    with (output / 'journal.jsonl').open('ab') as stream:
        stream.write(b'{"partial":')
    with pytest.raises(AcquisitionStopped, match='journal_truncated'):
        supplemental.Journal(output, resume=True, now=clock.now, monotonic=clock.mono)


def test_clock_expiry_and_backward_checkpoint_fail_closed(tmp_path):
    clock = Clock()
    output = tmp_path / 'journal-root'
    journal = supplemental.Journal(output, resume=False, now=clock.now, monotonic=clock.mono)
    clock.elapsed = 1800
    with pytest.raises(AcquisitionStopped, match='wall_deadline'):
        journal.remaining()
    clock2 = Clock()
    output2 = tmp_path / 'journal-backward'
    first = supplemental.Journal(output2, resume=False, now=clock2.now, monotonic=clock2.mono)
    first.append('checkpoint')
    clock2.elapsed = -1
    with pytest.raises(AcquisitionStopped, match='clock_went_backwards'):
        supplemental.Journal(output2, resume=True, now=clock2.now, monotonic=clock2.mono)


def test_utc_deadline_is_enforced_even_when_monotonic_clock_has_time_left(tmp_path):
    clock = Clock()
    journal = supplemental.Journal(tmp_path / 'utc-deadline', resume=False,
                                   now=clock.now, monotonic=clock.mono)
    clock.advance_utc(1800)
    assert clock.elapsed == 0
    with pytest.raises(AcquisitionStopped, match='wall_deadline'):
        journal.remaining()
    with pytest.raises(AcquisitionStopped, match='wall_deadline'):
        journal.append('must_not_be_recorded')
    assert [event['event'] for event in journal.events] == ['run_started']


def test_response_completion_after_utc_deadline_stays_unknown(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + 'd' * 64
    target, output, clock, journal, budget = make_budget(tmp_path, monkeypatch, identity=identity)

    class CrossingResponse(Response):
        def read(self, size=-1):
            chunk = super().read(size)
            if chunk:
                clock.advance_utc(1800)
            return chunk

    payload = raw_page()
    budget.opener = lambda *_a, **_k: CrossingResponse(payload)
    with pytest.raises(AcquisitionStopped, match='wall_deadline'):
        budget.fetch(identity, object(), lambda raw, _response: json.loads(raw), kind='page')
    assert clock.elapsed == 0  # monotonic still has the full window
    assert journal.unresolved_attempts() == ['supp-0001']
    assert budget.body_used() == 214 + supplemental.BODY_CAP
    assert not list(output.glob('response-*'))


def test_page_admission_after_absolute_deadline_is_rejected(tmp_path, monkeypatch):
    identity = 'hp:other:1:' + 'e' * 64
    _target, _output, clock, journal, budget = make_budget(tmp_path, monkeypatch, identity=identity)
    budget.opener = lambda *_a, **_k: Response(raw_page())
    budget.fetch(identity, object(), lambda raw, _response: json.loads(raw), kind='page')
    clock.advance_utc(1800)
    with pytest.raises(AcquisitionStopped, match='wall_deadline'):
        budget.admit_page(identity)
    assert not any(event['event'] == 'page_slot_admitted' for event in journal.events)


def test_final_journal_fsync_crossing_deadline_adds_late_failure_not_success(tmp_path, monkeypatch):
    clock = Clock()
    output = tmp_path / 'late-finalize'
    journal = supplemental.Journal(output, resume=False,
                                   now=clock.now, monotonic=clock.mono)
    real_append = supplemental._append_fsynced

    def fsync_then_cross_deadline(path, raw, *, create=False):
        real_append(path, raw, create=create)
        if json.loads(raw)['event'] == 'run_finalized':
            # UTC crosses D while the monotonic clock remains unchanged.
            clock.advance_utc(1800)

    monkeypatch.setattr(supplemental, '_append_fsynced', fsync_then_cross_deadline)
    with pytest.raises(AcquisitionStopped, match='finalization_after_deadline'):
        journal.append('run_finalized', {'status': 'complete', 'result': 'fixture.json'})
    assert [event['event'] for event in journal.events][-2:] == [
        'run_finalized', 'run_late_failure']
    assert journal.events[-1]['status'] == 'incomplete'
    assert journal.events[-1]['reason'] == 'finalization_not_durable_by_deadline'
    persisted = [json.loads(line) for line in (output / 'journal.jsonl').read_text().splitlines()]
    assert persisted[-1]['event'] == 'run_late_failure'
    assert persisted[-2]['event'] == 'run_finalized'


def test_unsafe_output_root_is_rejected_before_any_protected_tree_write(tmp_path):
    target = tmp_path / 'target-v4'
    (target / 'hp_development').mkdir(parents=True)
    (target / 'hp_development' / 'original.bin').write_bytes(b'preserve-me')
    before = supplemental.tree_digest(target)
    invalid_output = target / 'hp_development' / 'supplemental'
    clock = Clock()
    with pytest.raises(AcquisitionStopped, match='root_not_sibling'):
        supplemental.execute(manifest_path=tmp_path / 'missing.json',
                             owner_activation_path=tmp_path / 'missing-owner.json',
                             root_release_path=tmp_path / 'missing-root.json',
                             target_root=target, supplemental_root=invalid_output,
                             now=clock.now, monotonic=clock.mono,
                             opener=lambda *_a, **_k: pytest.fail('unsafe path reached I/O'),
                             api_key='fixture-only')
    assert not invalid_output.exists()
    assert supplemental.tree_digest(target) == before


def test_execute_binds_activation_journal_lock_and_full_hp_caller(tmp_path, monkeypatch):
    stations, identity = _sample32(monkeypatch)
    target = tmp_path / 'target-v4'
    (target / 'hp_development').mkdir(parents=True)
    (target / 'hp_development' / '.reader.lock').write_bytes(b'')
    output = tmp_path / 'supplemental-v1'
    clock = Clock()
    protocol_hash = '1' * 64
    decision_hash = '2' * 64
    evidence = {'hp_ledger': '3' * 64, 'hp_result': '4' * 64,
                'diagnostic_reservation': '5' * 64, 'diagnostic_outcome': '6' * 64}
    sample_hash = supplemental.sha256(supplemental.encoded(stations))
    query_hash = supplemental.sha256(supplemental.encoded(
        [{'slug': row['slug'], 'page1_identity': supplemental.request_identity(row, 1)} for row in stations]))
    snapshot = {'attempts_used': 2, 'attempt_limit': 400, 'body_bytes_used': 214,
                'body_byte_limit': supplemental.HP_BODY_LIMIT, 'admitted_pages': 0,
                'held_page_slots': 1, 'page_slot_limit': 320, 'hp_retained_bytes': 14_579,
                'hp_retained_limit': supplemental.HP_RETAINED_LIMIT,
                'global_retained_bytes': 41_468_376,
                'global_retained_limit': supplemental.GLOBAL_RETAINED_LIMIT}
    contract = {'protocol_sha256': protocol_hash, 'decision_sha256': decision_hash,
                'reviewed_git_head': 'head-test',
                'original_evidence_sha256': evidence, 'development_sample_sha256': sample_hash,
                'query_fingerprint_sha256': query_hash,
                'development_order': [row['slug'] for row in stations], 'budget_snapshot': snapshot}
    manifest = {'core': {'stations': stations}, 'budgets': {'hp_development': {
        'attempts': 400, 'response_body_bytes': supplemental.HP_BODY_LIMIT,
        'successful_pages': 320, 'pages_per_station': 50, 'response_bytes': supplemental.BODY_CAP,
        'socket_seconds': 20, 'minimum_request_interval_seconds': 0.6}},
        'supplemental_hp_development': contract}
    manifest_hash, map_hash, head = 'a' * 64, 'b' * 64, 'head-test'
    monkeypatch.setattr(supplemental, 'check_manifest', lambda *_args, **_kw: (manifest, manifest_hash, map_hash))
    original = {'attempts': [{'identity': identity, 'status': 'failed', 'retry_disposition': 'terminal'}],
                'status': 'incomplete', 'successful_pages': 0, 'charged_bytes': 107}
    monkeypatch.setattr(supplemental, '_verify_evidence', lambda *_: original)
    roots = [str(target.resolve()), str(output.resolve())]
    owner = {'kind': 'owner_supplemental_hp_activation', 'activation_id': 'activation-1',
             'run_id': 'run-1', 'single_use': True, 'manifest_sha256': manifest_hash,
             'git_head': head, 'code_map_sha256': map_hash, 'protocol_sha256': protocol_hash,
             'decision_sha256': decision_hash, 'evidence_sha256': evidence,
             'sample_sha256': sample_hash, 'query_fingerprint_sha256': query_hash,
             'target_root': roots[0], 'supplemental_root': roots[1], 'accounted_roots': roots,
             'budget_snapshot': snapshot, 'allowed_operation': 'supplemental_hp_development',
             'created_at': (clock.start - timedelta(seconds=10)).isoformat(),
             'activation_expires_at': (clock.start + timedelta(hours=1)).isoformat()}
    owner_raw = json.dumps(owner, sort_keys=True, separators=(',', ':')).encode()
    owner_path = tmp_path / 'owner.json'
    owner_path.write_bytes(owner_raw)
    root_gate = {'kind': 'root_supplemental_hp_release', **{k: v for k, v in owner.items()
                  if k not in ('kind', 'created_at', 'activation_expires_at')},
                 'owner_activation_sha256': hashlib.sha256(owner_raw).hexdigest(),
                 'root_manifest_check': True, 'native_review_approved_head': head,
                 'released_at': (clock.start - timedelta(seconds=5)).isoformat(),
                 'release_expires_at': (clock.start + timedelta(hours=1)).isoformat()}
    root_path = tmp_path / 'root.json'
    root_path.write_text(json.dumps(root_gate, sort_keys=True, separators=(',', ':')))
    payload_map = {(str(row['lat']), str(row['lng'])): row for row in stations}
    calls = []

    def opener(request, timeout):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        station = payload_map[(query['lat'][0], query['lng'][0])]
        start = int(query['start'][0])
        calls.append((station['slug'], start))
        return Response(_empty_page_for(start, gun=station['slug'] == 'gun-hatake'))

    result = supplemental.execute(
        manifest_path=tmp_path / 'manifest.json', owner_activation_path=owner_path,
        root_release_path=root_path, target_root=target, supplemental_root=output,
        now=clock.now, monotonic=clock.mono, opener=opener, sleeper=clock.sleep,
        head_provider=lambda: head, api_key='fixture-only')
    journal = supplemental.Journal(output, resume=True, now=clock.now, monotonic=clock.mono)
    assert result['status'] == 'complete'
    assert len(calls) == 32
    assert journal.events[0]['event'] == 'run_started'
    assert journal.events[0]['t0_utc'] == clock.start.isoformat()
    assert sum(event['event'] == 'activation_consumed' for event in journal.events) == 1
    assert journal.events[-1]['event'] == 'run_finalized'
    assert not (target / 'hp_development' / 'ledger.json').exists()
    with pytest.raises(AcquisitionStopped, match='already_finalized'):
        supplemental.execute(
            manifest_path=tmp_path / 'manifest.json', owner_activation_path=owner_path,
            root_release_path=root_path, target_root=target, supplemental_root=output, resume=True,
            now=clock.now, monotonic=clock.mono, opener=lambda *_a, **_k: calls.append(('unexpected', 0)),
            sleeper=clock.sleep, head_provider=lambda: head, api_key='fixture-only')
    assert len(calls) == 32

