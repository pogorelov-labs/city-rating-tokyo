"""Tests for the Bangkok district pipeline (pure-Python parts + committed data).

Runs in the lightweight CI `schema` job (pytest only — no numpy/shapely):
the geometry-heavy build.py is not imported; its *outputs* are checked.

    pytest scripts/bangkok/test_bangkok.py -v
"""
import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ratings as R  # noqa: E402
from static_data import HUBS, LINES, RU_NAMES  # noqa: E402

ROOT = HERE.parent.parent
EDITORIAL = json.loads((ROOT / "data" / "bangkok" / "editorial.json").read_text())["districts"]
APP = ROOT / "app" / "src" / "data" / "bangkok"
DISTRICTS = json.loads((APP / "districts.json").read_text())["districts"]
META = json.loads((APP / "meta.json").read_text())
SCHEMA = json.loads((ROOT / "packages" / "schema" / "constants.json").read_text())
RATING_KEYS = SCHEMA["rating_keys"]


# ── normalisation (mirrors scripts/compute-ratings.py) ──────────────────────

def test_percentile_spans_1_to_10():
    out = R.percentile_normalize({f"d{i}": float(i) for i in range(50)})
    assert min(out.values()) == 1
    assert max(out.values()) == 10
    assert out["d0"] == 1 and out["d49"] == 10


def test_percentile_invert_flips_order():
    out = R.percentile_normalize({"busy": 100.0, "quiet": 1.0}, invert=True)
    assert out["quiet"] == 10 and out["busy"] == 1


def test_percentile_ties_share_midpoint_rank():
    out = R.percentile_normalize({"a": 1.0, "b": 1.0, "c": 1.0, "d": 5.0})
    assert out["a"] == out["b"] == out["c"]
    assert 1 < out["a"] < out["d"]


def test_percentile_empty():
    assert R.percentile_normalize({}) == {}


def test_rent_affordability_range():
    assert R.rent_to_affordability(R.RENT_FLOOR_THB) == 10
    assert R.rent_to_affordability(R.RENT_CEILING_THB) == 1
    assert R.rent_to_affordability(3_000) == 10
    assert R.rent_to_affordability(90_000) == 1
    assert R.rent_to_affordability(None) is None
    assert R.rent_to_affordability(0) is None
    mid = (R.RENT_FLOOR_THB + R.RENT_CEILING_THB) / 2
    assert R.rent_to_affordability(mid) == 6  # 10 - 4.5 → round half to even is not used; 5.5 → 6


def test_weighted_median():
    assert R.weighted_median([10, 20, 30], [1, 1, 1]) == 20
    assert R.weighted_median([10, 20, 30], [10, 1, 1]) == 10
    with pytest.raises(ValueError):
        R.weighted_median([], [])


def test_composite_matches_app_semantics():
    ratings = {k: 5 for k in RATING_KEYS}
    ratings["food"] = 10
    weights = {k: 0 for k in RATING_KEYS}
    weights["food"] = 1
    weights["rent"] = 1
    assert R.composite(ratings, weights) == 7.5
    assert R.composite(ratings, {k: 0 for k in RATING_KEYS}) == 0.0


def test_anchor_index_rule():
    a = R.anchors([float(i) for i in range(1, 51)])
    assert a == {"p5": 3.0, "p50": 26.0, "p95": 48.0}


def test_two_source_confidence():
    assert R.two_source_confidence(True, True) == ("strong", ["overture", "osm"])
    assert R.two_source_confidence(True, False) == ("moderate", ["overture"])
    assert R.two_source_confidence(False, True) == ("moderate", ["osm"])
    assert R.two_source_confidence(False, False)[0] == "estimate"


# ── curated inputs ──────────────────────────────────────────────────────────

def test_editorial_covers_every_district():
    assert len(EDITORIAL) == 50
    assert set(EDITORIAL) == set(RU_NAMES)
    for slug, e in EDITORIAL.items():
        assert 5_000 <= e["rent_1br"] < e["rent_2br"] <= 120_000, slug
        assert 1 <= e["safety"] <= 10, slug
        assert e["aliases"] and all(a.strip() for a in e["aliases"]), slug


def test_line_metadata_is_complete():
    for lid, spec in LINES.items():
        for key in ("name_en", "name_th", "name_ja", "name_ru", "operator", "color", "kind"):
            assert spec[key], f"{lid}.{key}"
        assert spec["speed_kmh"] > 15 and spec["wait_min"] > 0
    assert set(HUBS) == {"siam", "asok", "silom", "rama9", "mochit"}


# ── committed outputs ──────────────────────────────────────────────────────

def test_export_matches_editorial_inputs():
    """Rent/safety ratings in the app are exactly what the editorial file implies."""
    for d in DISTRICTS:
        e = EDITORIAL[d["slug"]]
        assert d["ratings"]["rent"] == R.rent_to_affordability(e["rent_1br"]), d["slug"]
        assert d["ratings"]["safety"] == e["safety"], d["slug"]
        assert d["rent"]["one_bed"] == e["rent_1br"]
        assert d["confidence"]["rent"] == d["confidence"]["safety"] == "editorial"


def test_percentile_categories_are_uniform():
    """Percentile-normalised categories use the full 1-10 scale across 50 districts."""
    for key in ("food", "nightlife", "daily_essentials", "gym_sports", "vibe", "green", "transport", "crowd"):
        vals = [d["ratings"][key] for d in DISTRICTS]
        assert min(vals) == 1 and max(vals) == 10, key


def test_meta_medians_and_anchors():
    for key in RATING_KEYS:
        assert META["medians"][key] == R.median_int([d["ratings"][key] for d in DISTRICTS]), key
    scores = [R.composite(d["ratings"], SCHEMA["default_weights"]) for d in DISTRICTS]
    assert META["default_anchors"] == R.anchors(scores)
    assert META["rent_scale"] == {"floor": R.RENT_FLOOR_THB, "ceiling": R.RENT_CEILING_THB}


def test_commute_is_plausible():
    by = {d["slug"]: d for d in DISTRICTS}
    # Central districts sit next to their hub; the far east is > 1.5 h out.
    assert by["pathum-wan"]["transit_minutes"]["siam"] <= 20
    assert by["watthana"]["transit_minutes"]["asok"] <= 25
    assert by["nong-chok"]["min_transit"] >= 80
    for d in DISTRICTS:
        assert all(5 <= m <= 180 for m in d["transit_minutes"].values()), d["slug"]
        assert math.isclose(d["min_transit"], min(d["transit_minutes"].values()))
