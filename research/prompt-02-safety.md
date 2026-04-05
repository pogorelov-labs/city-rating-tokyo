# Research Prompt: Safety Rating

## Context

You are researching data sources for a "safety" rating (1-10, inverted: safer = higher) for 1493 train stations in Greater Tokyo. The rating should reflect how safe the area feels for a foreigner living there — low crime, well-lit streets, no sketchy areas.

## What We Already Have

**Crime stats** (91 wards, covering 264 stations = 18%):
- Source: Hardcoded from Keishicho (Tokyo Metropolitan Police) published data
- Metric: `crimes_per_10k` (total crimes / population * 10000)
- Range: 27 (Yokohama Sakaeku) to 711 (Chiyoda-ku)
- Mapped via `station-area-codes.json` — only 274 stations have ward_code mapping

**Known Problems**:

1. **82% of stations have NO safety data** — 1229 stations would use a prefecture average fallback, which is meaningless (all Tokyo stations get the same safety score)

2. **Chiyoda Problem**: crimes_per_10k = 711 — highest in the dataset. But Chiyoda is the Imperial Palace / government district, one of the safest areas in Tokyo. The distortion: residential population is 68k but daytime population is 800k+. Crimes are committed by/against commuters, not residents. The rate is fake-inflated.

3. **Ward-level granularity is too coarse**: Shinjuku-ku contains both Kabukicho (most dangerous in Tokyo) and Shinjuku Gyoen area (quiet residential). Both get crimes_per_10k=224.

4. **No distinction between crime types**: Petty theft in Shibuya vs violent crime are weighted equally. For foreigners, bicycle theft (the most common "crime" in safe suburban areas) shouldn't tank the safety rating.

## Research Tasks

### 1. Official Crime Data Sources (Japanese Police)

a) **Keishicho (警視庁) Open Data**:
   - URL: https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/
   - Research: Do they publish data more granular than ward-level? Check for:
     - 町丁目別 (cho-chome level = neighborhood level) crime data
     - Crime type breakdowns (窃盗=theft, 粗暴犯=violent, 侵入窃盗=burglary)
     - Annual CSV downloads
   - Specifically look for: `区市町村の町丁別、罪種別及び手口別認知件数`

b) **Kanagawa Prefectural Police** (神奈川県警):
   - Check their open data portal for ward/city level crime stats
   - URL pattern: kanagawa-kenkei or similar

c) **Saitama Prefectural Police** (埼玉県警):
   - Same check for Saitama cities

d) **Chiba Prefectural Police** (千葉県警):
   - Same check

e) **Government Statistics Portal** (e-Stat):
   - https://www.e-stat.go.jp/
   - Search for crime statistics that might be available at smaller geographic granularity

### 2. Daytime Population Adjustment
Research how to fix the Chiyoda/Minato/Chuo problem:
- Find **daytime population** (昼間人口) data per ward (Tokyo publishes this)
- Calculate adjusted rate: `crimes / daytime_population * 10000` for commercial wards
- Alternatively: use **nighttime population** for residential wards, **daytime** for commercial

### 3. Crime Type Weighting
Research which crime types matter for the safety *feeling* of a foreign resident:
- 凶悪犯 (violent crime) → weight 3x
- 粗暴犯 (assault/intimidation) → weight 2x
- 窃盗犯 (theft) → weight 1x but break down:
  - 自転車盗 (bicycle theft) → weight 0.3x (extremely common, not scary)
  - 車上ねらい (car break-in) → weight 0.5x
  - 侵入窃盗 (burglary) → weight 2x
  - ひったくり (purse snatching) → weight 2x
- 知能犯 (fraud/white-collar) → weight 0.2x (doesn't affect street safety)

Can we get this breakdown from the published data?

### 4. Alternative Safety Signals
Research non-crime data that indicates safety:

a) **Street lighting density**: Is this in OSM? (`highway=street_lamp`)
b) **Koban (交番) density**: Police boxes are a safety signal. OSM `amenity=police`?
c) **Convenience store density** (our OSM data already has this): Well-lit 24h stores = safer streets. Research the academic correlation between konbini density and perceived safety.
d) **Residential vs commercial ratio**: Purely residential areas feel safer. Can we detect this from OSM land use tags?

### 5. Neighborhood-Level Safety Map
Check if anyone has already built a Tokyo safety map at sub-ward level:
- Research: "東京 治安 マップ" (Tokyo safety map)
- ガッコム安全ナビ (gaccom.jp) — school district safety maps
- LIFULL HOME'S has 治安 ratings per area
- Suumo has area safety descriptions

Can we scrape safety scores from LIFULL/Suumo per station area?

### 6. Coverage Expansion
Currently only 274 stations have ward_code mapping. Research how to expand:
- Reverse geocoding lat/lng → ward code for all 1493 stations
- Nominatim API (free, OSM-based): `reverse?lat=35.69&lon=139.70&zoom=12` returns ward
- Japanese government geocoding API (国土地理院)
- This alone would take coverage from 18% to ~100% for ward-level data

### 7. Proposed Formula
Based on findings, propose a formula that:
- Uses the most granular crime data available
- Adjusts for daytime vs nighttime population where relevant
- Weights crime types appropriately
- Incorporates supplementary signals (koban, lighting, konbini)
- Has fallback logic for stations with no crime data
- Passes the Chiyoda test (should be 7-8, not 1-2)
- Passes the Kabukicho test (should be 3-4)

## Output Format

Save findings to `/Users/ruslan/msc_1/git/city-rating/research/02-safety.md` with sections:
1. Official Data Sources (with URLs, download links, granularity)
2. Daytime Population Fix (data source + calculation)
3. Crime Type Weights (with justification)
4. Alternative Safety Signals (feasibility assessment)
5. Coverage Expansion Method (reverse geocoding approach)
6. Recommended Formula
7. Implementation Plan
8. Expected Coverage & Confidence Level
