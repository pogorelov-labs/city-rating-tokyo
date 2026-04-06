# City Rating Tokyo — Dev Guide

## Project Overview

Interactive map of Greater Tokyo (1493 stations) with data-driven neighborhood ratings. Users filter by food, nightlife, transport, rent, safety, green, gym, vibe, crowd with adjustable weights.

**Live**: https://city-rating.pogorelov.dev
**Stack**: Next.js 14 (App Router) + Leaflet + Tailwind. Static JSON data, no DB at runtime.
**Deploy**: Coolify on VPS (217.196.61.98), GitHub App auto-deploy from `main`.

## Architecture

```
data/stations.json (1493 stations: slug, lat, lng, lines, line_count, prefecture)
     ↓
scripts/scrapers/ → NocoDB (nocodb.pogorelov.dev, base: city-rating-db)
     ↓
scripts/compute-ratings.py → NocoDB computed_ratings table
     ↓
scripts/export-ratings.py → app/src/data/demo-ratings.ts
     ↓
app/src/lib/data.ts merges: stations.json + demo-ratings.ts + rent-averages.json
```

## Data Pipeline

### NocoDB Tables (city-rating-db, base ID: ph4flgay4kmcgk4)

| Table | ID | Records | Source |
|-------|----|---------|--------|
| osm_pois | mnnuqtldvt4jxlj | 1398 | Overpass API (food, nightlife, green count, gym, convenience) |
| hotpepper | mfk9j2qoj2bkeoo | 1493 | HotPepper Gourmet API (+ midnight_count, dining_bar_count) |
| osm_extended | mrpqu8o796e6xzk | 1467 | Overpass (karaoke, nightclub, cultural venues, pedestrian streets, hostels) |
| station_crime | mxwixub7d0q5i00 | 615 | Keishicho ArcGIS FeatureServer (Tokyo neighborhood-level) |
| crime_stats | mxitpnomlom3j3q | 91 | Hardcoded ward-level (legacy fallback for non-Tokyo) |
| passenger_counts | m36bbxcv8t0asur | 1409 | MLIT S12 GeoJSON (94% coverage, was 6%) |
| station_wards | m74rdmspn3trrqc | 1493 | Nominatim reverse geocoding |
| hostels | ms9awzjv9j6suh7 | 3 | Overpass (test only — superseded by osm_extended.hostel_count) |
| computed_ratings | mkp046vo42kj55w | 1493 | Output of compute-ratings.py (includes confidence/sources/data_date columns) |
| feedback | mwuwwlko3278wrk | — | User feedback from site |

`computed_ratings` has 3 metadata columns alongside the 9 rating numbers:
- `confidence` (LongText) — JSON: `{"food":"strong","vibe":"estimate",...}`
- `sources` (LongText) — JSON: `{"food":["hotpepper","osm"],...}`
- `data_date` (SingleLineText) — e.g. `2026-04`

These feed the `ConfidenceBadge` UI component. NocoDB API token is data-only — schema changes (new columns) must be done manually in the NocoDB UI.

### NocoDB Access
```
URL: https://nocodb.pogorelov.dev
Token: 3hUf86bwbyw-OSJTlNwGOc1w8AcwrrgAkOuyIaTt
API: /api/v2/tables/{TABLE_ID}/records
```

### HotPepper API
```
Key: b20f206ef29b9f48 (also in Coolify env vars)
Docs: https://webservice.recruit.co.jp/doc/hotpepper/reference.html
Important param: midnight=1 (returns places open after 23:00)
```

## Rating Formulas (v2, research-backed)

All categories use **log-then-percentile** normalization across 1493 stations.

### food (15% default weight)
```
raw = log(1 + HP_total) * 0.6 + log(1 + OSM_food) * 0.4
```
Sources: HotPepper total_count (100%), OSM food_count (94%). Correlation r=0.855.

### nightlife (10%)
```
raw = log(1 + HP_midnight) * 0.25 + log(1 + HP_izak) * 0.2
    + log(1 + HP_bar*3) * 0.15 + log(1 + OSM_night) * 0.2
    + log(1 + karaoke*5) * 0.1 + log(1 + hostel*10) * 0.1
```
Sources: HP midnight_count, izakaya_count, bar_count; OSM nightlife + karaoke; hostel count.

### transport (20%)
```
raw = line_count * 2 + log(1 + daily_passengers) * 0.5
```
Sources: station line_count (100%), MLIT S12 passengers (94%).

### rent (20%, inverted: cheaper = higher)
```
raw = suumo_1k || lifull_1k || ward_average || prefecture_estimate
```
Sources: Suumo (18%), ward averages via Nominatim mapping, distance fallback.

### safety (10%, inverted: safer = higher)
```
weighted_crimes = violent*3 + assault*2 + burglary*2 + purse_snatch*2
                + pickpocket*1.5 + bike_theft*0.3 + fraud*0.2
rate = weighted_crimes / adjusted_population * 10000
```
Sources: Keishicho ArcGIS neighborhood polygons (Tokyo, 615 stations), prefectural police (others). Daytime population adjustment for commercial wards (Chiyoda ÷12, Chuo ÷4, Minato ÷3.6).

### green (10%)
```
raw = log(1 + green_area_sqm) * 0.55 + green_count * 0.25
    + large_park_bonus * 0.1 + water_proximity * 0.1
```
Sources: OSM leisure=park|garden|nature_reserve + landuse=religious|forest + natural=wood. Area calculation from polygon geometry.

