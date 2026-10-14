import json, glob, os, re, subprocess, time, urllib.parse

UA = 'city-rating-acq/1.0 (research snapshot; contact via repo issue tracker)'

def variants(q):
    parts = [p.strip() for p in q.split(',')]
    vs = []
    # tokyo: strip floor tokens like 4F/B1F/MF; then chome-level
    drop = lambda ps: [p for p in ps if not re.fullmatch(r'[0-9]+F|B[0-9]+F|MF|[0-9]+fl?', p, re.I)]
    if q.endswith('Japan'):
        v1 = ', '.join(drop(parts))
        vs.append(v1)
        # chome-level: "6-6-12 Ginza" -> "Ginza 6-chome"
        v2parts = []
        for p in drop(parts):
            m = re.match(r'^(\d+)-\d+(?:-\d+)?\s+(.+)$', p)
            v2parts.append(f'{m.group(2)} {m.group(1)}-chome' if m else p)
        vs.append(', '.join(v2parts))
    else:
        # bangkok: drop leading plot numbers and building-name prefix (first token w/o Road/Soi)
        def strip_lead(ps):
            ps = list(ps)
            while ps and re.fullmatch(r'[\d/]+', ps[0]):
                ps.pop(0)
            while len(ps) > 1 and not re.search(r'(Road|Soi|Lane| Alley|Yaek)', ps[0], re.I):
                ps.pop(0)
            return ps
        vs.append(', '.join(strip_lead(parts)))
        # subdistrict level: keep from first non-numeric district onward (khet = penultimate before Bangkok)
        vs.append(', '.join(parts[-4:]) if len(parts) >= 4 else ', '.join(parts))
    return vs

nulls = [f for f in glob.glob('geocode/cache/*.json') if json.load(open(f))['lat'] is None]
print(f'retrying {len(nulls)} nulls', flush=True)
fixed = 0
for n, f in enumerate(nulls):
    g = json.load(open(f))
    hit = None
    for v in variants(g['query'])[1:]:  # original already tried
        q = urllib.parse.quote(v)
        url = f'https://nominatim.openstreetmap.org/search?q={q}&format=jsonv2&limit=1&countrycodes={"jp" if v.endswith("Japan") else "th"}'
        body = subprocess.run(['curl', '-sS', '-m', '30', '-A', UA, url], capture_output=True, text=True).stdout.strip()
        try:
            res = json.loads(body)
        except json.JSONDecodeError:
            res = None
        if res:
            hit = (res[0], v)
            break
        time.sleep(1.05)
    if hit:
        rec, v = hit
        g.update({'lat': float(rec['lat']), 'lon': float(rec['lon']),
                  'display_name': rec['display_name'], 'osm_type': rec['osm_type'],
                  'osm_id': int(rec['osm_id']), 'type': rec['type'],
                  'query': v, 'query_original': g['query'], 'simplified_query': True})
        json.dump(g, open(f, 'w'), ensure_ascii=False, indent=1)
        fixed += 1
    if (n + 1) % 25 == 0:
        print(f'{n+1}/{len(nulls)} retried, fixed so far {fixed}', flush=True)
print(f'RETRY DONE: fixed {fixed}/{len(nulls)}, remaining nulls {len(nulls)-fixed}', flush=True)
