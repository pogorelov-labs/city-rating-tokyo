"""Tests for the Bangkok district pipeline (pure-Python parts + committed data).

Runs in the lightweight CI `schema` job (pytest only — no numpy/shapely):
the geometry-heavy build.py is not imported; its *outputs* are checked.

    pytest scripts/bangkok/test_bangkok.py -v
"""
import gzip
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
AREAS = json.loads((APP / "stations.json").read_text())["areas"]
RAIL = json.loads((APP / "rail.json").read_text())
GRID = json.loads((APP / "grid.json").read_text())
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


def test_weighted_percentile_spans_1_to_10():
    out = R.weighted_percentile_normalize([float(i) for i in range(20)], [1.0] * 20)
    assert out[0] == 1 and out[-1] == 10
    assert out == sorted(out)


def test_weighted_percentile_follows_weight():
    # Two heavy cells at the bottom push a light middle value up the scale:
    # the rating says "better than most places people live".
    vals = [1.0, 2.0, 3.0, 4.0]
    even = R.weighted_percentile_normalize(vals, [1, 1, 1, 1])
    heavy_low = R.weighted_percentile_normalize(vals, [10, 1, 1, 1])
    assert heavy_low[1] > even[1]
    assert R.weighted_percentile_normalize(vals, [1, 1, 1, 1], invert=True) == even[::-1]


def test_weighted_percentile_ties_and_empty():
    out = R.weighted_percentile_normalize([0.0, 0.0, 0.0, 5.0], [0.1, 0.1, 0.1, 1.0])
    assert out[0] == out[1] == out[2] == 1 and out[3] == 10
    assert R.weighted_percentile_normalize([], []) == []


def test_weighted_anchors():
    a = R.weighted_anchors([1.0, 5.0, 9.0], [1.0, 1.0, 1.0])
    assert a == {"p5": 1.0, "p50": 5.0, "p95": 9.0}
    assert R.weighted_anchors([1.0, 5.0, 9.0], [0.01, 0.01, 1.0])["p50"] == 9.0


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


# ── station areas ──────────────────────────────────────────────────────────

def test_station_areas_cover_every_station_inside_bangkok():
    inside = {st["id"] for st in RAIL["stations"] if st["district"]}
    members = [sid for a in AREAS for sid in a["station_ids"]]
    assert len(members) == len(set(members))
    assert set(members) == inside
    assert META["station_area_count"] == len(AREAS)
    by_area = {a["id"]: a for a in AREAS}
    for st in RAIL["stations"]:
        assert (st["area"] in by_area) if st["district"] else st["area"] is None, st["id"]


def test_station_area_ratings():
    for key in ("food", "nightlife", "daily_essentials", "gym_sports", "vibe", "green", "transport", "crowd"):
        vals = [a["ratings"][key] for a in AREAS]
        assert min(vals) == 1 and max(vals) == 10, key
    for a in AREAS:
        assert a["ratings"]["rent"] == R.rent_to_affordability(a["rent"]["one_bed"]), a["id"]
        assert 1 <= a["ratings"]["safety"] <= 10
        assert a["confidence"]["rent"] == a["confidence"]["safety"] == "editorial"
        assert a["min_transit"] == min(a["transit_minutes"].values())
    for key in RATING_KEYS:
        assert META["station_medians"][key] == R.median_int([a["ratings"][key] for a in AREAS]), key
    scores = [R.composite(a["ratings"], SCHEMA["default_weights"]) for a in AREAS]
    assert META["station_default_anchors"] == R.anchors(scores)


def test_interchanges_merge_only_across_lines():
    by_id = {a["id"]: a for a in AREAS}
    assert by_id["asok"]["station_ids"] == ["asok", "sukhumvit"]
    assert set(by_id["ha-yaek-lat-phrao"]["station_ids"]) == {"ha-yaek-lat-phrao", "phahon-yothin"}
    assert "chong-nonsi" in by_id and "saint-louis" in by_id  # 436 m apart, same line


