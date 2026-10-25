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
V6_MANIFEST_SHA256 = '7a6f996f2324a3158407e8b8e4ef63c2670cdd05d33ce6230171bee1f84e0c00'
V7_MANIFEST_SHA256 = '04d9137b38e2a20d34e7273f54eca264873382832d5b5c00e846468b4cb928c9'
V8_MANIFEST_SHA256 = 'c67e0c723ffa9eca6fa79028a2bc4900129c630bed6a48c2ea58c87c3795881d'
V9_MANIFEST_SHA256 = '9528171588e0d2f5c91bd9149733c65cfe5e66ee1e9e4c80d80d9ebb8d2d4b62'
V10_MANIFEST_SHA256 = 'd753a5d8238b03ab2c0774150794acbdaf3f09bb4f905c487a1ea661b1630f7b'
V11_MANIFEST_SHA256 = '5ceee657d5f7946675a773b760b4d525cc4cbdbb17391d68d8805c72e9c91e88'
V12_MANIFEST_SHA256 = '599c0489cd50b716dc36755414f6f47ae08032256d34570ba46a1d1fb2ba6345'
V13_MANIFEST_SHA256 = '0342111e73a8f076c862638805dd12058a391f92dff2a77b78699b13703c417d'
V14_MANIFEST_SHA256 = 'dc15c2b7ef850c754c60f34668722b268c9c17a3adda68bff787425c5079fd97'
V15_MANIFEST_SHA256 = 'bde52bdcdd04b7ee8a6df28a6aea9d9ac1bf4982d307064ace2e47ce4e9d7ef1'
V16_MANIFEST_SHA256 = '1cb2b0203f9fcd7601e2b0e93c17bd382500c601c1d9cfa715ea28f3c6fb4c5c'
V17_MANIFEST_SHA256 = 'd0183b183bb451bff39eec3fa710e141454759c94de051cb5a142035ad10f2a2'
V18_MANIFEST_SHA256 = '0f12301839516763eacfc9749f3127bf2239a68b3cda42e412bbc78f47b5a970'
V18_NONCODE_CONTRACT_SHA256 = 'fd0cd9ace8b2700af0b7865488d1fcdfa12aa8b9cd432e0e4cc76c0476b91e64'
V19_MANIFEST_SHA256 = 'afaeabe21f4ff49c79eb8eac67eebaeedd777d501f3717a2d41854ac6ae7f8d3'
V19_NONCODE_CONTRACT_SHA256 = '86c5924dda8244853e26426f0d872073faef564733fa4876bc1b4477e755ded9'
EXPECTED_CURRENT_ADMISSION_CONTRACT_SHA256 = '62b70c81a45de1b16ee86754d8980fbb2d02cfbefd21d6dbd2732126771f3912'
V8_NONCODE_CONTRACT_SHA256 = '74bfcef62f9fce2c14e73468a8f7c33ae2cbf7de7066fb0c47a1d4d935fc238c'
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


