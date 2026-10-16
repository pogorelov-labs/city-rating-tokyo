"""Explicitly gated offline admission of an incomplete Overture metadata cache.

This module only reads the original ledger/cache and diagnostic. It never uses
Budget, urllib, or any provider client. A successful invocation writes a
distinct downstream-admission receipt; it never completes the source phase.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .acquire_osm import encoded
from .bounded import AcquisitionStopped, ReplayBudget
from .overture import metadata

OWNER_EXCEPTION_TYPE = 'crtky194-owner-cache-only-exception'
ROOT_RELEASE_TYPE = 'crtky194-root-cache-only-admission-release'
ADMISSION_TYPE = 'crtky194-downstream-cache-only-admission'
ADMISSION_STATE = 'downstream_admitted_cache_only'
DOWNSTREAM_PHASE = 'overture_development'
EXPECTED_OBJECTS = 16
EXPECTED_GROUPS = 4864
EXPECTED_ATTEMPTS = 33
EXPECTED_CHARGED_BYTES = 30_147_627
SOURCE_V4_MANIFEST_SHA256 = '43a71f74f7e4cfc400e6de74454435f2be8496ccb00060cdf555cff7641e8ff9'
SOURCE_V4_LEDGER_SHA256 = 'b18fe378893e2a88cf306d0f4f6775d8412dce464d233bfb1a8ca746ffa5b399'
SOURCE_DIAGNOSTIC_SHA256 = '7c7fa5d2a0d2378a07e20ddcc2fd30d27b41a654072d7bded998af01e4ccf873'
V5_MANIFEST_SHA256 = 'df6e5d99290bed6e6f0aec47fc85fd01b6560558618db7caecf9108310eba6d4'
EXPECTED_STARTED_AT = '2026-10-16T11:37:07.610699+00:00'
EXPECTED_FINISHED_AT = '2026-10-16T11:38:01.834534+00:00'
EXPECTED_DEADLINE = '2026-10-16T11:47:07.610699+00:00'
SOURCE_PHASE_DIR = Path('/Users/ruslan/.ao/data/artifacts/city-rating-3/overture-food-shadow/target-v4/overture_metadata')
SOURCE_DIAGNOSTIC_NAME = 'offline-lossless-derivative-001.json'


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(value):
    return sha256(encoded(value))


def load_json(path):
    try:
        return json.loads(Path(path).read_bytes())
    except (OSError, ValueError, TypeError):
        raise AcquisitionStopped('invalid_recovery_input') from None


def checked_runtime_manifest(path):
    raw = Path(path).read_bytes()
    manifest = json.loads(raw)
    if manifest.get('state') != 'frozen' or not manifest.get('code_sha256'):
        raise AcquisitionStopped('recovery_manifest_not_frozen')
    root = Path(__file__).resolve().parents[2]
    for relative, expected in manifest['code_sha256'].items():
        source = (root / relative).resolve()
        if not source.is_relative_to(root / 'scripts' / 'food_pilot'):
            raise AcquisitionStopped('unapproved_recovery_code_path')
        if sha256(source.read_bytes()) != expected:
            raise AcquisitionStopped('recovery_code_changed_after_freeze')
    return manifest, sha256(raw)


def _object_identity_rows(result):
    return [{'url': obj['url'], 'etag': obj['etag'], 'size': obj['size']}
            for obj in sorted(result['objects'], key=lambda item: item['url'])]


def _row_group_rows(result):
    return [{'url': obj['url'], 'index': group['index'], 'rows': group['rows'],
             'bounds': group['bounds']}
            for obj in sorted(result['objects'], key=lambda item: item['url'])
            for group in obj['groups']]


def _footer_reference_rows(result):
    return [{'url': obj['url'], 'reference': obj['footer_ref']}
            for obj in sorted(result['objects'], key=lambda item: item['url'])]


def _bindings(*, source_manifest, source_manifest_sha, ledger, ledger_sha,
              diagnostic, diagnostic_sha, downstream_manifest, downstream_manifest_sha,
              phase_dir):
    if source_manifest.get('state') != 'frozen' or downstream_manifest.get('state') != 'frozen':
        raise AcquisitionStopped('recovery_manifest_not_frozen')
    if source_manifest_sha != SOURCE_V4_MANIFEST_SHA256 or ledger_sha != SOURCE_V4_LEDGER_SHA256:
        raise AcquisitionStopped('recovery_not_original_v4_phase')
    if diagnostic_sha != SOURCE_DIAGNOSTIC_SHA256:
        raise AcquisitionStopped('recovery_not_frozen_diagnostic')
    if source_manifest_sha == downstream_manifest_sha:
        raise AcquisitionStopped('recovery_manifest_not_successor')
    if downstream_manifest.get('supersedes_manifest_sha256') != V5_MANIFEST_SHA256:
        raise AcquisitionStopped('recovery_manifest_lineage_mismatch')
    if downstream_manifest.get('budgets') != source_manifest.get('budgets'):
        raise AcquisitionStopped('recovery_budget_contract_changed')
    if downstream_manifest.get('source_window') != source_manifest.get('source_window'):
        raise AcquisitionStopped('recovery_source_window_changed')
    code_map_sha = canonical_sha(downstream_manifest['code_sha256'])

    if ledger_sha != sha256((phase_dir / 'ledger.json').read_bytes()):
        raise AcquisitionStopped('recovery_ledger_changed')
    if ledger.get('manifest_sha256') != source_manifest_sha:
        raise AcquisitionStopped('recovery_ledger_manifest_mismatch')
    if ledger.get('status') != 'incomplete':
        raise AcquisitionStopped('recovery_source_not_incomplete')
    if ledger.get('limits') != source_manifest['budgets']['overture_metadata']:
        raise AcquisitionStopped('recovery_phase_budget_changed')
    started = datetime.fromisoformat(ledger['started_at'].replace('Z', '+00:00'))
    deadline = started + timedelta(seconds=ledger['limits']['wall_seconds'])
    finished = datetime.fromisoformat(ledger['finished_at'].replace('Z', '+00:00'))
    if started.tzinfo is None or finished.tzinfo is None:
        raise AcquisitionStopped('recovery_naive_timestamp')
    if len(ledger.get('attempts', [])) != EXPECTED_ATTEMPTS or ledger.get('charged_bytes') != EXPECTED_CHARGED_BYTES:
        raise AcquisitionStopped('recovery_original_counters_changed')
    if any(item.get('status') != 'complete' for item in ledger['attempts']):
        raise AcquisitionStopped('recovery_attempt_incomplete')
    if finished < started or finished > deadline:
        raise AcquisitionStopped('recovery_original_deadline_mismatch')
    if (started.isoformat() != EXPECTED_STARTED_AT or finished.isoformat() != EXPECTED_FINISHED_AT
            or deadline.isoformat() != EXPECTED_DEADLINE):
        raise AcquisitionStopped('recovery_original_timestamps_changed')
    if len(ledger.get('row_groups', [])) != 0:
        raise AcquisitionStopped('recovery_metadata_ledger_unexpected_groups')

    if (diagnostic.get('artifact_type') != 'offline_lossless_metadata_derivative'
            or diagnostic.get('phase_completion_claim') is not False
            or diagnostic.get('source_phase_status') != 'incomplete'
            or diagnostic.get('source_ledger_sha256') != ledger_sha
            or diagnostic.get('source_phase_started_at') != ledger['started_at']
            or diagnostic.get('source_phase_finished_at') != ledger['finished_at']
            or diagnostic.get('source_phase_original_deadline') != deadline.isoformat()
            or diagnostic.get('source_attempts') != EXPECTED_ATTEMPTS
            or diagnostic.get('source_charged_response_body_bytes') != EXPECTED_CHARGED_BYTES):
        raise AcquisitionStopped('recovery_diagnostic_provenance_mismatch')

    result = diagnostic.get('result')
    if not isinstance(result, dict) or result.get('complete') is not True:
        raise AcquisitionStopped('recovery_metadata_not_complete')
    if result.get('release') != source_manifest['overture']['release']:
        raise AcquisitionStopped('recovery_overture_release_mismatch')
    urls = [obj.get('url') for obj in result.get('objects', [])]
    if (len(urls) != EXPECTED_OBJECTS or len(set(urls)) != EXPECTED_OBJECTS
            or sorted(urls) != sorted(source_manifest['overture']['objects'])):
        raise AcquisitionStopped('recovery_object_identity_mismatch')
    if sum(len(obj.get('groups', [])) for obj in result['objects']) != EXPECTED_GROUPS:
        raise AcquisitionStopped('recovery_row_group_count_mismatch')
    if any('footer_ref' not in obj or 'footer_b64' in obj for obj in result['objects']):
        raise AcquisitionStopped('recovery_footer_reference_contract')

    # Reconstruct from the original cache using ReplayBudget only. This validates
    # listing, object identity, actual footer bytes, row-group metadata and hashes
    # without opening a socket or changing the source ledger.
    replayed = metadata(source_manifest, ReplayBudget(phase_dir))
    if replayed != result:
        raise AcquisitionStopped('recovery_cached_semantics_mismatch')

    identities = _object_identity_rows(result)
    row_groups = _row_group_rows(result)
    footer_refs = _footer_reference_rows(result)
    return {
        'source_manifest_sha256': source_manifest_sha,
        'source_ledger_sha256': ledger_sha,
        'source_phase_status': 'incomplete',
        'source_phase_started_at': ledger['started_at'],
        'source_phase_deadline': deadline.isoformat(),
        'source_phase_finished_at': ledger['finished_at'],
        'source_attempts': EXPECTED_ATTEMPTS,
        'source_charged_response_body_bytes': EXPECTED_CHARGED_BYTES,
        'diagnostic_sha256': diagnostic_sha,
        'diagnostic_result_sha256': canonical_sha(result),
        'downstream_manifest_sha256': downstream_manifest_sha,
        'downstream_code_map_sha256': code_map_sha,
        'downstream_phase': DOWNSTREAM_PHASE,
        'object_count': EXPECTED_OBJECTS,
        'object_identity_sha256': canonical_sha(identities),
        'row_group_count': EXPECTED_GROUPS,
        'row_group_metadata_sha256': canonical_sha(row_groups),
        'footer_reference_count': EXPECTED_OBJECTS,
        'footer_reference_sha256': canonical_sha(footer_refs),
        'phase_completion_claim': False,
        'metadata_requests_performed': 0,
    }


def _require_binding(receipt, bindings):
    for key, expected in bindings.items():
        if receipt.get(key) != expected:
            raise AcquisitionStopped('recovery_authorization_binding_mismatch')


def verify_owner_and_root(*, owner_path, root_path, **kwargs):
    try:
        owner_raw = Path(owner_path).read_bytes()
        root_raw = Path(root_path).read_bytes()
        owner, root = json.loads(owner_raw), json.loads(root_raw)
    except (OSError, ValueError, TypeError):
        raise AcquisitionStopped('invalid_owner_or_root_receipt') from None
    binding = kwargs['binding']
    if (owner.get('receipt_type') != OWNER_EXCEPTION_TYPE
            or owner.get('decision') != 'allow_cache_only_metadata_downstream_admission'
            or not owner.get('owner_exception_id') or not owner.get('recorded_at_utc')
            or owner.get('scope') != [DOWNSTREAM_PHASE]
            or owner.get('metadata_requests_permitted') is not False
            or owner.get('source_phase_completion_permitted') is not False):
        raise AcquisitionStopped('missing_explicit_owner_exception')
    _valid_receipt_time(owner.get('recorded_at_utc'), 'owner_exception_time_invalid')
    _require_binding(owner, binding)
    owner_sha = sha256(owner_raw)
    if (root.get('receipt_type') != ROOT_RELEASE_TYPE
            or root.get('operation') != 'write_cache_only_admission_receipt'
            or not root.get('root_release_id') or not root.get('released_at_utc')
            or root.get('owner_exception_sha256') != owner_sha
            or root.get('metadata_requests_permitted') is not False
            or root.get('source_phase_completion_permitted') is not False
            or root.get('downstream_phase_execution_permitted') is not False):
        raise AcquisitionStopped('missing_explicit_root_cache_release')
    _valid_receipt_time(root.get('released_at_utc'), 'root_release_time_invalid')
    _require_binding(root, binding)
    return owner_sha, sha256(root_raw)


def _valid_receipt_time(value, error):
    if not isinstance(value, str):
        raise AcquisitionStopped(error)
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise AcquisitionStopped(error) from None
    if parsed.tzinfo is None:
        raise AcquisitionStopped(error)


def make_admission(*, source_manifest_path, downstream_manifest_path, phase_dir,
                   diagnostic_path, owner_exception_path, root_release_path):
    """Validate separate approvals and write only a cache-admission receipt."""
    from .run import checked_manifest

    source_manifest_path = Path(source_manifest_path).resolve()
    downstream_manifest_path = Path(downstream_manifest_path).resolve()
    phase_dir = Path(phase_dir).resolve()
    diagnostic_path = Path(diagnostic_path).resolve()
    if (phase_dir != SOURCE_PHASE_DIR.resolve() or diagnostic_path.parent != phase_dir
            or diagnostic_path.name != SOURCE_DIAGNOSTIC_NAME or not phase_dir.is_dir()):
        raise AcquisitionStopped('recovery_artifacts_not_colocated')
    lock_path = phase_dir / '.reader.lock'
    if lock_path.is_symlink():
        raise AcquisitionStopped('unexpected_metadata_symlink')
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise AcquisitionStopped('metadata_cache_lock_unavailable') from None
    lock = os.fdopen(lock_fd, 'a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise AcquisitionStopped('metadata_cache_in_use') from None
    try:
        source_raw = source_manifest_path.read_bytes()
        source_manifest = json.loads(source_raw)
        source_sha = sha256(source_raw)
        downstream_manifest, downstream_sha = checked_manifest(downstream_manifest_path)
        ledger_raw = (phase_dir / 'ledger.json').read_bytes()
        ledger = json.loads(ledger_raw)
        diagnostic_raw = diagnostic_path.read_bytes()
        diagnostic = json.loads(diagnostic_raw)
        bindings = _bindings(source_manifest=source_manifest, source_manifest_sha=source_sha,
            ledger=ledger, ledger_sha=sha256(ledger_raw), diagnostic=diagnostic,
            diagnostic_sha=sha256(diagnostic_raw), downstream_manifest=downstream_manifest,
            downstream_manifest_sha=downstream_sha, phase_dir=phase_dir)
        owner_sha, root_sha = verify_owner_and_root(owner_path=owner_exception_path,
            root_path=root_release_path, binding=bindings)
        receipt = {'receipt_type': ADMISSION_TYPE, 'state': ADMISSION_STATE, **bindings,
            'owner_exception_sha256': owner_sha, 'root_release_sha256': root_sha,
            'diagnostic_file': diagnostic_path.name,
            'source_phase_directory': str(phase_dir),
            'admission_is_not_phase_completion': True}
        raw = encoded(receipt)
        receipt_sha = sha256(raw)
        output = phase_dir / f'cache-only-admission-{receipt_sha}.json'
        entries = list(phase_dir.rglob('*'))
        if any(item.is_symlink() for item in entries):
            raise AcquisitionStopped('unexpected_metadata_symlink')
        retained = sum(item.stat().st_size for item in entries if item.is_file())
        cap = source_manifest['budgets']['overture_metadata']['retained_bytes']
        if retained + (0 if output.exists() else len(raw)) > cap:
            raise AcquisitionStopped('combined_metadata_retention_budget')
        if output.exists():
            if output.read_bytes() != raw:
                raise AcquisitionStopped('immutable_admission_receipt_conflict')
        else:
            descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        if sha256((phase_dir / 'ledger.json').read_bytes()) != bindings['source_ledger_sha256']:
            raise AcquisitionStopped('recovery_source_ledger_mutated')
        return output, receipt_sha
    finally:
        lock.close()


def load_admitted_metadata(*, admission_path, source_manifest_path, downstream_manifest,
                           downstream_manifest_sha, owner_exception_path, root_release_path):
    """Revalidate an admission receipt before it can feed Overture development."""
    admission_path = Path(admission_path).resolve()
    phase_dir = admission_path.parent
    if phase_dir != SOURCE_PHASE_DIR.resolve():
        raise AcquisitionStopped('recovery_artifacts_not_colocated')
    try:
        receipt_raw = admission_path.read_bytes()
    except OSError:
        raise AcquisitionStopped('invalid_cache_only_admission') from None
    receipt = load_json(admission_path)
    if (receipt.get('receipt_type') != ADMISSION_TYPE
            or receipt.get('state') != ADMISSION_STATE
            or receipt.get('admission_is_not_phase_completion') is not True
            or receipt.get('downstream_phase') != DOWNSTREAM_PHASE
            or receipt.get('downstream_manifest_sha256') != downstream_manifest_sha):
        raise AcquisitionStopped('invalid_cache_only_admission')
    if admission_path.name != f'cache-only-admission-{sha256(receipt_raw)}.json':
        raise AcquisitionStopped('invalid_cache_only_admission_hash')
    diagnostic_name = receipt.get('diagnostic_file')
    if not isinstance(diagnostic_name, str) or Path(diagnostic_name).name != diagnostic_name:
        raise AcquisitionStopped('recovery_artifacts_not_colocated')
    diagnostic_path = phase_dir / diagnostic_name
    recorded_directory = receipt.get('source_phase_directory')
    if (diagnostic_name != SOURCE_DIAGNOSTIC_NAME or diagnostic_path.parent != phase_dir
            or not isinstance(recorded_directory, str)
            or Path(recorded_directory).resolve() != phase_dir):
        raise AcquisitionStopped('recovery_artifacts_not_colocated')
    source_raw = Path(source_manifest_path).read_bytes()
    source_manifest = json.loads(source_raw)
    ledger_raw = (phase_dir / 'ledger.json').read_bytes()
    ledger = json.loads(ledger_raw)
    diagnostic_raw = diagnostic_path.read_bytes()
    diagnostic = json.loads(diagnostic_raw)
    bindings = _bindings(source_manifest=source_manifest, source_manifest_sha=sha256(source_raw),
        ledger=ledger, ledger_sha=sha256(ledger_raw), diagnostic=diagnostic,
        diagnostic_sha=sha256(diagnostic_raw), downstream_manifest=downstream_manifest,
        downstream_manifest_sha=downstream_manifest_sha, phase_dir=phase_dir)
    owner_sha, root_sha = verify_owner_and_root(owner_path=owner_exception_path,
        root_path=root_release_path, binding=bindings)
    _require_binding(receipt, bindings)
    if (receipt.get('owner_exception_sha256') != owner_sha
            or receipt.get('root_release_sha256') != root_sha):
        raise AcquisitionStopped('recovery_authorization_changed')
    expected_receipt = {'receipt_type': ADMISSION_TYPE, 'state': ADMISSION_STATE, **bindings,
        'owner_exception_sha256': owner_sha, 'root_release_sha256': root_sha,
        'diagnostic_file': diagnostic_path.name,
        'source_phase_directory': str(phase_dir),
        'admission_is_not_phase_completion': True}
    if receipt != expected_receipt:
        raise AcquisitionStopped('invalid_cache_only_admission_contract')
    if sha256((phase_dir / 'ledger.json').read_bytes()) != bindings['source_ledger_sha256']:
        raise AcquisitionStopped('recovery_ledger_changed')
    entries = list(phase_dir.rglob('*'))
    if any(item.is_symlink() for item in entries):
        raise AcquisitionStopped('unexpected_metadata_symlink')
    if sum(item.stat().st_size for item in entries if item.is_file()) > source_manifest['budgets']['overture_metadata']['retained_bytes']:
        raise AcquisitionStopped('combined_metadata_retention_budget')
    return diagnostic['result'], ReplayBudget(phase_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--downstream-manifest', type=Path, required=True)
    parser.add_argument('--source-phase-dir', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--owner-exception', type=Path, required=True)
    parser.add_argument('--root-release', type=Path, required=True)
    args = parser.parse_args()
    try:
        path, digest = make_admission(source_manifest_path=args.source_manifest,
            downstream_manifest_path=args.downstream_manifest, phase_dir=args.source_phase_dir,
            diagnostic_path=args.diagnostic, owner_exception_path=args.owner_exception,
            root_release_path=args.root_release)
        print(json.dumps({'state': ADMISSION_STATE, 'receipt_path': str(path),
                          'sha256': digest, 'metadata_requests_performed': 0,
                          'source_phase_completed': False}))
    except Exception as exc:
        print(json.dumps({'state': 'stopped', 'error_type': type(exc).__name__}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
