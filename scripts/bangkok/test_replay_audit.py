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


def test_b1_ground_truth_reproduces_the_hand_pinned_receipts():
    """classify() on the B-1 merge's changed files must return EXACTLY the
    receipt set hand-pinned on 2026-11-09 — no false positives, no gaps."""
    changed = ra.merge_changed_files(ra.B1_MERGE)
    result = ra.classify(changed)
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
    files = ra.merge_changed_files(ra.B1_MERGE)
    assert 'app/src/data/bangkok/stations.json' in files
    assert 'data/bangkok/signals.json' in files
    assert all(not f.startswith('commit') for f in files)
