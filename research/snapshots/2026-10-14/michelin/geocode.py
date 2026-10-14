import json, os, subprocess, sys, time, urllib.parse

city = sys.argv[1]
cc = 'jp' if city == 'tokyo' else 'th'
roster = json.load(open(f'{city}-roster-nogeo.json'))
os.makedirs('geocode/cache', exist_ok=True)
UA = 'city-rating-acq/1.0 (research snapshot; contact via repo issue tracker)'

todo = [r for r in roster if r['address'] and not os.path.exists(f'geocode/cache/{r["slug"]}.json')]
print(f'{city}: {len(todo)} to geocode', flush=True)
for n, r in enumerate(todo):
    cache = f'geocode/cache/{r["slug"]}.json'
    q = urllib.parse.quote(r['address'])
    url = f'https://nominatim.openstreetmap.org/search?q={q}&format=jsonv2&limit=1&countrycodes={cc}'
    for attempt in range(3):
        out = subprocess.run(['curl', '-sS', '-m', '30', '-A', UA, url],
                             capture_output=True, text=True)
        body = out.stdout.strip()
        if body.startswith('['):
            try:
                res = json.loads(body)
                break
            except json.JSONDecodeError:
                res = None
        print(f'  retry {r["slug"]} attempt={attempt+1} out={body[:80]!r}', flush=True)
        time.sleep(3 * (attempt + 1))
    else:
        res = []
    rec = res[0] if res else None
    payload = {'lat': float(rec['lat']) if rec else None,
               'lon': float(rec['lon']) if rec else None,
               'display_name': rec['display_name'] if rec else None,
               'osm_type': rec['osm_type'] if rec else None,
               'osm_id': int(rec['osm_id']) if rec else None,
               'type': rec['type'] if rec else None,
               'query': r['address'], 'geocoded_at': '2026-10-14'}
    json.dump(payload, open(cache, 'w'), ensure_ascii=False, indent=1)
    if (n + 1) % 25 == 0:
        hits = sum(1 for f2 in os.listdir('geocode/cache') if json.load(open(f'geocode/cache/{f2}'))['lat'] is not None)
        print(f'{city}: {n+1}/{len(todo)} fetched, cache hits so far {hits}/{len(os.listdir("geocode/cache"))}', flush=True)
    time.sleep(1.05)
print(f'{city}: GEOCODE DONE', flush=True)
