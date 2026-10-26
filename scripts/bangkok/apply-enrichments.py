#!/usr/bin/env python3
"""Reapply pinned Bangkok enrichments (also an automatic full-build stage)."""
import json
from pathlib import Path

from enrichments import apply_enrichments


def main():
    root = Path(__file__).resolve().parents[2]
    app = root / 'app/src/data/bangkok'
    districts = json.loads((app / 'districts.json').read_text())
    stations = json.loads((app / 'stations.json').read_text())
    signals = json.loads((root / 'data/bangkok/signals.json').read_text())
    apply_enrichments(root, districts['districts'], stations['areas'])
    # The full builder shares these fact dictionaries with the signals output.
    # Keep the standalone replay consistent with that contract too.
    for row in districts['districts']:
        signals['districts'][row['slug']]['facts'] = row['facts'].copy()
    for row in stations['areas']:
        signals['station_areas'][row['id']]['facts'] = row['facts'].copy()
    for path, doc in [(app / 'districts.json', districts), (app / 'stations.json', stations),
                      (root / 'data/bangkok/signals.json', signals)]:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')


if __name__ == '__main__':
    main()
