#!/usr/bin/env python3
"""
Ingest MLIT 国土数値情報 S12 (駅別乗降客数) into data/passengers/s12-passengers.json.

Replaces the orphaned ingest that populated NocoDB `passenger_counts` (no code
for it was ever committed) and the 92 hand-typed rows of scrape-passengers.py.
compute-ratings.py and build-datamart.py read the JSON this writes (CRTKY-84).

Source
    https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html
    S12-25 = 2025年度整備 = data for FY2024 (令和6年度), published 2026-04.
    License: 国土数値情報ダウンロードサイトコンテンツ利用規約 (政府標準利用規約 2.0,
    CC BY 4.0 compatible) — attribution and a 加工 note are required; the
    attribution is written into the output metadata and shown on /methodology.

Usage
    python3 scripts/scrapers/ingest-mlit-s12.py            # download (cached) + write
    python3 scripts/scrapers/ingest-mlit-s12.py --dry-run  # report only
    python3 scripts/scrapers/ingest-mlit-s12.py --zip PATH # use a local copy of the zip

Matching (see research/03-crowd.md §1a for the full reasoning)
    * representative point = midpoint along each S12 station LineString
    * name keys: NFKC, ヶ/ヵ → ケ, strip trailing 駅, drop ・/spaces; bracket
      aliases (明治神宮前〈原宿〉) become extra keys
    * T1 same name ≤ 300 m · T2 same name ≤ 800 m and the operator serves us ·
      T3 nearest feature of a missing operator / non-JR line ≤ 400 m ·
      T4 fuzzy name ≥ 0.5 ≤ 300 m only when nothing else matched
    * each S12 feature goes to at most one slug (best tier, then nearest)

Aggregation
    Per feature, use the latest year's value only when duplicate code = 1 and
    existence code = 1; dup = 2 features carry 0 because their count sits on
    another feature, so summing across operators does not double count.
    Year-keyed corrections, each verified against the operator's own data:
      boarding_x2    Yokohama Municipal Subway FY2024 is boarding-only
      prev_year_max  Toei FY2024 drops transfer passengers → max(FY2023, FY2024)
      fallback_fyNN  JR East drops stations that became unmanned → last year with data
    They are keyed by fiscal year, so a new vintage does not inherit them
    silently: re-check per-operator year-on-year ratios before trusting it.

Confidence: strong when every summed value is from the latest two vintages,
moderate when any value is an older fallback.
"""

from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import io
import json
import math
import re
import sys
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "data" / "passengers" / "s12-passengers.json"
CACHE_DIR = ROOT / ".cache" / "s12"

DATASET_PAGE = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html"
S12_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/S12/S12-25/S12-25_GML.zip"
S12_SHA256 = "0785e932a32b3ec15e1a1345537ae145eafe1c07bf38d5c16c11ee2b391e7a28"
GEOJSON_MEMBER = "UTF-8/S12-25_NumberOfPassengers.geojson"
ATTRIBUTION = (
    "出典：「国土数値情報（駅別乗降客数データ）」（国土交通省）"
    f"({DATASET_PAGE}) を加工して作成"
)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

# ekidata/line-names.json operator_ja -> S12 運営会社 (S12_002)
OPERATOR_ALIASES = {
    "JR東日本": "東日本旅客鉄道",
    "JR東海": "東海旅客鉄道",
    "東京メトロ": "東京地下鉄",
    "東京都交通局": "東京都",
    "京急電鉄": "京浜急行電鉄",
    "横浜市交通局": "横浜市",
    "小湊鉄道": "小湊鐵道",
    "箱根登山鉄道": "小田急箱根",  # renamed 2024-04
}

# (operator, fiscal year) whose values are 乗車人員 (boarding only) although the
# remark does not say so. Verified: 横浜市 FY2024 S12 == city statistics
# 乗車人員/365 exactly (横浜 23,166,936/365 = 63,471; 湘南台 8,339,500/365 = 22,848).
BOARDING_ONLY = {("横浜市", 2024)}

# (operator, fiscal year) where the latest vintage drops 連絡/乗換人員 at transfer
# stations. Verified vs Toei open data (CC BY 4.0): S12 FY2023 is 0.90-0.97x of
# Toei's official FY2024 乗降人員 for all 92 features; S12 FY2024 is within 5%
# for only 51 of them and 0.16-0.91x at 41 transfer stations.
PREV_YEAR_MAX = {("東京都", 2024)}

