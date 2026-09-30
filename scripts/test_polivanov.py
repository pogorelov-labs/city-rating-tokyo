"""
Tests for scripts/polivanov.py and scripts/generate-name-ru.py (CRTKY-107):
transliteration rules, agreement with established Russian names, the source
tiers, and invariants of the committed name_ru data.
"""
import importlib.util
import json
import re
from pathlib import Path

import polivanov as p

_THIS_DIR = Path(__file__).resolve().parent
ROOT = _THIS_DIR.parent
_spec = importlib.util.spec_from_file_location("gen_name_ru", _THIS_DIR / "generate-name-ru.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

SNAPSHOT = json.loads((ROOT / "data" / "names" / "wikidata-station-labels.json").read_text())["items"]
STATIONS = json.loads((ROOT / "data" / "stations.json").read_text())
APP_STATIONS = json.loads((ROOT / "app" / "src" / "data" / "stations.json").read_text())


class TestTransliterate:
    def test_known_stations(self):
        cases = {
            "Shinjuku": "Синдзюку", "Shibuya": "Сибуя", "Ikebukuro": "Икэбукуро",
            "Kichijoji": "Китидзёдзи", "Ueno": "Уэно", "Ebisu": "Эбису",
            "Ochanomizu": "Отяномидзу", "Gotanda": "Готанда",
        }
        for en, ru in cases.items():
            assert p.transliterate(en) == ru, en

    def test_sokuon_doubles_the_consonant(self):
        assert p.transliterate("Hatchobori") == "Хаттёбори"
        assert p.transliterate("Nippori") == "Ниппори"

    def test_i_after_a_or_e_is_y_but_not_after_o(self):
        assert p.transliterate("Meiji-Jingumae") == "Мэйдзи-Дзингумаэ"
        assert p.transliterate("Kasai") == "Касай"
        assert p.transliterate("Oizumi-Gakuen") == "Оидзуми-Гакуэн"   # 大泉: い is its own mora
        assert p.transliterate("Iidabashi") == "Иидабаси"

    def test_syllabic_n(self):
        assert p.transliterate("Hon'atsugi") == "Хонъацуги"
        assert p.transliterate("Shimbashi") == "Симбаси"
        assert p.transliterate("Shim-Mikawashima") == "Сим-Микавасима"

    def test_conventional_names_particles_loanwords_acronyms(self):
        assert p.transliterate("Tokyo-Teleport") == "Токио-Тэрэпото"
        assert p.transliterate("Shin‐Yokohama") == "Син-Иокогама"          # U+2010 hyphen
        assert p.transliterate("Chokoku-no-Mori") == "Тёкоку-но-Мори"
        assert p.transliterate("Yomiuri-Land-mae") == "Ёмиури-Рандо-маэ"
        assert p.transliterate("Mae-Nishi") == "Маэ-Ниси"   # lowercase only after the first word
        assert p.transliterate("YRP Nobi") == "YRP-Ноби"

    def test_words_join_with_hyphens_and_brackets_keep_a_space(self):
        assert p.transliterate("Keisei Ueno") == "Кэйсэй-Уэно"
        assert p.transliterate("Tokyo Teleport") == "Токио-Тэрэпото"
        assert p.transliterate("Naritakuko (Daiichi Ryokyaku Taminaru)") == "Наритакуко (Дайити-Рёкяку-Таминару)"

    def test_macrons_and_oh_spelling(self):
        assert p.transliterate("Ōkubo") == "Окубо"
        assert p.transliterate("Inuboh") == "Инубо"


class TestAgreementWithEstablishedNames:
    """Regression guard for the rules: the 413 stations with both English and
    Russian labels on Wikidata. 393 (95.2%) agree as of 2026-09-30; 11 of the
    other 20 are い-after-a-vowel ambiguity (Хирай vs Хираи), the rest Wikidata
    label quirks (Умэсики, Тама-Центр)."""

    def test_agreement_stays_above_90_percent(self):
        squash = lambda s: re.sub(r"[\s\-]", "", s.lower().replace("ё", "е"))  # noqa: E731
        pairs = [(gen.clean_en(i["en"]), gen.clean_ru(i["ru"])) for i in SNAPSHOT if i["ru"] and i["en"]]
        agree = sum(squash(p.transliterate(en)) == squash(ru) for en, ru in pairs)
        assert len(pairs) > 300
        assert agree / len(pairs) > 0.90


class TestSources:
    def test_non_polivanov_labels_are_rejected(self):
        assert gen.is_polivanov("Синдзюку")
        assert not gen.is_polivanov("Йошиночо")
        assert not gen.is_polivanov("Шинджуку")

    def test_english_words_fall_through_to_name_en(self):
        station = {"name_en": "Chiba-Nyutaun-Chuo", "name_jp": "千葉ニュータウン中央"}
        item = {"ru": None, "en": "Chiba Newtown Chūō Station"}
        assert gen.name_ru_for(station, item) == ("Тиба-Нютаун-Тюо", "name_en")

    def test_wikidata_reading_beats_a_misread_name_en(self):
        station = {"name_en": "Nan'etsu-Tani", "name_jp": "南越谷"}
        item = {"ru": None, "en": "Minami-Koshigaya Station"}
        assert gen.name_ru_for(station, item) == ("Минами-Косигая", "wikidata_en")

    def test_katakana_long_vowels_collapse_only_with_the_long_vowel_mark(self):
        assert gen.romaji_of_name_en({"name_en": "Shinagawa-Shiisaido", "name_jp": "品川シーサイド"}) == "Shinagawa-Shisaido"
        assert "Daiichi" in gen.romaji_of_name_en({"name_en": "Naritakuko-(-Daiichi-Ryokyaku-Taaminaru-)", "name_jp": "成田空港（第１旅客ターミナル）"})
        assert gen.romaji_of_name_en({"name_en": "Iidabashi", "name_jp": "飯田橋"}) == "Iidabashi"


class TestCommittedData:
    def test_every_station_has_a_clean_russian_name(self):
        for s in STATIONS:
            assert s.get("name_ru") and gen.is_clean(s["name_ru"]), s["slug"]

    def test_committed_names_match_the_generator(self):
        """Editing polivanov.py or the source tiers without re-running
        generate-name-ru.py would leave stale names behind."""
        index = gen.build_index(SNAPSHOT)
        stale = {s["slug"]: s["name_ru"] for s in STATIONS
                 if gen.name_ru_for(s, gen.best_match(s, index))[0] != s["name_ru"]}
        assert not stale

    def test_words_are_hyphenated_like_established_names(self):
        for s in STATIONS:
            assert not re.search(r"[^\s)] +[^\s(]", s["name_ru"]), s["slug"]

    def test_both_station_files_agree(self):
        assert [(s["slug"], s["name_ru"]) for s in STATIONS] == [(s["slug"], s["name_ru"]) for s in APP_STATIONS]

    def test_major_stations_use_established_names(self):
        by_slug = {s["slug"]: s["name_ru"] for s in STATIONS}
        assert by_slug["tokyo"] == "Токио" and by_slug["yokohama"] == "Иокогама"
        assert by_slug["shinjuku"] == "Синдзюку" and by_slug["ikebukuro"] == "Икэбукуро"
