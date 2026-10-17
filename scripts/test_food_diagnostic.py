"""Offline-only tests for the disabled, one-request HP diagnostic command."""
import hashlib
import json
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import pytest

from food_pilot import diagnostic
from food_pilot import recovery
from food_pilot.acquire_osm import encoded
from food_pilot.bounded import AcquisitionStopped


HEAD = 'f' * 40
ORIGINAL_MANIFEST = diagnostic.ORIGINAL_MANIFEST_SHA256


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def map_sha(code_map):
    return sha((json.dumps(code_map, sort_keys=True, indent=2) + '\n').encode())


def make_case(tmp_path, monkeypatch, *, total_cap=2 * 1024**3):
    root = tmp_path / 'target-v4'
    phase = root / 'hp_development'
    phase.mkdir(parents=True)
    (phase / '.reader.lock').touch()
    monkeypatch.setattr(diagnostic, 'HP_PHASE_DIR', phase)
    monkeypatch.setattr(diagnostic, '_current_head', lambda: HEAD)

    budgets = {'attempts': 400, 'concurrency': 1, 'maximum_attempts_per_page': 2,
        'minimum_request_interval_seconds': .6, 'pages_per_station': 50,
        'response_body_bytes': 128 * 1024**2, 'response_bytes': 1024**2,
        'retained_bytes': 128 * 1024**2, 'socket_seconds': 20,
        'successful_pages': 320, 'wall_seconds': 1800}
    code_map = {str(p.relative_to(diagnostic.ROOT)): sha(p.read_bytes())
                for p in sorted((diagnostic.ROOT / 'scripts/food_pilot').glob('*.py'))}
    manifest = {'state': 'frozen', 'supersedes_manifest_sha256':
        'c67e0c723ffa9eca6fa79028a2bc4900129c630bed6a48c2ea58c87c3795881d',
        'supersession_reason': 'diagnostic-only code successor', 'code_sha256': code_map,
        'source_window': {'core_hp_complete_before': diagnostic.SOURCE_CUTOFF},
        'budgets': {'hp_development': budgets, 'total_retained_bytes': total_cap},
        'core': {'stations': [{'slug': 'gun-hatake', 'split': 'development',
                              'lat': 35.807382, 'lng': 139.207431}]}}
    manifest_path = tmp_path / 'manifest-v9.json'
    manifest_raw = encoded(manifest)
    manifest_path.write_bytes(manifest_raw)
    manifest_sha = sha(manifest_raw)
    code_sha = map_sha(code_map)
    manifest_contract = {key: value for key, value in manifest.items()
                         if key not in {'code_sha256', 'supersedes_manifest_sha256', 'supersession_reason'}}
    monkeypatch.setattr(recovery, 'V8_NONCODE_CONTRACT_SHA256', recovery.canonical_sha(manifest_contract))

    ledger = {'manifest_sha256': ORIGINAL_MANIFEST, 'status': 'incomplete',
        'started_at': diagnostic.ORIGINAL_PHASE_STARTED,
        'finished_at': diagnostic.ORIGINAL_PHASE_FINISHED,
        'limits': budgets, 'charged_bytes': 107, 'successful_pages': 0,
        'attempts': [{'identity': diagnostic.FIRST_REQUEST_IDENTITY, 'status': 'failed',
                      'retry_disposition': 'terminal', 'observed_bytes': 107,
                      'error_type': 'PaginationChanged'}]}
    ledger_raw = encoded(ledger)
    monkeypatch.setattr(diagnostic, 'ORIGINAL_LEDGER_SHA256', sha(ledger_raw))
    (phase / 'ledger.json').write_bytes(ledger_raw)
    result = {'phase': 'hp_development', 'manifest_sha256': ORIGINAL_MANIFEST,
        'result': {'status': 'incomplete', 'stations': [{'slug': 'gun-hatake',
                    'status': 'truncated', 'count_800m': None}]}}
    result_raw = encoded(result)
    monkeypatch.setattr(diagnostic, 'ORIGINAL_RESULT_SHA256', sha(result_raw))
    (phase / f'result-{sha(result_raw)}.json').write_bytes(result_raw)

    owner = {'type': diagnostic.OWNER_EXCEPTION_TYPE,
        'decision': 'allow_one_hp_diagnostic_only', 'owner_exception_id': 'synthetic-owner-only',
        'recorded_at_utc': '2026-10-17T10:00:00Z', 'manifest_sha256': manifest_sha,
        'code_head_sha256': HEAD, 'code_map_sha256': code_sha,
        'original_ledger_sha256': sha(ledger_raw), 'original_result_sha256': sha(result_raw),
        'request_identity': diagnostic.FIRST_REQUEST_IDENTITY,
        'query_sha256': diagnostic.FIRST_QUERY_SHA256,
        'source_cutoff_utc': diagnostic.SOURCE_CUTOFF, 'max_requests': 1,
        'max_body_bytes': diagnostic.MAX_BODY_BYTES,
        'socket_timeout_seconds': diagnostic.SOCKET_TIMEOUT_SECONDS,
        'hard_window_seconds': diagnostic.HARD_WINDOW_SECONDS,
        'max_receipt_bytes': diagnostic.MAX_RECEIPT_BYTES,
        'allow_retry': False, 'allow_redirect': False, 'pilot_count_permitted': False,
        'phase_completion_permitted': False, 'next_request_permitted': False}
    owner_path = phase / 'owner-diagnostic-exception.json'
    owner_raw = encoded(owner); owner_path.write_bytes(owner_raw)
    gate = {'type': diagnostic.ROOT_GATE_TYPE, 'root_release_id': 'synthetic-root-only',
        'released_at_utc': '2026-10-17T10:01:00Z',
        'root_session': 'city-rating-1', 'delivery_handle': 'synthetic-no-release',
        'root_manifest_check': True, 'diagnostic_only': True,
        'allowed_operation': 'one_hp_diagnostic_request', 'manifest_sha256': manifest_sha,
        'code_head_sha256': HEAD, 'code_map_sha256': code_sha,
        'native_review_approved_head': HEAD, 'owner_exception_sha256': sha(owner_raw),
        'ci_all_green': True, 'ci_run_id': 'synthetic-only', 'max_requests': 1,
        'max_body_bytes': diagnostic.MAX_BODY_BYTES, 'max_receipt_bytes': diagnostic.MAX_RECEIPT_BYTES,
        'socket_timeout_seconds': diagnostic.SOCKET_TIMEOUT_SECONDS,
        'hard_window_seconds': diagnostic.HARD_WINDOW_SECONDS,
        'allow_retry': False, 'allow_redirect': False,
        'source_cutoff_utc': diagnostic.SOURCE_CUTOFF,
        'metadata_requests_permitted': False, 'phase_completion_permitted': False,
        'pilot_count_permitted': False, 'next_request_permitted': False}
    root_path = phase / 'root-diagnostic-gate.json'
    root_path.write_bytes(encoded(gate))
    return {'phase': phase, 'target_root': root, 'manifest': manifest_path,
            'owner': owner_path, 'gate': root_path, 'ledger': ledger_raw,
            'result': result_raw, 'manifest_sha': manifest_sha}


