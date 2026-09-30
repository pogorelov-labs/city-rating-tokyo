"""Tests for scripts/scrapers/slugs.py — NocoDB rows keyed by pre-CRTKY-113 slugs."""
import importlib.util
import json
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("slugs", _THIS_DIR / "scrapers" / "slugs.py")
slugs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(slugs)

REDIRECTS = {"kouenji-old": "koenji", "oomiya-old": "omiya"}


class TestIndexBySlug:
    def test_current_slugs_pass_through(self):
        idx, remapped = slugs.index_by_slug([{"slug": "shinjuku", "v": 1}], REDIRECTS)
        assert idx == {"shinjuku": {"slug": "shinjuku", "v": 1}} and remapped == 0

    def test_old_slug_is_remapped(self):
        idx, remapped = slugs.index_by_slug([{"slug": "kouenji-old", "v": 1}], REDIRECTS)
        assert idx["koenji"]["v"] == 1 and "kouenji-old" not in idx and remapped == 1

    def test_remapped_row_carries_current_slug_and_input_is_not_mutated(self):
        row = {"slug": "kouenji-old", "v": 1}
        idx, _ = slugs.index_by_slug([row], REDIRECTS)
        assert idx["koenji"]["slug"] == "koenji"
        assert row["slug"] == "kouenji-old"

    def test_row_under_current_slug_wins_over_remapped_row(self):
        rows = [{"slug": "kouenji-old", "v": "stale"}, {"slug": "koenji", "v": "fresh"}]
        idx, remapped = slugs.index_by_slug(rows, REDIRECTS)
        assert idx["koenji"]["v"] == "fresh" and remapped == 0

    def test_rows_without_slug_are_skipped(self):
        idx, _ = slugs.index_by_slug([{"slug": ""}, {"x": 1}, {"slug": None}], REDIRECTS)
        assert idx == {}

    def test_custom_key(self):
        idx, _ = slugs.index_by_slug([{"station": "oomiya-old"}], REDIRECTS, key="station")
        assert "omiya" in idx


class TestRealRedirectMap:
    """Properties the one-step remap relies on."""

    redirects = slugs.load_slug_redirects()
    current = {s["slug"] for s in json.loads((_THIS_DIR.parent / "data" / "stations.json").read_text())}

    def test_every_target_is_a_current_station(self):
        assert set(self.redirects.values()) <= self.current

    def test_no_old_slug_is_still_a_current_station(self):
        # Otherwise a remap could steal another station's row.
        assert not set(self.redirects) & self.current

    def test_no_chains(self):
        assert not set(self.redirects) & set(self.redirects.values())
