#!/usr/bin/env python3
"""
Build the safety inputs from official crime open data (CRTKY-82).

Replaces scripts/scrapers/scrape-crime-stats.py — hand-typed literals that match
no Keishicho year, with Kanagawa ward codes shifted by one, and a name join that
reached only 187 of 878 stations outside Tokyo — and the Tokyo `station_crime`
rows in NocoDB, built from Esri Japan's CrimR6_tokyo layer by a script that was
never committed.

Year: 2024 in all four prefectures, the newest year Saitama publishes the full
breakdown for. One year everywhere: 2024→2025 totals moved +3.5…+9.5% by
prefecture, which would otherwise leak into the cross-prefecture comparison.

Formula (research/02-safety.md §3), identical everywhere:
    weighted = violent*3 + assault*2 + burglary*2 + purse_snatch*2
             + pickpocket*1.5 + bike_theft*0.3 + fraud*0.2
Denominator (research/02-safety.md §2), identical everywhere: daytime population
when it is more than 2x residents, residents below 1.5x, their mean in between.
    rate = weighted / denominator * 10000

Granularity:
    municipal     every station → the municipality or ward containing it
                  (point-in-polygon on e-Stat 2020 small-area boundaries): moderate
    neighborhood  Tokyo only: small areas (町丁) whose representative point is
                  within 800 m of the station, from Keishicho's 町丁 table: strong.
                  Clamped to [1/3, 3] x the station's municipal rate, so Tokyo does
                  not fill both tails of the shared normalisation from granularity
                  alone (single 町丁 rates run from 0 to thousands per 10k).

Outputs (committed):
    data/crime/municipal-2024.csv    one row per municipality/ward
    data/crime/station-safety.json   per slug; read by compute-ratings.py
    data/crime/sources.json          every source: URL, SHA-256, bytes, licence

Usage:
    pip install -r scripts/requirements-ingest.txt
    python3 scripts/scrapers/ingest-crime-open-data.py [--dry-run]

Updating to a newer year: change YEAR and every URL/SHA-256/page list below,
then re-check each parser's column headers (Chiba's changed between 2024 and 2025).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import OrderedDict, defaultdict
from pathlib import Path

import pdfplumber
import shapefile

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / ".cache" / "crime"
OUT_DIR = ROOT / "data" / "crime"
YEAR = 2024

WEIGHTS = {"violent": 3, "assault": 2, "burglary": 2, "snatch": 2,
           "pickpocket": 1.5, "bike": 0.3, "fraud": 0.2}
TERMS = ["total", *WEIGHTS]
PREFS = {"11": "Saitama", "12": "Chiba", "13": "Tokyo", "14": "Kanagawa"}
DESIGNATED = ("さいたま市", "千葉市", "横浜市", "川崎市", "相模原市")

CATCHMENT_M = 800
CATCHMENT_MIN_ZONES = 3
CATCHMENT_MIN_POP = 1000
CLAMP = 3.0

ESTAT_ATTRIBUTION = "出典：政府統計の総合窓口(e-Stat)（https://www.e-stat.go.jp/）を加工して作成"
SOURCES = {
    "tokyo": {
        "url": "https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/ninchikensu.files/R6.csv",
        "sha256": "e8758aa0c684aa819f1f701c2a0d8e350143605323808ea1e11d815a6d75045c",
        "page": "https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/ninchikensu.html",
        "title": "区市町村の町丁別、罪種別及び手口別認知件数 (令和6年)",
        "licence": "CC BY 4.0",
        "attribution": "出典：警視庁ホームページ（https://www.keishicho.metro.tokyo.lg.jp/）",
    },
    "kanagawa": {
        "url": "https://www.police.pref.kanagawa.jp/assets/entry/c0030_62.pdf",
        "sha256": "5e889b1a71492987e5734767902dcae95a9a18db0c3d8ff66a6ba66059efe515",
        "page": "https://www.police.pref.kanagawa.jp/tokei/hanzai_tokei/mesc0030.html",
        "title": "刑法犯 罪名別市区町村別 認知件数 (令和6年 確定値)",
        "licence": "free reuse with attribution (神奈川県警察 著作権について)",
        "attribution": "出典：神奈川県警察ホームページ（https://www.police.pref.kanagawa.jp/）",
    },
    "saitama": {
        "url": "https://www.police.pref.saitama.lg.jp/documents/31689/hannzaitoukeinennkann6nenn.pdf",
        "sha256": "0f9b25d658f4244a07582e1e12ac74c139429e657c071b36df6c1d2c632c611b",
        "page": "https://www.police.pref.saitama.lg.jp/e0010/keisou-toukei.html",
        "title": "犯罪統計年鑑 令和6年の犯罪, 表31 刑法犯 罪種別 市区町村別 認知件数",
        "pages": [[110, 111], [112, 113]],
        "licence": "free reuse with attribution (埼玉県警察 著作権について)",
        "attribution": "出典：埼玉県警察ホームページ（https://www.police.pref.saitama.lg.jp/）",
    },
    "chiba": {
        "url": "https://www.police.pref.chiba.jp/content/common/000069930.pdf",
        "sha256": "08c5a4f01cda39188579ca1cae37b437e6ac0b51f38f5231190ca74749e15512",
        "page": "https://www.police.pref.chiba.jp/keisoka/safe-life_crime_statisticsA-07.html",
        "title": "令和6年 犯罪の概要, 表4 刑法犯 市区町村別 罪種(手口)別 認知件数",
        "pages": [[54, 56], [55, 57]],
        "licence": "free reuse with attribution (千葉県警察 著作権について)",
        "attribution": "出典：千葉県警察ホームページ（https://www.police.pref.chiba.jp/）",
    },
    "tokyo_daytime": {
        "url": "https://www.toukei.metro.tokyo.lg.jp/tyukanj/2020/tj20zv1100.csv",
        "sha256": "9c296cda939b88850993dda2e4ac9e60c463a9a9430025cda56103289619dccf",
        "page": "https://www.toukei.metro.tokyo.lg.jp/tyukanj/2020/tj-20index.htm",
        "title": "東京都の昼間人口 2020, 表11 町丁・字等別昼間人口",
        "licence": "CC BY 4.0",
        "attribution": "出典：東京都の統計（https://www.toukei.metro.tokyo.lg.jp/）",
    },
    **{
        f"boundaries_{p}": {
            "url": ("https://www.e-stat.go.jp/gis/statmap-search/data?dlserveyId=A002005212020"
                    f"&code={p}&coordSys=1&format=shape&downloadType=5&datum=2011"),
            "sha256": sha,
            "page": "https://www.e-stat.go.jp/gis/statmap-search?type=2",
            "title": f"令和2年国勢調査 小地域 境界データ ({PREFS[p]})",
            "licence": "政府標準利用規約 2.0 (CC BY 4.0 compatible)",
            "attribution": ESTAT_ATTRIBUTION,
        }
        for p, sha in (
            ("11", "8f08dc5c345b9dba600d6092aa208c147235f6b1e811b5c781c87c5aa6ef7331"),
            ("12", "c00ef474930bbf53e814d0bef04b699c2d2e06bf0f09fd48a804c0cbe120fd4c"),
            ("13", "fefff9196e8d2dd0e089065a37bb30141ff07bac976cae138c42e26acb441886"),
            ("14", "82e901cf0e9736ff3a22803c8193419781988cb275579fb97cde1013907dc59c"),
        )
    },
}
POPULATION = {
    "api": "https://dashboard.e-stat.go.jp/api/1.0/Json/getData",
    "resident": {"indicator": "0201200000000010010", "time": f"{YEAR + 1}CY00",
                 "label": f"住民基本台帳人口 {YEAR + 1}-01-01"},
    "daytime": {"indicator": "0201060000000010000", "time": "2020CY00",
                "label": "昼間人口 (2020年国勢調査)"},
}


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch(key: str) -> bytes:
    """A pinned source file: from the cache, or downloaded, always SHA-256 checked."""
    src = SOURCES[key]
    path = CACHE / key
    if not path.exists():
        print(f"  downloading {key} …")
        CACHE.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(src["url"], headers={"User-Agent": "Mozilla/5.0 (city-rating ingest)"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            path.write_bytes(resp.read())
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != src["sha256"]:
        sys.exit(f"FATAL: {key} has SHA-256 {digest}, expected {src['sha256']} ({src['url']}). "
                 "The published file changed — re-verify it, then update SOURCES.")
    return data


def dashboard(indicator: str, codes: list[str], time: str) -> dict[str, int]:
    """e-Stat Statistics Dashboard (no app id). Cached so re-runs are offline."""
    cache = CACHE / f"dashboard_{indicator}_{time}.json"
    known = json.loads(cache.read_text()) if cache.exists() else {}
    missing = [c for c in codes if c not in known]
    for i in range(0, len(missing), 80):
        q = urllib.parse.urlencode({"Lang": "JP", "IndicatorCode": indicator,
                                    "RegionCode": ",".join(missing[i:i + 80]),
                                    "TimeFrom": time, "TimeTo": time})
        with urllib.request.urlopen(f"{POPULATION['api']}?{q}", timeout=120) as resp:
            doc = json.load(resp)
        objs = doc["GET_STATS"].get("STATISTICAL_DATA", {}).get("DATA_INF", {}).get("DATA_OBJ", [])
        for o in [objs] if isinstance(objs, dict) else objs:
            v = o["VALUE"]
            if v.get("@time") == time:
                known[v["@regionCode"]] = int(float(v["$"]))
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(known, sort_keys=True))
    return {c: known[c] for c in codes if c in known}


# --------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------

def clean(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def norm_muni(name: str) -> str:
    """Join key for a municipality/ward name across police tables and e-Stat."""
    s = clean(unicodedata.normalize("NFKC", name))
    s = re.sub(r"^.+?郡", "", s)                  # 西多摩郡瑞穂町 → 瑞穂町
    s = re.sub(r"^(三宅島|八丈島)", "", s)          # Keishicho island prefixes
    return s.replace("ヶ", "ケ").replace("ヵ", "ケ")


_KAN = "〇一二三四五六七八九"


def _num2kan(n: str) -> str:
    n = int(n)
    if n < 10:
        return _KAN[n]
    t, o = divmod(n, 10)
    return ("" if t == 1 else _KAN[t]) + "十" + (_KAN[o] if o else "")


def norm_town(s: str) -> str:
    """Keishicho writes 新宿３丁目; e-Stat writes 新宿三丁目."""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"(\d+)丁目", lambda m: _num2kan(m.group(1)) + "丁目", s)
    return s.replace("ヶ", "ケ").replace("ヵ", "ケ").replace("ﾉ", "ノ")


def num(s) -> int:
    s = (s or "").replace(",", "").replace("\n", "").strip()
    return int(s) if s not in ("", "-", "－") else 0


# --------------------------------------------------------------------------
# Crime tables
# --------------------------------------------------------------------------

def parse_tokyo(raw: bytes):
    """Keishicho 町丁 CSV → ({municipality: terms}, [(町丁 name, terms)], grand total)."""
    rows = list(csv.reader(io.StringIO(raw.decode("cp932"))))
    head = {h: i for i, h in enumerate(rows[0])}
    stop = next(i for i, r in enumerate(rows) if i > 0 and r and r[0] == "千代田区")

    def terms(r):
        g = lambda h: int(r[head[h]] or 0)  # noqa: E731
        return {"total": g("総合計"), "violent": g("凶悪犯計"), "assault": g("粗暴犯計"),
                "burglary": g("侵入窃盗計"), "snatch": g("非侵入窃盗ひったくり"),
                "pickpocket": g("非侵入窃盗すり"), "bike": g("非侵入窃盗自転車盗"),
                "fraud": g("その他詐欺")}

    municipal, choume = {}, []
    for r in rows[1:stop]:
        name = r[0]
        if name.endswith("計"):
            if name not in ("２３区計", "多摩地区・島部計", "合計"):
                municipal[norm_muni(name[:-1])] = terms(r)
        elif "以下不詳" not in name:
            choume.append((name, terms(r)))
    grand = next(int(r[head["総合計"]]) for r in rows if r and r[0] == "合計")
    return municipal, choume, grand


def parse_kanagawa(raw: bytes):
    """Tagged PDF: 罪名別 table on pp.1–2, 窃盗 手口別 on pp.3–4."""
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        tabs = [p.extract_tables()[0] for p in pdf.pages]
    out = {}
    for part, pages in (("zaimei", tabs[0:2]), ("teguchi", tabs[2:4])):
        head = [clean(c) for c in pages[0][2]]
        mid = [clean(c) for c in pages[0][1]]
        city = None
        for t in pages:
            for r in t[3:]:
                c1, c2 = clean(r[1]), clean(r[2])
                if not (c1 or c2):
                    if "総数" in out.get(part, {}):
                        continue
                    name = "総数"
                elif c1:
                    city = name = c1
                else:
                    name = (city + c2) if (city in DESIGNATED and c2.endswith("区")) else c2
                out.setdefault(part, {})[name] = ([num(x) for x in r[3:]], head[3:], mid[3:])
    municipal = {}
    for name, (v, head, mid) in out["zaimei"].items():
        if name == "総数" or name in DESIGNATED or name.endswith("郡") or "不明" in name:
            continue
        col = lambda g: next(i for i, m in enumerate(mid) if m.startswith(g))  # noqa: E731
        leaf = lambda lab, s: next(i for i in range(s, len(head)) if head[i] == lab)  # noqa: E731
        tv, th, tm = out["teguchi"][name]
        municipal[norm_muni(name)] = {
            "total": v[0], "violent": v[col("凶悪犯")], "assault": v[col("粗暴犯")],
            "fraud": v[leaf("詐欺", col("知能犯"))],
            "burglary": tv[next(i for i, m in enumerate(tm) if m.startswith("侵入盗"))],
            "bike": tv[th.index("自転車盗")], "snatch": tv[th.index("ひったくり")],
            "pickpocket": tv[th.index("すり")],
        }
    return municipal, out["zaimei"]["総数"][0][0]


def _same(a: str, b: str) -> bool:
    return sorted(a) == sorted(b)


def _rotated_parts(pdf, pages):
    """The Saitama/Chiba tables are drawn rotated: pdfplumber returns them transposed
    with every cell string reversed ('512,41' is 14,215). Undo both."""
    parts = []
    for pi in pages:
        T = [[clean(c) for c in r] for r in max(pdf.pages[pi].extract_tables(), key=len)]
        namerow = T[-1]
        s = 1
        while namerow[s] == "":
            s += 1
        names = [c[::-1] for c in namerow[s:]]
        cols = OrderedDict()
        group = sub = ""
        for r in T[:-1]:
            hdr = r[:s]
            if hdr[0]:
                group, sub = hdr[0], ""
            if s == 3 and hdr[1] and hdr[2]:
                sub = hdr[1]
            elif s == 3 and hdr[1] and not hdr[2]:
                sub = ""
            leaf = next((c for c in reversed(hdr[1:]) if c), "") or hdr[0]
            cols[(group, sub, leaf)] = [num(c[::-1]) for c in r[s:]]
        parts.append((names, cols))
    return parts


def _pick(cols, group=None, leaf=None, sub=None):
    for (g, sb, lf), v in cols.items():
        if group and not _same(g, group):
            continue
        if sub is not None and not _same(sb, sub):
            continue
        if leaf and not _same(lf, leaf):
            continue
        return v
    raise KeyError((group, sub, leaf))


def _chiba_burglary(A, j):
    # No 侵入盗 subtotal is printed; sum its 手口.
    return sum(_pick(A, None, lab)[j] for lab in ("空き巣", "忍込み", "居空き", "事務所荒し", "出店荒し", "その他侵入盗"))


def _saitama_burglary(A, j):
    return next(v[j] for (g, sb, lf), v in A.items() if _same(sb, "侵入盗") and lf == "計")


def parse_rotated(raw: bytes, page_pairs, pref: str):
    burglary = _chiba_burglary if pref == "12" else _saitama_burglary
    municipal, grand = {}, None
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for pa, pb in page_pairs:
            (names, A), (names_b, B) = _rotated_parts(pdf, (pa, pb))
            assert len(names) == len(names_b), "table halves disagree on row count"
            city = None
            total_key = next(k for k in A if _same(k[0], "総数") or _same(k[2], "総数"))
            for j, nm in enumerate(names):
                if pref == "12" and nm.count("区") >= 3:
                    nm = "千葉市"          # merged vertical cell in Chiba's layout
                if nm in DESIGNATED:
                    city = nm
                elif nm.endswith("区") and city:
                    nm = city + nm
                elif not nm.endswith("区"):
                    city = None
                tot = A[total_key][j]
                if nm == "総数":
                    grand = tot
                if nm in ("総数", "県外", "発生地不明", "不明") or nm in DESIGNATED or nm.endswith("郡") or tot == 0:
                    continue
                bike = _pick(A, "窃盗犯", "自転車盗")[j] if pref == "12" else _pick(A, None, "自転車盗")[j]
                municipal[norm_muni(nm)] = {
                    "total": tot, "violent": _pick(A, "凶悪犯", "計")[j], "assault": _pick(A, "粗暴犯", "計")[j],
                    "burglary": burglary(A, j), "bike": bike,
                    "snatch": _pick(B, None, "ひったくり")[j], "pickpocket": _pick(B, None, "すり")[j],
                    "fraud": _pick(B, "知能犯", "詐欺")[j],
                }
    return municipal, grand


def weighted(t: dict) -> float:
    return sum(WEIGHTS[k] * t[k] for k in WEIGHTS)


def denominator(resident: int, daytime: int | None) -> tuple[float, str]:
    """research/02-safety.md §2, applied identically in every prefecture."""
    if not daytime:
        return resident, "resident"
    factor = daytime / resident
    if factor > 2.0:
        return daytime, "daytime"
    if factor < 1.5:
        return resident, "resident"
    return (daytime + resident) / 2, "blended"


# --------------------------------------------------------------------------
# Geography
# --------------------------------------------------------------------------

def load_areas(pref: str):
    """e-Stat 2020 small areas: (records with code5/point/population, shapes)."""
    z = zipfile.ZipFile(io.BytesIO(fetch(f"boundaries_{pref}")))
    base = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")),
                         shx=io.BytesIO(z.read(base + ".shx")), encoding="cp932")
    areas = []
    for rec, shp in zip(r.records(), r.shapes()):
        areas.append({
            "code5": f"{rec['PREF']}{rec['CITY']}", "key": rec["KEY_CODE"], "hcode": rec["HCODE"],
            "city": rec["CITY_NAME"], "town": rec["S_NAME"], "pop": rec["JINKO"] or 0,
            "lat": rec["Y_CODE"], "lng": rec["X_CODE"], "bbox": shp.bbox,
            "parts": [shp.points[a:b] for a, b in zip(shp.parts, [*shp.parts[1:], len(shp.points)])],
        })
    return areas


def _inside(lng: float, lat: float, parts) -> bool:
    """Even-odd ray casting across all rings (holes included)."""
    hit = False
    for ring in parts:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def haversine(lat1, lng1, lat2, lng2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(h))


def locate(station, areas):
    """The small area containing the station; nearest representative point if none does."""
    lat, lng = station["lat"], station["lng"]
    for a in areas:
        x1, y1, x2, y2 = a["bbox"]
        if x1 <= lng <= x2 and y1 <= lat <= y2 and _inside(lng, lat, a["parts"]):
            return a, "polygon"
    return min(areas, key=lambda a: haversine(lat, lng, a["lat"], a["lng"])), "nearest"


# --------------------------------------------------------------------------
# Tokyo neighbourhoods
# --------------------------------------------------------------------------

def tokyo_zones(choume, areas13, daytime_raw: bytes):
    """Join Keishicho 町丁 rows to e-Stat small areas → zones with terms and populations."""
    index = defaultdict(list)
    cities = set()
    for a in areas13:
        if a["hcode"] == 8101 and a["town"]:
            index[(a["city"], norm_town(a["town"]))].append(a)
            cities.add(a["city"])
    by_len = sorted(cities, key=len, reverse=True)

    day_by_key, day_by_name = load_tokyo_daytime(daytime_raw)

    def daytime_of(a):
        """Daytime population of a small area, and whether it came from the table."""
        v = day_by_key.get(a["key"])
        if v is None:
            v = day_by_name.get((a["city"], norm_town(a["town"])))
        return (v, True) if v is not None else (a["pop"], False)

    zones, matched, unmatched = [], 0, 0
    day_hits = day_total = 0
    for name, terms in choume:
        city = next((c for c in by_len if name.startswith(c)), None)
        if city is None:
            m = re.match(r".+?郡(.+?[町村])", name)
            if m:
                city = next((c for c in by_len if c == m.group(1)), None)
                name = name[name.index(m.group(1)):] if city else name
        members = index.get((city, norm_town(name[len(city):]))) if city else None
        if not members:
            unmatched += terms["total"]
            continue
        matched += terms["total"]
        pop = sum(a["pop"] for a in members)
        dpop = 0
        for a in members:
            v, found = daytime_of(a)
            dpop += v
            day_hits += found
            day_total += 1
        lead = max(members, key=lambda a: a["pop"])
        zones.append({"lat": lead["lat"], "lng": lead["lng"], "pop": pop, "daytime": dpop,
                      "weighted": weighted(terms), "code5": lead["code5"]})
    return zones, matched / (matched + unmatched), day_hits / day_total


def load_tokyo_daytime(raw: bytes):
    """TMG table 11 → daytime population by national KEY_CODE, and by (city, town) name.

    The table's 「対応する国の小地域集計町丁字コード」 is local to the municipality
    (001002 for 丸の内２丁目), so the national key is 13 + city code + that code.
    Some rows leave it blank (丸の内１丁目); those are joined by name instead.
    """
    rows = csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    head = next(rows)
    ci = head.index("対応する国の小地域集計町丁字コード")
    cityi = head.index("オリジナル地域階層コード／区市町村（市区町村コード）")
    muni_flag = head.index("地域階層フラグ／区市町村")
    namei = head.index("表側表章地域（階層なし）／地域名称")
    di = head.index("昼間人口（人）")
    by_key, by_name, city = {}, {}, None
    for r in rows:
        if r[muni_flag].strip():
            city = clean(r[namei])
            continue
        value = num(r[di])
        if r[ci].strip():
            by_key[f"13{r[cityi].strip()}{r[ci].strip()}"] = value
        if city:
            by_name.setdefault((city, norm_town(clean(r[namei]))), value)
    return by_key, by_name


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="report only, do not write outputs")
    args = ap.parse_args()

    print(f"Crime tables ({YEAR}):")
    tokyo, choume, tokyo_grand = parse_tokyo(fetch("tokyo"))
    kanagawa, kanagawa_grand = parse_kanagawa(fetch("kanagawa"))
    saitama, saitama_grand = parse_rotated(fetch("saitama"), SOURCES["saitama"]["pages"], "11")
    chiba, chiba_grand = parse_rotated(fetch("chiba"), SOURCES["chiba"]["pages"], "12")
    crime = {"13": tokyo, "14": kanagawa, "11": saitama, "12": chiba}
    grand = {"13": tokyo_grand, "14": kanagawa_grand, "11": saitama_grand, "12": chiba_grand}
    source_key = {"13": "tokyo", "14": "kanagawa", "11": "saitama", "12": "chiba"}

    # Gate: municipal rows must account for the published prefecture total
    # (the remainder is 不明 / 県外 / 以下不詳 rows that cannot be placed).
    for p, rows in crime.items():
        share = sum(t["total"] for t in rows.values()) / grand[p]
        print(f"  {PREFS[p]:9s} {len(rows):3d} municipalities · {share:.2%} of the published total")
        assert share > 0.99, f"{PREFS[p]}: municipal rows cover only {share:.2%}"

    print("Boundaries:")
    areas = {p: load_areas(p) for p in PREFS}
    code_of = {}
    for p, rows in areas.items():
        for a in rows:
            if a["city"]:
                code_of[(p, norm_muni(a["city"]))] = a["code5"]
        print(f"  {PREFS[p]:9s} {len(rows)} small areas")

    municipalities = []
    for p, rows in crime.items():
        for name, terms in rows.items():
            code = code_of.get((p, name))
            assert code, f"{PREFS[p]} municipality {name!r} has no boundary code"
            municipalities.append({"pref": p, "code5": code, "name": name, **terms})
    codes = sorted(m["code5"] for m in municipalities)
    resident = dashboard(POPULATION["resident"]["indicator"], codes, POPULATION["resident"]["time"])
    daytime = dashboard(POPULATION["daytime"]["indicator"], codes, POPULATION["daytime"]["time"])
    for m in municipalities:
        assert m["code5"] in resident, f"no resident population for {m['name']} ({m['code5']})"
        m["weighted"] = round(weighted(m), 1)
        m["pop_resident"] = resident[m["code5"]]
        m["pop_daytime"] = daytime.get(m["code5"])
        denom, rule = denominator(m["pop_resident"], m["pop_daytime"])
        m["denominator_rule"] = rule
        m["rate"] = round(m["weighted"] / denom * 10000, 2)
    by_code = {m["code5"]: m for m in municipalities}

    print("Tokyo neighbourhoods:")
    zones, join_rate, day_rate = tokyo_zones(choume, areas["13"], fetch("tokyo_daytime"))
    print(f"  {len(zones)} zones · {join_rate:.1%} of 町丁 crimes joined to a small area · "
          f"{day_rate:.1%} of small areas have daytime population")
    assert join_rate > 0.98, f"Keishicho 町丁 join fell to {join_rate:.1%}"
    # Without daytime population the §2 rule silently degrades to residents and
    # CBD catchments (Hibiya: ~100 residents) explode — fail instead.
    assert day_rate > 0.95, f"TMG daytime join fell to {day_rate:.1%}"

    stations = json.loads((ROOT / "data" / "stations.json").read_text(encoding="utf-8"))
    out, failures, nearest = {}, [], 0
    for st in stations:
        pref = st.get("prefecture")
        area, how = locate(st, areas[pref]) if pref in areas else (None, None)
        m = by_code.get(area["code5"]) if area else None
        if not m:
            failures.append(st["slug"])
            continue
        nearest += how == "nearest"
        entry = {"rate": m["rate"], "municipal_rate": m["rate"], "code": m["code5"],
                 "municipality": m["name"], "level": "municipal", "confidence": "moderate",
                 "source": "police_municipal"}
        if pref == "13":
            near = [z for z in zones if haversine(st["lat"], st["lng"], z["lat"], z["lng"]) <= CATCHMENT_M]
            pop = sum(z["pop"] for z in near)
            if len(near) >= CATCHMENT_MIN_ZONES and pop >= CATCHMENT_MIN_POP:
                denom, _ = denominator(pop, sum(z["daytime"] for z in near))
                local = sum(z["weighted"] for z in near) / denom * 10000
                rate = min(max(local, m["rate"] / CLAMP), m["rate"] * CLAMP)
                entry.update({"rate": round(rate, 2), "level": "neighborhood", "confidence": "strong",
                              "source": "keishicho_choume", "zones": len(near),
                              "clamped": round(rate, 2) != round(local, 2)})
        out[st["slug"]] = entry
    assert not failures, f"stations with no municipality/crime data: {failures}"

    # ---- report
    print(f"\nStations: {len(out)} / {len(stations)} (point-in-polygon; {nearest} by nearest area)")
    for p in ("13", "14", "11", "12"):
        rates = sorted(e["rate"] for s, e in out.items() if e["code"].startswith(p))
        levels = defaultdict(int)
        for e in out.values():
            if e["code"].startswith(p):
                levels[e["level"]] += 1
        q = lambda f: rates[min(len(rates) - 1, int(len(rates) * f))]  # noqa: E731
        print(f"  {PREFS[p]:9s} {len(rates):4d} stations · p10 {q(.1):6.1f} · median {q(.5):6.1f} · "
              f"p90 {q(.9):6.1f} per 10k · {dict(levels)}")
    clamped = sum(1 for e in out.values() if e.get("clamped"))
    print(f"  Tokyo catchments clamped to [1/{CLAMP:g}, {CLAMP:g}]x municipal: {clamped}")

    if args.dry_run:
        print("\nDry run — not writing.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = ["pref", "code5", "name", *TERMS, "weighted", "pop_resident", "pop_daytime",
            "denominator_rule", "rate", "source"]
    with open(OUT_DIR / f"municipal-{YEAR}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for m in sorted(municipalities, key=lambda m: m["code5"]):
            w.writerow({**{k: m.get(k, "") for k in cols}, "source": source_key[m["pref"]]})
    (OUT_DIR / "station-safety.json").write_text(json.dumps({
        "metadata": {
            "year": YEAR, "unit": "weighted crimes per 10,000 people (research/02-safety.md §2–3)",
            "weights": WEIGHTS, "catchment_m": CATCHMENT_M, "clamp": CLAMP,
            "generated_by": "scripts/scrapers/ingest-crime-open-data.py",
        },
        "stations": dict(sorted(out.items())),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (OUT_DIR / "sources.json").write_text(json.dumps({
        "files": {k: {f: v[f] for f in ("title", "url", "page", "sha256", "licence", "attribution")}
                  | {"bytes": len(fetch(k))} for k, v in SOURCES.items()},
        "population": {**POPULATION, "attribution": ESTAT_ATTRIBUTION},
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nWrote data/crime/municipal-{YEAR}.csv, station-safety.json, sources.json")


if __name__ == "__main__":
    main()