def _check_successor_lineage(downstream_manifest, downstream_manifest_sha):
    """Accept only the pinned V5–V18 chain and one exact-contract V18 child."""
    pinned_parents = {
        V5_MANIFEST_SHA256: SOURCE_V4_MANIFEST_SHA256,
        V6_MANIFEST_SHA256: V5_MANIFEST_SHA256,
        V7_MANIFEST_SHA256: V6_MANIFEST_SHA256,
        V8_MANIFEST_SHA256: V7_MANIFEST_SHA256,
        V9_MANIFEST_SHA256: V8_MANIFEST_SHA256,
        V10_MANIFEST_SHA256: V9_MANIFEST_SHA256,
        V11_MANIFEST_SHA256: V10_MANIFEST_SHA256,
        V12_MANIFEST_SHA256: V11_MANIFEST_SHA256,
        V13_MANIFEST_SHA256: V12_MANIFEST_SHA256,
        V14_MANIFEST_SHA256: V13_MANIFEST_SHA256,
        V15_MANIFEST_SHA256: V14_MANIFEST_SHA256,
        V16_MANIFEST_SHA256: V15_MANIFEST_SHA256,
        V17_MANIFEST_SHA256: V16_MANIFEST_SHA256,
        V18_MANIFEST_SHA256: V17_MANIFEST_SHA256,
    }
    expected_parent = pinned_parents.get(downstream_manifest_sha)
    actual_parent = downstream_manifest.get('supersedes_manifest_sha256')
    if expected_parent is not None and actual_parent == expected_parent:
        return
    # Preserve the legacy V8 code-only extension, but do not let it license a
    # later descendant or a changed source/budget contract.
    if downstream_manifest_sha not in pinned_parents and actual_parent == V8_MANIFEST_SHA256:
        contract = {key: value for key, value in downstream_manifest.items()
                    if key not in {'code_sha256', 'supersedes_manifest_sha256',
                                   'supersession_reason'}}
        if canonical_sha(contract) != V8_NONCODE_CONTRACT_SHA256:
            raise AcquisitionStopped('recovery_manifest_noncode_contract_changed')
        return
    # V19 adds one pinned historical HP-run handoff block to V18. Apart from
    # that exact block, version, code hashes and supersession fields, every
    # non-code contract field must remain byte-equivalent to the V18 contract.
    if downstream_manifest_sha not in pinned_parents and actual_parent == V18_MANIFEST_SHA256:
        from .historical_handoff import EXPECTED_HANDOFF_CONTRACT_SHA256

        handoff = downstream_manifest.get('historical_supplemental_hp_run')
        if not isinstance(handoff, dict) or canonical_sha(handoff) != EXPECTED_HANDOFF_CONTRACT_SHA256:
            raise AcquisitionStopped('recovery_historical_hp_handoff_contract_changed')
        contract = {key: value for key, value in downstream_manifest.items()
                    if key not in {'code_sha256', 'supersedes_manifest_sha256',
                                   'supersession_reason', 'version',
                                   'historical_supplemental_hp_run'}}
        if canonical_sha(contract) != V18_NONCODE_CONTRACT_SHA256:
            raise AcquisitionStopped('recovery_manifest_noncode_contract_changed')
        return
    if downstream_manifest_sha not in pinned_parents and actual_parent == V19_MANIFEST_SHA256:
        admission_contract = downstream_manifest.get('current_manifest_cache_admission')
        if (not isinstance(admission_contract, dict)
                or canonical_sha(admission_contract) != EXPECTED_CURRENT_ADMISSION_CONTRACT_SHA256):
            raise AcquisitionStopped('recovery_current_admission_contract_changed')
        contract = {key: value for key, value in downstream_manifest.items()
                    if key not in {'code_sha256', 'supersedes_manifest_sha256',
                                   'supersession_reason', 'version',
                                   'current_manifest_cache_admission'}}
        if canonical_sha(contract) != V19_NONCODE_CONTRACT_SHA256:
            raise AcquisitionStopped('recovery_manifest_noncode_contract_changed')
        return
    raise AcquisitionStopped('recovery_manifest_lineage_mismatch')


def _reject_symlink_components(path, error):
    candidate = Path(path).absolute()
    for item in (candidate, *candidate.parents):
        if item.exists() and item.is_symlink():
            raise AcquisitionStopped(error)


