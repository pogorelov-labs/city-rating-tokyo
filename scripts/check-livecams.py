#!/usr/bin/env python3
"""Report missing YouTube thumbnails in the shipped livecam snapshot.

A thumbnail is only a stale-ID signal: HTTP 200 does not establish that a
stream is live or embeddable, and HTTP 404 does not prove why it is missing.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "app/src/data/livecams.json"
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def load_ids(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("expected station-to-camera object")
    ids = set()
    for rows in data.values():
        if not isinstance(rows, list):
            raise ValueError("expected camera list for each station")
        for row in rows:
            value = row.get("video_id") if isinstance(row, dict) else None
            if not isinstance(value, str) or not VIDEO_ID.fullmatch(value):
                raise ValueError("invalid or missing video_id")
            ids.add(value)
    if not ids:
        raise ValueError("snapshot contains no camera IDs")
    return sorted(ids)


def check(ids, get=requests.head, delay=0.2, sleep=time.sleep):
    missing, unknown = [], []
    consecutive_errors = 0
    for index, video_id in enumerate(ids):
        if index:
            sleep(delay)
        try:
            response = get(f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg", timeout=10,
                           allow_redirects=False)
            if response.status_code == 404:
                missing.append(video_id)
                consecutive_errors = 0
            elif response.status_code == 200:
                consecutive_errors = 0
            else:
                unknown.append((video_id, f"HTTP {response.status_code}"))
                consecutive_errors += 1
        except requests.RequestException as exc:
            unknown.append((video_id, type(exc).__name__))
            consecutive_errors += 1
        if consecutive_errors == 3:
            unknown.extend((remaining, "not checked after consecutive errors") for remaining in ids[index + 1:])
            break
    return missing, unknown


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--threshold", type=int, default=0, help="maximum missing thumbnails")
    parser.add_argument("--offline", action="store_true", help="validate input; skip network (not a health pass)")
    args = parser.parse_args(argv)
    if args.threshold < 0:
        parser.error("--threshold must be non-negative")
    try:
        ids = load_ids(args.data)
    except (OSError, ValueError) as exc:
        print(f"ERROR: invalid snapshot: {exc}", file=sys.stderr)
        return 2
    if args.offline:
        print(f"SKIP: network disabled; {len(ids)} distinct IDs validated")
        return 0
    missing, unknown = check(ids)
    for video_id in missing:
        print(f"MISSING thumbnail: {video_id}")
    for video_id, reason in unknown:
        print(f"UNKNOWN: {video_id}: {reason}")
    print(f"Checked {len(ids)} distinct IDs: {len(missing)} missing, {len(unknown)} unknown; threshold {args.threshold}")
    print("Thumbnail status does not establish stream availability or embed permission.")
    if unknown:
        return 2
    return 1 if len(missing) > args.threshold else 0


if __name__ == "__main__":
    sys.exit(main())
