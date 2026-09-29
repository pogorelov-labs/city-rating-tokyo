"""
Tests for scripts/scrapers/ingest-crime-open-data.py (CRTKY-82): name joins,
the §2 denominator rule, geometry helpers, the TMG daytime join, and
invariants of the committed data/crime outputs.

Needs the ingest extras: pip install -r scripts/requirements-ingest.txt
"""
import csv
import importlib.util
import json
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
ROOT = _THIS_DIR.parent
_spec = importlib.util.spec_from_file_location("ingest_crime", _THIS_DIR / "scrapers" / "ingest-crime-open-data.py")
ic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ic)

MUNICIPAL = list(csv.DictReader(open(ROOT / "data" / "crime" / "municipal-2024.csv", encoding="utf-8")))
SAFETY = json.loads((ROOT / "data" / "crime" / "station-safety.json").read_text())
SOURCES = json.loads((ROOT / "data" / "crime" / "sources.json").read_text())
STATIONS = {s["slug"]: s for s in json.loads((ROOT / "data" / "stations.json").read_text())}


class TestNames:
    def test_gun_prefix_and_ke_are_normalised(self):
        assert ic.norm_muni("西多摩郡瑞穂町") == "瑞穂町"
        assert ic.norm_muni("鎌ヶ谷市") == ic.norm_muni("鎌ケ谷市")

    def test_keishicho_island_prefix(self):
        assert ic.norm_muni("三宅島三宅村") == "三宅村"

    def test_fullwidth_chome_becomes_kanji(self):
        assert ic.norm_town("新宿３丁目") == "新宿三丁目"
        assert ic.norm_town("銀座１２丁目") == "銀座十二丁目"


class TestFormula:
    def test_weights_match_research_02_safety(self):
        assert ic.WEIGHTS == {"violent": 3, "assault": 2, "burglary": 2, "snatch": 2,
                              "pickpocket": 1.5, "bike": 0.3, "fraud": 0.2}

    def test_weighted(self):
        t = {"violent": 1, "assault": 1, "burglary": 1, "snatch": 1, "pickpocket": 2, "bike": 10, "fraud": 10}
        assert ic.weighted(t) == 3 + 2 + 2 + 2 + 3 + 3 + 2

    def test_denominator_rule(self):
        assert ic.denominator(100, 300) == (300, "daytime")        # office district
        assert ic.denominator(100, 120) == (100, "resident")       # residential
        assert ic.denominator(100, 170) == (135, "blended")        # in between
        assert ic.denominator(100, None) == (100, "resident")


class TestGeometry:
    SQUARE_WITH_HOLE = [
        [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
        [(4, 4), (6, 4), (6, 6), (4, 6), (4, 4)],
    ]

    def test_point_in_polygon(self):
        assert ic._inside(2, 2, self.SQUARE_WITH_HOLE)
        assert not ic._inside(5, 5, self.SQUARE_WITH_HOLE)   # in the hole
        assert not ic._inside(11, 5, self.SQUARE_WITH_HOLE)

    def test_haversine_one_km(self):
        assert 1100 < ic.haversine(35.0, 139.0, 35.01, 139.0) < 1120


class TestTokyoDaytimeJoin:
    """The TMG code is local to the municipality; the national key must be built.
    Joining on the raw code matched 0 of 6,467 rows and silently fell back to
    residents, which made CBD catchments (Hibiya: ~100 residents) explode."""

    HEADER = ["地域ＩＤ", "オリジナル地域階層コード", "オリジナル地域階層コード／区市町村（市区町村コード）",
              "地域階層フラグ／区市町村", "対応する国の小地域集計町丁字コード",
              "表側表章地域（階層なし）／地域名称", "昼間人口（人）"]

    def table(self, rows):
        lines = [",".join(self.HEADER)] + [",".join(r) for r in rows]
        return ("﻿" + "\n".join(lines)).encode("utf-8")

    def test_national_key_is_prefecture_city_and_local_code(self):
        raw = self.table([
            ["1", "", "101", "●", "", "千代田区", "903780"],
            ["2", "", "101", "", "001002", "丸の内２丁目", "51120"],
        ])
        by_key, _ = ic.load_tokyo_daytime(raw)
        assert by_key["13101001002"] == 51120

    def test_rows_without_a_code_join_by_name(self):
        raw = self.table([
            ["1", "", "101", "●", "", "千代田区", "903780"],
            ["2", "", "101", "", "", "丸の内１丁目", "76503"],
        ])
        _, by_name = ic.load_tokyo_daytime(raw)
        assert by_name[("千代田区", "丸の内一丁目")] == 76503


class TestCommittedData:
    def test_every_municipality_of_the_four_prefectures(self):
        per_pref = {p: sum(1 for m in MUNICIPAL if m["pref"] == p) for p in ("11", "12", "13", "14")}
        assert per_pref == {"11": 72, "12": 59, "13": 58, "14": 58}

    def test_municipal_rows_are_complete(self):
        for m in MUNICIPAL:
            # >= 0: 三宅村 had 2 crimes in 2024, neither in a weighted category.
            assert float(m["rate"]) >= 0, m["name"]
            assert int(m["pop_resident"]) > 0, m["name"]
            assert m["denominator_rule"] in {"resident", "daytime", "blended"}, m["name"]

    def test_office_wards_use_daytime_population(self):
        rule = {m["code5"]: m["denominator_rule"] for m in MUNICIPAL}
        assert rule["13101"] == "daytime"   # 千代田区
        assert rule["13102"] == "daytime"   # 中央区

    def test_every_station_has_a_rate(self):
        assert set(SAFETY["stations"]) == set(STATIONS)

    def test_granularity_and_confidence_agree(self):
        for slug, e in SAFETY["stations"].items():
            tokyo = STATIONS[slug]["prefecture"] == "13"
            if e["level"] == "neighborhood":
                assert tokyo and e["confidence"] == "strong" and e["source"] == "keishicho_choume", slug
                assert e["municipal_rate"] / ic.CLAMP - 0.01 <= e["rate"] <= e["municipal_rate"] * ic.CLAMP + 0.01, slug
            else:
                assert e["confidence"] == "moderate" and e["source"] == "police_municipal", slug
                assert e["rate"] == e["municipal_rate"], slug

    def test_station_code_matches_its_prefecture(self):
        for slug, e in SAFETY["stations"].items():
            assert e["code"][:2] == STATIONS[slug]["prefecture"], slug

    def test_sources_are_pinned_and_attributed(self):
        for key, meta in ic.SOURCES.items():
            recorded = SOURCES["files"][key]
            assert recorded["sha256"] == meta["sha256"] and recorded["attribution"], key

    def test_every_source_key_has_a_label_in_every_locale(self):
        keys = {e["source"] for e in SAFETY["stations"].values()}
        for loc in ("en", "ja", "ru"):
            labels = json.loads((ROOT / "app" / "src" / "messages" / loc / "common.json").read_text())["sources"]
            assert keys <= set(labels), (loc, keys - set(labels))
