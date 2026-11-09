#!/usr/bin/env python3
"""CRTKY-210: one-shot replay audit — which pipeline receipts does a rebuild invalidate?

The B-1 intended data change (2026-11-09) required five rounds of manual
receipt re-pinning because each drift guard pins a different file. This tool
encodes that map so the next intended change is one command:

  uv run scripts/bangkok/replay_audit.py                    # live audit: replay in a temp
                                                            # worktree, diff vs HEAD, list receipts
  uv run scripts/bangkok/replay_audit.py --against-merge <merge-sha>
                                                            # classify a recorded merge diff (no replay)
  uv run scripts/bangkok/replay_audit.py --emit checklist.md

The live audit never writes the real tree: it replays inside a temporary
`git worktree` (raw/ is symlinked in), diffs, and removes the worktree.
Receipt actions are REPORTED, never executed — re-pinning stays a reviewed,
documented change. Run from a clean tree at HEAD.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Receipt catalog: what each re-pin touches, and the guard test that catches
# a stale pin. IDs are stable; the B-1 ground-truth test (test_replay_audit.py)
# pins the mapping.
# ---------------------------------------------------------------------------
RECEIPTS = {
    'refresh_baseline.signatures.districts':
        'data/bangkok/population-baseline-refresh-2026-10-24.json _meta.unchanged_signatures.districts '
        '(snapshot_signature of current app districts.json) — guard: test_population_snapshot.py',
    'refresh_baseline.signatures.signals':
        'refresh baseline _meta.unchanged_signatures.signals (snapshot_signature of current data/bangkok/signals.json) — guard: test_population_snapshot.py',
    'refresh_baseline.signatures.meta':
        'refresh baseline _meta.unchanged_signatures.meta (snapshot_signature of current app meta.json) — guard: test_population_snapshot.py',
    'refresh_baseline.signals_sha256':
        'refresh baseline _meta.signals_sha256 (sha256 of the reconstructed original signals) — guard: rebuild-population validate_crowd_state',
    'refresh_baseline.inputs_manifest_sha256':
        '..._meta.inputs_manifest_sha256 (sha256 of data/bangkok/refresh-inputs.json) — guard: test_refresh_inputs.py',
    'refresh_baseline.geometry_sha256':
        '..._meta.geometry_sha256 — guard: rebuild-population geometry preflight',
    'refresh_inputs.manifest.entry':
        'data/bangkok/refresh-inputs.json files[<path>] = {bytes, sha256} — guard: test_refresh_inputs manifest loop',
    'fixtures.bangkok_build_signals':
        'scripts/fixtures/bangkok-build/signals.json must byte-equal data/bangkok/signals.json — guard: test_frozen_signals_snapshot',
    'normalization_golden.refresh':
        'scripts/fixtures/normalization/bangkok-refresh-2026-10-24-golden.json output (recomputed aggregates) — guard: test_bangkok_committed_aggregate_golden',
    'review.evidence.golden_changes':
        'research/bangkok/notes/2026-10-26-frozen-refresh-review.json golden_changes/removed_keys rows — guard: test_bangkok_refresh_golden_changes_have_complete_review_evidence',
    'provenance_only.fixture_entry':
        'scripts/fixtures/bangkok-population/provenance-only.json files[<path>] excluding_allowed_hash_fields_sha256 '
        '(masked: app districts/geometry/stations input rows are placeholders) — guard: test_cross_city_outputs_only_change_authorized_bangkok_provenance_hashes',
    'population.baselines.adoption':
        'data/bangkok/population-baseline.json (adoption pins the FIXTURE-era docs; only fixture changes re-pin it)',
}

# Regeneration actions: the generator is the source of truth for these export
# artifacts; run its build and commit the output (provenance stamps update).
ACTIONS = {
    'institutions_exports.regenerate':
        'run scripts/institutions/compute-institutions.py build() and write district-/station-institutions.json to BOTH data/institutions/ and app/src/data/institutions/',
    'noise_exports.regenerate':
        'run scripts/noise/build.py and write app/src/data/noise/quietness.json + data/noise/{calibration,tmg-matched}.json',
}

# changed-path pattern -> (receipt ids, action ids). Exact per-file entries where
# the B-1 session proved granularity matters; globs elsewhere.
FILE_RULES: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
    # population receipt targets themselves
    ('data/bangkok/population-baseline-refresh-2026-10-24.json', (), ()),
    ('data/bangkok/population-baseline.json', (), ()),
    # app snapshot documents
    ('app/src/data/bangkok/districts.json',
     ('refresh_baseline.signatures.districts',), ('institutions_exports.regenerate',)),
    ('app/src/data/bangkok/meta.json',
     ('refresh_baseline.signatures.meta',), ()),
    ('data/bangkok/signals.json',
     ('refresh_baseline.signatures.signals', 'refresh_baseline.signals_sha256',
      'fixtures.bangkok_build_signals', 'normalization_golden.refresh', 'review.evidence.golden_changes'),
     ()),
    ('app/src/data/bangkok/geometry.json',
     ('refresh_baseline.geometry_sha256',), ()),
    # regenerated snapshot set: self-consistent, no external receipts
    ('app/src/data/bangkok/grid.json', (), ()),
    ('app/src/data/bangkok/rail.json', (), ()),
    ('app/src/data/bangkok/station-geometry.json', (), ()),
    ('app/src/data/bangkok/stations.json',
     (), ('institutions_exports.regenerate', 'noise_exports.regenerate')),
    # regenerated export artifacts (formatting/provenance changes ride along)
    ('app/src/data/institutions/district-institutions.json',
     ('provenance_only.fixture_entry',), ()),
    ('data/institutions/district-institutions.json',
     ('provenance_only.fixture_entry', 'refresh_inputs.manifest.entry'), ()),
    # station-institutions content only ever changes in MASKED input rows ->
    # masked fixture hash is unchanged; listed for visibility, no re-pin
    ('app/src/data/institutions/station-institutions.json', (), ()),
    ('data/institutions/station-institutions.json', ('refresh_inputs.manifest.entry',), ()),
    ('app/src/data/noise/quietness.json', ('provenance_only.fixture_entry',), ()),
    ('data/noise/calibration.json', ('provenance_only.fixture_entry',), ()),
    ('data/noise/tmg-matched.json', (), ()),
    # manifest + pinned inputs
    ('data/bangkok/refresh-inputs.json', ('refresh_baseline.inputs_manifest_sha256',), ()),
    ('data/bangkok/enrichments-baseline.json',
     ('refresh_inputs.manifest.entry', 'refresh_baseline.inputs_manifest_sha256'), ()),
    ('data/bangkok/editorial.json', ('refresh_inputs.manifest.entry',), ()),
    ('data/bangkok/flood.json', ('refresh_inputs.manifest.entry',), ()),
    ('data/bangkok/rent-overrides.json', ('refresh_inputs.manifest.entry',), ()),
    ('data/bangkok/population-source.json', ('refresh_inputs.manifest.entry',), ()),
    ('data/bangkok/descriptions/*.json', ('refresh_inputs.manifest.entry',), ()),
    # fixtures
    ('scripts/fixtures/bangkok-population/adoption/*',
     ('population.baselines.adoption',), ()),
    ('scripts/fixtures/bangkok-population/provenance-only.json', (), ()),
    ('scripts/fixtures/normalization/bangkok-refresh-2026-10-24-golden.json',
     ('review.evidence.golden_changes',), ()),
    ('scripts/fixtures/normalization/bangkok-golden.json', (), ()),
    ('scripts/fixtures/bangkok-build/signals.json',
     ('fixtures.bangkok_build_signals',), ()),
]

# Informational only: no pipeline receipts (editorial surface, packed bin, code).
NO_RECEIPT_PREFIXES = (
    'app/public/data/bangkok/editorial/', 'app/src/data/bangkok/editorial-index.json',
    'app/public/data/bangkok/grid-', 'research/', 'scripts/bangkok/',
    'scripts/test_', 'scripts/normalization_replay.py', 'app/scripts/',
    '.github/', 'e2e/', 'packages/', 'mcp/', 'app/src/lib/',
)


def classify(changed_files: list[str]) -> dict[str, set[str]]:
    receipts: set[str] = set()
    actions: set[str] = set()
    unmatched: list[str] = []
    for path in changed_files:
        hit = False
        for pattern, r_ids, a_ids in FILE_RULES:
            if fnmatch.fnmatch(path, pattern):
                receipts.update(r_ids)
                actions.update(a_ids)
                hit = True
                break
        if not hit and not path.startswith(NO_RECEIPT_PREFIXES):
            unmatched.append(path)
    return {'receipts': receipts, 'actions': actions, 'unmatched': unmatched}


# Recorded ground truth: the receipts actually hand-pinned during the B-1
# replay (2026-11-09) for the files changed by merge f416e51. The unit test
# asserts classify() reproduces exactly this set from that diff's file list.
B1_MERGE = 'f416e51'
B1_EXPECTED_RECEIPTS = {
    'refresh_baseline.signatures.districts',
    'refresh_baseline.signatures.signals',
    'refresh_baseline.signatures.meta',
    'refresh_baseline.signals_sha256',
    'refresh_baseline.inputs_manifest_sha256',
    'refresh_inputs.manifest.entry',
    'fixtures.bangkok_build_signals',
    'normalization_golden.refresh',
    'review.evidence.golden_changes',
    'provenance_only.fixture_entry',
}


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def merge_changed_files(merge_sha: str) -> list[str]:
    out = git('diff', '--name-only', f'{merge_sha}^1', merge_sha)
    return [line for line in out.splitlines() if line.strip()]


def live_audit(emit: Path | None, keep: bool) -> int:
    dirty = git('status', '--porcelain').strip()
    if dirty:
        print('REFUSING: working tree is not clean — the audit compares a replay against HEAD.')
        for line in dirty.splitlines()[:10]:
            print('  ', line)
        return 2
    # 1. frozen-input verification in the real tree (fail fast)
    sys.path.insert(0, str(ROOT / 'scripts'))
    from bangkok.refresh_inputs import verify_inputs  # noqa: E402
    verify_inputs(ROOT, ROOT / 'data/bangkok/refresh-inputs.json')
    print('frozen inputs: 90/90 verified')

    # 2. replay in a temporary worktree (real tree untouched)
    tmp = Path(subprocess.run(['mktemp', '-d'], capture_output=True, text=True, check=True).stdout.strip())
    git('worktree', 'add', '--detach', str(tmp), 'HEAD')
    try:
        raw_link = tmp / 'data/bangkok/raw'
        raw_link.symlink_to(ROOT / 'data/bangkok/raw', target_is_directory=True)
        print('replaying build.py in worktree ...')
        proc = subprocess.run(
            ['uv', 'run', 'scripts/bangkok/build.py', '--inputs-manifest', 'data/bangkok/refresh-inputs.json'],
            cwd=tmp, capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stdout[-2000:])
            print(proc.stderr[-2000:])
            print('REFUSING: replay failed inside the worktree (see above).')
            return 2
        changed = [line[3:] if line[:3] in ('?? ', 'M  ', ' M ', 'AM ', ' D ') else line
                   for line in git('status', '--porcelain', cwd=tmp).splitlines() if line.strip()]
        changed = sorted({c.split(' -> ')[-1] for c in changed})
        # provisioning artifact: the raw/ symlink the audit itself creates
        # (gitignore's trailing-slash rule doesn't match a symlink)
        changed = [c for c in changed if c != 'data/bangkok/raw']
    finally:
        if keep:
            print(f'worktree kept at {tmp}')
        else:
            git('worktree', 'remove', '--force', str(tmp))

    # 3. classify
    result = classify(changed)
    print(f'\nreplay vs HEAD: {len(changed)} file(s) changed')
    for c in changed:
        print('  M', c)
    if not changed:
        print('\nCLEAN TREE: replay is byte-identical to HEAD — zero receipts need re-pinning.')
        return 0
    print('\nRECEIPTS TO RE-PIN (review each; never apply blindly):')
    for r in sorted(result['receipts']):
        print(f'  - {r}: {RECEIPTS[r]}')
    if result['actions']:
        print('\nREGENERATION ACTIONS:')
        for a in sorted(result['actions']):
            print(f'  - {a}: {ACTIONS[a]}')
    if result['unmatched']:
        print('\nUNMATCHED CHANGED FILES (no rule — extend FILE_RULES):')
        for u in result['unmatched']:
            print('  ?', u)
    if emit:
        lines = ['# Replay audit checklist', '', f'Changed files: {len(changed)}', '', '## Receipts']
        lines += [f'- [ ] {r}: {RECEIPTS[r]}' for r in sorted(result['receipts'])]
        lines += ['', '## Actions']
        lines += [f'- [ ] {a}: {ACTIONS[a]}' for a in sorted(result['actions'])]
        emit.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'\nchecklist written: {emit}')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--against-merge', metavar='SHA', help='classify a recorded merge diff instead of a live replay')
    ap.add_argument('--emit', type=Path, help='write the re-pin checklist markdown')
    ap.add_argument('--keep-worktree', action='store_true', help='keep the temp worktree for inspection')
    args = ap.parse_args()
    if args.against_merge:
        result = classify(merge_changed_files(args.against_merge))
        print(json.dumps({'receipts': sorted(result['receipts']),
                          'actions': sorted(result['actions']),
                          'unmatched': sorted(result['unmatched'])}, indent=1))
        return
    raise SystemExit(live_audit(args.emit, args.keep_worktree))


if __name__ == '__main__':
    main()
