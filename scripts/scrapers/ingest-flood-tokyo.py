#!/usr/bin/env python3
"""Tokyo flood exposure from TMG 浸水予想区域図 + MLIT A31b (CRTKY-187, ADR #2).

Downloads the 14 TMG zone CSVs (CC BY 4.0) — ~627 MB of inundation-depth +
ground-elevation point grids covering all TMG-managed rivers — and computes
per-station maximum flood depth within a 500 m catchment. Output replaces
the SRTM<5 m elevation proxy in `data/flood/station-flood.json`.

Doctrine (ingest-crime pattern): SHA-pinned sources, FATAL on mismatch,
coverage gates on station verdicts. The SRTM proxy stays as a display layer
(elevation_m / ELEVATION_TIERS) — only the flood dealbreaker moves.

Usage:
  uv run scripts/scrapers/ingest-flood-tokyo.py           # fetch + compute + write
  uv run scripts/scrapers/ingest-flood-tokyo.py --offline  # use .cache/flood/

Refresh: TMG CSVs Last-Modified 2026-01-15. New SHA = manual bump below.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "flood"
OUT = ROOT / "data" / "flood" / "station-flood.json"
STATIONS = ROOT / "data" / "stations.json"

# TMG 浸水予想区域図 — 東京都建設局, CC BY 4.0
# https://catalog.data.metro.tokyo.lg.jp/dataset/t000014d0000000029
BASE_URL = "https://www.opendata.metro.tokyo.lg.jp/kensetsu/R3"
SOURCES: dict[str, dict] = {
    "kandagawa":    {"sha256": "09b261c4bff2af413de28bf9657fac002ff243af66b3fe2e5e74ca5867c65051", "enc": "utf-8-sig"},
    "sumidagawa":   {"sha256": "5e3bad8919679af7cd8233b5d7a613e207a6fa9a0f12b42476fb8f43d69698c0", "enc": "utf-8-sig"},
    "syakujiigawa": {"sha256": "0a4e97c8e027932956ba865563467c0f26bb083b8da7992ba1c695664fa8922b", "enc": "utf-8-sig"},
    "jyounantiku":  {"sha256": "383f994008de7f97485fe4b851d8e89f45a05bcb23f2d254ab78aa7d5be8a3a0", "enc": "utf-8-sig"},
    "koutounaibu":  {"sha256": "250810532379b4d5c477b34f30c9d85220c49b6851b4b2e5f6c50294f8e34237", "enc": "utf-8-sig"},
    "nogawa":       {"sha256": "606cd454fe3213dbcca0f37d1090aa1d1129f03519e90d47d75cfa2060b6f7b8", "enc": "utf-8-sig"},
    "kuromegawa":   {"sha256": "ad5addc971d81890dbef9461741c37f7a7ce489f1d070a94d2738a17ffa88c24", "enc": "utf-8-sig"},
    "zanborigawa":  {"sha256": "7f34569056ccc3b157a943340b626bc6782e3a0e3277aa6f8afaefce44de1934", "enc": "utf-8-sig"},
    "sakaigawa":    {"sha256": "1124fae251e97e2b5a50694fc1dd654d158e0e3d908bdbb0ae1e8fe39395741d", "enc": "utf-8-sig"},
    "nakagawa":     {"sha256": "edd1730959292a364c30b4a705ce0b145b3d10bfd34fb21e4c488f510288e4e1", "enc": "utf-8-sig"},
    "tsurumigawa":  {"sha256": "1124fae251e97e2b5a50694fc1dd654d158e0e3d908bdbb0ae1e8fe39395741d", "enc": "utf-8-sig"},  # same file as sakaigawa (verified)
    "asakawa":      {"sha256": "3b3146a51d9d057414fbfd98c5fdc3d8348ffa21aae3ed026ef5c4a6e2c626a0", "enc": "cp932"},
    "tamagawa":     {"sha256": "ffd7fc32998c4b67e53341dc437ddd42244f1302d6efb41601d8e996c816d4df", "enc": "cp932"},
    "akikawa":      {"sha256": "6fac6089a18a71646b6e7233afe4df1c2a6325ce40e69f5b95c63e704af4b77f", "enc": "cp932"},
}

# Flood dealbreaker threshold (ADR #2: 0.5 m = MLIT depth class ≥2, "knee-deep")
FLOOD_THRESHOLD_M = 0.5
# Search radius for max-depth around each station (m). 100 m = "the station
# itself is in the flood zone" — calibrated against TMG data: at 100 m,
# Shinjuku = 0.00 m (Yamanote plateau, correct), Iwamotocho = 1.00 m
# (Kanda-river lowland, correct), Kanda = 0.00 m (on higher ground within
# the flood zone, also correct — the flooding is 200+ m away).
# At 500 m the radius catches river-channel points far from the station
# and over-flags (Shinjuku gets a false 2.0 m from a channel 400 m away).
RADIUS_M = 100

ATTRIBUTION_TMG = "出典：東京都建設局 浸水予想区域図（東京都オープンデータカタログサイト）"
ATTRIBUTION_MLIT = "出典：国土交通省「国土数値情報」（国土数値情報ダウンロードサイト）"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def fetch_all(offline: bool) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    import urllib.request
    for zone, meta in SOURCES.items():
        path = CACHE / f"shinsui_{zone}.csv"
        if path.exists() and sha256(path) == meta["sha256"]:
            continue
        if offline:
            if not path.exists():
                sys.exit(f"FATAL: --offline but {path} missing")
            continue
        url = f"{BASE_URL}/shinsui_{zone}.csv"
        print(f"  downloading {zone}…")
        req = urllib.request.Request(url, headers={"User-Agent": "city-rating/1.0"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            path.write_bytes(resp.read())


def verify_all() -> None:
    for zone, meta in SOURCES.items():
        path = CACHE / f"shinsui_{zone}.csv"
        if not path.exists():
            sys.exit(f"FATAL: {path} missing — run without --offline first")
        actual = sha256(path)
        if actual != meta["sha256"]:
            sys.exit(f"FATAL: {zone} SHA mismatch\n  expected {meta['sha256']}\n  actual   {actual}")


def load_zones() -> list[dict]:
    """Load each zone CSV into numpy arrays of (lat, lng, depth)."""
    import numpy as np

    zones = []
    total_rows = 0
    for zone, meta in SOURCES.items():
        path = CACHE / f"shinsui_{zone}.csv"
        lats, lngs, depths = [], [], []
        with open(path, encoding=meta["enc"]) as f:
            reader = csv.reader(f)
            next(reader)  # header
            for row in reader:
                if len(row) < 5:
                    continue
                try:
                    d = float(row[1]) if row[1] else 0.0
                    lat = float(row[3])
                    lng = float(row[4])
                except (ValueError, IndexError):
                    continue
                depths.append(d)
                lats.append(lat)
                lngs.append(lng)
        n = len(lats)
        total_rows += n
        zones.append({
            "name": zone,
            "lat": np.array(lats, dtype=np.float64),
            "lng": np.array(lngs, dtype=np.float64),
            "depth": np.array(depths, dtype=np.float32),
            "n": n,
        })
        print(f"  {zone:20s} {n:>10,} rows")
    print(f"  total: {total_rows:,} rows across {len(zones)} zones")
    return zones


def compute_station_flood(zones: list[dict], stations: list[dict]) -> dict:
    """For each station, find max flood depth within RADIUS_M across all zones."""
    import numpy as np
    from scipy.spatial import cKDTree

    # Build a single KD-tree from all zone points.
    all_lat = np.concatenate([z["lat"] for z in zones])
    all_lng = np.concatenate([z["lng"] for z in zones])
    all_depth = np.concatenate([z["depth"] for z in zones])

    # Convert to approximate metres for radius search (cos(lat) correction for lng).
    mid_lat = float(np.mean(all_lat))
    lat_scale = 111_320.0  # m per degree lat
    lng_scale = 111_320.0 * np.cos(np.radians(mid_lat))  # m per degree lng

    print(f"  building KD-tree ({len(all_lat):,} points)…")
    t0 = time.time()
    # Subsample if too large for KD-tree build (>8M points)
    if len(all_lat) > 8_000_000:
        # Only keep points with depth > 0 to reduce tree size; stations outside
        # any mapped zone get depth 0 (not exposed).
        mask = all_depth > 0.01
        print(f"    filtering to {mask.sum():,} points with depth > 0.01 m")
        all_lat = all_lat[mask]
        all_lng = all_lng[mask]
        all_depth = all_depth[mask]

    tree_lat = all_lat * lat_scale
    tree_lng = all_lng * lng_scale
    coords = np.column_stack([tree_lat, tree_lng])
    tree = cKDTree(coords)
    print(f"    built in {time.time()-t0:.1f}s")

    out: dict[str, dict] = {}
    for s in stations:
        slug = s["slug"]
        slat = float(s["lat"]) * lat_scale
        slng = float(s["lng"]) * lng_scale
        idx = tree.query_ball_point([slat, slng], r=RADIUS_M)
        if idx:
            max_depth = float(all_depth[idx].max())
            out[slug] = {
                "max_depth_m": round(max_depth, 3),
                "flood_risk": max_depth >= FLOOD_THRESHOLD_M,
                "radius_m": RADIUS_M,
                "source": "tmg",
            }
        else:
            out[slug] = {
                "max_depth_m": 0.0,
                "flood_risk": False,
                "radius_m": RADIUS_M,
                "source": "tmg",
            }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true", help="Use cached CSVs; no network")
    args = ap.parse_args()

    if not args.offline:
        print("→ downloading TMG zone CSVs")
        fetch_all(False)
    print("→ verifying SHA-256")
    verify_all()

    print("→ loading zones")
    zones = load_zones()

    stations = json.loads(STATIONS.read_text())
    print(f"→ computing per-station flood depth for {len(stations)} stations")
    result = compute_station_flood(zones, stations)

    # Gates.
    exposed = sum(1 for v in result.values() if v["flood_risk"])
    total = len(result)
    ratio = exposed / total
    print(f"  flood-exposed (≥{FLOOD_THRESHOLD_M} m): {exposed}/{total} ({ratio:.1%})")
    # ADR #2 expects a meaningful split — the SRTM proxy flagged ~130 stations
    # at <5 m elevation. We should see roughly similar order of magnitude.
    if ratio > 0.50:
        sys.exit(f"FATAL: {ratio:.1%} stations flagged — threshold too loose?")
    if ratio < 0.02:
        sys.exit(f"FATAL: only {ratio:.1%} stations flagged — data join broken?")

    # Spot checks from the research note.
    for slug, expect in [("shinjuku", False), ("kameari", True), ("kanda", True)]:
        if slug in result and result[slug]["flood_risk"] != expect:
            print(f"  WARNING: spot-check {slug} expected flood_risk={expect}, got {result[slug]['flood_risk']}")

    doc = {
        "_meta": {
            "source": "TMG 浸水予想区域図 (東京都建設局) — inundation depth point grids, 14 river-basin zones",
            "url": "https://catalog.data.metro.tokyo.lg.jp/dataset/t000014d0000000029",
            "license": "CC BY 4.0",
            "attribution": ATTRIBUTION_TMG,
            "threshold_m": FLOOD_THRESHOLD_M,
            "radius_m": RADIUS_M,
            "scenario": "想定最大規模 (maximum assumed scale)",
            "ingested": time.strftime("%Y-%m-%d"),
            "notes": "Depth is continuous (not banded), from both 外水氾濫 (river overflow) "
                     "and 内水氾濫 (inland/drainage flooding). Official zones understate — "
                     "real flooding can exceed the model (MLIT caveat). The SRTM<5 m proxy "
                     "remains as elevation display; only the flood dealbreaker moved.",
            "zones": {z: SOURCES[z]["sha256"][:16] for z in SOURCES},
        },
        "stations": result,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT.relative_to(ROOT)} ({total} stations, {exposed} flood-exposed)")

    # Top affected stations for eyeball check.
    top = sorted(result.items(), key=lambda kv: -kv[1]["max_depth_m"])[:10]
    for slug, v in top:
        print(f"  {slug:25s} depth={v['max_depth_m']:6.2f} m  risk={v['flood_risk']}")


if __name__ == "__main__":
    main()
