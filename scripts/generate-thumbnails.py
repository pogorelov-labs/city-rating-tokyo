#!/usr/bin/env python3
"""Generate 320px thumbnails + 8×6 LQIP base64 for station images.

Runs on VPS as Docker container with /docker-volume/img mounted.
Reads station-images-all.json, processes the first image per station.

Output:
  - Thumbnails on disk at /app/thumb/{source}/{slug}/{filename}
  - /tmp/station-thumbnails.json with {slug: {thumb: url, lqip: base64}}

Usage (Docker on VPS):
  docker run -d --name generate-thumbnails --restart=no \
    -v /tmp/generate-thumbnails.py:/app/script.py:ro \
    -v /tmp/station-images-all.json:/app/station-images-all.json:ro \
    -v /docker-volume/img:/app/images:ro \
    -v /docker-volume/img/thumb:/app/thumb \
    python:3.11-slim bash -c "pip install --quiet Pillow && python3 -u /app/script.py"
"""

import json
import base64
import io
import os
import sys
from pathlib import Path

from PIL import Image

IMAGE_HOST = "https://img.pogorelov.dev"
IMAGES_DIR = Path("/app/images")
THUMB_DIR = Path("/app/thumb")
INPUT_JSON = Path("/app/station-images-all.json")
OUTPUT_JSON = Path("/tmp/station-thumbnails.json")

THUMB_WIDTH = 320
THUMB_QUALITY = 80
LQIP_SIZE = (8, 6)
LQIP_QUALITY = 5


def url_to_local_path(url: str) -> Path | None:
    """Convert img.pogorelov.dev URL to local file path."""
    prefix = f"{IMAGE_HOST}/"
    if not url.startswith(prefix):
        return None
    relative = url[len(prefix):]
    return IMAGES_DIR / relative


def generate_thumbnail(img: Image.Image) -> Image.Image:
    """Resize to THUMB_WIDTH wide, preserving aspect ratio."""
    w, h = img.size
    ratio = THUMB_WIDTH / w
    new_h = int(h * ratio)
    return img.resize((THUMB_WIDTH, new_h), Image.LANCZOS)


def generate_lqip(img: Image.Image) -> str:
    """Generate tiny 8×6 JPEG as base64 data URL."""
    tiny = img.resize(LQIP_SIZE, Image.LANCZOS)
    buf = io.BytesIO()
    tiny.save(buf, format="JPEG", quality=LQIP_QUALITY)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def main():
    print(f"Reading {INPUT_JSON}")
    with open(INPUT_JSON) as f:
        all_images = json.load(f)

    print(f"Found {len(all_images)} stations in input JSON")

    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    processed = 0
    skipped = 0
    errors = 0

    for slug, images in sorted(all_images.items()):
        if not images:
            skipped += 1
            continue

        first = images[0]
        url = first.get("url", "")
        local_path = url_to_local_path(url)

        if not local_path or not local_path.exists():
            print(f"  SKIP {slug}: file not found ({local_path})")
            skipped += 1
            continue

        try:
            img = Image.open(local_path)
            img = img.convert("RGB")

            # Generate thumbnail
            thumb = generate_thumbnail(img)
            relative = str(local_path.relative_to(IMAGES_DIR))
            thumb_path = THUMB_DIR / relative
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            thumb.save(thumb_path, format="JPEG", quality=THUMB_QUALITY)

            thumb_url = f"{IMAGE_HOST}/thumb/{relative}"

            # Generate LQIP
            lqip = generate_lqip(img)

            results[slug] = {"thumb": thumb_url, "lqip": lqip}
            processed += 1

            if processed % 100 == 0:
                print(f"  Processed {processed} stations...")

        except Exception as e:
            print(f"  ERROR {slug}: {e}")
            errors += 1

    print(f"\nDone: {processed} processed, {skipped} skipped, {errors} errors")
    print(f"Writing {OUTPUT_JSON}")

    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, separators=(",", ":"))

    size_kb = os.path.getsize(OUTPUT_JSON) / 1024
    print(f"Output: {len(results)} entries, {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
