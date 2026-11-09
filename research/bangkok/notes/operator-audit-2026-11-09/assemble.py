#!/usr/bin/env python3
"""Assemble the 178-row operator-audit CSV + findings skeleton from the two raw parts.

Reads raw/raw-part-a.json + raw/raw-part-b.json + app/src/data/bangkok/rail.json.
Writes operator-audit.csv (178 rows) and prints a mismatch summary classified as
  factual   — status or line membership differs from rail.json (pipeline-ticket material)
  naming    — operator label granularity differs (service name vs concessionaire; owner decision)
  uncertain — agent confidence low or empty sources
Refuses to run until both parts exist and cover exactly their seed ids.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

SEEDS = {'a': HERE / 'seed-part-a.json', 'b': HERE / 'seed-part-b.json'}
RAWS = {'a': HERE / 'raw' / 'raw-part-a.json', 'b': HERE / 'raw' / 'raw-part-b.json'}
CONCESSIONAIRES = {
    'mrt_yellow': 'Eastern Bangkok Monorail (EBM, BTS Group, MRTA concession)',
    'mrt_pink': 'Northern Bangkok Monorail (NBM, BTS Group, MRTA concession)',
    'arl': 'SRT Electrified Train (SRTET, SRT subsidiary)',
}

def main():
    rail = json.loads((ROOT / 'app/src/data/bangkok/rail.json').read_text(encoding='utf-8'))
    recorded = {s['id']: s for s in rail['stations']}
    rows = []
    for part in ('a', 'b'):
        seed_ids = [s['id'] for s in json.loads(SEEDS[part].read_text(encoding='utf-8'))['stations']]
        raw = json.loads(RAWS[part].read_text(encoding='utf-8'))
        got = [s['id'] for s in raw['stations']]
        if sorted(got) != sorted(seed_ids):
            sys.exit(f'part {part}: record set != seed set (missing={set(seed_ids)-set(got)}, extra={set(got)-set(seed_ids)})')
        by_id = {s['id']: s for s in raw['stations']}
        for sid in seed_ids:
            r = by_id[sid]
            rec = recorded[sid]
            facts = []
            if sorted(r['lines_found']) != sorted(rec.get('lines', [])):
                facts.append(f"lines recorded={rec.get('lines')} found={r['lines_found']}")
            if r['status'] != 'operational':
                facts.append(f"status={r['status']}")
            naming = (not facts) and r.get('mismatch_vs_recorded')
            rows.append({
                'station_id': sid, 'name_en': rec.get('name_en', ''),
                'operator_found': r['operator_found'], 'lines_found': ';'.join(r['lines_found']),
                'lines_recorded': ';'.join(rec.get('lines', [])), 'status': r['status'],
                'confidence': r['confidence'],
                'classification': 'factual' if facts else ('naming' if naming else 'match'),
                'detail': r.get('mismatch_detail') or ('; '.join(facts) if facts else ''),
                'source_urls': ';'.join(r['source_urls']),
            })
    if len(rows) != 178:
        sys.exit(f'expected 178 rows, got {len(rows)}')
    out = HERE / 'operator-audit.csv'
    with out.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f'wrote {out} ({len(rows)} rows)')
    print('classification:', dict(Counter(r['classification'] for r in rows)))
    for r in rows:
        if r['classification'] == 'factual':
            print('FACTUAL:', r['station_id'], '→', r['detail'])
    unc = [r['station_id'] for r in rows if r['confidence'] == 'low' or not r['source_urls']]
    print('uncertain/unsourced rows:', unc or 'none')

if __name__ == '__main__':
    main()
