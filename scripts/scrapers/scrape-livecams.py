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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


# Extract YouTube video ID from the MT3D `html` field, which looks like:
#   <iframe ... src="https://www.youtube.com/embed/VIDEO_ID?autoplay=1&..." ...>
# This is the primary playable reference — MT3D's endpoint refreshes these
# periodically as live streams end. Video IDs go stale; re-scrape is required.
EMBED_RE = re.compile(r"/embed/([A-Za-z0-9_-]{11})")

# Extract video ID from a thumbnail URL like:
#   https://i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg?...
THUMB_RE = re.compile(r"/vi/([A-Za-z0-9_-]{11})/")

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


def extract_video_id(cam: dict) -> Optional[str]:
    """Extract the live-stream video ID from the MT3D cam record.

    Tries `html` first (the iframe src), then `thumbnail` URL as a fallback.
    Returns None if neither yields a valid 11-char YouTube video ID.
    """
    html = cam.get("html") or ""
    m = EMBED_RE.search(html)
    if m:
        return m.group(1)
    thumbnail = cam.get("thumbnail") or ""
    m = THUMB_RE.search(thumbnail)
    if m:
        return m.group(1)
    return None


def build_record(cam: dict, distance_m: float, data_date: str) -> Optional[dict]:
    """Construct the slim per-station record shape.

    Returns None (skipping the cam) if no video ID can be extracted — without
    it, the embed can't be built reliably. This filters out entries that MT3D
    hasn't refreshed to a valid currently-live stream.

    Output uses:
      - embed_url: youtube.com/embed/{VIDEO_ID} — matches what MT3D's own
        plugin embeds, maximizing compatibility. We tried the stricter
        youtube-nocookie.com domain but some video owners disallow embeds
        there while allowing them on youtube.com. Privacy is preserved by
        the click-to-load facade + GDPR footer (no cookies until the user
        explicitly clicks play).
      - watch_url: youtube.com/watch?v={VIDEO_ID} (exact video, not channel)
      - thumbnail: YouTube's video thumbnail URL (displayed on the facade)

    Channel ID is retained as metadata only — it's not used for the embed
    because the `embed/live_stream?channel=` pattern is deprecated and
    unreliable. The video ID pattern is what MT3D's own plugin embeds.
    """
    video_id = extract_video_id(cam)
    if not video_id:
        return None

    channel_id = cam.get("channel") or ""
    name = cam.get("name") or {}
    name_en = name.get("en") or cam.get("id") or "Live Camera"
    name_ja = name.get("ja") or name_en
    # MT3D's thumbnail URL includes short-lived signed query params; always
    # use the unsigned permanent form to avoid link rot between re-scrapes.
    thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    return {
        "id": cam["id"],
        "name_en": name_en,
        "name_ja": name_ja,
        "video_id": video_id,
        "channel_id": channel_id,
        "embed_url": f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&playsinline=1",
        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": thumbnail,
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
        records = [r for r in (build_record(cam, d, data_date) for d, cam in matches) if r is not None]
        if not records:
            continue  # cam had no extractable video_id
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
