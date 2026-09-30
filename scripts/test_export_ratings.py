"""
Tests for scripts/export-ratings.py — the daily_essentials backfill for
AI-researched entries (CRTKY-129).

export-ratings.py imports `utils`, which exits when NOCODB_API_TOKEN is unset,
so we stub it before loading the module (same approach as
test_compute_ratings.py). The functions under test are pure text transforms.
"""
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

if "utils" not in sys.modules:
    utils_stub = types.ModuleType("utils")
    utils_stub.NocoDB = object
    utils_stub.load_stations = lambda: []
    sys.modules["utils"] = utils_stub

_THIS_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("export_ratings", _THIS_DIR / "export-ratings.py")
er = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(er)

DEMO_RATINGS = _THIS_DIR.parent / "app" / "src" / "data" / "demo-ratings.ts"

# Shape of an AI-researched entry as it exists in demo-ratings.ts today:
# legacy key order, no daily_essentials anywhere.
AI_ENTRY = """  abiko: {
    ratings: { food: 5, nightlife: 3, transport: 6, rent: 9, safety: 9, green: 8, gym_sports: 5, vibe: 6, crowd: 9 },
    transit_minutes: { shibuya: 75, shinjuku: 70, tokyo: 55, ikebukuro: 65, shinagawa: 75 },
    description: { atmosphere: "a", landmarks: "b", food: "c", nightlife: "d" },
    confidence: { food: 'editorial', rent: 'strong', crowd: 'editorial' },
    sources: { food: ['ai_research'], rent: ['suumo'], crowd: ['ai_research'] },
    data_date: '2026-04',
  },"""


def computed(de=6, conf="strong", srcs=("osm_livability",)):
    return {
        "daily_essentials": de,
        "confidence": json.dumps({"daily_essentials": conf}),
        "sources": json.dumps({"daily_essentials": list(srcs)}),
    }


def block(text, field):
    return re.search(rf"{field}: \{{([^{{}}]*)\}}", text).group(1)


class TestBackfillDailyEssentials:
    def test_fills_rating_confidence_and_sources_from_computed(self):
        out, status = er.backfill_daily_essentials(AI_ENTRY, computed())
        assert status == "filled"
        assert "daily_essentials: 6" in block(out, "ratings")
        assert "daily_essentials: 'strong'" in block(out, "confidence")
        assert "daily_essentials: ['osm_livability']" in block(out, "sources")

    def test_filled_value_is_computed_not_editorial(self):
        # No researcher rated this category, so nothing is editorial about it.
        out, _ = er.backfill_daily_essentials(AI_ENTRY, computed(conf="moderate"))
        assert "daily_essentials: 'moderate'" in block(out, "confidence")
        assert "editorial" not in re.search(r"daily_essentials: '(\w+)'", out).group(1)

    def test_other_keys_untouched(self):
        out, _ = er.backfill_daily_essentials(AI_ENTRY, computed())
        assert "food: 5, nightlife: 3, transport: 6" in out
        assert "rent: 'strong'" in out and "rent: ['suumo']" in out
        assert 'atmosphere: "a"' in out

    def test_idempotent(self):
        once, _ = er.backfill_daily_essentials(AI_ENTRY, computed())
        twice, status = er.backfill_daily_essentials(once, computed())
        assert twice == once
        assert status == "present"

    def test_missing_when_no_computed_value(self):
        out, status = er.backfill_daily_essentials(AI_ENTRY, None)
        assert status == "missing"
        assert out == AI_ENTRY

    def test_researcher_value_that_agrees_inherits_computed_metadata(self):
        entry = AI_ENTRY.replace("crowd: 9 }", "crowd: 9, daily_essentials: 6 }")
        out, status = er.backfill_daily_essentials(entry, computed(de=6))
        assert status == "present"
        assert "daily_essentials: 'strong'" in block(out, "confidence")

    def test_researcher_value_that_disagrees_is_editorial(self):
        entry = AI_ENTRY.replace("crowd: 9 }", "crowd: 9, daily_essentials: 3 }")
        out, _ = er.backfill_daily_essentials(entry, computed(de=6))
        assert "daily_essentials: 3" in block(out, "ratings")  # researcher value kept
        assert "daily_essentials: 'editorial'" in block(out, "confidence")
        assert "daily_essentials: ['ai_research']" in block(out, "sources")

    def test_parse_ai_ratings_sees_the_filled_value(self):
        out, _ = er.backfill_daily_essentials(AI_ENTRY, computed(de=7))
        assert er.parse_ai_ratings(out)["daily_essentials"] == 7


