"""Read-only, non-authorizing handoff for the completed V18 HP development run."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .bounded import AcquisitionStopped

V18_HEAD = '4bb8f181b029019a9ce412627fb8655b677817f0'
V18_MANIFEST_SHA256 = '0f12301839516763eacfc9749f3127bf2239a68b3cda42e412bbc78f47b5a970'
V18_CODE_MAP_SHA256 = '1fb1b7cd991f649fca58532f84d2ccda8efc720a5365a2d3f0a66793ac8dbb6d'
EXPECTED_HANDOFF_CONTRACT_SHA256 = '9f78d9381cbafce7aac3de0fec0303dde0cda82474d1a1278b66eea4ff182564'
SOURCE_CUTOFF = '2026-10-22T00:00:00Z'
TARGET_V4_TREE_SHA256 = '49df1e59182bfeb5a3c6eb25f6d53676a96b0cb93c312ff3ccf3d698c5c0af36'
PRE_RECEIPT_TREE_SHA256 = '68c125c986f388e56b2a23be3f76867ad41bf0c52cc45469c250f49db112d012'
EXPECTED_RUN_ID = 'bf9f4f84-1775-45e4-9733-cc46dffd763c'
EXPECTED_ACTIVATION_ID = 'a71a59c4-8a77-4147-91bf-9b8732ac92f1'


def canonical_sha(value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc(value):
    if not isinstance(value, str):
        raise AcquisitionStopped('historical_handoff_timestamp_invalid')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise AcquisitionStopped('historical_handoff_timestamp_invalid') from None
    if parsed.tzinfo is None:
        raise AcquisitionStopped('historical_handoff_timestamp_invalid')
    return parsed.astimezone(timezone.utc)


def informational_zero_windows(stations, development_order, source_cutoff=SOURCE_CUTOFF):
    """Derive timestamps only; these core rows are not hp_confirmation candidates."""
    cutoff = utc(source_cutoff)
    by_slug = {row.get('slug'): row for row in stations if isinstance(row, dict)}
    windows = []
    for slug in development_order:
        row = by_slug.get(slug)
        if row is None:
            raise AcquisitionStopped('historical_handoff_station_missing')
        if row.get('status') not in ('complete_provider_zero', 'complete_800m_zero'):
            continue
        first = utc(row.get('finished_at'))
        start, end = first + timedelta(hours=24), first + timedelta(hours=72)
        if end > cutoff:
            raise AcquisitionStopped('historical_handoff_confirmation_window_after_cutoff')
        windows.append({
            'slug': slug,
            'first_status': row['status'],
            'first_complete_at': first.isoformat(),
            'eligible_from': start.isoformat(),
            'eligible_until': end.isoformat(),
            'phase_eligible_under_current_policy': False,
            'policy_reason': 'core_development_not_manifest_matching_hp_prescreen_challenge_order',
        })
    return windows


def _read_json(path, error):
    try:
        raw = Path(path).read_bytes()
        return json.loads(raw), raw
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise AcquisitionStopped(error) from None


def _safe_child(root, relative, error, *, directory=False):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise AcquisitionStopped(error)
    root = Path(root).resolve()
    candidate = root / relative
    if candidate.is_symlink():
        raise AcquisitionStopped(error)
    resolved = candidate.resolve()
    if (not resolved.is_relative_to(root)
            or (not resolved.is_dir() if directory else not resolved.is_file())):
        raise AcquisitionStopped(error)
    return resolved


def _verify_journal(run_dir, *, t0, deadline, finished):
    """Verify the append-only journal without constructing a writable Journal."""
    from .supplemental import canonical

    journal_raw = (Path(run_dir) / 'journal.jsonl').read_bytes()
    if journal_raw and not journal_raw.endswith(b'\n'):
        raise AcquisitionStopped('historical_handoff_journal_truncated')
    events = []
    previous = '0' * 64
    for index, line in enumerate(journal_raw.splitlines()):
        try:
            row = json.loads(line)
            digest = row.pop('event_sha256')
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            raise AcquisitionStopped('historical_handoff_journal_invalid') from None
        if (row.get('seq') != index or row.get('previous_sha256') != previous
                or hashlib.sha256(canonical(row)).hexdigest() != digest):
            raise AcquisitionStopped('historical_handoff_journal_chain_invalid')
        previous = digest
        events.append({**row, 'event_sha256': digest})
    if not events:
        raise AcquisitionStopped('historical_handoff_journal_empty')
    first = events[0]
    if first.get('event') != 'run_started' or utc(first.get('t0_utc')) != t0:
        raise AcquisitionStopped('historical_handoff_journal_window_mismatch')
    started_mono = first.get('monotonic_anchor')
    if type(started_mono) not in (int, float):
        raise AcquisitionStopped('historical_handoff_journal_clock_invalid')
    prev_utc, prev_mono = None, None
    for event in events:
        stamp = utc(event.get('utc'))
        mono = event.get('monotonic')
        if (type(mono) not in (int, float) or mono < started_mono
                or mono >= started_mono + 1800 or stamp < t0 or stamp >= deadline
                or stamp >= utc(SOURCE_CUTOFF)
                or (prev_utc is not None and stamp < prev_utc)
                or (prev_mono is not None and mono < prev_mono)):
            raise AcquisitionStopped('historical_handoff_journal_clock_invalid')
        prev_utc, prev_mono = stamp, mono
    claim_state = first.get('activation_claim_state')
    claim_events = [event for event in events
                    if event.get('event') in ('activation_preflight_started',
                                              'activation_consumed',
                                              'activation_claim_ready')]
    if claim_state != 'pending' or [event.get('event') for event in claim_events] != [
            'activation_preflight_started', 'activation_consumed', 'activation_claim_ready']:
        raise AcquisitionStopped('historical_handoff_activation_claim_invalid')
    preflight, consumed, ready = claim_events
    claim_keys = ('activation_id', 'run_id', 'owner_activation_sha256', 'root_release_sha256')
    if (any(ready.get(key) != consumed.get(key) for key in claim_keys)
            or any(preflight.get(key) != consumed.get(key) for key in claim_keys[2:])):
        raise AcquisitionStopped('historical_handoff_activation_claim_invalid')
    if events[-1].get('event') != 'run_finalized':
        raise AcquisitionStopped('historical_handoff_not_finalized')
    if events[-1].get('status') != 'complete' or utc(events[-1].get('utc')) != finished:
        raise AcquisitionStopped('historical_handoff_finalization_mismatch')
    if sum(event.get('event') == 'run_finalized' for event in events) != 1:
        raise AcquisitionStopped('historical_handoff_finalization_mismatch')
    return events, journal_raw


def verify_historical_supplemental_run(manifest, *, artifact_root):
    """Validate the completed run as historical development input, never as a gate."""
    handoff = manifest.get('historical_supplemental_hp_run')
    if not isinstance(handoff, dict) or canonical_sha(handoff) != EXPECTED_HANDOFF_CONTRACT_SHA256:
        raise AcquisitionStopped('historical_handoff_contract_mismatch')
    if (handoff.get('state') != 'historical_development_evidence_only'
            or handoff.get('phase_execution_authorized') is not False
            or handoff.get('confirmation_phase_eligible') is not False
            or handoff.get('source_manifest_sha256') != V18_MANIFEST_SHA256
            or handoff.get('source_git_head') != V18_HEAD
            or handoff.get('run_id') != EXPECTED_RUN_ID
            or handoff.get('activation_id') != EXPECTED_ACTIVATION_ID):
        raise AcquisitionStopped('historical_handoff_scope_mismatch')

    root = Path(artifact_root).resolve()
    run_dir = _safe_child(root, handoff.get('run_directory'), 'historical_handoff_run_path', directory=True)
    auth_dir = _safe_child(root, handoff.get('authorization_directory'), 'historical_handoff_auth_path', directory=True)
    owner_path = _safe_child(auth_dir, handoff.get('owner_file'), 'historical_handoff_owner_path')
    root_path = _safe_child(auth_dir, handoff.get('root_file'), 'historical_handoff_root_path')
    journal_path = _safe_child(run_dir, handoff.get('journal_file'), 'historical_handoff_journal_path')
    result_path = _safe_child(run_dir, handoff.get('result_file'), 'historical_handoff_result_path')

    owner, owner_raw = _read_json(owner_path, 'historical_handoff_owner_invalid')
    root_release, root_raw = _read_json(root_path, 'historical_handoff_root_invalid')
    result, result_raw = _read_json(result_path, 'historical_handoff_result_invalid')
    if not all(isinstance(record, dict) for record in (owner, root_release, result)):
        raise AcquisitionStopped('historical_handoff_receipt_shape_invalid')
    if (file_sha(journal_path) != handoff.get('journal_sha256')
            or hashlib.sha256(result_raw).hexdigest() != handoff.get('result_sha256')
            or hashlib.sha256(owner_raw).hexdigest() != handoff.get('owner_activation_sha256')
            or hashlib.sha256(root_raw).hexdigest() != handoff.get('root_release_sha256')):
        raise AcquisitionStopped('historical_handoff_file_hash_mismatch')

    from .supplemental import development_fingerprints

    sample_sha, query_sha, development = development_fingerprints(manifest)
    contract = manifest.get('supplemental_hp_development')
    if not isinstance(contract, dict):
        raise AcquisitionStopped('historical_handoff_manifest_contract_invalid')
    if (contract.get('development_sample_sha256') != sample_sha
            or contract.get('query_fingerprint_sha256') != query_sha):
        raise AcquisitionStopped('historical_handoff_manifest_sample_mismatch')
    if (handoff.get('target_v4_tree_sha256') != contract.get('target_v4_tree_sha256')
            or handoff.get('pre_receipt_tree_sha256') != contract.get('pre_receipt_tree_sha256')
            or handoff.get('target_v4_file_count') != contract.get('target_v4_file_count')
            or handoff.get('pre_receipt_file_count') != contract.get('pre_receipt_file_count')):
        raise AcquisitionStopped('historical_handoff_source_tree_binding_mismatch')
    target_root = _safe_child(root, 'target-v4', 'historical_handoff_target_root', directory=True)
    expected_roots = [str(target_root.resolve()), str(run_dir.resolve())]
    if any(record.get('accounted_roots') != expected_roots
           or record.get('target_root') != expected_roots[0]
           or record.get('supplemental_root') != expected_roots[1]
           or record.get('allowed_operation') != 'supplemental_hp_development'
           for record in (owner, root_release)):
        raise AcquisitionStopped('historical_handoff_output_root_binding_mismatch')
    from .supplemental import (BASE_ATTEMPTS, BASE_BODY_BYTES, BASE_HELD_PAGES,
        EXPECTED_EVIDENCE, EXCEPTIONAL_IDENTITY, GLOBAL_RETAINED_LIMIT,
        HP_ATTEMPT_LIMIT, HP_BODY_LIMIT, HP_PAGE_LIMIT, HP_RETAINED_LIMIT,
        PRE_RECEIPT_EXCLUSIONS, file_size, tree_digest)
    target_tree_sha, _target_bytes, target_count = tree_digest(target_root)
    subset_sha, _subset_bytes, subset_count = tree_digest(
        target_root, excluded=PRE_RECEIPT_EXCLUSIONS)
    if (target_tree_sha != TARGET_V4_TREE_SHA256
            or subset_sha != PRE_RECEIPT_TREE_SHA256
            or target_tree_sha != handoff.get('target_v4_tree_sha256')
            or subset_sha != handoff.get('pre_receipt_tree_sha256')
            or target_count != handoff.get('target_v4_file_count')
            or subset_count != handoff.get('pre_receipt_file_count')):
        raise AcquisitionStopped('historical_handoff_source_tree_changed')
    if contract.get('original_evidence_sha256') != EXPECTED_EVIDENCE:
        raise AcquisitionStopped('historical_handoff_original_evidence_contract_changed')
    evidence_paths = contract.get('original_evidence_paths')
    if not isinstance(evidence_paths, dict):
        raise AcquisitionStopped('historical_handoff_original_evidence_contract_changed')
    for name, relative in evidence_paths.items():
        expected_sha = contract.get('original_evidence_sha256', {}).get(name)
        source = _safe_child(target_root, relative, 'historical_handoff_original_evidence_path')
        if expected_sha is None or file_sha(source) != expected_sha:
            raise AcquisitionStopped('historical_handoff_original_evidence_changed')
    expected = {
        'manifest_sha256': V18_MANIFEST_SHA256,
        'git_head': V18_HEAD,
        'code_map_sha256': V18_CODE_MAP_SHA256,
        'activation_id': EXPECTED_ACTIVATION_ID,
        'run_id': EXPECTED_RUN_ID,
        'sample_sha256': sample_sha,
        'query_fingerprint_sha256': query_sha,
        'protocol_sha256': contract.get('protocol_sha256'),
        'decision_sha256': contract.get('decision_sha256'),
        'evidence_sha256': contract.get('original_evidence_sha256'),
    }
    for record in (owner, root_release):
        if any(record.get(key) != value for key, value in expected.items()):
            raise AcquisitionStopped('historical_handoff_activation_binding_mismatch')
    if (owner.get('single_use') is not True
            or owner.get('budget_snapshot') != contract.get('budget_snapshot')
            or root_release.get('owner_activation_sha256') != handoff['owner_activation_sha256']
            or root_release.get('root_manifest_check') is not True
            or root_release.get('native_review_approved_head') != V18_HEAD):
        raise AcquisitionStopped('historical_handoff_release_binding_mismatch')

    t0, deadline = utc(handoff.get('started_at')), utc(handoff.get('deadline'))
    finalized = utc(handoff.get('finalized_at'))
    cutoff = utc(SOURCE_CUTOFF)
    if (deadline != t0 + timedelta(seconds=1800) or deadline > cutoff
            or finalized < t0 or finalized >= deadline
            or handoff.get('source_cutoff') != SOURCE_CUTOFF):
        raise AcquisitionStopped('historical_handoff_window_invalid')
    inner_result = result.get('result')
    if not isinstance(inner_result, dict):
        raise AcquisitionStopped('historical_handoff_result_binding_mismatch')
    if (result.get('phase') != 'supplemental_hp_development'
            or result.get('manifest_sha256') != V18_MANIFEST_SHA256
            or result.get('run_id') != EXPECTED_RUN_ID
            or result.get('activation_id') != EXPECTED_ACTIVATION_ID
            or utc(result.get('started_at')) != t0 or utc(result.get('deadline')) != deadline
            or inner_result.get('status') != 'complete'):
        raise AcquisitionStopped('historical_handoff_result_binding_mismatch')

    events, _journal_raw = _verify_journal(run_dir, t0=t0, deadline=deadline, finished=finalized)
    finalized_events = [event for event in events if event.get('event') == 'run_finalized']
    bound = [event for event in events if event.get('event') == 'activation_bound']
    attempts = [event for event in events if event.get('event') == 'attempt_reserved']
    settled = [event for event in events if event.get('event') == 'attempt_settled']
    unknown = [event for event in events if event.get('event') == 'attempt_unknown']
    eof = [event for event in events if event.get('event') == 'response_complete' and event.get('eof') is True]
    responses = [event for event in events if event.get('event') == 'response_complete']
    reserved_slots = [event for event in events if event.get('event') == 'page_slot_reserved']
    admitted = [event for event in events if event.get('event') == 'page_slot_admitted']
    if (len(finalized_events) != 1 or finalized_events[0].get('result_sha256') != handoff['result_sha256']
            or finalized_events[0].get('result') != handoff['result_file']
            or len(bound) != 1
            or bound[0].get('activation_id') != EXPECTED_ACTIVATION_ID
            or bound[0].get('run_id') != EXPECTED_RUN_ID
            or bound[0].get('manifest_sha256') != V18_MANIFEST_SHA256
            or bound[0].get('git_head') != V18_HEAD
            or bound[0].get('code_map_sha256') != V18_CODE_MAP_SHA256
            or bound[0].get('owner_activation_sha256') != handoff['owner_activation_sha256']
            or bound[0].get('root_release_sha256') != handoff['root_release_sha256']
            or len(attempts) != handoff.get('attempt_count')
            or len(settled) != handoff.get('settled_count')
            or len(unknown) != handoff.get('unknown_count')
            or len(responses) != handoff.get('complete_response_count')
            or len(eof) != handoff.get('complete_response_count')
            or len(reserved_slots) != handoff.get('admitted_page_slots')
            or len(admitted) != handoff.get('admitted_page_slots')):
        raise AcquisitionStopped('historical_handoff_journal_accounting_mismatch')
    if any(event.get('status') != 'complete' for event in settled):
        raise AcquisitionStopped('historical_handoff_attempt_not_complete')
    charged = sum(event.get('charged_body_bytes', 0) for event in settled)
    if charged != handoff.get('body_bytes'):
        raise AcquisitionStopped('historical_handoff_body_accounting_mismatch')
    special_attempts = [event for event in attempts if event.get('identity') == EXCEPTIONAL_IDENTITY]
    held_slots = handoff.get('held_diagnostic_page_slots')
    if (len(special_attempts) != 1 or len(attempts) != handoff.get('attempt_count')
            or len(admitted) != handoff.get('admitted_page_slots')
            or held_slots != BASE_HELD_PAGES
            or handoff.get('historically_admitted_pages') != 0
            or handoff.get('cumulative_attempts') != BASE_ATTEMPTS + len(attempts)
            or handoff.get('cumulative_body_bytes') != BASE_BODY_BYTES + charged
            or handoff.get('occupied_page_slots') != len(admitted) + held_slots
            or handoff.get('page_slot_limit') != HP_PAGE_LIMIT
            or handoff.get('attempt_limit') != HP_ATTEMPT_LIMIT
            or handoff.get('body_byte_limit') != HP_BODY_LIMIT):
        raise AcquisitionStopped('historical_handoff_cumulative_budget_mismatch')

    run_retained = file_size(run_dir)
    authorization_retained = file_size(auth_dir)
    hp_retained = file_size(target_root / 'hp_development') + run_retained + authorization_retained
    global_retained = _target_bytes + run_retained + authorization_retained
    if (run_retained != handoff.get('run_retained_bytes')
            or authorization_retained != handoff.get('authorization_retained_bytes')
            or hp_retained != handoff.get('hp_retained_bytes')
            or global_retained != handoff.get('global_retained_bytes')
            or hp_retained > HP_RETAINED_LIMIT or global_retained > GLOBAL_RETAINED_LIMIT):
        raise AcquisitionStopped('historical_handoff_retention_mismatch')

    result_rows = inner_result.get('stations')
    order = [row['slug'] for row in development]
    if (not isinstance(result_rows, list)
            or not all(isinstance(row, dict) for row in result_rows)
            or [row.get('slug') for row in result_rows] != order):
        raise AcquisitionStopped('historical_handoff_sample_order_mismatch')
    if len(result_rows) != handoff.get('station_count'):
        raise AcquisitionStopped('historical_handoff_station_count_mismatch')
    status_counts = {}
    page_count = 0
    for row, station in zip(result_rows, development):
        status = row.get('status')
        if status not in ('complete_provider_zero', 'complete_800m_zero', 'complete_positive'):
            raise AcquisitionStopped('historical_handoff_station_incomplete')
        pages = row.get('pages')
        total = row.get('results_available_1000m')
        if (not isinstance(pages, list) or not pages
                or not all(isinstance(page, dict) for page in pages)
                or type(total) is not int or total < 0):
            raise AcquisitionStopped('historical_handoff_pagination_missing')
        expected_pages = max(1, math.ceil(total / 100))
        if len(pages) != expected_pages or row.get('unique_fetched') != total:
            raise AcquisitionStopped('historical_handoff_pagination_incomplete')
        status_counts[status] = status_counts.get(status, 0) + 1
        page_count += len(pages)
        count_800m = row.get('count_800m')
        if (type(count_800m) is not int or count_800m < 0
                or (status in ('complete_provider_zero', 'complete_800m_zero') and count_800m != 0)
                or (status == 'complete_positive' and count_800m == 0)):
            raise AcquisitionStopped('historical_handoff_analysis_count_invalid')
        received = []
        returned_total = 0
        for index, page in enumerate(pages):
            start = 1 + index * 100
            params = {'lat': station['lat'], 'lng': station['lng'], 'range': 3,
                      'count': 100, 'start': start, 'format': 'json', 'order': 1}
            expected_query = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
            if (page.get('start') != start or page.get('query_sha256') != expected_query
                    or type(page.get('returned')) is not int or page['returned'] < 0):
                raise AcquisitionStopped('historical_handoff_page_identity_mismatch')
            if status == 'complete_provider_zero':
                if (total != 0 or len(pages) != 1 or start != 1
                        or page.get('results_start') != 0 or page.get('returned') != 0):
                    raise AcquisitionStopped('historical_handoff_zero_shape_mismatch')
            elif page.get('results_start') != start:
                raise AcquisitionStopped('historical_handoff_page_start_mismatch')
            expected_returned = min(100, max(0, total - start + 1))
            if page.get('returned') != expected_returned:
                raise AcquisitionStopped('historical_handoff_page_count_mismatch')
            returned_total += page['returned']
            stamp = utc(page.get('received_at'))
            if not t0 <= stamp < deadline or stamp >= cutoff:
                raise AcquisitionStopped('historical_handoff_page_timestamp_invalid')
            received.append(stamp)
        finished_at = utc(row.get('finished_at'))
        if (finished_at != received[-1] or row.get('first_received_at') != pages[0].get('received_at')
                or returned_total != total or finished_at >= cutoff):
            raise AcquisitionStopped('historical_handoff_station_timestamp_invalid')

    windows = informational_zero_windows(result_rows, order, SOURCE_CUTOFF)
    if (windows != handoff.get('informational_confirmation_windows')
            or page_count != handoff.get('page_count')
            or status_counts != handoff.get('station_status_counts')):
        raise AcquisitionStopped('historical_handoff_confirmation_windows_mismatch')
    return {
        'state': 'verified_historical_development_input_only',
        'phase_execution_authorized': False,
        'confirmation_phase_eligible': False,
        'run_id': EXPECTED_RUN_ID,
        'activation_id': EXPECTED_ACTIVATION_ID,
        'started_at': t0.isoformat(),
        'deadline': deadline.isoformat(),
        'finalized_at': finalized.isoformat(),
        'result_path': str(result_path),
        'journal_path': str(journal_path),
        'result_sha256': handoff['result_sha256'],
        'journal_sha256': handoff['journal_sha256'],
        'sample_sha256': sample_sha,
        'query_fingerprint_sha256': query_sha,
        'code_map_sha256': V18_CODE_MAP_SHA256,
        'station_count': len(result_rows),
        'page_count': page_count,
        'attempt_count': len(attempts),
        'unknown_count': len(unknown),
        'body_bytes': charged,
        'informational_confirmation_windows': windows,
    }
