#!/usr/bin/env python3
"""Remove confirmed face images from station-images-all.json and VPS disk.

Reads confirmed-removals.json (exported from face-review.html) and:
1. Removes matching entries from station-images-all.json
2. Deletes image files from /docker-volume/img/
3. Reports which stations lost their first image (thumbnail regen needed)

Runs on VPS as Docker container.

Output:
  /app/output/station-images-all.json — cleaned (removals applied)
  /app/output/removal-report.json — what was removed + regen list

Usage (Docker on VPS):
  docker run -d --name face-remove --restart=no \
    -v /tmp/remove-flagged-images.py:/app/remove.py:ro \
    -v /tmp/station-images-all.json:/app/station-images-all.json:ro \
    -v /tmp/confirmed-removals.json:/app/confirmed-removals.json:ro \
    -v /docker-volume/img:/app/images \
    -v /tmp/face-remove-results:/app/output \
    python:3.11-slim bash -c "python3 -u /app/remove.py"

Or dry-run (no disk deletions):
  ... python3 -u /app/remove.py --dry-run
"""

import json
import os
import sys
from pathlib import Path

IMAGES_DIR = Path("/app/images")
INPUT_JSON = Path("/app/station-images-all.json")
REMOVALS_JSON = Path("/app/confirmed-removals.json")
OUTPUT_DIR = Path("/app/output")
IMAGE_HOST = "https://img.pogorelov.dev/"

DRY_RUN = "--dry-run" in sys.argv


def url_to_disk_path(url: str) -> Path | None:
    """Convert img.pogorelov.dev URL to local disk path.

    Flickr local_path omits 'flickr/' prefix, but URL includes it.
    Always derive disk path from URL to get the correct location.
    """
    if not url.startswith(IMAGE_HOST):
        return None
    relative = url[len(IMAGE_HOST):]
    return IMAGES_DIR / relative


def main():
    print("=== Face Image Removal ===", flush=True)
    if DRY_RUN:
        print("*** DRY RUN — no files will be deleted ***", flush=True)

    # Load inputs
    with open(INPUT_JSON) as f:
        all_images = json.load(f)

    with open(REMOVALS_JSON) as f:
        removals = json.load(f)

    print(f"Loaded {sum(len(v) for v in all_images.values())} images across {len(all_images)} stations", flush=True)
    print(f"Removals requested: {len(removals)}", flush=True)

    # Build removal set: (slug, local_path) for fast lookup
    removal_set = set()
    for r in removals:
        removal_set.add((r["slug"], r["local_path"]))

    # Track results
    removed_count = 0
    disk_deleted = 0
    disk_errors = 0
    first_image_changed = []  # stations where image[0] was removed
    stations_emptied = []     # stations with no images left

    # Process each station
    cleaned = {}
    for slug, images in sorted(all_images.items()):
        original_first = images[0]["local_path"] if images else None
        kept = []

        for img in images:
            lp = img.get("local_path", "")
            if (slug, lp) in removal_set:
                removed_count += 1

                # Delete from disk — derive path from URL (local_path may omit source prefix)
                url = img.get("url", "")
                disk_path = url_to_disk_path(url) if url else IMAGES_DIR / lp
                if disk_path and disk_path.exists():
                    if DRY_RUN:
                        print(f"  [DRY] Would delete: {disk_path}", flush=True)
                    else:
                        try:
                            os.remove(disk_path)
                            disk_deleted += 1
                        except OSError as e:
                            print(f"  ERROR deleting {disk_path}: {e}", flush=True)
                            disk_errors += 1
                else:
                    print(f"  WARN: file not found on disk: {disk_path}", flush=True)
            else:
                kept.append(img)

        if kept:
            cleaned[slug] = kept
            # Check if first image changed
            new_first = kept[0]["local_path"] if kept else None
            if new_first != original_first:
                first_image_changed.append(slug)
        else:
            stations_emptied.append(slug)

    # Save cleaned JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_json = OUTPUT_DIR / "station-images-all.json"
    with open(output_json, "w") as f:
        json.dump(cleaned, f, ensure_ascii=False, separators=(",", ":"))

    new_total = sum(len(v) for v in cleaned.values())

    # Save report
    report = {
        "dry_run": DRY_RUN,
        "removals_requested": len(removals),
        "images_removed_from_json": removed_count,
        "files_deleted_from_disk": disk_deleted,
        "disk_delete_errors": disk_errors,
        "stations_with_changed_preview": first_image_changed,
        "stations_emptied": stations_emptied,
        "remaining_images": new_total,
        "remaining_stations": len(cleaned),
    }
    report_path = OUTPUT_DIR / "removal-report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Summary
    print(f"\n=== Results ===", flush=True)
    print(f"Images removed from JSON: {removed_count}", flush=True)
    print(f"Files deleted from disk: {disk_deleted} (errors: {disk_errors})", flush=True)
    print(f"Remaining: {new_total} images across {len(cleaned)} stations", flush=True)
    print(f"Stations with changed preview (need thumbnail regen): {len(first_image_changed)}", flush=True)

    if first_image_changed:
        print(f"  Affected previews: {', '.join(first_image_changed[:20])}", flush=True)
        if len(first_image_changed) > 20:
            print(f"  ... and {len(first_image_changed) - 20} more", flush=True)

    if stations_emptied:
        print(f"Stations with NO images left: {len(stations_emptied)}", flush=True)
        print(f"  {', '.join(stations_emptied)}", flush=True)

    print(f"\nSaved: {output_json}", flush=True)
    print(f"Report: {report_path}", flush=True)

    if first_image_changed:
        print(f"\nNEXT STEP: Regenerate thumbnails with generate-thumbnails.py", flush=True)
        print(f"  Then regenerate gallery LQIP with generate-gallery-lqip.py", flush=True)


if __name__ == "__main__":
    main()
