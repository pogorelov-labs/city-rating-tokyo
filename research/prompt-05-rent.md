# Research Prompt: Rent Rating Coverage Expansion

## Context

You are researching how to expand rent data coverage for 1493 train stations in Greater Tokyo. The "rent" rating (1-10, inverted: cheaper = higher) is one of the most important categories (20% default weight). Currently only 274 stations (18%) have real Suumo data.

## What We Already Have

**Suumo scraped data** (274 stations):
- Source: `app/src/data/rent-averages.json` (also in `data/rent/rent-averages-v2.json`)
- Fields: `1k_1ldk` (1K/1LDK price), `2ldk` price, source, updated
- Area: 40-55 sqm apartments within 10 min walk of station
- Scraper: `scripts/scrape-suumo-v2.py` (requests + BeautifulSoup)

**Station-area mapping** (274 stations):
- `scripts/station-area-codes.json` maps station → ward (area_code like "13104")
- Uses nearest-ward-center assignment from `scripts/build-station-ward-map.mjs`

**Known Problems**:

1. **82% of stations have no rent data** — 1219 stations need a fallback
2. **Current fallback is distance heuristic**: `price = 160000 - distance_km * 15000` — not data-driven
3. **Ward mapping only covers 274 stations** — even ward average fallback only helps the already-covered ones
4. **Suumo scraper is area-code based**, not station-based — it scrapes by ward, so adding more wards would help

## Research Tasks

### 1. Expand Suumo Scraping Coverage

a) **Missing ward codes**: The scraper in `scrape-suumo-v2.py` uses `station-area-codes.json` which has 274 stations mapped to ~70 area codes. Research:
   - How many unique ward/city codes exist in Greater Tokyo?
   - Which wards/cities are missing from the mapping?
   - The `build-station-ward-map.mjs` script has hardcoded ward centers — check what's missing

b) **Expand station-area mapping**:
   - Use reverse geocoding (Nominatim) to get ward code for ALL 1493 stations
   - Query: `https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&zoom=12&format=json`
   - Parse `address.city_district` or `address.suburb` for ward name
   - This would give ward-level rent fallback for all stations

c) **Suumo station-based search**: Research if Suumo has a station-based search URL (using `ek` parameter) that could scrape per-station instead of per-ward:
   - URL: `https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ek=...&...`
   - This might give more precise per-station averages
   - Research how ekidata station codes map to Suumo `ek` codes

### 2. Alternative Rent Data Sources

a) **LIFULL HOME'S (homes.co.jp)**:
   - Major Japanese rental portal alongside Suumo
   - Research: do they have a similar search structure?
   - Can we scrape average rent per station/area?

b) **at home (athome.co.jp)**:
   - Another rental platform
   - Research availability and structure

c) **Government rent statistics**:
   - 国土交通省 publishes 地価公示 (land price) data
   - 住宅・土地統計調査 (Housing & Land Survey) has average rent by ward
   - Research: https://www.stat.go.jp/ for rent statistics

d) **Real estate price aggregators**:
   - マンションレビュー (mansion-review.jp) has area averages
   - Research if they publish station-level averages that could be scraped

### 3. Ward-Average Fallback Quality
If we map all 1493 stations to wards, how good is "ward average rent" as a proxy?

a) **Intra-ward rent variance**: Research how much rent varies WITHIN a single ward.
   - Example: Shinjuku-ku has both luxury Nishi-Shinjuku towers and affordable Okubo — how much spread?
   - If variance is high (>30%), ward average is unreliable
   - If variance is moderate (<20%), ward average is fine

b) **Station proximity factor**: Research whether rent decreases linearly with distance from station, or has a step function (e.g., "within 5 min walk" = premium, "10+ min" = flat).

### 4. Proposed Coverage Strategy
Rank these approaches by effort/impact:

1. **Quick win**: Reverse geocode all 1493 stations → ward codes → ward average from existing Suumo data
2. **Medium effort**: Expand Suumo scraping to cover more area_codes (target: all wards/cities in Greater Tokyo)
3. **High effort**: Station-based Suumo scraping for each of 1493 stations directly

### 5. Rent Normalization
Current plan: inverted percentile (cheaper = higher rating).
Research considerations:
- Should the scale be log or linear? Rent range: 50k-200k yen
- Is the difference between 150k and 160k as important as between 60k and 70k? (Probably not — log scale favors affordable range)
- Should we cap at extremes? (Ginza 200k+ → always 1, rural 40k → always 10)

## Output Format

Save findings to `/Users/ruslan/msc_1/git/city-rating/research/05-rent.md` with sections:
1. Coverage Expansion Options (with effort/impact assessment)
2. Alternative Data Sources
3. Ward-Average Reliability Analysis
4. Recommended Approach (prioritized steps)
5. Normalization Method
6. Expected Final Coverage
