import json, os, re, sys

city = sys.argv[1]
country = 'Japan' if city == 'tokyo' else 'Thailand'
roster = json.load(open(f'{city}-roster-nogeo.json'))
for r in roster:
    path = f'raw/{city}/detail-{r["slug"]}.md'
    r['address'] = None
    if not os.path.exists(path):
        continue
    lines = open(path, errors='replace').read().split('\n')
    addr = None
    for i, ln in enumerate(lines):
        if re.match(r'^# .+', ln) and not ln.startswith('## '):
            for j in range(i + 1, min(i + 4, len(lines))):
                cand = lines[j].strip()
                if not cand:
                    continue
                if cand.endswith(f', {country}') and not cand.startswith(('[', '!', '#')):
                    addr = cand
                break
            if addr:
                break
    r['address'] = addr
have = sum(1 for r in roster if r['address'])
print(f'{city}: {have}/{len(roster)} addresses extracted')
json.dump(roster, open(f'{city}-roster-nogeo.json', 'w'), ensure_ascii=False, indent=1)
missing = [r['slug'] for r in roster if not r['address']]
if missing:
    print('missing:', missing[:20])
