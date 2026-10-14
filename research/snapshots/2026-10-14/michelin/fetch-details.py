import json, os, subprocess, sys, time

city = sys.argv[1]
region_path = {'tokyo': 'tokyo-region', 'bangkok': 'bangkok-region'}[city]
city_slug = 'tokyo' if city == 'tokyo' else 'bangkok'
roster = json.load(open(f'{city}-roster-nogeo.json'))
os.makedirs(f'raw/{city}', exist_ok=True)
todo = [r for r in roster if not os.path.exists(f'raw/{city}/detail-{r["slug"]}.md') or os.path.getsize(f'raw/{city}/detail-{r["slug"]}.md') < 5000]
print(f'{city}: {len(todo)} to fetch', flush=True)
for n, r in enumerate(todo):
    url = f'https://r.jina.ai/https://guide.michelin.com/us/en/{region_path}/{city_slug}/restaurant/{r["slug"]}'
    out = f'raw/{city}/detail-{r["slug"]}.md'
    for attempt in range(4):
        code = subprocess.run(['curl', '-sS', '-m', '90', '-o', out, '-w', '%{http_code}', url],
                              capture_output=True, text=True).stdout.strip()
        size = os.path.getsize(out) if os.path.exists(out) else 0
        if code == '200' and size > 5000:
            break
        print(f'  retry {n+1}/{len(todo)} {r["slug"]} code={code} size={size} attempt={attempt+1}', flush=True)
        time.sleep(8 * (attempt + 1))
    if (n + 1) % 20 == 0:
        print(f'{city}: {n+1}/{len(todo)} done', flush=True)
    time.sleep(3.2)
print(f'{city}: ALL DONE', flush=True)
