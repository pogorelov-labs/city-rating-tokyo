#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1"]
# ///
"""Capture (once) or verify the authorized Bangkok refresh input manifest."""
import argparse
import json
from pathlib import Path

from refresh_inputs import capture, verify_inputs

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--build-date', default='2026-10-26')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/bangkok/refresh-inputs.json')
    args = parser.parse_args()
    if args.verify:
        verify_inputs(ROOT, args.output)
        print('All frozen input bytes and hashes verified')
    else:
        if args.output.exists():
            parser.error('Refusing to overwrite an existing frozen manifest')
        doc = capture(ROOT, args.build_date)
        args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
        print(f'Frozen {len(doc["files"])} inputs in {args.output}')


if __name__ == '__main__':
    main()
