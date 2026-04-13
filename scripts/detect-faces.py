#!/usr/bin/env python3
"""Detect faces in station images using OpenCV DNN.

Scans all images in station-images-all.json, flags those with prominent faces
(area_ratio > threshold OR high confidence). Outputs a JSON report for human review.

Runs on VPS as Docker container with /docker-volume/img mounted read-only.

Output:
  /app/output/flagged-faces.json — images with detected faces
  /app/output/face-detect-stats.json — summary statistics

Usage (Docker on VPS):
  docker run -d --name face-detect --restart=no \
    -v /tmp/detect-faces.py:/app/detect.py:ro \
    -v /tmp/station-images-all.json:/app/station-images-all.json:ro \
    -v /docker-volume/img:/app/images:ro \
    -v /tmp/face-detect-results:/app/output \
    python:3.11-slim bash -c \
    "pip install --quiet opencv-python-headless numpy && python3 -u /app/detect.py"
"""

import json
import os
import sys
import time
import urllib.request
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

# ---------- config ----------
IMAGES_DIR = Path("/app/images")
INPUT_JSON = Path("/app/station-images-all.json")
OUTPUT_DIR = Path("/app/output")

# Face detection thresholds
CONFIDENCE_THRESHOLD = 0.5      # minimum DNN confidence to count as a face
AREA_RATIO_FLAG = 0.02          # flag if any face covers >2% of image area
HIGH_CONFIDENCE_FLAG = 0.7      # flag if any face has >70% confidence (even if small)
CONCURRENCY = 8                 # threads for I/O + detection

# DNN model files (downloaded on first run)
MODEL_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
WEIGHTS_URL = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
MODEL_DIR = Path("/tmp/face_model")


