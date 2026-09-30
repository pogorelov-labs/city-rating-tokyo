"""
Tests for scripts/kana.py and scripts/fix-name-en.py (CRTKY-134): kana
romanisation, the rules that decide a correction, and invariants of the
committed name_en data — no name disagrees with its kana reading unless it
is in the hand-reviewed MANUAL table.
"""
import importlib.util
import json
import re
from pathlib import Path

import kana

_THIS_DIR = Path(__file__).resolve().parent
ROOT = _THIS_DIR.parent
_spec = importlib.util.spec_from_file_location("fix_name_en", _THIS_DIR / "fix-name-en.py")
fix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fix)
gen = fix.names

LABELS = json.loads((ROOT / "data" / "names" / "wikidata-station-labels.json").read_text())["items"]
KANA = json.loads((ROOT / "data" / "names" / "wikidata-station-kana.json").read_text())["items"]
STATIONS = json.loads((ROOT / "data" / "stations.json").read_text())
APP_STATIONS = json.loads((ROOT / "app" / "src" / "data" / "stations.json").read_text())


class TestKana:
    def test_romaji(self):
        cases = {
            "もとかじえき": "motokaji", "しんおおくぼ": "shin'ookubo", "はっちょうぼり": "hatchoubori",
            "ちゃや": "chaya", "ながた": "nagata", "きんいち": "kin'ichi", "たまプラーザ": "tamapuraaza",
            "ふじフィルム": "fujifirumu", "ウィ": "wi", "さくらぎちょう": "sakuragichou",
        }
        for k, romaji in cases.items():
            assert kana.to_romaji(k) == romaji, k

    def test_key_folds_spelling_style(self):
        assert kana.romaji_key("Shinbashi") == kana.romaji_key("Shimbashi")
        assert kana.romaji_key("Ōkubo") == kana.romaji_key("Ookubo") == kana.romaji_key("Okubo")
        assert kana.romaji_key("Inuboh") == kana.romaji_key("Inubō") == kana.romaji_key(kana.to_romaji("いぬぼう"))
        assert kana.romaji_key("Sōunzan") == kana.romaji_key(kana.to_romaji("そううんざん"))
        assert kana.romaji_key("Genka-Osamu") not in kana.readings(["もとかじえき"])


class TestCorrectionRules:
    item = staticmethod(lambda en: {"qid": "Q0", "ja": "", "ru": None, "en": en, "lat": 0, "lng": 0})

    def test_a_misread_name_takes_the_label_the_kana_confirms(self):
        station = {"slug": "genka-osamu", "name_en": "Genka-Osamu"}
        assert fix.corrected(station, self.item("Motokaji Station"), ["もとかじえき"]) == ("Motokaji", "wikidata")

    def test_a_label_the_kana_contradicts_is_not_applied(self):
        station = {"slug": "x", "name_en": "Tama-Puraaza"}      # the real label is vandalised
        assert fix.corrected(station, self.item("閻魔大王"), ["たまプラーザえき"]) is None

    def test_spelling_style_alone_is_not_a_correction(self):
        station = {"slug": "x", "name_en": "Nakano-Shinbashi"}
        assert fix.corrected(station, self.item("Nakano-shimbashi Station"), ["なかのしんばしえき"]) is None

    def test_malformed_names_are_rewritten_even_when_the_reading_is_right(self):
        station = {"slug": "x", "name_en": "Motomachi-・-Chukagai"}
        got = fix.corrected(station, self.item("Motomachi-Chūkagai Station"), ["もとまち・ちゅうかがいえき"])
        assert got == ("Motomachi-Chukagai", "wikidata")

    def test_labels_take_the_dataset_style(self):
        assert fix.site_style("Takashimachō Station") == "Takashimacho"
        assert fix.site_style("Nishiaraidaishi-nishi") == "Nishiaraidaishi-Nishi"
        assert fix.site_style("Keisei Shisui") == "Keisei-Shisui"
        assert fix.site_style("Komba") == "Konba"
        assert fix.site_style("Shim-Mikawashima") == "Shin-Mikawashima"


class TestCommittedData:
    def test_the_fixer_has_nothing_left_to_correct(self):
        index = gen.build_index(LABELS)
        pending = {}
        for s in STATIONS:
            item = gen.best_match(s, index)
            got = fix.corrected(s, item, KANA.get(item["qid"], []) if item else [])
            if got:
                pending[s["slug"]] = got
        assert not pending

    def test_no_name_contradicts_its_kana_reading(self):
        """Loanwords written in English (Tama-Plaza) are the reviewed exceptions."""
        index = gen.build_index(LABELS)
        checked, wrong = 0, []
        for s in STATIONS:
            item = gen.best_match(s, index)
            kanas = KANA.get(item["qid"], []) if item else []
            if kanas and s["slug"] not in fix.MANUAL:
                checked += 1
                if kana.romaji_key(s["name_en"]) not in kana.readings(kanas):
                    wrong.append((s["slug"], s["name_en"]))
        assert checked > 1350 and not wrong

    def test_manual_names_are_applied(self):
        by_slug = {s["slug"]: s["name_en"] for s in STATIONS}
        assert {slug: by_slug[slug] for slug in fix.MANUAL} == fix.MANUAL

    def test_names_are_well_formed(self):
        for s in STATIONS:
            assert fix.STYLE.fullmatch(s["name_en"]) and "kurikaesi" not in s["name_en"], s["slug"]
            assert not re.search(r"--|^-|-$", s["name_en"]), s["slug"]

    def test_well_known_misreadings_are_gone(self):
        by_slug = {s["slug"]: s["name_en"] for s in STATIONS}
        assert by_slug["genka-osamu"] == "Motokaji" and by_slug["me-ke-saki"] == "Chigasaki"
        assert by_slug["sekiuchi"] == "Kannai" and by_slug["sen-da-ke-tani"] == "Sendagaya"
        assert by_slug["naritakuko-daiichi-ryokyaku-taaminaru"] == "Narita Airport Terminal 1"

    def test_both_station_files_are_identical(self):
        assert STATIONS == APP_STATIONS