def _resolve_admission_roots(downstream_manifest, source_phase_dir, admission_root,
                             *, require_admission_root=False):
    """Resolve the immutable V4 cache separately from a current-manifest receipt root."""
    _reject_symlink_components(source_phase_dir, 'recovery_source_cache_root_symlink')
    if admission_root is not None:
        _reject_symlink_components(admission_root, 'recovery_admission_root_symlink')
    source_phase_dir = Path(source_phase_dir).resolve()
    if source_phase_dir != SOURCE_PHASE_DIR.resolve():
        raise AcquisitionStopped('recovery_not_original_v4_phase')
    current = downstream_manifest.get('current_manifest_cache_admission')
    if current is None:
        if downstream_manifest.get('historical_supplemental_hp_run') is not None:
            if require_admission_root:
                raise AcquisitionStopped('recovery_current_admission_contract_missing')
            if admission_root is not None:
                raise AcquisitionStopped('recovery_unbound_admission_root')
        elif admission_root is not None and Path(admission_root).resolve() != source_phase_dir:
            raise AcquisitionStopped('recovery_unbound_admission_root')
        return source_phase_dir, source_phase_dir, None
    if canonical_sha(current) != EXPECTED_CURRENT_ADMISSION_CONTRACT_SHA256:
        raise AcquisitionStopped('recovery_current_admission_contract_changed')

    artifact_root = source_phase_dir.parents[1].resolve()

    def resolve_relative(value, error, *, must_exist):
        if not isinstance(value, str):
            raise AcquisitionStopped(error)
        relative = Path(value)
        if relative.is_absolute() or not relative.parts or any(part in ('', '.', '..') for part in relative.parts):
            raise AcquisitionStopped(error)
        candidate = artifact_root
        for part in relative.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise AcquisitionStopped(error)
        resolved = candidate.resolve()
        if not resolved.is_relative_to(artifact_root):
            raise AcquisitionStopped(error)
        if must_exist and not resolved.is_dir():
            raise AcquisitionStopped(error)
        return resolved

    expected_source = resolve_relative(current.get('source_cache_directory'),
                                       'recovery_source_cache_path_invalid', must_exist=True)
    expected_output = resolve_relative(current.get('admission_directory'),
                                       'recovery_admission_root_invalid', must_exist=False)
    if expected_source != source_phase_dir:
        raise AcquisitionStopped('recovery_source_cache_root_mismatch')
    target_root = (artifact_root / 'target-v4').resolve()
    repository_root = Path(__file__).resolve().parents[2]
    if (expected_output == source_phase_dir
            or expected_output.is_relative_to(target_root)
            or expected_output.is_relative_to(repository_root)):
        raise AcquisitionStopped('recovery_admission_root_unsafe')
    if expected_output.exists() and not expected_output.is_dir():
        raise AcquisitionStopped('recovery_admission_root_invalid')
    if admission_root is None:
        if require_admission_root:
            raise AcquisitionStopped('recovery_admission_root_required')
    elif Path(admission_root).resolve() != expected_output:
        raise AcquisitionStopped('recovery_admission_root_mismatch')
    if current.get('source_manifest_sha256') != SOURCE_V4_MANIFEST_SHA256:
        raise AcquisitionStopped('recovery_current_source_manifest_mismatch')
    if current.get('source_ledger_sha256') != SOURCE_V4_LEDGER_SHA256:
        raise AcquisitionStopped('recovery_current_source_ledger_mismatch')
    if current.get('source_diagnostic_sha256') != SOURCE_DIAGNOSTIC_SHA256:
        raise AcquisitionStopped('recovery_current_source_diagnostic_mismatch')
    handoff = downstream_manifest.get('historical_supplemental_hp_run')
    if (not isinstance(handoff, dict)
            or current.get('historical_supplemental_hp_run_sha256') != canonical_sha(handoff)):
        raise AcquisitionStopped('recovery_current_historical_handoff_mismatch')
    if current.get('metadata_requests_permitted') is not False:
        raise AcquisitionStopped('recovery_current_source_io_not_disabled')
    if current.get('source_phase_completion_claim') is not False:
        raise AcquisitionStopped('recovery_current_source_completion_claim')
    if (current.get('fresh_owner_root_required') is not True
            or current.get('admission_is_not_phase_completion') is not True
            or current.get('downstream_phase_execution_permitted') is not False
            or current.get('authorization_subdirectory') != 'authorizations'
            or current.get('owner_file') != 'owner-exception.json'
            or current.get('root_file') != 'root-release.json'):
        raise AcquisitionStopped('recovery_current_admission_contract_changed')
    return source_phase_dir, expected_output, canonical_sha(current)


def _validate_current_authorization_paths(downstream_manifest, admission_root,
                                         owner_path, root_path):
    current = downstream_manifest.get('current_manifest_cache_admission')
    if current is None:
        return
    _reject_symlink_components(admission_root, 'recovery_admission_root_symlink')
    _reject_symlink_components(owner_path, 'recovery_authorization_root_symlink')
    _reject_symlink_components(root_path, 'recovery_authorization_root_symlink')
    output = Path(admission_root).resolve()
    auth_root = output / current['authorization_subdirectory']
    if auth_root.is_symlink():
        raise AcquisitionStopped('recovery_authorization_root_invalid')
    expected_owner = auth_root / current['owner_file']
    expected_root = auth_root / current['root_file']
    if (Path(owner_path).is_symlink() or Path(root_path).is_symlink()
            or Path(owner_path).resolve() != expected_owner.resolve()
            or Path(root_path).resolve() != expected_root.resolve()
            or expected_owner.is_symlink() or expected_root.is_symlink()):
        raise AcquisitionStopped('recovery_authorization_root_mismatch')


