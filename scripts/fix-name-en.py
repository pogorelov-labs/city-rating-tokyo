#!/usr/bin/env python3
"""
Correct misread `name_en` values in data/stations.json and
app/src/data/stations.json (CRTKY-134). Slugs are never touched, so URLs
stay as they are.

name_en came from automated kanji→romaji and misreads about 350 stations:
元加治 "Genka-Osamu" is Motokaji, 青海 "Seikai" is Aomi, 酒々井 came out as
"Sake-(kurikaesi)-I". A station takes its Wikidata English label when the
label agrees with the station's kana reading (Wikidata P1814) and name_en
does not, or when name_en is malformed ("Motomachi-・-Chukagai"). The kana
decides, not the label: labels can be vandalised (たまプラーザ's reads
"閻魔大王").

MANUAL holds what the kana cannot settle: katakana loanwords that station
signs write in English (Tama-Plaza, not Tama-Puraaza), stations with no kana
reading on Wikidata, and names with an alias in brackets.

A corrected station's own description (data/descriptions/<slug>.json) is
renamed too — the LLM wrote "Takashima-Taira park" and, in Russian,
"Манацуру" from the misread name.

Reads the Wikidata snapshots of scripts/generate-name-ru.py. Afterwards run
that script (name_ru falls back to name_en) and scripts/merge-descriptions.py.
Re-running is a no-op once every name agrees with its reading.

Usage: python3 scripts/fix-name-en.py [--dry-run]
"""
import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESCRIPTIONS = ROOT / "data" / "descriptions"
sys.path.insert(0, str(ROOT / "scripts"))
import kana  # noqa: E402
import polivanov  # noqa: E402

_spec = importlib.util.spec_from_file_location("generate_name_ru", ROOT / "scripts" / "generate-name-ru.py")
names = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(names)

# What a name may contain: romaji words joined by hyphens, an alias in
# brackets, and English phrases (Narita Airport Terminal 2·3).
STYLE = re.compile(r"[A-Za-z0-9'()· -]+")

MANUAL = {
    # Katakana loanwords: station signs write the English word.
    "keiotama-sentaa": "Keio-Tama-Center",
    "chiba-nyutaun-chuo": "Chiba-Newtown-Chuo",
    "sentaa-kita": "Center-Kita",
    "sentaa-minami": "Center-Minami",
    "ariake-tenisu-no-mori": "Ariake-Tennis-No-Mori",
    "chiku-sentaa": "Chiku-Center",
    "kashiwa-no-ha-kyanpasu": "Kashiwanoha-Campus",
    "keio-yomiuri-rando": "Keio-Yomiuri-Land",
    "koshigaya-reikutaun": "Koshigaya-Laketown",
    "nagareyama-sentorarupaaku": "Nagareyama-Central-Park",
    "ryutsu-sentaa": "Ryutsu-Center",
    "sangyo-shinko-sentaa": "Sangyo-Shinko-Center",
    "shinagawa-shiisaido": "Shinagawa-Seaside",
    "soshio-ryutsu-sentaa": "Socio-Ryutsu-Center",
    "tama-puraaza": "Tama-Plaza",
    "terekomusentaa": "Telecom-Center",
    "tokyo-sukaitsurii": "Tokyo-Skytree",
    "yomiurirando-mae": "Yomiuri-Land-Mae",
    "fuji-fuirumu-mae": "Fujifilm-Mae",          # フィルム, read "Fuirumu"
    "namekawa-airando": "Namegawa-Island",       # 行川 is Namegawa
    "inuboe": "Inubo",                           # 犬吠 いぬぼう; Wikidata spells it Inuboh
    "tennozu-isle": "Tennozu Isle",              # already English (CRTKY-113)
    "sports-center": "Sports-Center",
    "tokyo-teleport": "Tokyo-Teleport",
    "y-r-p-nobi": "YRP-Nobi",                    # ＹＲＰ野比: an acronym, not Y-R-P
    # No kana reading on Wikidata; the readings are the operators' (New Shuttle,
    # Tobu Ogose Line, Ryutetsu).
    "hane-kan": "Hanuki",
    "hire-ke-saki": "Hiregasaki",
    "ima-hane": "Konba",
    "kamo-miya": "Kamonomiya",
    "kawasumi": "Kawakado",
    "kokorozashi-kyu": "Shiku",
    "nai-yado": "Uchijuku",
    "togu-hara": "Higashi-Miyahara",
    # Aliases in brackets, which the kana reading leaves out.
    "naritakuko-daiichi-ryokyaku-taaminaru": "Narita Airport Terminal 1",
    "kuko-daini-biru-daini-ryokyaku-taaminaru": "Narita Airport Terminal 2·3",
    "oshiage-sukaitsurii-mae": "Oshiage (Skytree)",
    "dokkyodaigaku-zen-eki-soka-matsubara": "Dokkyodaigaku-Mae (Soka-Matsubara)",
}