### gym_sports (5%)
```
raw = OSM gym_count
```
Sources: OSM leisure=fitness_centre|sports_centre|swimming_pool.

### vibe (5%)
```
raw = log(1 + cultural_venues) * 0.6 + log(1 + pedestrian_streets) * 0.15
    + log(1 + cafe_count) * 0.15 + cultural_shop_ratio * 0.1
```
Sources: OSM theatre|cinema|arts_centre + shop=books|music|art|vintage; pedestrian streets. AI-researched override for 272 stations.

### crowd (5%, inverted: fewer = higher)
```
raw = daily_passengers (MLIT/hardcoded) || HP_total * 300 + line_count * 10000
```
Sources: MLIT S12 (94%), HotPepper total as fallback.

## Override Hierarchy
1. **AI-researched** (272 stations with `description` field in demo-ratings.ts) — never overwritten
2. **Computed data-driven** — from NocoDB pipeline
3. **Heuristic fallback** — only where real data unavailable

## Key Files

| File | Purpose |
|------|---------|
| `app/src/data/demo-ratings.ts` | All ratings (AI + computed). ~7700 lines. |
| `app/src/data/rent-averages.json` | Suumo rent data (274 stations) |
| `app/src/data/station-images.json` | Wikimedia photos per station — **623/1493 coverage (42%)**. Missing stations fall back to a gradient placeholder in the map tooltip. |
| `app/src/lib/data.ts` | Merges stations + ratings + rent at build time |
| `app/src/lib/types.ts` | TypeScript interfaces (StationRatings, etc.) |
| `app/src/lib/store.ts` | Zustand store: weights, filters, `selectedStation`, `hoveredStation`, compare list, heatmap |
| `app/src/lib/scoring.ts` | Weighted score, affordability, **magma + category-hue palettes** via `scoreToColor(score, dimension?)` — composite = magma, heatmap passes the dimension for category-specific hues |
| `data/stations.json` | Master station list (1493 entries) |
| `scripts/station-area-codes.json` | Station → ward code mapping (274 entries) |
| `scripts/scrapers/utils.py` | Shared NocoDB client, rate limiter, station loader |
| `scripts/scrapers/scrape-osm-pois.py` | OSM POI scraper (food, nightlife, green, gym) |
| `scripts/scrapers/scrape-hotpepper.py` | HotPepper restaurant/izakaya/bar scraper |
| `scripts/compute-ratings.py` | Normalizes all sources → 1-10 ratings + confidence metadata |
| `scripts/export-ratings.py` | NocoDB computed → demo-ratings.ts (with confidence/sources/data_date) |
| `scripts/refresh-ratings.sh` | One-command chain: compute → export → build verify → commit → push |
| `app/src/components/ConfidenceBadge.tsx` | 🟢🟡⚪ badge component with source tooltip |
| `app/src/components/Map.tsx` | Leaflet map; highlights `selectedStation`/`hoveredStation` with brand-blue border + pulsating `.station-halo` ring (keyframes in `globals.css`) |

## Running Scrapers on VPS

Scrapers run as detached Docker containers on VPS to avoid laptop sleep issues:

```bash
# SSH to VPS (use Coolify localhost key)
ssh -i /tmp/coolify_key root@217.196.61.98

# Launch a scraper
docker run -d --name SCRAPER_NAME --restart=no \
  -e NOCODB_API_URL=https://nocodb.pogorelov.dev \
  -e NOCODB_API_TOKEN=3hUf86bwbyw-OSJTlNwGOc1w8AcwrrgAkOuyIaTt \
  -e HOTPEPPER_API_KEY=b20f206ef29b9f48 \
  -v /tmp/SCRIPT.py:/app/scraper.py:ro \
  -v /tmp/stations.json:/app/data/stations.json:ro \
  python:3.11-slim bash -c "pip install --quiet requests && python3 -u /app/scraper.py"

# Check logs
docker logs --tail 20 SCRAPER_NAME

# Check all scraper containers
docker ps -a --format "{{.Names}}\t{{.Status}}" | grep -E "osm|hp|arcgis|mlit|nominatim"
```

All scrapers are incremental — they skip stations already in NocoDB. Safe to restart.

## Research Documents

Detailed data source research in `research/`:
- `00-overview.md` — Status summary
- `01-nightlife.md` — HP midnight, karaoke, club sources
- `02-safety.md` — ArcGIS crime polygons, daytime population, crime weights
- `03-crowd.md` — MLIT S12 dataset, railway company data
- `04-green.md` — Park area calculation, landuse=religious, NDVI
- `05-rent.md` — LIFULL HOME'S, Nominatim ward mapping
- `06-vibe.md` — Cultural venue density, pedestrian streets

## Build & Deploy

```bash
cd app && npm run build  # Verify after export-ratings.py
git push origin main     # Coolify auto-deploys
```

## Refreshing ratings data

Use the one-command script instead of running compute/export/build manually:

```bash
scripts/refresh-ratings.sh              # interactive: prompts before commit
scripts/refresh-ratings.sh --auto --push  # hands-off on a feature branch
scripts/refresh-ratings.sh --dry-run    # preview without writes
scripts/refresh-ratings.sh --no-build   # skip build verification
```

Safety: the script refuses to run with unrelated dirty files and refuses to push directly to main without `--force-main`. Never uses `--amend` or force push.

**Note:** the frontend bakes ratings into static HTML at build time. Re-running scrapers alone does NOT update the live site — you must also run the refresh chain so `demo-ratings.ts` gets rewritten and committed.