def download_model():
    """Download OpenCV DNN face detection model if not cached."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    proto_path = MODEL_DIR / "deploy.prototxt"
    weights_path = MODEL_DIR / "res10_300x300_ssd_iter_140000.caffemodel"

    if not proto_path.exists():
        print("Downloading prototxt...")
        urllib.request.urlretrieve(MODEL_URL, proto_path)

    if not weights_path.exists():
        print("Downloading caffemodel (10 MB)...")
        urllib.request.urlretrieve(WEIGHTS_URL, weights_path)

    return str(proto_path), str(weights_path)


def create_detector():
    """Create and return OpenCV DNN face detector."""
    proto_path, weights_path = download_model()
    net = cv2.dnn.readNetFromCaffe(proto_path, weights_path)
    return net


def url_to_local_path(url: str) -> Path | None:
    """Convert img.pogorelov.dev URL to local file path."""
    prefix = "https://img.pogorelov.dev/"
    if not url.startswith(prefix):
        return None
    relative = url[len(prefix):]
    return IMAGES_DIR / relative


def detect_faces_in_image(image_path: Path, net):
    """Detect faces in a single image. Returns list of face dicts."""
    img = cv2.imread(str(image_path))
    if img is None:
        return []

    h, w = img.shape[:2]
    img_area = h * w

    # Prepare blob for DNN (300x300 input)
    blob = cv2.dnn.blobFromImage(
        cv2.resize(img, (300, 300)),
        1.0, (300, 300),
        (104.0, 177.0, 123.0)
    )
    net.setInput(blob)
    detections = net.forward()

    faces = []
    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        if confidence < CONFIDENCE_THRESHOLD:
            continue

        # Bounding box (relative coordinates)
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        x1, y1, x2, y2 = box.astype("int")

        # Clamp to image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        face_w = x2 - x1
        face_h = y2 - y1
        face_area = face_w * face_h
        area_ratio = face_area / img_area if img_area > 0 else 0

        faces.append({
            "confidence": round(confidence, 3),
            "area_ratio": round(area_ratio, 4),
            "bbox": [int(x1), int(y1), int(face_w), int(face_h)],
        })

    return faces


def should_flag(faces):
    """Determine if an image should be flagged based on detected faces."""
    for face in faces:
        if face["area_ratio"] >= AREA_RATIO_FLAG:
            return True
        if face["confidence"] >= HIGH_CONFIDENCE_FLAG:
            return True
    return False


def process_image(args):
    """Process a single image. Thread-safe (each thread gets its own net)."""
    slug, idx, image_entry, net = args
    url = image_entry.get("url", "")
    local_path = url_to_local_path(url)

    if not local_path or not local_path.exists():
        return None  # skip missing files

    try:
        faces = detect_faces_in_image(local_path, net)
        if faces and should_flag(faces):
            lp = image_entry.get("local_path", str(local_path.relative_to(IMAGES_DIR)))
            return {
                "slug": slug,
                "url": url,
                "local_path": lp,
                "index": idx,
                "faces": faces,
                "face_count": len(faces),
                "max_area_ratio": round(max(f["area_ratio"] for f in faces), 4),
                "max_confidence": round(max(f["confidence"] for f in faces), 3),
                "is_first_image": idx == 0,
            }
    except Exception as e:
        print(f"  ERROR {slug}[{idx}]: {e}", flush=True)

    return None


def main():
    print("=== Face Detection Scanner ===", flush=True)
    print(f"Thresholds: area_ratio>{AREA_RATIO_FLAG}, confidence>{HIGH_CONFIDENCE_FLAG}", flush=True)

    # Load images
    with open(INPUT_JSON) as f:
        all_images = json.load(f)
    print(f"Loaded {len(all_images)} stations", flush=True)

    # Count total images
    total_images = sum(len(imgs) for imgs in all_images.values())
    print(f"Total images to scan: {total_images}", flush=True)

    # Create detector (one per thread since DNN forward is not thread-safe)
    # We'll use sequential processing with a single net for correctness
    print("Loading face detection model...", flush=True)
    net = create_detector()
    print("Model loaded.", flush=True)

    # Build task list
    tasks = []
    for slug, images in sorted(all_images.items()):
        for idx, img_entry in enumerate(images):
            tasks.append((slug, idx, img_entry))

    # Process sequentially (OpenCV DNN net is not thread-safe)
    flagged = {}
    processed = 0
    flagged_count = 0
    errors = 0
    first_image_flags = 0
    start_time = time.time()

    for slug, idx, img_entry in tasks:
        result = process_image((slug, idx, img_entry, net))
        processed += 1

        if result:
            if result["slug"] not in flagged:
                flagged[result["slug"]] = []
            flagged[result["slug"]].append(result)
            flagged_count += 1
            if result["is_first_image"]:
                first_image_flags += 1

        if processed % 200 == 0 or processed == len(tasks):
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (len(tasks) - processed) / rate if rate > 0 else 0
            print(
                f"  [{processed}/{len(tasks)}] "
                f"Flagged: {flagged_count} ({len(flagged)} stations) "
                f"| {rate:.0f} img/s | ETA: {eta:.0f}s",
                flush=True,
            )

    elapsed = time.time() - start_time

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / "flagged-faces.json"
    with open(output_path, "w") as f:
        json.dump(flagged, f, indent=2, ensure_ascii=False)

    stats = {
        "total_images": total_images,
        "processed": processed,
        "flagged_images": flagged_count,
        "flagged_stations": len(flagged),
        "first_image_flags": first_image_flags,
        "elapsed_seconds": round(elapsed, 1),
        "thresholds": {
            "confidence": CONFIDENCE_THRESHOLD,
            "area_ratio_flag": AREA_RATIO_FLAG,
            "high_confidence_flag": HIGH_CONFIDENCE_FLAG,
        },
    }
    stats_path = OUTPUT_DIR / "face-detect-stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n=== Results ===", flush=True)
    print(f"Scanned: {processed} images in {elapsed:.1f}s", flush=True)
    print(f"Flagged: {flagged_count} images across {len(flagged)} stations", flush=True)
    print(f"First-image flags (affects map preview): {first_image_flags}", flush=True)
    print(f"Saved: {output_path}", flush=True)
    print(f"Stats: {stats_path}", flush=True)

    # Show top-10 by area ratio
    all_flagged = []
    for slug_entries in flagged.values():
        all_flagged.extend(slug_entries)
    all_flagged.sort(key=lambda x: x["max_area_ratio"], reverse=True)

    print(f"\nTop 10 by face area ratio:", flush=True)
    for entry in all_flagged[:10]:
        print(
            f"  {entry['slug']}[{entry['index']}]: "
            f"area={entry['max_area_ratio']:.1%} "
            f"conf={entry['max_confidence']:.0%} "
            f"faces={entry['face_count']} "
            f"{'[PREVIEW]' if entry['is_first_image'] else ''}",
            flush=True,
        )


if __name__ == "__main__":
    main()