def site_style(label: str) -> str:
    """A Wikidata label in the dataset's style: no macrons, words joined by
    hyphens and capitalised, n before b/m/p (Konba, like Nihonbashi)."""
    s = "".join(c for c in unicodedata.normalize("NFD", names.clean_en(label)) if not unicodedata.combining(c))
    s = re.sub(r"m(?=-?[bmpBMP])", "n", re.sub(r"[\s･・·]+", "-", s.strip()))  # Shim-Mikawashima too
    return "-".join(p[:1].upper() + p[1:] for p in s.split("-") if p)


def corrected(station, item, kanas):
    """(name_en, why) when the station's name_en should change, else None."""
    slug = station["slug"]
    if slug in MANUAL:
        return (MANUAL[slug], "manual") if MANUAL[slug] != station["name_en"] else None
    if not (item and item["en"] and kanas):
        return None
    label = names.clean_en(item["en"])
    ours, theirs, heard = kana.romaji_key(station["name_en"]), kana.romaji_key(label), kana.readings(kanas)
    misread = ours != theirs and ours not in heard
    malformed = not STYLE.fullmatch(station["name_en"]) or "(kurikaesi)" in station["name_en"]
    if theirs in heard and (misread or malformed):
        return site_style(label), "wikidata"
    return None


def _mention(name: str):
    """A name as written in prose: its words, joined by a hyphen, a space or nothing."""
    words = [w for w in re.split(r"[-\s()<>・]+", name) if w and w != "kurikaesi"]
    return re.compile(r"\b" + r"[\s-]?".join(map(re.escape, words)) + r"\b", re.IGNORECASE)


def rename_in_description(slug: str, old_en: str, new_en: str, new_ru: str) -> int:
    """Replace the misread name in the station's own description, wherever it
    is written in Latin (the Russian text quotes it too) or as its Polivanov
    transliteration. Edits the text in place: the files come from several
    LLM agents in different JSON layouts, and each keeps its own."""
    path = DESCRIPTIONS / f"{slug}.json"
    if not path.exists():
        return 0
    raw = path.read_text(encoding="utf-8")
    raw, n_en = _mention(old_en).subn(lambda _: new_en, raw)
    raw, n_ru = _mention(polivanov.transliterate(old_en)).subn(lambda _: new_ru, raw)
    if n_en + n_ru:
        json.loads(raw)                                       # still valid JSON
        path.write_text(raw, encoding="utf-8")
    return n_en + n_ru


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="list the corrections, do not write")
    args = ap.parse_args()

    index = names.build_index(json.loads(names.SNAPSHOT.read_text(encoding="utf-8"))["items"])
    kana_by_qid = json.loads(names.KANA_SNAPSHOT.read_text(encoding="utf-8"))["items"]
    stations = json.loads(names.STATION_FILES[0].read_text(encoding="utf-8"))
    unknown = set(MANUAL) - {s["slug"] for s in stations}
    if unknown:
        sys.exit(f"FATAL: MANUAL names slugs that do not exist: {sorted(unknown)}")

    fixes, new_ru = {}, {}
    for st in stations:
        item = names.best_match(st, index)
        kanas = kana_by_qid.get(item["qid"], []) if item else []
        fix = corrected(st, item, kanas)
        if fix:
            fixes[st["slug"]] = (st["name_en"], *fix)
            new_ru[st["slug"]] = names.name_ru_for({**st, "name_en": fix[0]}, item, kanas)[0]
    by_why = {w: sum(f[2] == w for f in fixes.values()) for w in ("wikidata", "manual")}
    print(f"name_en corrections: {len(fixes)} {by_why}")
    for slug, (old, new, why) in fixes.items():
        print(f"  {slug:42s} {old:45s} → {new}  ({why})")

    if args.dry_run or not fixes:
        print("\nDry run — not writing." if args.dry_run else "\nNothing to correct.")
        return
    for path in names.STATION_FILES:
        rows = json.loads(path.read_text(encoding="utf-8"))
        for st in rows:
            if st["slug"] in fixes:
                st["name_en"] = fixes[st["slug"]][1]
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    renamed = {slug: n for slug, (old, new, _) in fixes.items()
               if (n := rename_in_description(slug, old, new, new_ru[slug]))}
    print(f"\nWrote name_en into {', '.join(str(p.relative_to(ROOT)) for p in names.STATION_FILES)}; "
          f"renamed {sum(renamed.values())} mentions in {len(renamed)} descriptions. "
          "Now run scripts/generate-name-ru.py and scripts/merge-descriptions.py.")


if __name__ == "__main__":
    main()
