#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.31"]
# ///
"""Download the pinned 29 MB WorldPop raster atomically; no other data refresh."""
import argparse
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]


def verify(path, source):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if path.stat().st_size != source['bytes'] or digest != source['sha256']:
        raise ValueError('WorldPop checksum/size mismatch; retry with --refresh; a changed source version requires review')


def fetch(raw, source, refresh=False):
    raw.mkdir(parents=True, exist_ok=True)
    target = raw / source['filename']
    if target.exists() and not refresh:
        verify(target, source)
        return target
    part = target.with_suffix('.tif.part')
    try:
        with requests.get(source['url'], stream=True, timeout=(30, 120)) as response:
            response.raise_for_status()
            with part.open('wb') as stream:
                for chunk in response.iter_content(1024 * 1024):
                    stream.write(chunk)
        verify(part, source)
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='replace cache only after a verified download')
    args = parser.parse_args()
    source = json.loads((ROOT / 'data/bangkok/population-source.json').read_text())
    print(fetch(ROOT / 'data/bangkok/raw', source, args.refresh))