def _current_accounting_roots(source_phase_dir, current):
    artifact_root = Path(source_phase_dir).resolve().parents[1]
    relative_roots = current.get('global_retention_roots')
    if not isinstance(relative_roots, list) or not relative_roots or len(set(relative_roots)) != len(relative_roots):
        raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
    resolved = []
    for relative in relative_roots:
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
        candidate = artifact_root
        for part in Path(relative).parts:
            if part in ('', '.', '..'):
                raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
            candidate = candidate / part
            if candidate.is_symlink():
                raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
        candidate = candidate.resolve()
        if not candidate.is_relative_to(artifact_root):
            raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
        if candidate.exists() and not candidate.is_dir():
            raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
        resolved.append(str(candidate))
    if str(Path(source_phase_dir).resolve().parents[1] / 'target-v4') not in resolved:
        raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
    if str(Path(source_phase_dir).resolve().parents[1] / current['admission_directory']) not in resolved:
        raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
    handoff = current.get('historical_supplemental_hp_run_sha256')
    if handoff is None:
        raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
    expected_roots = {
        str(artifact_root / 'target-v4'),
        str(artifact_root / 'supplemental-hp-v18-001'),
        str(artifact_root / 'supplemental-hp-v18-001-authorizations'),
        str(artifact_root / current['admission_directory']),
    }
    if set(resolved) != expected_roots:
        raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
    expected_metadata_roots = {
        str(Path(source_phase_dir).resolve()),
        str(artifact_root / current['admission_directory']),
    }
    metadata_roots = current.get('metadata_retention_roots')
    if not isinstance(metadata_roots, list):
        raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
    resolved_metadata = []
    for relative in metadata_roots:
        candidate = artifact_root / relative
        _reject_symlink_components(candidate, 'recovery_current_accounting_roots_invalid')
        resolved_metadata.append(str(candidate.resolve()))
    if set(resolved_metadata) != expected_metadata_roots:
        raise AcquisitionStopped('recovery_current_accounting_roots_invalid')
    return resolved


def _current_retention_usage(*, source_phase_dir, admission_root, downstream_manifest,
                             source_manifest):
    """Count metadata source+new receipt separately; count source only once globally."""
    from .supplemental import file_size

    current = downstream_manifest.get('current_manifest_cache_admission')
    if not isinstance(current, dict):
        raise AcquisitionStopped('recovery_current_admission_contract_missing')
    artifact_root = Path(source_phase_dir).resolve().parents[1]
    handoff = downstream_manifest.get('historical_supplemental_hp_run')
    if not isinstance(handoff, dict):
        raise AcquisitionStopped('recovery_historical_hp_handoff_missing')
    run_root = (artifact_root / handoff['run_directory']).resolve()
    auth_root = (artifact_root / handoff['authorization_directory']).resolve()
    target_root = artifact_root / 'target-v4'
    if Path(admission_root).is_symlink():
        raise AcquisitionStopped('recovery_admission_root_invalid')
    source_used = file_size(source_phase_dir)
    if Path(admission_root).is_symlink():
        raise AcquisitionStopped('recovery_admission_root_invalid')
    output_used = file_size(admission_root) if Path(admission_root).exists() else 0
    target_used = file_size(target_root)
    run_used = file_size(run_root)
    auth_used = file_size(auth_root)
    metadata_used = source_used + output_used
    global_used = target_used + run_used + auth_used + output_used
    metadata_limit = source_manifest['budgets']['overture_metadata']['retained_bytes']
    global_limit = downstream_manifest['budgets']['total_retained_bytes']
    if (metadata_limit != current.get('metadata_retention_limit')
            or global_limit != current.get('global_retention_limit')
            or source_used != current.get('baseline_metadata_source_bytes')
            or target_used + run_used + auth_used != current.get('baseline_global_bytes')):
        raise AcquisitionStopped('recovery_current_retention_baseline_mismatch')
    if metadata_used > metadata_limit or global_used > global_limit:
        raise AcquisitionStopped('combined_current_admission_retention_budget')
    return {'metadata_used': metadata_used, 'metadata_limit': metadata_limit,
            'global_used': global_used, 'global_limit': global_limit,
            'output_used': output_used}


