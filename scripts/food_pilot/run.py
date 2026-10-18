"""Explicitly gated acquisition phases; never run at import time."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .acquire_osm import encoded
from .bounded import AcquisitionStopped, Budget, ReplayBudget
from .hotpepper import acquire_sites, confirmation_checkpoint
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
        if not datetime.fromisoformat(checkpoint['batch_eligible_from']) <= now <= datetime.fromisoformat(checkpoint['batch_eligible_until']):
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


def immutable_result(directory, value, retained_limit):
    raw = encoded(value)
    digest = hashlib.sha256(raw).hexdigest()
    path = directory/f'result-{digest}.json'
    if path.exists():
        if path.read_bytes() != raw:
            raise AcquisitionStopped('immutable_result_conflict')
    else:
        used=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())
        if used+len(raw)>retained_limit:
            raise AcquisitionStopped('retained_result_budget')
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--execution-gate', type=Path, required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--primary-freeze', type=Path)
    parser.add_argument('--prior-prescreen', type=Path)
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
    root = args.output_root.resolve()
    if root.is_relative_to(ROOT):
        parser.error('Raw pilot data must stay outside git')
    manifest, manifest_hash = checked_manifest(args.manifest)
    checked_gate(args.execution_gate, manifest_hash, args.phase)
    if args.phase not in manifest['budgets'] or not isinstance(manifest['budgets'][args.phase],dict):
        raise AcquisitionStopped('unknown_phase')
    if args.phase.endswith('holdout'):
        if args.primary_freeze is None:
            raise AcquisitionStopped('holdout_locked')
        primary_gate(args.primary_freeze, manifest_hash, manifest)
    if datetime.now(timezone.utc) >= datetime.fromisoformat(manifest['source_window']['core_hp_complete_before'].replace('Z','+00:00')):
        raise AcquisitionStopped('frozen_pilot_window_expired')
    prior = json.loads(args.prior_prescreen.read_text()) if args.prior_prescreen else None
    checkpoint = None
    if prior is not None:
        prior = checked_confirmation_prior(prior, manifest_hash)
    if args.phase == 'hp_confirmation':
        checkpoint = confirmation_checkpoint(prior)
    sites = phase_sites(manifest, args.phase, prior)
    phase_dir = root/args.phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    retained = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    already = sum(p.stat().st_size for p in phase_dir.rglob('*') if p.is_file())
    if retained-already+manifest['budgets'][args.phase]['retained_bytes'] > manifest['budgets']['total_retained_bytes']:
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
    with Budget(phase_dir, manifest['budgets'][args.phase], manifest_hash, resume=args.resume,
                absolute_deadline=manifest['source_window']['core_hp_complete_before'],
                identity_windows=windows, completion_window=completion_window) as budget:
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
        except Exception as exc:
            result={'status':'incomplete','error_type':type(exc).__name__}
        envelope={'phase':args.phase,'manifest_sha256':manifest_hash,'result':result}
        path,digest=immutable_result(phase_dir,envelope,budget.limits['retained_bytes'])
        if args.phase=='hp_prescreen' and 'stations' in result:
            immutable_result(phase_dir,{'manifest_sha256':manifest_hash,'prescreen_result_sha256':digest,
                                      'zero_confirmation':confirmation_checkpoint(result)},budget.limits['retained_bytes'])
        print(json.dumps({'phase':args.phase,'status':result['status'],'result_path':str(path),'sha256':digest}),flush=True)
        if result['status'] != 'complete':
            raise AcquisitionStopped('phase_incomplete_no_budget_extension')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Never print exception messages, URLs, request headers or credentials.
        print(json.dumps({'status':'stopped','error_type':type(exc).__name__}),flush=True)
        raise SystemExit(1) from None
