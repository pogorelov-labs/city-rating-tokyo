#!/usr/bin/env python3
"""Scrape YouTube live camera feeds near stations from mini-tokyo-3d (MIT).

Source: https://mini-tokyo.appspot.com/livecam
Backing plugin: https://github.com/nagix/mt3d-plugin-livecam (MIT)

The endpoint returns a list of ~98 YouTube channel-live cameras with
coordinates along railway tracks. Each entry has:
    id, name {en, ja, ko, ne, pt, th, zh-Hans, zh-Hant},
    channel (YouTube channel ID), keyword, center [lng, lat],
    zoom, bearing, pitch

Strategy:
  1. Fetch livecam JSON (single HTTP call, ~60 KB)
  2. For each of our 1493 stations, find cameras within MATCH_RADIUS_M
     (Haversine). Allow multiple cameras per station; sort by distance.
  3. Construct channel-live embed + watch URLs (no per-video ID needed).
  4. Write slim per-station records to both data/ and app/src/data/.

Usage:
    python scripts/scrapers/scrape-livecams.py             # full run
    python scripts/scrapers/scrape-livecams.py --dry-run   # no write
    python scripts/scrapers/scrape-livecams.py --cache-dir /tmp/mt3d
    python scripts/scrapers/scrape-livecams.py --debug     # print every match
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
LIVECAM_URL = "https://mini-tokyo.appspot.com/livecam"

OUR_STATIONS_PATH = ROOT / "data" / "stations.json"
OUTPUT_PATH_ROOT = ROOT / "data" / "livecams.json"
OUTPUT_PATH_APP = ROOT / "app" / "src" / "data" / "livecams.json"

MATCH_RADIUS_M = 300  # looser than last-trains' 200m — cameras are near tracks, not on platforms


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance between two WGS84 coordinates in meters."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_livecams(cache_dir: Optional[Path]) -> List[dict]:
    """Fetch the livecam endpoint. Caches raw JSON when --cache-dir is set."""
    cache_path = cache_dir / "livecam.json" if cache_dir else None
    if cache_path and cache_path.exists():
        print(f"  (cache) {cache_path}")
        return json.loads(cache_path.read_text())
    print(f"  Fetching {LIVECAM_URL}")
    r = requests.get(LIVECAM_URL, timeout=30)
    r.raise_for_status()
    data = r.json()
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, ensure_ascii=False))
    return data


def build_record(cam: dict, distance_m: float, data_date: str) -> dict:
    """Construct the slim per-station record shape.

    We store youtube-nocookie.com for the embed (matches our GDPR footer)
    and regular youtube.com for the watch-through link. Per-video IDs are
    not available from the source — channel-live URLs resolve at view time
    to whatever is currently live (or show YouTube's 'offline' placeholder).
    """
    channel_id = cam["channel"]
    name = cam.get("name") or {}
    name_en = name.get("en") or cam.get("id") or "Live Camera"
    name_ja = name.get("ja") or name_en
    return {
        "id": cam["id"],
        "name_en": name_en,
        "name_ja": name_ja,
        "channel_id": channel_id,
        "embed_url": f"https://www.youtube-nocookie.com/embed/live_stream?channel={channel_id}",
        "watch_url": f"https://www.youtube.com/channel/{channel_id}/live",
        "distance_m": round(distance_m),
        "source": "mini-tokyo-3d",
        "data_date": data_date,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="don't write output")
    parser.add_argument("--cache-dir", type=Path, default=None, help="cache the livecam fetch here")
    parser.add_argument("--debug", action="store_true", help="print every match with distance")
    args = parser.parse_args()

    if args.cache_dir:
        args.cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load our stations
    our_stations = json.loads(OUR_STATIONS_PATH.read_text())
    print(f"Loaded {len(our_stations)} of our stations")

    # 2. Load livecam data
    print("Loading livecam endpoint...")
    cams = load_livecams(args.cache_dir)
    print(f"Loaded {len(cams)} livecam entries")

    # Build (lng, lat) per cam, skip invalid
    cam_coords: List[Tuple[dict, float, float]] = []
    for cam in cams:
        center = cam.get("center")
        if not center or len(center) != 2:
            continue
        try:
            lng, lat = float(center[0]), float(center[1])
        except (TypeError, ValueError):
            continue
        cam_coords.append((cam, lng, lat))
    print(f"  Valid coords: {len(cam_coords)} / {len(cams)}")

    # 3. Match each of our slugs to nearby cameras
    data_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Matching by coordinates (radius {MATCH_RADIUS_M}m)...")
    output: Dict[str, List[dict]] = {}
    for s in our_stations:
        slug = s["slug"]
        our_lat, our_lng = s["lat"], s["lng"]
        matches: List[Tuple[float, dict]] = []
        for cam, c_lng, c_lat in cam_coords:
            d = haversine_m(our_lat, our_lng, c_lat, c_lng)
            if d <= MATCH_RADIUS_M:
                matches.append((d, cam))
        if not matches:
            continue
        # Sort nearest first
        matches.sort(key=lambda t: t[0])
        records = [build_record(cam, d, data_date) for d, cam in matches]
        output[slug] = records
        if args.debug:
            names = ", ".join(f"{r['name_en']} ({r['distance_m']}m)" for r in records)
            print(f"  {slug}: {names}")

    matched = len(output)
    print(f"\nMatched {matched} / {len(our_stations)} stations ({matched / len(our_stations):.1%})")

    # Stats: how many stations have multiple cams?
    total_cam_rows = sum(len(v) for v in output.values())
    multi = sum(1 for v in output.values() if len(v) > 1)
    print(f"  Total camera rows: {total_cam_rows}")
    print(f"  Stations with 2+ cameras: {multi}")
    if multi:
        print("  Examples:")
        for slug, rows in sorted(output.items(), key=lambda kv: -len(kv[1]))[:5]:
            if len(rows) > 1:
                print(f"    {slug}: {len(rows)} cameras")

    # Sanity spot-check on hubs
    print("\n  Hub spot-check:")
    for sample in ["shibuya", "shinjuku", "tokyo", "akabane", "ikebukuro", "haneda_airport_terminal_1", "narita_airport_terminal_1"]:
        if sample in output:
            cam_name = output[sample][0]["name_en"]
            print(f"    {sample}: {cam_name}")

    # Also: unmatched cameras (cameras that didn't match ANY of our stations)
    matched_cam_ids = {r["id"] for rows in output.values() for r in rows}
    unmatched_cams = [cam for cam in cams if cam.get("id") not in matched_cam_ids]
    print(f"\n  Cameras with no station match (outside {MATCH_RADIUS_M}m of any slug): {len(unmatched_cams)}")
    if args.debug and unmatched_cams:
        for cam in unmatched_cams[:10]:
            name = (cam.get("name") or {}).get("en") or cam.get("id")
            center = cam.get("center")
            print(f"    - {cam.get('id')}: {name} @ {center}")

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