R_NAME = 300.0       # T1
R_NAME_FAR = 800.0   # T2 (operator must agree)
R_OP_NEAR = 400.0    # T3 (400 adds only 京成八幡->本八幡 over 300; 500 adds nothing more)
R_FUZZY = 300.0      # T4
FUZZY_MIN = 0.5
R_OWNER = 1500.0     # an S12 name "belongs" to another slug of that name within this range

JR_OPERATORS = {"東日本旅客鉄道", "東海旅客鉄道"}  # one count per station; line check not needed

TIER_RANK = {"name": 0, "name_far": 1, "fuzzy": 2, "op_near": 3, "line_near": 3}

EXIST_LABEL = {1: "data", 2: "no_data", 3: "undisclosed", 4: "not_existing"}
DUP_LABEL = {1: "here", 2: "counted_on_other_line", 3: "not_existing"}

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

_BRACKET = re.compile(r"[〈<(\[【]([^〉>)\]】]*)[〉>)\]】]")


def _clean(s: str) -> str:
    s = s.replace("ヶ", "ケ").replace("ヵ", "ケ").replace("﨑", "崎").replace("髙", "高")
    s = re.sub(r"[\s・･·]", "", s)
    s = re.sub(r"駅$", "", s)
    return s


def name_keys(name: str) -> set[str]:
    """Normalized primary name + bracket aliases."""
    s = unicodedata.normalize("NFKC", name or "")
    aliases = [a for a in _BRACKET.findall(s) if a]
    keys = {_clean(_BRACKET.sub("", s))}
    keys.update(_clean(a) for a in aliases)
    return {k for k in keys if k}


def primary_key(name: str) -> str:
    s = unicodedata.normalize("NFKC", name or "")
    return _clean(_BRACKET.sub("", s))


_LINE_PREFIX = re.compile(r"^(東京メトロ|都営|都電|東急|京急|京王|小田急|西武|東武|京成|相鉄)")


def line_key(name: str) -> str:
    """'東京メトロ銀座線' (ekidata) and '3号線銀座線' (S12) -> '銀座'."""
    s = unicodedata.normalize("NFKC", name or "")
    s = re.sub(r"^\d+号線", "", s)
    s = _LINE_PREFIX.sub("", s)
    return re.sub(r"線$", "", s)


def haversine(lat1, lng1, lat2, lng2) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def line_midpoint(coords) -> tuple[float, float]:
    """Point halfway along a GeoJSON LineString ([lng, lat] pairs) -> (lat, lng)."""
    if len(coords) == 1:
        return coords[0][1], coords[0][0]
    segs, total = [], 0.0
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        seg = haversine(y1, x1, y2, x2)
        segs.append((seg, x1, y1, x2, y2))
        total += seg
    if total == 0:
        return coords[0][1], coords[0][0]
    half = total / 2
    for seg, x1, y1, x2, y2 in segs:
        if half <= seg:
            t = half / seg if seg else 0.0
            return y1 + (y2 - y1) * t, x1 + (x2 - x1) * t
        half -= seg
    return coords[-1][1], coords[-1][0]


def year_fields(year: int) -> tuple[str, str, str, str]:
    """(duplicate code, existence code, remark, passengers) for a fiscal year."""
    k = year - 2011
    return tuple(f"S12_{n:03d}" for n in (6 + 4 * k, 7 + 4 * k, 8 + 4 * k, 9 + 4 * k))


def latest_year(props: dict) -> int:
    y = 2011
    while year_fields(y + 1)[3] in props:
        y += 1
    return y


def _usable(p: dict, year: int) -> int:
    dup_f, ex_f, _, val_f = year_fields(year)
    v = p.get(val_f) or 0
    return v if (p.get(dup_f) == 1 and p.get(ex_f) == 1 and v > 0) else 0


def _boarding_fix(p: dict, year: int, value: int, flags: list[str]) -> int:
    rem = p.get(year_fields(year)[2])
    if (rem and "乗車人員" in rem) or (p["S12_002"], year) in BOARDING_ONLY:
        flags.append("boarding_x2")
        return value * 2
    return value


