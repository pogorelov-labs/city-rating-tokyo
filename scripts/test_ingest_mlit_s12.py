"""
Tests for scripts/scrapers/ingest-mlit-s12.py (CRTKY-84): the S12 field and
correction rules, and invariants of the committed data/passengers file.
"""
import importlib.util
import json
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("ingest_s12", _THIS_DIR / "scrapers" / "ingest-mlit-s12.py")
s12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s12)

DATA = json.loads((_THIS_DIR.parent / "data" / "passengers" / "s12-passengers.json").read_text())
STATIONS = {s["slug"] for s in json.loads((_THIS_DIR.parent / "data" / "stations.json").read_text())}


def props(operator="東急電鉄", year=2024, dup=1, exist=1, value=1000, prev=None, remark=None):
    d, e, r, v = s12.year_fields(year)
    p = {"S12_002": operator, d: dup, e: exist, r: remark, v: value}
    if prev is not None:
        pd, pe, _, pv = s12.year_fields(year - 1)
        p.update({pd: 1, pe: 1, pv: prev})
    return p


class TestNames:
    def test_ke_and_suffix_normalised(self):
        assert s12.name_keys("市ヶ谷駅") == s12.name_keys("市ケ谷")

    def test_bracket_alias_is_an_extra_key(self):
        assert s12.name_keys("明治神宮前〈原宿〉") == {"明治神宮前", "原宿"}

    def test_line_key_matches_ekidata_and_s12_spellings(self):
        assert s12.line_key("東京メトロ銀座線") == s12.line_key("3号線銀座線") == "銀座"


class TestFields:
    def test_fy2024_fields(self):
        assert s12.year_fields(2024) == ("S12_058", "S12_059", "S12_060", "S12_061")


class TestFeatureValue:
    def test_counted_here_is_used(self):
        assert s12.feature_value(props(value=5000), 2024)[0] == 5000

    def test_counted_on_another_line_contributes_zero(self):
        assert s12.feature_value(props(dup=2, value=0), 2024)[0] == 0

    def test_yokohama_2024_is_boarding_only_and_doubled(self):
        value, _, flags, _ = s12.feature_value(props(operator="横浜市", value=63471), 2024)
        assert value == 126942 and "boarding_x2" in flags

    def test_boarding_correction_is_keyed_by_year(self):
        # A new vintage must not inherit the FY2024 fix silently.
        assert s12.feature_value(props(operator="横浜市", year=2025, value=70000), 2025)[0] == 70000

    def test_toei_2024_takes_the_larger_of_two_years(self):
        value, _, flags, _ = s12.feature_value(props(operator="東京都", value=33601, prev=200000), 2024)
        assert value == 200000 and "prev_year_max" in flags

    def test_unmanned_station_falls_back_to_last_year_with_data(self):
        p = props(operator="東日本旅客鉄道", exist=2, value=0, prev=3942)
        value, _, flags, _ = s12.feature_value(p, 2024, fallback_from=2011)
        assert value == 3942 and flags == ["fallback_fy2023"]

    def test_no_fallback_for_duplicate_features(self):
        p = props(dup=2, value=0, prev=5000)
        assert s12.feature_value(p, 2024, fallback_from=2011)[0] == 0


class TestCommittedData:
    def test_metadata_carries_source_and_required_attribution(self):
        m = DATA["metadata"]
        assert m["fiscal_year"] == 2024 and m["sha256"] == s12.S12_SHA256
        assert "国土数値情報" in m["attribution"] and "加工して作成" in m["attribution"]

    def test_every_slug_is_a_current_station(self):
        assert set(DATA["stations"]) <= STATIONS
        assert set(DATA["metadata"]["stations_without_data"]) <= STATIONS

    def test_coverage(self):
        assert len(DATA["stations"]) >= 1400
        assert len(DATA["stations"]) + len(DATA["metadata"]["stations_without_data"]) == len(STATIONS)

    def test_confidence_levels(self):
        assert {v["confidence"] for v in DATA["stations"].values()} <= {"strong", "moderate"}

    def test_known_hubs_are_plausible(self):
        st = DATA["stations"]
        for slug in ("shinjuku", "shibuya", "ikebukuro"):
            assert 2_000_000 < st[slug]["daily_passengers"] < 3_500_000, slug
        assert st["shinjuku"]["daily_passengers"] > st["omiya"]["daily_passengers"]
