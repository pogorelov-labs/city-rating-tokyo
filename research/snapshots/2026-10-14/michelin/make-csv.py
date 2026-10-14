import csv, json, sys
city = sys.argv[1]
roster = json.load(open(f'michelin-{city}.roster.json'))
with open(f'michelin-{city}.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['name', 'distinction', 'address', 'lat', 'lon'])
    for r in roster:
        g = json.load(open(f'geocode/cache/{r["slug"]}.json'))
        w.writerow([r['name'], r['distinction'], r['address'] or '', g['lat'] or '', g['lon'] or ''])
print(f'michelin-{city}.csv written')
