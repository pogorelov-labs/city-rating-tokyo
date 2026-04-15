#!/usr/bin/env python3
"""Scrape last train departure times from mini-tokyo-3d (MIT licensed).

Source: https://github.com/nagix/mini-tokyo-3d/tree/master/data/train-timetables
174 JSON files covering JR East, Tokyo Metro, Toei, and all major private
railways. Each file contains trips with `tt` (timetable) array of
{s: station_id, d: "HH:MM" departure, a: "HH:MM" arrival}.

Strategy:
  1. Fetch MT3D stations.json (2522 entries with id + coord)
  2. Match to our 1493 slugs via Haversine distance (<200m)
  3. Download all timetable JSONs, group by day_type (Weekday / SaturdayHoliday)
  4. For each station, compute MAX(departure) — handling post-midnight carefully
  5. Output app/src/data/last-trains.json keyed by our slug

Usage:
    python scripts/scrapers/scrape-last-trains.py             # full run
    python scripts/scrapers/scrape-last-trains.py --dry-run   # no write
    python scripts/scrapers/scrape-last-trains.py --cache-dir /tmp/mt3d   # cache downloads
"""
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
MT3D_RAW = "https://raw.githubusercontent.com/nagix/mini-tokyo-3d/master"
MT3D_API_DIR = "https://api.github.com/repos/nagix/mini-tokyo-3d/contents/data/train-timetables"

OUR_STATIONS_PATH = ROOT / "data" / "stations.json"
OUTPUT_PATH_ROOT = ROOT / "data" / "last-trains.json"
OUTPUT_PATH_APP = ROOT / "app" / "src" / "data" / "last-trains.json"