def _bindings(*, source_manifest, source_manifest_sha, ledger, ledger_sha,
              diagnostic, diagnostic_sha, downstream_manifest, downstream_manifest_sha,
              phase_dir, admission_root=None, require_admission_root=False):
    if source_manifest.get('state') != 'frozen' or downstream_manifest.get('state') != 'frozen':
        raise AcquisitionStopped('recovery_manifest_not_frozen')
    if source_manifest_sha != SOURCE_V4_MANIFEST_SHA256 or ledger_sha != SOURCE_V4_LEDGER_SHA256:
        raise AcquisitionStopped('recovery_not_original_v4_phase')
    if diagnostic_sha != SOURCE_DIAGNOSTIC_SHA256:
        raise AcquisitionStopped('recovery_not_frozen_diagnostic')
    if source_manifest_sha == downstream_manifest_sha:
        raise AcquisitionStopped('recovery_manifest_not_successor')
    _check_successor_lineage(downstream_manifest, downstream_manifest_sha)
    handoff = downstream_manifest.get('historical_supplemental_hp_run')
    handoff_binding_sha = None
    if handoff is not None:
        from .historical_handoff import canonical_sha as handoff_canonical_sha
        from .historical_handoff import verify_historical_supplemental_run

        verify_historical_supplemental_run(
            downstream_manifest, artifact_root=phase_dir.resolve().parents[1])
        handoff_binding_sha = handoff_canonical_sha(handoff)
    source_cache_dir, output_dir, current_admission_sha = _resolve_admission_roots(
        downstream_manifest, phase_dir, admission_root,
        require_admission_root=require_admission_root)
    if current_admission_sha is not None:
        _current_retention_usage(source_phase_dir=source_cache_dir,
            admission_root=output_dir, downstream_manifest=downstream_manifest,
            source_manifest=source_manifest)
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
    bindings = {
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
    if handoff_binding_sha is not None:
        bindings['historical_supplemental_hp_run_sha256'] = handoff_binding_sha
    if current_admission_sha is not None:
        current = downstream_manifest['current_manifest_cache_admission']
        accounted_roots = _current_accounting_roots(source_cache_dir, current)
        authorization_dir = output_dir / current['authorization_subdirectory']
        bindings.update({
            'source_phase_directory': str(source_cache_dir),
            'admission_directory': str(output_dir),
            'authorization_directory': str(authorization_dir),
            'accounted_roots': accounted_roots,
            'current_manifest_cache_admission_sha256': current_admission_sha,
            'metadata_retention_limit': current['metadata_retention_limit'],
            'global_retention_limit': current['global_retention_limit'],
        })
    return bindings


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
                   diagnostic_path, owner_exception_path, root_release_path,
                   admission_root=None):
    """Validate separate approvals and write only a cache-admission receipt."""
    from .run import checked_manifest

    source_manifest_path = Path(source_manifest_path).resolve()
    downstream_manifest_path = Path(downstream_manifest_path).resolve()
    _reject_symlink_components(phase_dir, 'recovery_source_cache_root_symlink')
    if admission_root is not None:
        _reject_symlink_components(admission_root, 'recovery_admission_root_symlink')
    phase_dir = Path(phase_dir).resolve()
    diagnostic_path = Path(diagnostic_path).resolve()
    if (phase_dir != SOURCE_PHASE_DIR.resolve() or diagnostic_path.parent != phase_dir
            or diagnostic_path.name != SOURCE_DIAGNOSTIC_NAME or not phase_dir.is_dir()):
        raise AcquisitionStopped('recovery_artifacts_not_colocated')
    lock_path = phase_dir / '.reader.lock'
    if lock_path.is_symlink():
        raise AcquisitionStopped('unexpected_metadata_symlink')
    try:
        # Current-manifest admission is read-only against the frozen V4 source:
        # never create a missing lock inside that tree. Keep the legacy V6
        # in-place behavior unchanged when no external admission root is used.
        lock_flags = os.O_RDWR | os.O_NOFOLLOW
        if admission_root is None:
            lock_flags |= os.O_CREAT
        lock_fd = os.open(lock_path, lock_flags, 0o600)
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
            downstream_manifest_sha=downstream_sha, phase_dir=phase_dir,
            admission_root=admission_root, require_admission_root=True)
        if downstream_manifest.get('current_manifest_cache_admission') is not None:
            _validate_current_authorization_paths(downstream_manifest,
                bindings['admission_directory'], owner_exception_path, root_release_path)
        owner_sha, root_sha = verify_owner_and_root(owner_path=owner_exception_path,
            root_path=root_release_path, binding=bindings)
        output_dir = Path(bindings.get('admission_directory', phase_dir)).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        if output_dir.is_symlink() or not output_dir.is_dir():
            raise AcquisitionStopped('recovery_admission_root_invalid')
        receipt = {'receipt_type': ADMISSION_TYPE, 'state': ADMISSION_STATE, **bindings,
            'owner_exception_sha256': owner_sha, 'root_release_sha256': root_sha,
            'diagnostic_file': diagnostic_path.name,
            'source_phase_directory': str(phase_dir),
            'admission_is_not_phase_completion': True}
        if output_dir != phase_dir:
            receipt['admission_directory'] = str(output_dir)
        raw = encoded(receipt)
        receipt_sha = sha256(raw)
        output = output_dir / f'cache-only-admission-{receipt_sha}.json'
        if any(item.is_symlink() for item in phase_dir.rglob('*')):
            raise AcquisitionStopped('unexpected_metadata_symlink')
        if any(item.is_symlink() for item in output_dir.rglob('*')):
            raise AcquisitionStopped('unexpected_admission_symlink')
        if bindings.get('current_manifest_cache_admission_sha256') is None:
            entries = list(phase_dir.rglob('*'))
            retained = sum(item.stat().st_size for item in entries if item.is_file())
            cap = source_manifest['budgets']['overture_metadata']['retained_bytes']
            if retained + (0 if output.exists() else len(raw)) > cap:
                raise AcquisitionStopped('combined_metadata_retention_budget')
        else:
            usage = _current_retention_usage(source_phase_dir=phase_dir,
                admission_root=output_dir, downstream_manifest=downstream_manifest,
                source_manifest=source_manifest)
            new_bytes = 0 if output.exists() else len(raw)
            if (usage['metadata_used'] + new_bytes > usage['metadata_limit']
                    or usage['global_used'] + new_bytes > usage['global_limit']):
                raise AcquisitionStopped('combined_current_admission_retention_budget')
        if output.exists():
            if output.read_bytes() != raw:
                raise AcquisitionStopped('immutable_admission_receipt_conflict')
        else:
            descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        if bindings.get('current_manifest_cache_admission_sha256') is not None:
            _current_retention_usage(source_phase_dir=phase_dir,
                admission_root=output_dir, downstream_manifest=downstream_manifest,
                source_manifest=source_manifest)
        if sha256((phase_dir / 'ledger.json').read_bytes()) != bindings['source_ledger_sha256']:
            raise AcquisitionStopped('recovery_source_ledger_mutated')
        return output, receipt_sha
    finally:
        lock.close()


