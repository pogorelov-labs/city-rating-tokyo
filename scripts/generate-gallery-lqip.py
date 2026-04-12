#!/usr/bin/env python3
"""Add LQIP base64 to every image entry in station-images-all.json.

Reads station-images-all.json, generates 8×6 LQIP for each image,
writes enriched JSON with `lqip` field per entry.

Usage (Docker on VPS):
  docker run -d --name gallery-lqip --restart=no \
    -v /tmp/generate-gallery-lqip.py:/app/script.py:ro \
    -v /tmp/station-images-all.json:/app/station-images-all.json:ro \
    -v /var/lib/docker/volumes/zqos2v05v3w5n9nq0ory0t2k_image-data/_data:/app/images:ro \
    python:3.11-slim bash -c "pip install --quiet Pillow && python3 -u /app/script.py"
"""

import json
import base64
import io
import os
from pathlib import Path

from PIL import Image

IMAGE_HOST = "https://img.pogorelov.dev"
IMAGES_DIR = Path("/app/images")
INPUT_JSON = Path("/app/station-images-all.json")
OUTPUT_JSON = Path("/tmp/station-images-all-lqip.json")

LQIP_SIZE = (8, 6)
LQIP_QUALITY = 5


def url_to_local_path(url: str) -> Path | None:
    prefix = f"{IMAGE_HOST}/"
    if not url.startswith(prefix):
        return None
    relative = url[len(prefix):]
    return IMAGES_DIR / relative


def generate_lqip(img: Image.Image) -> str:
    tiny = img.resize(LQIP_SIZE, Image.LANCZOS)
    buf = io.BytesIO()
    tiny.save(buf, format="JPEG", quality=LQIP_QUALITY)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def main():
    print(f"Reading {INPUT_JSON}")
    with open(INPUT_JSON) as f:
        all_images = json.load(f)

    total_stations = len(all_images)
    total_images = sum(len(imgs) for imgs in all_images.values())
    print(f"Found {total_stations} stations, {total_images} images total")

    processed = 0
    skipped = 0
    errors = 0

    for slug, images in sorted(all_images.items()):
        for entry in images:
            url = entry.get("url", "")
            local_path = url_to_local_path(url)

            if not local_path or not local_path.exists():
                skipped += 1
                continue

            try:
                img = Image.open(local_path)
                img = img.convert("RGB")
                entry["lqip"] = generate_lqip(img)
                processed += 1
            except Exception as e:
                print(f"  ERROR {slug}/{url.split('/')[-1]}: {e}")
                errors += 1

        if (processed + skipped + errors) % 500 == 0:
            print(f"  Processed {processed} images...")

    print(f"\nDone: {processed} processed, {skipped} skipped, {errors} errors")
    print(f"Writing {OUTPUT_JSON}")

    with open(OUTPUT_JSON, "w") as f:
        json.dump(all_images, f, separators=(",", ":"))

    size_mb = os.path.getsize(OUTPUT_JSON) / (1024 * 1024)
    print(f"Output: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