class Response:
    status = 200

    def __init__(self, body):
        self.body = body
        self.offset = 0
        self.read_bytes = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size):
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        self.read_bytes += len(chunk)
        return chunk


def valid_empty_page():
    return json.dumps({'results': {'results_available': 0, 'results_start': 1,
        'results_returned': 0, 'shop': []}}).encode()


def run(case, opener, **kwargs):
    return diagnostic.run_diagnostic(case['manifest'], case['owner'], case['gate'],
                                     api_key='synthetic-test-key', opener=opener, **kwargs)


def test_disabled_command_requires_fresh_owner_and_root_before_reservation(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    case['owner'].unlink()
    calls = []
    with pytest.raises(AcquisitionStopped, match='diagnostic_gate_file_missing_or_symlinked'):
        run(case, lambda *_a, **_kw: calls.append('called'))
    assert calls == []
    assert not (case['phase'] / diagnostic.RESERVATION_NAME).exists()


def test_v6_or_v8_approval_cannot_activate_v9_diagnostic(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    owner = json.loads(case['owner'].read_text())
    owner['type'] = 'crtky194-owner-cache-only-exception'
    owner['decision'] = 'allow_cache_only_metadata_downstream_admission'
    owner_raw = encoded(owner)
    case['owner'].write_bytes(owner_raw)
    gate = json.loads(case['gate'].read_text())
    gate['owner_exception_sha256'] = sha(owner_raw)
    case['gate'].write_bytes(encoded(gate))
    calls = []
    with pytest.raises(AcquisitionStopped, match='diagnostic_owner_exception_mismatch'):
        run(case, lambda *_a, **_kw: calls.append('called'))
    assert calls == []
    assert not (case['phase'] / diagnostic.RESERVATION_NAME).exists()


def test_old_root_approval_for_v8_cannot_activate_v9_diagnostic(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    gate = json.loads(case['gate'].read_text())
    gate['manifest_sha256'] = 'c67e0c723ffa9eca6fa79028a2bc4900129c630bed6a48c2ea58c87c3795881d'
    case['gate'].write_bytes(encoded(gate))
    calls = []
    with pytest.raises(AcquisitionStopped, match='diagnostic_root_gate_mismatch'):
        run(case, lambda *_a, **_kw: calls.append('called'))
    assert calls == []
    assert not (case['phase'] / diagnostic.RESERVATION_NAME).exists()


@pytest.mark.parametrize('field', ['allow_retry', 'allow_redirect', 'pilot_count_permitted',
                                  'phase_completion_permitted', 'next_request_permitted'])
def test_root_gate_cannot_widen_diagnostic_permissions(tmp_path, monkeypatch, field):
    case = make_case(tmp_path, monkeypatch)
    gate = json.loads(case['gate'].read_text())
    gate[field] = True
    case['gate'].write_bytes(encoded(gate))
    calls = []
    with pytest.raises(AcquisitionStopped, match='diagnostic_root_gate_mismatch'):
        run(case, lambda *_a, **_kw: calls.append('called'))
    assert calls == []
    assert not (case['phase'] / diagnostic.RESERVATION_NAME).exists()


def test_exact_request_valid_empty_page_writes_only_bounded_diagnostic(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    body = valid_empty_page()
    response = Response(body)
    captured = {}

    def opener(request, *, timeout):
        captured['url'] = request.full_url
        captured['timeout'] = timeout
        return response

    result = run(case, opener)
    assert captured['timeout'] == 20
    assert 'key=synthetic-test-key' in captured['url']  # request memory only
    assert 'start=1' in captured['url']
    assert result['state'] == 'diagnostic_only'
    assert result['body_bytes_charged'] == len(body)
    assert response.read_bytes == len(body)

    reservation_raw = (case['phase'] / diagnostic.RESERVATION_NAME).read_bytes()
    outcome_raw = (case['phase'] / diagnostic.OUTCOME_NAME).read_bytes()
    reservation, outcome = json.loads(reservation_raw), json.loads(outcome_raw)
    assert reservation['body_bytes_reserved'] == diagnostic.MAX_BODY_BYTES
    assert reservation['request_attempts_reserved'] == 1
    assert reservation['phase_attempts_used_before'] == 1
    assert reservation['phase_attempt_cap'] == 400
    assert reservation['same_page_attempts_used_before'] == 1
    assert reservation['same_page_attempt_cap'] == 2
    assert reservation['response_body_bytes_charged_before'] == 107
    assert reservation['response_body_bytes_cap'] == 128 * 1024**2
    assert reservation['original_phase_deadline_utc'] == diagnostic.ORIGINAL_PHASE_DEADLINE
    assert outcome['diagnostic_status'] == 'response_contract_valid'
    assert outcome['eof_observed'] is True
    assert outcome['body_bytes_charged'] == len(body)  # only complete EOF refunds reservation remainder
    assert outcome['pilot_count_created'] is False and outcome['hp_zero_confirmed'] is False
    assert 'count_800m' not in outcome and 'venues' not in outcome
    assert len(reservation_raw) + len(outcome_raw) <= diagnostic.MAX_RECEIPT_BYTES
    for raw in (reservation_raw, outcome_raw):
        assert b'synthetic-test-key' not in raw
        assert b'webservice.recruit.co.jp' not in raw
        assert body not in raw
    assert (case['phase'] / 'ledger.json').read_bytes() == case['ledger']
    assert next(case['phase'].glob('result-*.json')).read_bytes() == case['result']


def test_http_200_provider_error_is_structural_only(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    body = json.dumps({'results': {
        'error': [{'code': '2000', 'message': 'private provider text'}],
        'results_available': 0, 'results_start': 1, 'results_returned': 0, 'shop': []}}).encode()
    response = Response(body)
    result = run(case, lambda *_a, **_kw: response)
    outcome_raw = (case['phase'] / diagnostic.OUTCOME_NAME).read_bytes()
    outcome = json.loads(outcome_raw)
    assert result['diagnostic_status'] == 'parser_rejected'
    assert outcome['diagnostic']['http_status'] == 200
    assert outcome['diagnostic']['provider_error_present'] is True
    assert outcome['diagnostic']['provider_error_codes'] == ['2000']
    assert 'private provider text' not in outcome_raw.decode()
    assert body not in outcome_raw
    assert outcome['pilot_count_created'] is False


def test_redirect_is_reported_without_following_or_leaking_location(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    calls = []

    def opener(*_args, **_kwargs):
        calls.append(1)
        raise AcquisitionStopped('redirect_rejected')

    result = run(case, opener)
    outcome_raw = (case['phase'] / diagnostic.OUTCOME_NAME).read_bytes()
    outcome = json.loads(outcome_raw)
    assert calls == [1]
    assert result['diagnostic_status'] == 'http_error'
    assert outcome['diagnostic'] == {'parser_reason': 'redirect_rejected'}
    assert b'Location' not in outcome_raw and b'key=' not in outcome_raw


def test_timeout_keeps_full_reservation_and_cannot_be_retried(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    calls = []

    def opener(*_args, **_kwargs):
        calls.append(1)
        raise urllib.error.URLError('must never persist this message')

    outcome = run(case, opener)
    assert outcome['diagnostic_status'] == 'transport_unknown'
    assert outcome['body_bytes_charged'] == diagnostic.MAX_BODY_BYTES
    receipt = json.loads((case['phase'] / diagnostic.OUTCOME_NAME).read_text())
    assert receipt['eof_observed'] is False
    assert 'must never persist' not in (case['phase'] / diagnostic.OUTCOME_NAME).read_text()
    with pytest.raises(AcquisitionStopped, match='diagnostic_already_attempted'):
        run(case, opener)
    assert calls == [1]


def test_response_limit_never_reads_over_one_mib_and_charges_full_reservation(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    response = Response(b'x' * (diagnostic.MAX_BODY_BYTES + 10))
    result = run(case, lambda *_a, **_kw: response)
    assert response.read_bytes == diagnostic.MAX_BODY_BYTES
    assert result['diagnostic_status'] == 'response_limit_or_eof_unknown'
    assert result['body_bytes_charged'] == diagnostic.MAX_BODY_BYTES
    receipt = json.loads((case['phase'] / diagnostic.OUTCOME_NAME).read_text())
    assert receipt['observed_body_bytes'] == diagnostic.MAX_BODY_BYTES
    assert receipt['eof_observed'] is False


def test_source_cutoff_blocks_before_reservation_or_request(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    monkeypatch.setattr(diagnostic, '_now', lambda: datetime(2026, 10, 22, tzinfo=timezone.utc))
    calls = []
    with pytest.raises(AcquisitionStopped, match='diagnostic_source_cutoff'):
        run(case, lambda *_a, **_kw: calls.append(1))
    assert calls == []
    assert not (case['phase'] / diagnostic.RESERVATION_NAME).exists()


def test_source_cutoff_crossed_during_read_keeps_full_charge_and_incomplete_state(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    now = {'value': datetime(2026, 10, 21, 23, 59, 59, tzinfo=timezone.utc)}
    monkeypatch.setattr(diagnostic, '_now', lambda: now['value'])

    class CrossingResponse(Response):
        def read(self, size):
            chunk = super().read(size)
            now['value'] = datetime(2026, 10, 22, tzinfo=timezone.utc)
            return chunk

    result = run(case, lambda *_a, **_kw: CrossingResponse(valid_empty_page()))
    reservation = json.loads((case['phase'] / diagnostic.RESERVATION_NAME).read_text())
    outcome = json.loads((case['phase'] / diagnostic.OUTCOME_NAME).read_text())
    assert reservation['original_phase_status_remains'] == 'incomplete'
    assert outcome['diagnostic_status'] == 'diagnostic_window_or_cutoff_rejected'
    assert outcome['eof_observed'] is False
    assert outcome['body_bytes_charged'] == diagnostic.MAX_BODY_BYTES
    assert result['body_bytes_charged'] == diagnostic.MAX_BODY_BYTES
    assert (case['phase'] / 'ledger.json').read_bytes() == case['ledger']
    assert next(case['phase'].glob('result-*.json')).read_bytes() == case['result']


def test_global_retention_reservation_fails_before_io(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    tree_bytes = diagnostic._tree_bytes
    def over_global_cap(path):
        if Path(path) == case['target_root']:
            return 2 * 1024**3 - diagnostic.MAX_RECEIPT_BYTES + 1
        return tree_bytes(path)
    monkeypatch.setattr(diagnostic, '_tree_bytes', over_global_cap)
    calls = []
    with pytest.raises(AcquisitionStopped, match='diagnostic_global_retention_budget'):
        run(case, lambda *_a, **_kw: calls.append(1))
    assert calls == []
    assert not (case['phase'] / diagnostic.RESERVATION_NAME).exists()


def test_phase_retention_reservation_fails_before_io(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    tree_bytes = diagnostic._tree_bytes

    def over_phase_cap(path):
        if Path(path) == case['phase']:
            return 128 * 1024**2 - diagnostic.MAX_RECEIPT_BYTES + 1
        return tree_bytes(path)

    monkeypatch.setattr(diagnostic, '_tree_bytes', over_phase_cap)
    calls = []
    with pytest.raises(AcquisitionStopped, match='diagnostic_phase_retention_budget'):
        run(case, lambda *_a, **_kw: calls.append(1))
    assert calls == []
    assert not (case['phase'] / diagnostic.RESERVATION_NAME).exists()


def test_original_response_budget_reservation_fails_closed_before_io(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    original_inputs = diagnostic._original_inputs

    def near_budget(*args):
        ledger, ledger_raw, result_raw = original_inputs(*args)
        ledger = dict(ledger)
        ledger['charged_bytes'] = ledger['limits']['response_body_bytes'] - diagnostic.MAX_BODY_BYTES + 1
        return ledger, ledger_raw, result_raw

    monkeypatch.setattr(diagnostic, '_original_inputs', near_budget)
    calls = []
    with pytest.raises(AcquisitionStopped, match='diagnostic_original_budget_exhausted'):
        run(case, lambda *_a, **_kw: calls.append(1))
    assert calls == []
    assert not (case['phase'] / diagnostic.RESERVATION_NAME).exists()


def test_expired_hard_window_after_reservation_makes_no_request(tmp_path, monkeypatch):
    case = make_case(tmp_path, monkeypatch)
    ticks = iter([0.0, 0.0, 0.0, 0.0, 61.0, 61.0, 61.0, 61.0])
    monkeypatch.setattr(diagnostic.time, 'monotonic', lambda: next(ticks))
    calls = []
    result = run(case, lambda *_a, **_kw: calls.append(1))
    assert calls == []
    assert result['body_bytes_charged'] == diagnostic.MAX_BODY_BYTES
    assert result['diagnostic_status'] == 'diagnostic_window_expired'