def feature_value(p: dict, year: int, fallback_from: int | None = None) -> tuple[int, int, list[str], str]:
    """-> (value used, raw value, flags, status).

    fallback_from: oldest fiscal year allowed when the latest year has no data
    (exist=2/3) — JR East drops stations from its tables when they become
    unmanned, so FY2024 loses stations that had FY2023 data. None = no fallback.
    dup=2 features never fall back: their count lives on another feature.
    """
    dup_f, ex_f, _, val_f = year_fields(year)
    dup, ex, raw = p.get(dup_f), p.get(ex_f), p.get(val_f) or 0
    if dup != 1:
        return 0, raw, [], DUP_LABEL.get(dup, f"dup{dup}")
    if ex != 1 or raw <= 0:
        status = EXIST_LABEL.get(ex, f"exist{ex}")
        if fallback_from is not None and ex in (2, 3):
            for y in range(year - 1, fallback_from - 1, -1):
                v = _usable(p, y)
                if v:
                    flags = [f"fallback_fy{y}"]
                    return _boarding_fix(p, y, v, flags), raw, flags, "data"
        return 0, raw, [], status
    flags: list[str] = []
    value = _boarding_fix(p, year, raw, flags)
    if (p["S12_002"], year) in PREV_YEAR_MAX:
        prev = _usable(p, year - 1)
        if prev > value:
            value = prev
            flags.append("prev_year_max")
    return value, raw, flags, "data"


# --------------------------------------------------------------------------
# Load
# --------------------------------------------------------------------------


def load_s12(path: Path, bbox):
    g = json.loads(path.read_text(encoding="utf-8"))
    feats = []
    for i, f in enumerate(g["features"]):
        lat, lng = line_midpoint(f["geometry"]["coordinates"])
        if not (bbox[0] <= lat <= bbox[1] and bbox[2] <= lng <= bbox[3]):
            continue
        p = f["properties"]
        feats.append({
            "idx": i, "lat": lat, "lng": lng, "props": p,
            "name": p["S12_001"], "key": primary_key(p["S12_001"]),
            "operator": p["S12_002"], "line": p["S12_003"],
            "group": p["S12_001g"],
        })
    return feats


def load_station_ops(stations, line_names):
    ops = {}
    for s in stations:
        o = set()
        for lid in s.get("lines", []):
            op = (line_names.get(lid) or {}).get("operator_ja")
            if op:
                o.add(OPERATOR_ALIASES.get(op, op))
        ops[s["slug"]] = o
    return ops


def load_station_lines(stations, line_names):
    """slug -> {(S12 operator, line key)} from ekidata line ids."""
    out = {}
    for s in stations:
        lines = set()
        for lid in s.get("lines", []):
            ln = line_names.get(lid) or {}
            if ln.get("operator_ja") and ln.get("name_ja"):
                op = OPERATOR_ALIASES.get(ln["operator_ja"], ln["operator_ja"])
                lines.add((op, line_key(ln["name_ja"])))
        out[s["slug"]] = lines
    return out


# --------------------------------------------------------------------------
# Match
# --------------------------------------------------------------------------


class Grid:
    """Tiny spatial hash so the 1493 x ~2k distance checks stay cheap."""

    def __init__(self, feats, cell=0.01):
        self.cell = cell
        self.cells = collections.defaultdict(list)
        for f in feats:
            self.cells[(int(f["lat"] / cell), int(f["lng"] / cell))].append(f)

    def near(self, lat, lng, radius_m):
        span = int(radius_m / 800) + 1  # 0.01 deg lat ~ 1.1 km, lng ~ 0.9 km here
        ci, cj = int(lat / self.cell), int(lng / self.cell)
        for di in range(-span, span + 1):
            for dj in range(-span, span + 1):
                for f in self.cells.get((ci + di, cj + dj), ()):
                    d = haversine(lat, lng, f["lat"], f["lng"])
                    if d <= radius_m:
                        yield d, f


