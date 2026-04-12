#!/usr/bin/env python3
"""
Check health of all image URLs in station-images-all.json.
Outputs a report of broken URLs and writes a cleaned JSON with only working URLs.

Runs on VPS to check img.pogorelov.dev URLs with -k (skip SSL verify since cert is broken).

Usage on VPS:
  docker run -d --name image-checker --restart=no \
    -v /tmp/check-image-urls.py:/app/scraper.py:ro \
    -v /tmp/station-images-all.json:/app/station-images-all.json:ro \
    -v /tmp/image-check-results:/app/output \
    python:3.11-slim bash -c "pip install --quiet requests && python3 -u /app/scraper.py"

Or locally:
  python3 scripts/scrapers/check-image-urls.py
"""

import json
import os
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- config ----------
CONCURRENCY = 20  # parallel HEAD requests
TIMEOUT = 10  # seconds per request
INPUT_FILE = "/app/station-images-all.json"
OUTPUT_DIR = "/app/output"

# ---------- helpers ----------
def load_images():
    """Find and load station-images-all.json."""
    paths = [
        INPUT_FILE,
        "app/src/data/station-images-all.json",
        "station-images-all.json",
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f), p
    print("ERROR: station-images-all.json not found")
    sys.exit(1)


def check_url(slug, idx, url):
    """HEAD request to check if URL is accessible. Returns (slug, idx, url, status, ok)."""
    try:
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True, verify=False)
        return (slug, idx, url, r.status_code, r.status_code < 400)
    except requests.exceptions.SSLError:
        # Try without SSL
        try:
            r = requests.head(url, timeout=TIMEOUT, allow_redirects=True, verify=False)
            return (slug, idx, url, r.status_code, r.status_code < 400)
        except Exception as e:
            return (slug, idx, url, 0, False)
    except Exception as e:
        return (slug, idx, url, 0, False)


def main():
    print("=== Image URL Health Check ===")

    images, path = load_images()
    print(f"Loaded from: {path}")
    print(f"Stations with images: {len(images)}")

    # Collect all URLs
    tasks = []
    total_urls = 0
    for slug, imgs in images.items():
        for idx, img in enumerate(imgs):
            url = img.get("url", "")
            if url:
                tasks.append((slug, idx, url))
                total_urls += 1

    print(f"Total URLs to check: {total_urls}")

    # Parallel HEAD checks
    broken = []
    ok_count = 0
    checked = 0

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(check_url, s, i, u): (s, i, u) for s, i, u in tasks}

        for future in as_completed(futures):
            slug, idx, url, status, is_ok = future.result()
            checked += 1

            if is_ok:
                ok_count += 1
            else:
                broken.append({"slug": slug, "index": idx, "url": url, "status": status})

            if checked % 200 == 0 or checked == total_urls:
                print(f"  [{checked}/{total_urls}] OK: {ok_count}, Broken: {len(broken)}")

    # Report
    print(f"\n=== Results ===")
    print(f"Total checked: {total_urls}")
    print(f"OK: {ok_count} ({ok_count*100/total_urls:.1f}%)")
    print(f"Broken: {len(broken)} ({len(broken)*100/total_urls:.1f}%)")

    if broken:
        print(f"\nBroken URLs by domain:")
        from collections import Counter
        domains = Counter()
        for b in broken:
            url = b["url"]
            domain = url.split("/")[2] if url.startswith("http") else "unknown"
            domains[domain] += 1
        for domain, count in domains.most_common(10):
            print(f"  {domain}: {count}")

        print(f"\nFirst 20 broken URLs:")
        for b in broken[:20]:
            print(f"  [{b['status']}] {b['slug']}: {b['url'][:100]}")

    # Build cleaned JSON (remove broken entries)
    broken_set = {(b["slug"], b["index"]) for b in broken}
    cleaned = {}
    removed_stations = 0
    for slug, imgs in images.items():
        good = [img for idx, img in enumerate(imgs) if (slug, idx) not in broken_set]
        if good:
            cleaned[slug] = good
        else:
            removed_stations += 1

    print(f"\nCleaned JSON: {len(cleaned)} stations (removed {removed_stations} with all broken)")

    # Save results
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(os.path.join(OUTPUT_DIR, "broken-urls.json"), "w") as f:
        json.dump(broken, f, indent=2)
    print(f"Saved: {OUTPUT_DIR}/broken-urls.json")

    with open(os.path.join(OUTPUT_DIR, "station-images-all-cleaned.json"), "w") as f:
        json.dump(cleaned, f, ensure_ascii=False)
    print(f"Saved: {OUTPUT_DIR}/station-images-all-cleaned.json")

    # Station coverage summary
    orig_count = len(images)
    clean_count = len(cleaned)
    print(f"\nCoverage: {orig_count} → {clean_count} stations ({clean_count*100/1493:.1f}% of 1493)")


if __name__ == "__main__":
    # Suppress InsecureRequestWarning for -k style checks
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