class TestBackfillOnRealEntries:
    """Run the backfill over every real AI entry: only daily_essentials may change."""

    def test_every_real_ai_entry_gets_exactly_one_key_per_object(self):
        entries = er.parse_existing_ai_entries(DEMO_RATINGS)
        assert len(entries) >= 250
        for slug, text in entries.items():
            out, status = er.backfill_daily_essentials(text, computed())
            assert status in ("filled", "present"), slug
            for field in ("ratings", "confidence", "sources"):
                assert block(out, field).count("daily_essentials:") == 1, (slug, field)
            # Removing the injected fragments must give back the original text.
            restored = re.sub(r", daily_essentials: (\d+|'\w+'|\[[^\]]*\]) \}", " }", out)
            assert restored == text, slug


def computed_rent(value=7, conf="strong", srcs=("suumo",)):
    return {
        "rent": value,
        "confidence": json.dumps({"rent": conf}),
        "sources": json.dumps({"rent": list(srcs)}),
    }


EDITORIAL_RENT_ENTRY = AI_ENTRY.replace(
    "confidence: { food: 'editorial', rent: 'strong', crowd: 'editorial' }",
    "confidence: { food: 'editorial', rent: 'editorial', crowd: 'editorial' }",
).replace(
    "sources: { food: ['ai_research'], rent: ['suumo'], crowd: ['ai_research'] }",
    "sources: { food: ['ai_research'], rent: ['ai_research'], crowd: ['ai_research'] }",
)


class TestStationLevelRent:
    """D3b (2026-09-30): station-level rent data wins over the editorial rating."""

    def test_suumo_rating_and_metadata_replace_editorial(self):
        out, changed = er.apply_station_level_rent(EDITORIAL_RENT_ENTRY, computed_rent(value=7))
        assert changed
        assert re.search(r"\brent: 7\b", block(out, "ratings"))
        assert "rent: 'strong'" in block(out, "confidence")
        assert "rent: ['suumo']" in block(out, "sources")

    def test_area_level_rent_leaves_editorial_alone(self):
        for srcs in (("estat",), ("ward_average",), ("distance_regression",)):
            out, changed = er.apply_station_level_rent(
                EDITORIAL_RENT_ENTRY, computed_rent(conf="moderate", srcs=srcs))
            assert not changed and out == EDITORIAL_RENT_ENTRY, srcs

    def test_no_computed_row_is_a_no_op(self):
        assert er.apply_station_level_rent(EDITORIAL_RENT_ENTRY, None) == (EDITORIAL_RENT_ENTRY, False)

    def test_only_rent_keys_change(self):
        out, _ = er.apply_station_level_rent(EDITORIAL_RENT_ENTRY, computed_rent(value=7))
        assert "food: 5, nightlife: 3, transport: 6" in out
        assert "food: 'editorial'" in out and "crowd: ['ai_research']" in out

    def test_idempotent(self):
        once, _ = er.apply_station_level_rent(EDITORIAL_RENT_ENTRY, computed_rent())
        twice, changed = er.apply_station_level_rent(once, computed_rent())
        assert twice == once and not changed

    def test_real_entries_only_rent_changes(self):
        entries = er.parse_existing_ai_entries(DEMO_RATINGS)
        changed_count = 0
        for slug, text in entries.items():
            out, changed = er.apply_station_level_rent(text, computed_rent(value=4))
            changed_count += changed
            strip = lambda t: re.sub(r"\brent: (\d+|'\w+'|\[[^\]]*\])", "rent: X", t)
            assert strip(out) == strip(text), slug
        assert changed_count > 150  # ~190 editorial-labelled entries today
