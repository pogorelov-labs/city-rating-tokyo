import json, os, sys
from collections import Counter

city = sys.argv[1]
country = 'Japan' if city == 'tokyo' else 'Thailand'
roster = json.load(open(f'michelin-{city}.roster.json'))
features, nulledgeo = [], 0
for r in roster:
    cache = f'geocode/cache/{r["slug"]}.json'
    lon = lat = None
    if os.path.exists(cache):
        g = json.load(open(cache))
        lon, lat = g['lon'], g['lat']
    if lat is None:
        nulledgeo += 1
    features.append({
        'type': 'Feature',
        'geometry': {'type': 'Point', 'coordinates': [lon, lat]} if lat is not None else None,
        'properties': {
            'name': r['name'], 'distinction': r['distinction'],
            'address': r['address'], 'city': 'Tokyo' if city == 'tokyo' else 'Bangkok',
            'country': country, 'guide_year': 2026,
            'source': 'guide.michelin.com', 'source_url': r['url'],
            'attribution': '© Michelin',
        },
    })
# GeoJSON spec: null geometry allowed for unlocated features
fc = {'type': 'FeatureCollection',
      'name': f'michelin-{city}',
      'metadata': {'city': features[0]['properties']['city'], 'guide_year': 2026,
                   'scraped': '2026-10-14', 'source': 'guide.michelin.com (via r.jina.ai reader)',
                   'attribution': '© Michelin — factual roster, INTERNAL ONLY — not for site publication without owner sign-off',
                   'distinctions': dict(Counter(f['properties']['distinction'] for f in features)),
                   'geocoded': len(features) - nulledgeo, 'geocode_null': nulledgeo,
                   'geocoder': 'Nominatim (openstreetmap.org)'},
      'features': features}
json.dump(fc, open(f'michelin-{city}.geojson', 'w'), ensure_ascii=False, indent=1)
print(f'{city}: {len(features)} features, {nulledgeo} without coordinates -> michelin-{city}.geojson')
