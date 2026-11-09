"""CRTKY-210: replay_audit classification tests (pure functions; no build run).

The live clean-tree check runs replay_audit.py itself (it needs uv + the
frozen raw inputs) and is recorded on the ticket, not here.
"""
import importlib.util
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('replay_audit', HERE / 'replay_audit.py')
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)


def test_clean_tree_yields_no_receipts():
    result = ra.classify([])
    assert result == {'receipts': set(), 'actions': set(), 'unmatched': []}


# Recorded fixture: the exact file list of the B-1 merge (f416e51), captured
# from a full-history checkout on 2026-11-09. Embedded so the ground-truth
# test never depends on the CI checkout's git depth (actions/checkout is
# depth=1; the merge's parents are absent there).
B1_CHANGED_FILES = ['app/public/data/bangkok/editorial/st.sena-ruam.json', 'app/public/data/bangkok/grid-1d6ed2ef00c3.bin', 'app/public/data/bangkok/grid-9f58a60ae7ca.bin', 'app/scripts/export-editorial.mjs', 'app/src/data/bangkok/districts.json', 'app/src/data/bangkok/editorial-index.json', 'app/src/data/bangkok/grid.json', 'app/src/data/bangkok/meta.json', 'app/src/data/bangkok/rail.json', 'app/src/data/bangkok/station-geometry.json', 'app/src/data/bangkok/stations.json', 'app/src/data/institutions/district-institutions.json', 'app/src/data/institutions/station-institutions.json', 'app/src/data/noise/quietness.json', 'app/src/lib/area-guide.test.ts', 'app/src/lib/institutions.test.ts', 'data/bangkok/enrichments-baseline.json', 'data/bangkok/population-baseline-refresh-2026-10-24.json', 'data/bangkok/refresh-inputs.json', 'data/bangkok/signals.json', 'data/institutions/district-institutions.json', 'data/institutions/station-institutions.json', 'data/noise/calibration.json', 'e2e/smoke.spec.ts', 'research/bangkok/editorial/2026-11-08-continuation-plan.md', 'research/bangkok/editorial/batches/2026-11-07-batch3-zcode-main/profiles/st.sena-ruam.json', 'research/bangkok/notes/2026-10-26-frozen-refresh-review.json', 'scripts/bangkok/enrichments.py', 'scripts/bangkok/rail.py', 'scripts/bangkok/static_data.py', 'scripts/bangkok/test_bangkok.py', 'scripts/bangkok/test_enrichments.py', 'scripts/fixtures/bangkok-build/signals.json', 'scripts/fixtures/bangkok-population/provenance-only.json', 'scripts/fixtures/normalization/bangkok-refresh-2026-10-24-golden.json', 'scripts/test_institutions.py', 'scripts/test_noise.py', 'scripts/test_normalization.py']

def test_b1_ground_truth_reproduces_the_hand_pinned_receipts():
    """classify() on the B-1 merge's changed files must return EXACTLY the
    receipt set hand-pinned on 2026-11-09 — no false positives, no gaps."""
    result = ra.classify(B1_CHANGED_FILES)
    assert result['receipts'] == ra.B1_EXPECTED_RECEIPTS, (
        f"missing={ra.B1_EXPECTED_RECEIPTS - result['receipts']} "
        f"unexpected={result['receipts'] - ra.B1_EXPECTED_RECEIPTS}")
    # the regeneration actions the session actually ran
    assert result['actions'] == {'institutions_exports.regenerate', 'noise_exports.regenerate'}
    # every changed data-bearing file is matched by a rule (code/test files are
    # informational by design)
    assert result['unmatched'] == []


def test_receipt_map_paths_exist():
    """Every exact-path rule must point at a real file — catches renames that
    would silently orphan a receipt."""
    for pattern, _r, _a in ra.FILE_RULES:
        if '*' in pattern or '?' in pattern:
            continue
        assert (ra.ROOT / pattern).exists(), f'receipt-map path missing on disk: {pattern}'


def test_receipt_catalog_is_complete():
    """Every receipt id referenced by a rule must have a catalog entry, and the
    catalog entry must name its guard test (the audit trail contract)."""
    rule_ids = {rid for _p, r_ids, _a in ra.FILE_RULES for rid in r_ids}
    assert rule_ids | set(ra.B1_EXPECTED_RECEIPTS) <= set(ra.RECEIPTS)
    for rid, text in ra.RECEIPTS.items():
        assert 'guard:' in text or rid == 'population.baselines.adoption', rid


def test_merge_changed_files_reads_real_history():
    """Exercises the --against-merge helper; needs full history (CI checks out
    depth=1, where the B-1 merge's parents are absent — skipped there)."""
    if Path(ra.ROOT / '.git/shallow').exists():
        import pytest
        pytest.skip('shallow checkout: B-1 merge parents not present')
    files = ra.merge_changed_files(ra.B1_MERGE)
    assert 'app/src/data/bangkok/stations.json' in files
    assert 'data/bangkok/signals.json' in files
    assert all(not f.startswith('commit') for f in files)