def test_no_area_holds_two_stops_of_one_line():
    """Interchange merging never chains same-line neighbours into one area."""
    line_of = {st["id"]: set(st["lines"]) for st in RAIL["stations"]}
    for a in AREAS:
        seen: set[str] = set()
        for sid in a["station_ids"]:
            assert not (line_of[sid] & seen), (a["id"], sid)
            seen |= line_of[sid]


def test_station_commute_is_plausible():
    by_id = {a["id"]: a for a in AREAS}
    assert by_id["siam"]["transit_minutes"]["siam"] == 0
    assert by_id["asok"]["transit_minutes"]["asok"] == 0
    assert by_id["chit-lom"]["transit_minutes"]["siam"] <= 8
    assert by_id["min-buri"]["min_transit"] >= 40


def test_commons_credits_are_one_line():
    for item in [*DISTRICTS, *AREAS]:
        if item.get("image"):
            artist = item["image"]["artist"]
            assert len(artist) <= 60 and "machine-readable" not in artist, artist


# ── 200 m grid ────────────────────────────────────────────────────────────

def _decode_grid():
    packed = (ROOT / "app" / "public" / GRID["file"].lstrip("/")).read_bytes()
    assert len(packed) == GRID["bytes"]
    raw = gzip.decompress(packed)
    nx, ny = GRID["nx"], GRID["ny"]
    size = nx * ny
    assert len(raw) == size * len(GRID["fields"])
    planes = {}
    for k, name in enumerate(GRID["fields"]):
        src = raw[k * size:(k + 1) * size]
        out = bytearray(size)
        for r in range(ny):
            acc = 0
            for c in range(nx):
                acc = (acc + src[r * nx + c]) & 0xFF
                out[r * nx + c] = acc
        planes[name] = out
    return planes


PLANES = _decode_grid()
INSIDE = [i for i, d in enumerate(PLANES["district"]) if d]


def test_grid_header_matches_data():
    assert len(INSIDE) == GRID["cells"] == META["grid_cell_count"]
    assert GRID["districts"] == [d["slug"] for d in DISTRICTS]
    assert GRID["stations"] == [st["id"] for st in RAIL["stations"]]
    assert GRID["areas"] == [a["id"] for a in AREAS]
    assert GRID["medians"] == META["grid_medians"]
    assert GRID["cell_m"] == 200


def test_grid_values_in_range():
    for key in ("food", "nightlife", "daily_essentials", "gym_sports", "vibe", "green", "transport", "crowd"):
        plane = PLANES[key]
        vals = [plane[i] for i in INSIDE]
        assert min(vals) == 1 and max(vals) == 10, key
    weights = [PLANES["weight"][i] for i in INSIDE]
    assert min(weights) >= 25 and max(weights) == 250  # 0.1 floor … fully built-up
    for hub in HUBS:
        vals = [PLANES[f"hub_{hub}"][i] for i in INSIDE]
        assert min(vals) <= 5 and max(vals) <= 250, hub


def test_grid_medians_are_resident_weighted():
    weights = [PLANES["weight"][i] / 250 for i in INSIDE]
    for key in ("food", "transport", "crowd"):
        vals = [PLANES[key][i] for i in INSIDE]
        assert GRID["medians"][key] == int(R.weighted_median(vals, weights)), key


def test_grid_places_stations_in_their_areas():
    """The cell under each rated station belongs to that station's area."""
    h = GRID
    areas = {aid: k + 1 for k, aid in enumerate(h["areas"])}
    misses = []
    for st in RAIL["stations"]:
        if not st["district"]:
            continue
        c = int((st["lng"] - h["west"]) / (h["east"] - h["west"]) * h["nx"])
        r = int((h["north"] - st["lat"]) / (h["north"] - h["south"]) * h["ny"])
        i = r * h["nx"] + c
        if PLANES["area"][i] != areas[st["area"]]:
            misses.append(st["id"])
    # A cell centre can sit up to ~140 m from its station, so an interchange
    # neighbour may own it; allow a handful.
    assert len(misses) <= 8, misses