def load_admitted_metadata(*, admission_path, source_manifest_path, downstream_manifest,
                           downstream_manifest_sha, owner_exception_path, root_release_path,
                           source_phase_dir=None, admission_root=None):
    """Revalidate an admission receipt before it can feed Overture development."""
    _reject_symlink_components(admission_path, 'recovery_admission_path_symlink')
    if source_phase_dir is not None:
        _reject_symlink_components(source_phase_dir, 'recovery_source_cache_root_symlink')
    if admission_root is not None:
        _reject_symlink_components(admission_root, 'recovery_admission_root_symlink')
    admission_path = Path(admission_path).resolve()
    current = downstream_manifest.get('current_manifest_cache_admission')
    if current is not None:
        if source_phase_dir is None or admission_root is None:
            raise AcquisitionStopped('recovery_current_admission_roots_required')
        phase_dir, output_dir, _contract_sha = _resolve_admission_roots(
            downstream_manifest, source_phase_dir, admission_root,
            require_admission_root=True)
        if admission_path.parent != output_dir:
            raise AcquisitionStopped('recovery_admission_root_mismatch')
        _validate_current_authorization_paths(downstream_manifest, output_dir,
            owner_exception_path, root_release_path)
    else:
        phase_dir = admission_path.parent
        if phase_dir != SOURCE_PHASE_DIR.resolve():
            raise AcquisitionStopped('recovery_artifacts_not_colocated')
        if source_phase_dir is not None and Path(source_phase_dir).resolve() != phase_dir:
            raise AcquisitionStopped('recovery_source_cache_root_mismatch')
        if admission_root is not None and Path(admission_root).resolve() != phase_dir:
            raise AcquisitionStopped('recovery_unbound_admission_root')
        output_dir = phase_dir
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
    if current is not None and receipt.get('admission_directory') != str(output_dir):
        raise AcquisitionStopped('recovery_admission_root_mismatch')
    source_raw = Path(source_manifest_path).read_bytes()
    source_manifest = json.loads(source_raw)
    ledger_raw = (phase_dir / 'ledger.json').read_bytes()
    ledger = json.loads(ledger_raw)
    diagnostic_raw = diagnostic_path.read_bytes()
    diagnostic = json.loads(diagnostic_raw)
    bindings = _bindings(source_manifest=source_manifest, source_manifest_sha=sha256(source_raw),
        ledger=ledger, ledger_sha=sha256(ledger_raw), diagnostic=diagnostic,
        diagnostic_sha=sha256(diagnostic_raw), downstream_manifest=downstream_manifest,
        downstream_manifest_sha=downstream_manifest_sha, phase_dir=phase_dir,
        admission_root=output_dir, require_admission_root=current is not None)
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
    if output_dir != phase_dir:
        expected_receipt['admission_directory'] = str(output_dir)
    if receipt != expected_receipt:
        raise AcquisitionStopped('invalid_cache_only_admission_contract')
    if sha256((phase_dir / 'ledger.json').read_bytes()) != bindings['source_ledger_sha256']:
        raise AcquisitionStopped('recovery_ledger_changed')
    if current is None:
        entries = list(phase_dir.rglob('*'))
        if any(item.is_symlink() for item in entries):
            raise AcquisitionStopped('unexpected_metadata_symlink')
        if sum(item.stat().st_size for item in entries if item.is_file()) > source_manifest['budgets']['overture_metadata']['retained_bytes']:
            raise AcquisitionStopped('combined_metadata_retention_budget')
    else:
        if any(item.is_symlink() for item in output_dir.rglob('*')):
            raise AcquisitionStopped('unexpected_admission_symlink')
        _current_retention_usage(source_phase_dir=phase_dir,
            admission_root=output_dir, downstream_manifest=downstream_manifest,
            source_manifest=source_manifest)
    return diagnostic['result'], ReplayBudget(phase_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--downstream-manifest', type=Path, required=True)
    parser.add_argument('--source-phase-dir', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--owner-exception', type=Path, required=True)
    parser.add_argument('--root-release', type=Path, required=True)
    parser.add_argument('--admission-root', type=Path)
    args = parser.parse_args()
    try:
        path, digest = make_admission(source_manifest_path=args.source_manifest,
            downstream_manifest_path=args.downstream_manifest, phase_dir=args.source_phase_dir,
            diagnostic_path=args.diagnostic, owner_exception_path=args.owner_exception,
            root_release_path=args.root_release, admission_root=args.admission_root)
        print(json.dumps({'state': ADMISSION_STATE, 'receipt_path': str(path),
                          'sha256': digest, 'metadata_requests_performed': 0,
                          'source_phase_completed': False}))
    except Exception as exc:
        print(json.dumps({'state': 'stopped', 'error_type': type(exc).__name__}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