MATCH_RADIUS_M = 200  # coordinate matching threshold in meters


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance between two WGS84 coordinates in meters."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_mt3d_stations(cache_dir: Optional[Path]) -> List[dict]:
    """Fetch MT3D stations.json. Each entry has id, coord [lng, lat], title."""
    cache_path = cache_dir / "mt3d-stations.json" if cache_dir else None
    if cache_path and cache_path.exists():
        print(f"  (cache) {cache_path}")
        return json.loads(cache_path.read_text())
    url = f"{MT3D_RAW}/data/stations.json"
    print(f"  Fetching {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data))
    return data


def list_timetable_files() -> List[str]:
    """List all timetable JSON filenames from MT3D's train-timetables dir."""
    r = requests.get(MT3D_API_DIR, timeout=30)
    r.raise_for_status()
    return [f["name"] for f in r.json() if f["name"].endswith(".json")]


def fetch_timetable(filename: str, cache_dir: Optional[Path]) -> List[dict]:
    """Fetch one timetable JSON file (list of trip dicts)."""
    cache_path = cache_dir / filename if cache_dir else None
    if cache_path and cache_path.exists():
        return json.loads(cache_path.read_text())
    url = f"{MT3D_RAW}/data/train-timetables/{filename}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data))
    return data


def parse_hhmm(t: str) -> Optional[int]:
    """'HH:MM' → minutes since 00:00 of the operating day. None on bad input."""
    if not t or len(t) != 5 or t[2] != ":":
        return None
    try:
        h, m = int(t[:2]), int(t[3:])
        return h * 60 + m
    except ValueError:
        return None


def analyze_trip(trip: dict) -> List[Tuple[str, str, int, bool]]:
    """Extract (station_id, day_type, departure_minutes, is_late_night) tuples.

    Only considers `d` (departure) times — `a` (arrival-only, terminal stop)
    is skipped because a passenger cannot board a train that ends there.

    `is_late_night` flags whether this stop follows a 22:00+ stop in the same
    trip, allowing us to distinguish post-midnight last-train service from
    early-morning first-train service. Without it, a 00:05 first train would
    be mistaken for a last train.
    """
    trip_id = trip.get("id", "")
    day_type = "holiday" if "SaturdayHoliday" in trip_id else "weekday"
    tt = trip.get("tt") or []

    # Decide once per trip whether any stop is timed after 22:00 (use d or a
    # here — we care about trip shape, not boardability)
    any_late = False
    for stop in tt:
        t = stop.get("d") or stop.get("a")
        m = parse_hhmm(t)
        if m is not None and m >= 22 * 60:
            any_late = True
            break

    results: List[Tuple[str, str, int, bool]] = []
    seen_late = False
    for stop in tt:
        # Track trip progression using either departure or arrival
        t_any = stop.get("d") or stop.get("a")
        m_any = parse_hhmm(t_any)
        if m_any is not None and m_any >= 22 * 60:
            seen_late = True
        # But only emit a result if the stop has a DEPARTURE (boardable)
        t_dep = stop.get("d")
        m = parse_hhmm(t_dep)
        if m is None:
            continue
        is_late_night = True
        if m < 3 * 60:  # 00:00-02:59
            is_late_night = seen_late or any_late
        sid = stop.get("s")
        if sid:
            results.append((sid, day_type, m, is_late_night))
    return results


def minutes_to_hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="don't write output")
    parser.add_argument("--cache-dir", type=Path, default=None, help="cache MT3D downloads here")
    parser.add_argument("--limit", type=int, default=0, help="max timetable files to fetch (debug)")
    args = parser.parse_args()

    cache_dir = args.cache_dir
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load our stations
    our_stations = json.loads(OUR_STATIONS_PATH.read_text())
    print(f"Loaded {len(our_stations)} of our stations")

    # 2. Load MT3D stations
    print("Loading MT3D stations.json...")
    mt3d_stations = load_mt3d_stations(cache_dir)
    print(f"Loaded {len(mt3d_stations)} MT3D station entries")

    # Build MT3D id -> (lng, lat) map
    mt3d_coords: Dict[str, Tuple[float, float]] = {}
    for s in mt3d_stations:
        sid = s.get("id")
        coord = s.get("coord")
        if sid and coord and len(coord) == 2:
            mt3d_coords[sid] = (coord[0], coord[1])  # (lng, lat)

    # 3. For each of our slugs, find matching MT3D IDs
    print(f"Matching by coordinates (radius {MATCH_RADIUS_M}m)...")
    slug_to_mt3d_ids: Dict[str, List[str]] = {}
    for s in our_stations:
        slug = s["slug"]
        our_lat, our_lng = s["lat"], s["lng"]
        matches: List[str] = []
        for mid, (m_lng, m_lat) in mt3d_coords.items():
            if haversine_m(our_lat, our_lng, m_lat, m_lng) <= MATCH_RADIUS_M:
                matches.append(mid)
        if matches:
            slug_to_mt3d_ids[slug] = matches
    matched = len(slug_to_mt3d_ids)
    print(f"Matched {matched} / {len(our_stations)} stations ({matched / len(our_stations):.1%})")

    # Build reverse index for fast lookup
    mt3d_id_to_slug: Dict[str, str] = {}
    for slug, ids in slug_to_mt3d_ids.items():
        for mid in ids:
            # If a MT3D id maps to multiple of our slugs (rare — only if two
            # of our slugs are within 200m of the same MT3D entry), keep the
            # first. Log a warning.
            if mid in mt3d_id_to_slug and mt3d_id_to_slug[mid] != slug:
                print(f"  warning: {mid} matches both {mt3d_id_to_slug[mid]} and {slug}")
                continue
            mt3d_id_to_slug[mid] = slug

    # 4. List timetable files
    print("Listing timetable files...")
    files = list_timetable_files()
    if args.limit:
        files = files[: args.limit]
    print(f"Found {len(files)} timetable files")

    # 5. Fetch + parse
    # max_dep[slug][day_type] = max departure minutes
    max_dep: Dict[str, Dict[str, int]] = {}
    trips_processed = 0
    for i, fname in enumerate(files, 1):
        if i % 20 == 0 or i == len(files):
            print(f"  [{i}/{len(files)}] {fname}")
        try:
            trips = fetch_timetable(fname, cache_dir)
        except requests.HTTPError as e:
            print(f"  skip {fname}: {e}")
            continue
        for trip in trips:
            trips_processed += 1
            for sid, day_type, m, is_late in analyze_trip(trip):
                if not is_late:
                    continue
                slug = mt3d_id_to_slug.get(sid)
                if not slug:
                    continue
                prev = max_dep.setdefault(slug, {}).get(day_type, -1)
                # For post-midnight slots, shift by 24h in comparison so 00:30
                # always beats 23:55
                cmp_m = m + 24 * 60 if m < 3 * 60 else m
                cmp_prev = prev + 24 * 60 if 0 <= prev < 3 * 60 else prev
                if cmp_m > cmp_prev:
                    max_dep[slug][day_type] = m
        # Be polite to GitHub raw CDN
        if not cache_dir:
            time.sleep(0.05)
    print(f"Processed {trips_processed} trips across {len(files)} files")

    # 6. Assemble output
    data_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output: Dict[str, dict] = {}
    for slug, by_day in max_dep.items():
        entry: Dict[str, object] = {}
        if "weekday" in by_day:
            entry["weekday"] = minutes_to_hhmm(by_day["weekday"])
        if "holiday" in by_day:
            entry["holiday"] = minutes_to_hhmm(by_day["holiday"])
        if not entry:
            continue
        entry["sources"] = sorted(slug_to_mt3d_ids.get(slug, []))
        entry["data_date"] = data_date
        output[slug] = entry

    print(f"\nCoverage: {len(output)} / {len(our_stations)} stations have last_train data")

    # Stats
    has_both = sum(1 for v in output.values() if "weekday" in v and "holiday" in v)
    weekday_only = sum(1 for v in output.values() if "weekday" in v and "holiday" not in v)
    holiday_only = sum(1 for v in output.values() if "holiday" in v and "weekday" not in v)
    print(f"  both day types:   {has_both}")
    print(f"  weekday only:     {weekday_only}")
    print(f"  holiday only:     {holiday_only}")

    # Sample for sanity check
    for sample_slug in ["shinjuku", "tokyo", "shibuya", "yokohama", "takao", "ofuna"]:
        if sample_slug in output:
            print(f"  {sample_slug}: {output[sample_slug].get('weekday', '?')} (wk) / {output[sample_slug].get('holiday', '?')} (hol)")

    if args.dry_run:
        print("\n(dry run — not writing)")
        return

    OUTPUT_PATH_ROOT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH_APP.parent.mkdir(parents=True, exist_ok=True)
    # Sort keys for stable diffs
    sorted_output = dict(sorted(output.items()))
    OUTPUT_PATH_ROOT.write_text(json.dumps(sorted_output, ensure_ascii=False, indent=2))
    OUTPUT_PATH_APP.write_text(json.dumps(sorted_output, ensure_ascii=False, indent=2))
    print(f"\nWrote {OUTPUT_PATH_ROOT}")
    print(f"Wrote {OUTPUT_PATH_APP}")


if __name__ == "__main__":
    sys.exit(main() or 0)
