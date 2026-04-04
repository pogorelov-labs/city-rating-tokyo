#!/bin/bash
#
# VPS Image Pipeline Orchestrator
# Runs all phases sequentially, downloads images, and moves to nginx volume.
#
# Usage: bash scripts/run-image-pipeline.sh
# Env:   FLICKR_API_KEY (required for Phase 2)
#        IMAGE_DIR=/data/images (where to download images)
#        NGINX_VOLUME=/docker-volume/img (where nginx serves from)
#        IMAGE_HOST=https://img.pogorelov.dev
#
set -euo pipefail

export IMAGE_DIR="${IMAGE_DIR:-/data/images}"
export IMAGE_HOST="${IMAGE_HOST:-https://img.pogorelov.dev}"
NGINX_VOLUME="${NGINX_VOLUME:-/docker-volume/img}"

echo "=== City Rating Image Pipeline ==="
echo "IMAGE_DIR: $IMAGE_DIR"
echo "IMAGE_HOST: $IMAGE_HOST"
echo "NGINX_VOLUME: $NGINX_VOLUME"
echo ""

# Ensure dirs exist
mkdir -p "$IMAGE_DIR"

# Phase 1: Download Wikimedia images
echo "=== Phase 1: Wikimedia download ==="
node scripts/download-wiki-to-vps.mjs
echo ""

# Phase 2: Wikimedia geo search (main coverage source — all 1,493 stations)
echo "=== Phase 2: Wikimedia geo search ==="
node scripts/fetch-wiki-geo.mjs
echo ""

# Move downloaded images to nginx volume
echo "=== Moving images to nginx volume ==="
if [ -d "$IMAGE_DIR/wiki" ]; then
  rsync -a "$IMAGE_DIR/wiki/" "$NGINX_VOLUME/wiki/"
  echo "  wiki/ synced"
fi
if [ -d "$IMAGE_DIR/wiki-geo" ]; then
  rsync -a "$IMAGE_DIR/wiki-geo/" "$NGINX_VOLUME/wiki-geo/"
  echo "  wiki-geo/ synced"
fi
echo ""

# Phase 4: Merge all sources
echo "=== Phase 4: Merge & validate ==="
node scripts/merge-all-images.mjs
echo ""

echo "=== Pipeline complete ==="
echo "Next steps:"
echo "  1. Review station-images-all.json"
echo "  2. Copy it to repo: cp app/src/data/station-images-all.json <repo-path>"
echo "  3. Commit and deploy"
