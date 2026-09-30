#!/usr/bin/env python3
"""
Add `name_ru` to every station in data/stations.json and app/src/data/stations.json
(CRTKY-107). The frontend already prefers `name_ru` on /ru pages and in search;
until now the field did not exist, so Russian pages showed English names.

Sources, in order:
  1. wikidata_ru  — the station's established Russian name on Wikidata, if it is
                    in the Polivanov system (labels with ш/ч/ж are rejected).
  2. wikidata_en  — Polivanov transliteration (scripts/polivanov.py) of the
                    station's English label on Wikidata. Wikidata has the correct
                    reading where our name_en was romanised wrongly (南越谷 is
                    Minami-Koshigaya, not "Nan'etsu-Tani").
  3. name_en      — Polivanov transliteration of our own name_en.

Matching: same kanji name (NFKC, ヶ→ケ, without 駅, bracket aliases included)
and at most 1.5 km apart.

Wikidata labels come from a committed snapshot (data/names/wikidata-station-
labels.json, CC0) so re-runs are reproducible offline; --refresh re-queries it.
A per-station source report goes to data/names/name-ru-report.json.

Usage: python3 scripts/generate-name-ru.py [--refresh] [--dry-run]
"""
import argparse
import collections
import json
import math
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import polivanov  # noqa: E402

STATION_FILES = [ROOT / "data" / "stations.json", ROOT / "app" / "src" / "data" / "stations.json"]
SNAPSHOT = ROOT / "data" / "names" / "wikidata-station-labels.json"
REPORT = ROOT / "data" / "names" / "name-ru-report.json"
MAX_DIST_M = 1500

SPARQL = """SELECT ?item ?ja ?ru ?en ?lat ?lng WHERE {
  SERVICE wikibase:box {
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point(138.9 34.85)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point(140.95 36.35)"^^geo:wktLiteral .
  }
  ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja" && STRENDS(?ja, "駅"))
  OPTIONAL { ?item rdfs:label ?ru . FILTER(LANG(?ru) = "ru") }
  OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en) = "en") }
  BIND(geof:latitude(?coord) AS ?lat) BIND(geof:longitude(?coord) AS ?lng)
}"""

_BRACKET = re.compile(r"[〈<(\[【]([^〉>)\]】]*)[〉>)\]】]")


def _clean_jp(s: str) -> str:
    s = s.replace("ヶ", "ケ").replace("ヵ", "ケ")
    return re.sub(r"駅$", "", re.sub(r"[\s・･]", "", s))


def name_keys(name_jp: str) -> set:
    """明治神宮前〈原宿〉 → {明治神宮前, 原宿}."""
    s = unicodedata.normalize("NFKC", name_jp or "")
    keys = {_clean_jp(_BRACKET.sub("", s))} | {_clean_jp(a) for a in _BRACKET.findall(s) if a}
    return {k for k in keys if k}


def clean_ru(label: str) -> str:
    return re.sub(r"\s*\(.*?\)\s*$", "", re.sub(r"^[Сс]танция\s+", "", label)).strip()


def is_polivanov(label: str) -> bool:
    """Polivanov never uses ш/ч/щ/ж, and writes よ as ё, not Йо."""
    return not re.search(r"[шчщжШЧЩЖ]|(^|[\s-])Й", label)


def clean_en(label: str) -> str:
    return re.sub(r"\s+Station$", "", re.sub(r"\s*\(.*?\)", "", label)).strip()


def haversine(lat1, lng1, lat2, lng2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(h))