def match(stations, feats, station_ops, station_lines):
    grid = Grid(feats)
    owners = collections.defaultdict(list)  # name key -> [(slug, lat, lng)]
    for s in stations:
        for k in name_keys(s["name_jp"]):
            owners[k].append((s["slug"], s["lat"], s["lng"]))

    def owned_elsewhere(f, slug):
        """Another of our stations carries this S12 name nearby -> not ours to take."""
        return any(o != slug and haversine(f["lat"], f["lng"], la, ln) <= R_OWNER
                   for o, la, ln in owners.get(f["key"], ()))

    def take_with_siblings(got, near, f, tier):
        # the chosen feature plus every feature of that operator sharing its name
        # nearby (the dup=1 carrier may be a sibling of the nearest one)
        for d2, f2 in near:
            if f2["operator"] == f["operator"] and f2["key"] == f["key"] and d2 <= R_NAME_FAR:
                got.append((d2, f2, tier))

    claims = collections.defaultdict(list)  # feature idx -> [(rank, dist, slug, tier)]
    for s in stations:
        slug, keys, ops = s["slug"], name_keys(s["name_jp"]), station_ops[s["slug"]]
        near = list(grid.near(s["lat"], s["lng"], R_NAME_FAR))
        got = []
        for d, f in near:
            if f["key"] in keys:
                if d <= R_NAME:
                    got.append((d, f, "name"))
                elif f["operator"] in ops:
                    got.append((d, f, "name_far"))
        covered_ops = {f["operator"] for _, f, _ in got}
        # T3a: operators of ours with no feature yet (ekidata merged groups)
        for op in sorted(ops - covered_ops):
            cands = [(d, f) for d, f in near if d <= R_OP_NEAR and f["operator"] == op
                     and not owned_elsewhere(f, slug)]
            if cands:
                take_with_siblings(got, near, min(cands, key=lambda x: x[0])[1], "op_near")
        # T3b: non-JR lines of ours with no feature of that line yet — ekidata
        # groups differently named subway stations (永田町 + 赤坂見附)
        covered_lines = {(f["operator"], line_key(f["line"])) for _, f, _ in got}
        for op, lk in sorted(station_lines[slug]):
            if op in JR_OPERATORS or (op, lk) in covered_lines:
                continue
            cands = [(d, f) for d, f in near if d <= R_OP_NEAR and f["operator"] == op
                     and line_key(f["line"]) == lk and not owned_elsewhere(f, slug)]
            if cands:
                take_with_siblings(got, near, min(cands, key=lambda x: x[0])[1], "line_near")
                covered_lines.add((op, lk))
        if not got:
            best = []
            for d, f in near:
                if d > R_FUZZY or owned_elsewhere(f, slug):
                    continue
                sim = max(difflib.SequenceMatcher(None, k, f["key"]).ratio() for k in keys)
                contains = any(k in f["key"] or f["key"] in k for k in keys)
                if sim >= FUZZY_MIN or contains:
                    best.append((d, f, "fuzzy"))
            got = best
        for d, f, tier in got:
            claims[f["idx"]].append((TIER_RANK[tier], d, slug, tier))

    assigned = collections.defaultdict(list)  # slug -> [(feature, dist, tier)]
    by_idx = {f["idx"]: f for f in feats}
    for idx, cl in claims.items():
        rank, d, slug, tier = min(cl)
        assigned[slug].append((by_idx[idx], d, tier))
    return assigned


def _data_year(flags: list[str], year: int) -> int:
    for fl in flags:
        if fl.startswith("fallback_fy"):
            return int(fl[len("fallback_fy"):])
    return year - 1 if "prev_year_max" in flags else year


def aggregate(stations, assigned, year, station_ops, fallback_from=None):
    out = {}
    for s in stations:
        slug = s["slug"]
        rows, total = [], 0
        for f, d, tier in sorted(assigned.get(slug, []), key=lambda x: (x[0]["operator"], x[1])):
            value, raw, flags, status = feature_value(f["props"], year, fallback_from)
            total += value
            rows.append({
                "name": f["name"], "operator": f["operator"], "line": f["line"],
                "group": f["group"], "tier": tier, "dist_m": round(d),
                "status": status, "raw": raw, "value": value, "flags": flags,
                "remark": f["props"].get(year_fields(year)[2]),
            })
        matched_ops = {r["operator"] for r in rows}
        years = [_data_year(r["flags"], year) for r in rows if r["value"] > 0]
        oldest = min(years) if years else None
        out[slug] = {
            "daily_passengers": total,
            "fiscal_year": year,
            "oldest_data_year": oldest,
            # proposal: strong = latest two vintages, moderate = older fallback
            "confidence": None if not years else ("strong" if oldest >= year - 1 else "moderate"),
            "match": min((r["tier"] for r in rows), key=TIER_RANK.get) if rows else None,
            "n_features": len(rows),
            "n_valued": sum(1 for r in rows if r["value"] > 0),
            "missing_operators": sorted(station_ops[slug] - matched_ops),
            "flags": sorted({fl for r in rows for fl in r["flags"]}),
            "features": rows,
        }
    return out

