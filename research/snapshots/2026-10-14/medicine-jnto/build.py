#!/usr/bin/env python3
"""Merge JNTO eng+jpn raw JSON into medicine-jnto.json."""
import json, pathlib, re

D = ('d01','d02','d03','d04','d05','d06','d07','d08','d09','d10','d11','d12','d13','d14','d15','d16')
HOSP = re.compile(r'病院|[Hh]ospital')
DENTAL = re.compile(r'歯|齿|[Oo]ral|[Dd]ental|dent')

def depts(r):
    out = []
    for k in D:
        v = (r.get(k) or '').strip()
        if v:
            out.append(v.split(':')[0])
    return out

def categorize(en_row, ja_row):
    name_all = ja_row['medical_institution'] + ' ' + en_row['medical_institution']
    if HOSP.search(name_all):
        return 'hospital'
    if DENTAL.search(name_all) or any(DENTAL.search(d) for d in depts(ja_row)):
        return 'dental'
    return 'clinic'

PREFS = json.loads(pathlib.Path('prefs.json').read_text()) if pathlib.Path('prefs.json').exists() else None
if PREFS is None:
    # regenerate the code->name map from the fetched guide HTML
    import re as _re
    html = pathlib.Path('mi_guide.html').read_text(encoding='utf-8')
    sel = _re.search(r'<select name="cb-area".*?</select>', html, _re.S).group(0)
    opts = _re.findall(r'<option value="(a\d\d_[a-z]+)"[^>]*>([A-Za-z]+)</option>', sel)
    PREFS = {c: n for c, n in opts}

rows, mismatches, badgeo = [], [], []
for code, pref in sorted(PREFS.items()):
    e = json.loads(pathlib.Path(f'raw/{code}_eng.json').read_text(encoding='utf-8'))
    j = json.loads(pathlib.Path(f'raw/{code}_jpn.json').read_text(encoding='utf-8'))
    er, jr = e['rdata'], j['rdata']
    if len(er) != len(jr):
        print(f"ROWCOUNT MISMATCH {code}: eng={len(er)} jpn={len(jr)}"); continue
    for a, b in zip(er, jr):
        key = ('phone_number','postal_code','latitude')
        if tuple(a[k] for k in key) != tuple(b[k] for k in key):
            mismatches.append((code, a['medical_institution'], b['medical_institution']))
        try:
            lat, lon = float(a['latitude']), float(a['longitude'])
        except (TypeError, ValueError):
            badgeo.append((code, a['medical_institution'])); continue
        if not (20 <= lat <= 46.5 and 122 <= lon <= 154.5):
            badgeo.append((code, a['medical_institution'], lat, lon))
        rows.append({
            'pref': pref,
            'name': a['medical_institution'].strip(),
            'name_ja': b['medical_institution'].strip(),
            'category': categorize(a, b),
            'lat': lat,
            'lon': lon,
            'address': a['street_address'].strip(),
            'phone': a['phone_number'].strip(),
        })

pathlib.Path('medicine-jnto.json').write_text(
    json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')

import collections
print("total rows:", len(rows))
print("by category:", dict(collections.Counter(r['category'] for r in rows)))
print("pref count:", len(set(r['pref'] for r in rows)))
per = collections.Counter(r['pref'] for r in rows)
print("min/max per pref:", min(per.values()), max(per.values()))
print("index mismatches:", len(mismatches), mismatches[:5])
print("bad geo rows:", len(badgeo), badgeo[:5])
print("missing name:", sum(1 for r in rows if not r['name']), "| missing name_ja:", sum(1 for r in rows if not r['name_ja']))
print("missing address:", sum(1 for r in rows if not r['address']), "| missing phone:", sum(1 for r in rows if not r['phone']))