def refresh_snapshot():
    q = urllib.parse.urlencode({"query": SPARQL})
    req = urllib.request.Request(
        f"https://query.wikidata.org/sparql?{q}",
        headers={"Accept": "application/sparql-results+json",
                 "User-Agent": "city-rating-tokyo/1.0 (https://city-rating.pogorelov.dev)"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        rows = json.load(resp)["results"]["bindings"]
    items = sorted(({
        "qid": r["item"]["value"].rsplit("/", 1)[1],
        "ja": r["ja"]["value"],
        "ru": r.get("ru", {}).get("value"),
        "en": r.get("en", {}).get("value"),
        "lat": round(float(r["lat"]["value"]), 6),
        "lng": round(float(r["lng"]["value"]), 6),
    } for r in rows), key=lambda x: x["qid"])
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({
        "metadata": {"source": "Wikidata (CC0)", "endpoint": "https://query.wikidata.org/sparql",
                     "retrieved": date.today().isoformat(), "query": SPARQL},
        "items": items,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wikidata snapshot: {len(items)} stations written to {SNAPSHOT.relative_to(ROOT)}")


def build_index(items) -> dict:
    """Wikidata items keyed by every kanji name they go by."""
    index = collections.defaultdict(list)
    for item in items:
        for key in name_keys(item["ja"]):
            index[key].append(item)
    return index


def best_match(station, index):
    """The matching Wikidata item: prefer one with a usable Russian label, then the nearest."""
    cands = []
    for key in name_keys(station["name_jp"]):
        for item in index.get(key, ()):
            d = haversine(station["lat"], station["lng"], item["lat"], item["lng"])
            if d <= MAX_DIST_M:
                usable_ru = bool(item["ru"]) and is_polivanov(clean_ru(item["ru"]))
                cands.append((not usable_ru, d, item))
    return min(cands, key=lambda c: (c[0], c[1]))[2] if cands else None


def romaji_of_name_en(station) -> str:
    """name_en tidied for transliteration: ekidata bracket aliases become
    parentheses, and doubled vowels that spell katakana ー collapse
    (Taaminaru → Taminaru) — only when the kanji name has ー, since 飯田橋
    Iidabashi has a real double vowel."""
    s = station["name_en"]
    s = re.sub(r"-?[(<]-?", " (", s)
    s = re.sub(r"-?[)>]-?", ")", s).strip()
    if "ー" in station["name_jp"]:
        s = re.sub(r"([aueo])\1", r"\1", s)
        s = re.sub(r"(?<![aiueo])ii", "i", s)  # シー → shi, but 第一 dai-ichi keeps "ii"
    return s


def is_clean(name: str) -> bool:
    """Cyrillic words with the punctuation station names use; no Latin leftovers."""
    return bool(re.fullmatch(r"[А-Яа-яЁёA-Z0-9\s\-()･·]+", name))  # A-Z: acronyms


def name_ru_for(station, item):
    """(name_ru, source) for one station: the first source that yields clean Cyrillic.
    English labels with English words (Narita Airport Terminal 1) fall through."""
    candidates = []
    if item and item["ru"] and is_polivanov(clean_ru(item["ru"])):
        candidates.append((clean_ru(item["ru"]), "wikidata_ru"))
    if item and item["en"]:
        candidates.append((polivanov.transliterate(clean_en(item["en"])), "wikidata_en"))
    candidates.append((polivanov.transliterate(romaji_of_name_en(station)), "name_en"))
    for name, source in candidates:
        if is_clean(name):
            return name, source
    return candidates[-1]


def squash(s: str) -> str:
    """Compare romanisations ignoring case, macrons, hyphens and spacing."""
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    return re.sub(r"[\s\-‐'’]", "", s.lower())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="re-query Wikidata and rewrite the snapshot")
    ap.add_argument("--dry-run", action="store_true", help="report only, do not write")
    args = ap.parse_args()

    if args.refresh or not SNAPSHOT.exists():
        refresh_snapshot()
    index = build_index(json.loads(SNAPSHOT.read_text(encoding="utf-8"))["items"])

    stations = json.loads(STATION_FILES[0].read_text(encoding="utf-8"))
    names, report, sources = {}, {}, collections.Counter()
    mismatched_en = {}
    for st in stations:
        item = best_match(st, index)
        name_ru, source = name_ru_for(st, item)
        names[st["slug"]] = name_ru
        sources[source] += 1
        entry = {"name_ru": name_ru, "source": source}
        if item:
            entry["wikidata"] = item["qid"]
            if item["en"] and squash(clean_en(item["en"])) != squash(st["name_en"]):
                entry["wikidata_en"] = clean_en(item["en"])
                mismatched_en[st["slug"]] = (st["name_en"], clean_en(item["en"]))
        report[st["slug"]] = entry

    unclean = {slug: n for slug, n in names.items() if not is_clean(n)}
    if unclean:
        sys.exit(f"FATAL: {len(unclean)} names are not clean Cyrillic: {list(unclean.items())[:10]}")
    print(f"name_ru for {len(names)} stations: {dict(sources)}")
    print(f"name_en differs from Wikidata's English label for {len(mismatched_en)} stations "
          f"(possible misreadings — see the report), e.g. "
          + ", ".join(f"{s}: {a} vs {b}" for s, (a, b) in list(mismatched_en.items())[:4]))
    for slug in ("shinjuku", "shibuya", "tokyo", "yokohama", "kichijoji", "nan-etsu-tani"):
        if slug in names:
            print(f"  {slug:15s} → {names[slug]} ({report[slug]['source']})")

    if args.dry_run:
        print("\nDry run — not writing.")
        return

    for path in STATION_FILES:
        rows = json.loads(path.read_text(encoding="utf-8"))
        updated = []
        for st in rows:
            out = {}
            for k, v in st.items():
                if k == "name_ru":
                    continue
                out[k] = v
                if k == "name_jp":
                    out["name_ru"] = names[st["slug"]]
            updated.append(out)
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "sources": dict(sources),
        "name_en_differs_from_wikidata": len(mismatched_en),
        "stations": report,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nWrote name_ru into {', '.join(str(p.relative_to(ROOT)) for p in STATION_FILES)} "
          f"and {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