# --------------------------------------------------------------------------
# Source file
# --------------------------------------------------------------------------


def fetch_zip(zip_path: Path | None) -> bytes:
    """Return the pinned S12 zip, downloading into the cache when needed."""
    if zip_path is None:
        zip_path = CACHE_DIR / S12_URL.rsplit("/", 1)[1]
        if not zip_path.exists():
            print(f"Downloading {S12_URL} ...")
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(S12_URL, timeout=120) as resp:
                zip_path.write_bytes(resp.read())
    data = zip_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != S12_SHA256:
        sys.exit(f"FATAL: {zip_path} has SHA-256 {digest}, expected {S12_SHA256}. "
                 "The published file changed — re-verify the vintage and corrections, "
                 "then update S12_URL / S12_SHA256.")
    return data


def load_geojson(zip_bytes: bytes) -> Path:
    """Extract the UTF-8 GeoJSON next to the cached zip and return its path."""
    out = CACHE_DIR / Path(GEOJSON_MEMBER).name
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            member = next(n for n in zf.namelist() if n.endswith(GEOJSON_MEMBER))
            out.write_bytes(zf.read(member))
    return out


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def build(stations, line_names, feats, year):
    station_ops = load_station_ops(stations, line_names)
    assigned = match(stations, feats, station_ops, load_station_lines(stations, line_names))
    return aggregate(stations, assigned, year, station_ops, fallback_from=2011)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", type=Path, help="local copy of the S12 zip (default: download to .cache/s12)")
    ap.add_argument("--dry-run", action="store_true", help="report only, do not write the output")
    ap.add_argument("--show", default="shinjuku,shibuya,ikebukuro,yokohama,omiya")
    args = ap.parse_args()

    stations = json.loads((ROOT / "data" / "stations.json").read_text(encoding="utf-8"))
    line_names = json.loads((ROOT / "data" / "line-names.json").read_text(encoding="utf-8"))

    geojson = load_geojson(fetch_zip(args.zip))
    lats, lngs = [s["lat"] for s in stations], [s["lng"] for s in stations]
    bbox = (min(lats) - 0.05, max(lats) + 0.05, min(lngs) - 0.05, max(lngs) + 0.05)
    feats = load_s12(geojson, bbox)
    year = latest_year(feats[0]["props"])
    print(f"S12 features in area: {len(feats)} · fiscal year: FY{year}")

    result = build(stations, line_names, feats, year)
    valued = {k: v for k, v in sorted(result.items()) if v["daily_passengers"] > 0}
    unvalued = sorted(k for k, v in result.items() if v["daily_passengers"] <= 0)

    corrections = collections.Counter(fl.split("_fy")[0] if fl.startswith("fallback") else fl
                                      for v in valued.values() for fl in v["flags"])
    doc = {
        "metadata": {
            "source": "国土数値情報 駅別乗降客数データ (S12), 国土交通省",
            "dataset_page": DATASET_PAGE,
            "file": S12_URL,
            "sha256": S12_SHA256,
            "fiscal_year": year,
            "unit": "persons/day, boarding + alighting, summed across operators",
            "license": "政府標準利用規約 2.0 (CC BY 4.0 compatible)",
            "attribution": ATTRIBUTION,
            "generated_by": "scripts/scrapers/ingest-mlit-s12.py",
            "stations_valued": len(valued),
            "stations_without_data": unvalued,
            "corrections_applied": dict(sorted(corrections.items())),
        },
        "stations": {
            slug: {
                "daily_passengers": v["daily_passengers"],
                "data_year": v["oldest_data_year"],
                "confidence": v["confidence"],
                "flags": v["flags"],
            }
            for slug, v in valued.items()
        },
    }

    n = len(stations)
    print(f"valued: {len(valued)} / {n} ({len(valued) / n:.1%}) · without data: {len(unvalued)}")
    print("confidence:", dict(collections.Counter(v["confidence"] for v in valued.values())))
    print("corrections:", doc["metadata"]["corrections_applied"])
    for slug in [x for x in args.show.split(",") if x]:
        v = result.get(slug)
        print(f"  {slug}: {v['daily_passengers']:,}/day" if v else f"  {slug}: unknown slug")

    if args.dry_run:
        print("\nDry run — not writing.")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nWrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
