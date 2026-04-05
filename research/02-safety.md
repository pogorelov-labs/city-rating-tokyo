# Safety Rating Research Findings

Date: 2026-04-03

## 1. Official Data Sources

### 1a. Keishicho (Tokyo Metropolitan Police) -- BEST SOURCE

**Neighborhood-level crime data (町丁別) exists and is freely downloadable.**

Primary URL: https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/ninchikensu.html

**What's available:**
- Title: 区市町村の町丁別、罪種別及び手口別認知件数 (Crime counts by municipality/neighborhood, crime type, and modus operandi)
- Format: CSV (489KB for 2024) and XLSX (1,259KB for 2024)
- Years: 2018-2025 (令和7年 = 2025 data already available)
- Updated: Monthly cumulative + annual totals
- Geographic granularity: **町丁目 (cho-chome) = neighborhood level** -- this is far more granular than ward-level
- Crime type breakdown: YES -- full breakdown by crime category and sub-type

**Also available on Tokyo Open Data Catalog:**
- https://catalog.data.metro.tokyo.lg.jp/dataset/t000022d0000100001
- Open data license, free for commercial use

**Crime occurrence CSV files (per-incident level):**
- URL: https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/hanzaihasseijyouhou.html
- 56 CSV files across 7 crime types for years 2018-2024
- Crime types: ひったくり (purse snatching), 車上ねらい (car break-in), 部品ねらい (parts theft), 自販機ねらい (vending machine), 自動車盗 (car theft), オートバイ盗 (motorcycle theft), 自転車盗 (bicycle theft)
- These are individual incident records with location data

**Tokyo Open Data API Catalog (JSON/XML API access):**
- URL: https://spec.api.metro.tokyo.lg.jp/spec/search?organizations=%E8%AD%A6%E8%A6%96%E5%BA%81
- API endpoints for crime data in JSON/XML format
- Includes: town-level crime data (annual + monthly cumulative), crime occurrence info by type
- This is a REST API -- no scraping needed

### 1b. ArcGIS FeatureServer -- CRITICAL DISCOVERY

**Keishicho publishes neighborhood-level crime data as a geospatial FeatureServer with polygon boundaries.**

2023 data: `https://services.arcgis.com/wlVTGRSYTzAbjjiC/ArcGIS/rest/services/CrimR5_tokyo/FeatureServer/0`
2024 data: `https://services.arcgis.com/wlVTGRSYTzAbjjiC/ArcGIS/rest/services/CrimR6_tokyo/FeatureServer/0`

**Record count: 5,596 polygons** covering all of Tokyo (23 wards + Tama cities)

**Fields available (45 total):**

| Field | Description |
|-------|-------------|
| CC_CODE | Area code |
| NAME | Neighborhood name (e.g., 丸の内一丁目) |
| SHI_NAME | Municipality name (e.g., 千代田区) |
| TOTPOP_R2 | Total population (2020 census) |
| TOTMALE_R2 | Male population |
| TOTFEMALE_R2 | Female population |
| TOTHH_R2 | Total households |

**Crime category fields (SUM_USER_ prefix):**

| Category | Japanese | Sub-types available |
|----------|----------|---------------------|
| 総合計 | Total crimes | Sum of all below |
| 凶悪犯計 | Violent felonies | 強盗 (robbery), その他 (other) |
| 粗暴犯計 | Assault crimes | 凶器準備集合, 暴行, 傷害, 脅迫, 恐喝 |
| 侵入窃盗計 | Burglary | 金庫破り, 学校荒し, 事務所荒し, 出店荒し, 空き巣, 忍込み, 居空き, その他 |
| 非侵入窃盗計 | Non-entry theft | 自動車盗, オートバイ盗, 自転車盗, 車上ねらい, 自販機ねらい, 工事場ねらい, すり, ひったくり, 置引き, 万引き, その他 |
| その他計 | Other | 詐欺, 占有離脱物横領, その他知能犯, 賭博, その他刑法犯 |

**Why this is the best source:**
- Geospatial polygons = can do point-in-polygon lookup for any lat/lng
- Population included = can compute per-capita rates immediately
- Crime type breakdown = can apply weights
- 5,596 neighborhoods = extremely granular (avg neighborhood has ~2,500 residents)
- REST API = no scraping needed, direct JSON/GeoJSON queries
- Query example: `?where=1%3D1&outFields=*&resultRecordCount=10&f=json`
- Supports GeoJSON output: add `&f=geojson`

**This single source solves the granularity problem, the crime type problem, AND the coverage problem for all Tokyo stations.**

### 1c. Kanagawa Prefectural Police

**Crime statistics by municipality:**
- URL: https://www.police.pref.kanagawa.jp/tokei/hanzai_tokei/mesc0027.html
- Data: 刑法犯 罪名別 市区町村別 認知件数 (Penal code crime by type by municipality)
- Crime categories: 凶悪犯, 粗暴犯, 窃盗犯, 知能犯, 風俗犯, other
- Format: HTML table on page + PDF download (903.9KB)
- Granularity: **Municipality/ward level** (市区町村別) -- NOT neighborhood level
- Updated: Monthly (latest: February 2026 provisional)

**Open data (incident-level CSV):**
- URL: https://www.police.pref.kanagawa.jp/tokei/hanzai_tokei/mesd0145.html
- Format: CSV
- Years: 2018-2024
- Crime types: 7 theft categories (ひったくり, 車上ねらい, 部品ねらい, 自販機ねらい, 自動車盗, オートバイ盗, 自転車盗)
- These are per-incident records with location data
- Example file sizes suggest per-incident granularity: bicycle theft 2024 = 2MB, bag snatching = 4.5KB

**Limitation:** No neighborhood-level aggregate statistics like Keishicho. Only ward/city-level aggregates or individual incident CSVs.

### 1d. Saitama Prefectural Police

- Crime stats page: https://www.police.pref.saitama.lg.jp/kurashi/toke/index.html
- Municipality-level data: https://www.police.pref.saitama.lg.jp/c0011/keihouhan.html
- Format: **PDF only** for municipality-level breakdowns
- Open data: https://www.police.pref.saitama.lg.jp/c0011/kurashi/0pendata2019/opendate-2019.html (years 2018-2024)
- Open data format: CSV (per-incident, same 7 theft types as national standard)
- Granularity: Municipality level in PDFs; incident-level in open data CSVs

**Limitation:** PDFs need parsing. No neighborhood-level aggregates. Open data only covers 7 theft types.

### 1e. Chiba Prefectural Police

- Open data: https://www.police.pref.chiba.jp/seisoka/safe-life_publicspace-statistics_00002.html
- Municipality stats: https://www.police.pref.chiba.jp/keisoka/safe-life_crime_statistics-02.html
- Format: CSV for open data (per-incident, 7 theft types)
- Years: 2018-2024
- File sizes: bicycle theft 1,651KB, car break-ins 213KB (2024)

**Limitation:** Same as Saitama -- municipality level aggregates, incident-level CSVs for theft only.

### 1f. National Police Agency (NPA) Open Data Link Collection

- URL: https://www.npa.go.jp/toukei/seianki/hanzaiopendatalink.html
- Aggregates links to all 47 prefectural police open data sites
- Standard format: CSV with 7 theft crime types (national standard)
- All four prefectures (Tokyo, Kanagawa, Saitama, Chiba) have entries

### 1g. e-Stat (Government Statistics Portal)

- URL: https://www.e-stat.go.jp/stat-search/files?toukei=00130001
- Crime statistics: 令和6年 (2024) confirmed values available
- Granularity: **Prefecture-level only** (都道府県別) in the standard crime tables
- Tables 3 and 6 provide prefectural totals only
- NOT useful for sub-prefectural analysis
- Census small-area data (小地域集計) available at town/cho-cho level but this is population, not crime

**Verdict: e-Stat crime data is too coarse. The prefectural police publish more granular data directly.**

## 2. Daytime Population Fix

### The Problem
Chiyoda-ku: residential pop 67,803, total crimes 4,826, rate = 711 per 10k -- appears most dangerous.
Reality: daytime pop ~820,000. Adjusted rate = 59 per 10k -- much more reasonable.

### Data Sources for Daytime Population

**Source 1: Tokyo Metropolitan Government -- 2020 Census Daytime Population**
- URL: https://www.toukei.metro.tokyo.lg.jp/tyukanj/2020/tj-20index.htm
- Format: Excel (799KB) and CSV (794KB)
- Coverage: All Tokyo wards and cities
- Table 11 has the most granular breakdown: 町丁・字等別昼間人口 (town-level daytime population estimates)
- Based on 2020 National Census (令和2年国勢調査), commuter/student place of work/study

**Source 2: Tokyo Statistical Yearbook**
- URL: https://www.toukei.metro.tokyo.lg.jp/tnenkan/tn-eindex.htm
- Annual publication with ward-level daytime/nighttime population comparisons

**Source 3: e-Stat Small Area Census Data**
- URL: https://www.e-stat.go.jp/stat-search/files?tstat=000001136464&toukei=00200521
- 小地域集計 (small area compilation) for Tokyo
- Town/cho-cho level population data downloadable as CSV

### Proposed Adjustment Calculation

For each ward, compute a "commercial district factor":
```
commercial_factor = daytime_pop / nighttime_pop
```

Wards with commercial_factor > 2.0 (e.g., Chiyoda = ~12x, Chuo = ~4x, Minato = ~3x):
```
adjusted_rate = total_crimes / daytime_pop * 10000
```

Wards with commercial_factor < 1.5 (residential areas):
```
adjusted_rate = total_crimes / nighttime_pop * 10000
```

Wards with factor 1.5-2.0: blend both:
```
blended_pop = (daytime_pop + nighttime_pop) / 2
adjusted_rate = total_crimes / blended_pop * 10000
```

**Key daytime population ratios (2020 Census estimates):**

| Ward | Night Pop | Day Pop | Ratio |
|------|-----------|---------|-------|
| Chiyoda | ~67k | ~820k | ~12.1x |
| Chuo | ~170k | ~660k | ~3.9x |
| Minato | ~260k | ~940k | ~3.6x |
| Shibuya | ~244k | ~530k | ~2.2x |
| Shinjuku | ~349k | ~770k | ~2.2x |
| Toshima | ~302k | ~420k | ~1.4x |
| Taito | ~212k | ~310k | ~1.5x |

Using daytime population for Chiyoda: 4,826 / 820,000 * 10,000 = ~59 per 10k (vs 711 with night pop).
This passes the Chiyoda test -- it would score 7-8 on a 1-10 safety scale, not 1-2.

### For Neighborhoods (ArcGIS data)
The ArcGIS FeatureServer only includes census nighttime population (TOTPOP_R2). For neighborhood-level daytime adjustment:
- Option A: Apply ward-level daytime factor uniformly to all neighborhoods in that ward
- Option B: Use the town-level daytime population from Table 11 of the census data (best but more work)
- Option C: Use a heuristic -- neighborhoods with very low residential population (< 500) but high crime counts are likely commercial zones; apply a higher divisor

## 3. Crime Type Weights

### Available Breakdown (from ArcGIS FeatureServer)

The data supports the exact weighting scheme proposed in the prompt:

| Crime Type | Japanese | Available in Data | Proposed Weight |
|-----------|----------|-------------------|-----------------|
| Violent felonies (凶悪犯) | 強盗 etc. | YES (凶悪犯計) | 3.0x |
| Assault/intimidation (粗暴犯) | 暴行, 傷害, 脅迫, 恐喝 | YES (粗暴犯計) | 2.0x |
| Burglary (侵入窃盗) | 空き巣, 忍込み etc. | YES (侵入窃盗計) | 2.0x |
| Purse snatching (ひったくり) | ひったくり | YES (individual field) | 2.0x |
| Pickpocketing (すり) | すり | YES (individual field) | 1.5x |
| General theft (万引き etc.) | 万引き, 置引き | YES (individual fields) | 0.8x |
| Bicycle theft (自転車盗) | 自転車盗 | YES (individual field) | 0.3x |
| Car break-in (車上ねらい) | 車上ねらい | YES (individual field) | 0.5x |
| Car/motorcycle theft | 自動車盗, オートバイ盗 | YES (individual fields) | 0.5x |
| Fraud (詐欺) | 詐欺 | YES (individual field) | 0.2x |
| Other white collar (知能犯) | 占有離脱物横領 etc. | YES | 0.1x |
| Gambling (賭博) | 賭博 | YES (individual field) | 0.0x |

### Justification for Weights
- **3.0x for violent crime**: Robbery, homicide -- these are the strongest signals of a dangerous area. Even one incident in a neighborhood is alarming.
- **2.0x for assault/burglary/snatching**: These directly affect physical safety and home security.
- **1.5x for pickpocketing**: Affects perceived street safety, common concern for foreigners.
- **0.3x for bicycle theft**: Extremely common even in safe areas. Japan reports bicycle theft as a crime at rates that would be ignored in other countries. This should not tank a safety score.
- **0.2x for fraud**: Ore-ore sago (phone scams) targeting elderly -- irrelevant to street safety.
- **0.0x for gambling**: No impact on personal safety perception.

### Weighted Crime Score Formula
```
weighted_crimes = (
    凶悪犯計 * 3.0 +
    粗暴犯計 * 2.0 +
    侵入窃盗計 * 2.0 +
    ひったくり * 2.0 +
    すり * 1.5 +
    自転車盗 * 0.3 +
    車上ねらい * 0.5 +
    自動車盗 * 0.5 +
    オートバイ盗 * 0.5 +
    万引き * 0.8 +
    置引き * 0.8 +
    その他非侵入窃盗 * 0.5 +
    詐欺 * 0.2 +
    その他知能犯 * 0.1 +
    賭博 * 0.0 +
    その他刑法犯 * 0.3
)
```

## 4. Alternative Safety Signals

### 4a. Koban (交番) Density -- FEASIBLE

**OSM tagging:** `amenity=police` is the standard tag. Japanese koban are tagged as `amenity=police` nodes.
There is no widely-used `police=koban` sub-tag, but many entries have `name` containing "交番".

**Overpass API query:**
```
[out:json][timeout:60];
area["name"="東京都"]->.searchArea;
(
  node["amenity"="police"](area.searchArea);
  way["amenity"="police"](area.searchArea);
);
out count;
```

**Expected coverage:** ~6,000 koban exist nationwide; Tokyo area should have hundreds.

**Usage:** Count koban within 800m radius of each station. Higher count = safer feeling.
- 0 koban = slight penalty
- 1+ koban within 500m = slight bonus
- This is a secondary signal, not primary.

### 4b. Street Lighting (highway=street_lamp) -- LOW FEASIBILITY

OSM does have `highway=street_lamp` tags, but coverage in Japan is extremely inconsistent. Urban Tokyo likely has sparse street lamp mapping because mappers focus on buildings/roads, not individual lamps.

**Verdict: Skip. Coverage too inconsistent to be meaningful.**

### 4c. Convenience Store Density -- FEASIBLE (already have data)

We already have OSM konbini data from our POI scraper. Academic/practical connection to safety:
- Japan Franchise Association runs "Safety Station" (SS) program -- konbini serve as safe shelters
- Konbini responded to 6,681 incidents involving women in crisis in 2023
- 24-hour illumination + staff presence + cameras = natural surveillance
- Academic research from JST/J-STAGE confirms convenience stores play a role in crime prevention

**Usage:** Already computed in OSM POI data. Use as a secondary signal:
- konbini_count within 500m >= 5: slight safety bonus (+0.3 points)
- konbini_count within 500m == 0: slight penalty (-0.2 points)

### 4d. Residential vs. Commercial Ratio -- FEASIBLE

Can be detected from:
- OSM `landuse=residential` vs `landuse=commercial`/`landuse=retail`
- The population data itself: low residential population + high crime = commercial area (different safety profile)
- ArcGIS data has TOTPOP_R2 and TOTHH_R2 (households) -- neighborhoods with very few households are commercial

**Usage:** Use as a contextual adjustment rather than direct signal. Commercial areas have different crime profiles (more theft, less residential burglary).

## 5. Coverage Expansion Method

### Current State
- 274 stations have manual ward_code mapping in station-area-codes.json (18%)
- 91 wards have crime data (covers those 274 stations)
- 1,219 stations have NO safety data

### Solution: Nominatim Reverse Geocoding

**Tested and confirmed working for all four prefectures:**

| Test Location | Lat/Lng | Result | Ward/City |
|---------------|---------|--------|-----------|
| Shinjuku | 35.6897, 139.7005 | city: "新宿区" | Shinjuku-ku |
| Shinagawa area | 35.6284, 139.7387 | city: "港区" | Minato-ku |
| Yokohama | 35.4437, 139.6380 | city: "横浜市", suburb: "中区" | Yokohama Naka-ku |
| Saitama | 35.8617, 139.6453 | city: "さいたま市", suburb: "浦和区" | Saitama Urawa-ku |
| Chiba | 35.6132, 140.1133 | city: "千葉市", suburb: "中央区" | Chiba Chuo-ku |

**API call format:**
```
https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&zoom=14&accept-language=ja
```

**Key findings:**
- Returns ward name in `address.city` for Tokyo 23 wards
- Returns city in `address.city` and ward in `address.suburb` for designated cities (Yokohama, Kawasaki, Saitama, Chiba)
- Zoom level 14 gives ward/city-level results consistently
- Response includes full address hierarchy

**Rate limiting:**
- Public Nominatim: max 1 request/second, needs custom User-Agent
- 1,493 stations at 1/sec = ~25 minutes -- completely acceptable as a one-time batch job
- Alternatively: self-host Nominatim for faster processing (but unnecessary for 1,493 requests)

**This would expand ward-level crime data coverage from 18% to ~100%.**

### Better Solution: ArcGIS Point-in-Polygon

Since the ArcGIS FeatureServer has 5,596 polygons with geometry, we can do point-in-polygon queries:
```
https://services.arcgis.com/wlVTGRSYTzAbjjiC/ArcGIS/rest/services/CrimR6_tokyo/FeatureServer/0/query?geometry={lng},{lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=*&f=json
```

This returns the exact neighborhood polygon containing any given lat/lng, along with all crime data and population.

**Limitation: Tokyo only.** Kanagawa/Saitama/Chiba stations still need Nominatim + prefectural police ward-level data.

### Hybrid Approach (Recommended)
1. **Tokyo stations (~700)**: Use ArcGIS point-in-polygon for neighborhood-level crime data
2. **Kanagawa/Saitama/Chiba stations (~800)**: Use Nominatim reverse geocoding to get ward/city, then match against prefectural police ward-level crime data

## 6. Existing Safety Maps and Scores

### Keishicho Crime Information Map (犯罪情報マップ)
- URL: https://www.keishicho.metro.tokyo.lg.jp/toukei/johomap/johomap.htm
- Built on ArcGIS, displays crime data on interactive map
- Same data as the FeatureServer we identified above
- No API for scores, but the underlying data is accessible via FeatureServer

### Gaccom Safety Navi (ガッコム安全ナビ)
- URL: https://www.gaccom.jp/safety
- Covers all 47 prefectures, ~400,000 incidents recorded
- Shows incidents on map with avatars
- Uses police notification data (メールけいしちょう etc.)
- No public API, would require scraping -- not recommended as primary source

### LIFULL HOME'S (まちむすび)
- Has resident-reported safety satisfaction scores per station/area
- "まちむすび 生成AI API" exists for accessing evaluation data
- Commercial API, likely requires licensing
- Good for validation but not as primary data source

### StudySapuri Station Safety Rankings
- URL: https://shingakunet.com/area/ranking_station-safety/tokyo/
- Rankings of stations by safety for Tokyo
- Methodology unclear, likely based on ward-level crime stats
- Could be used for cross-validation

### Japan Neighborhoods (japanneighborhoods.com)
- Uses same Keishicho cho-cho-level data we identified
- Aggregates 3,110 neighborhoods across Tokyo 23 wards
- Uses 2020 Census population as denominator
- Good validation reference for our own calculations

### ALSOK Tokyo Safety Ranking
- URL: https://www.alsok.co.jp/person/recommend/tokyo-security-ranking/
- Ward-level ranking, same underlying data

**Verdict: No need to scrape third-party scores. We have access to the same primary data (Keishicho + Census) that all these sites use. Building from primary data gives us more control and transparency.**

## 7. Recommended Formula

### Safety Score (1-10, higher = safer)

```python
def compute_safety_score(station):
    # Step 1: Get crime data
    if station.prefecture == "13":  # Tokyo
        # Use ArcGIS point-in-polygon for neighborhood-level data
        neighborhood = arcgis_query(station.lat, station.lng)
        weighted_crimes = compute_weighted_crimes(neighborhood)
        population = neighborhood.TOTPOP_R2

        # Apply daytime population adjustment
        ward = neighborhood.SHI_NAME
        day_factor = daytime_pop[ward] / nighttime_pop[ward]
        if day_factor > 2.0:
            effective_pop = daytime_pop[ward] * (population / nighttime_pop[ward])
        elif day_factor > 1.5:
            effective_pop = population * (1 + day_factor) / 2
        else:
            effective_pop = population
    else:
        # Kanagawa/Saitama/Chiba: ward-level data
        ward = nominatim_reverse(station.lat, station.lng)
        ward_data = prefectural_crime_data[ward]
        weighted_crimes = ward_data.weighted_crimes
        effective_pop = ward_data.population  # No daytime adjustment for suburbs

    # Step 2: Compute per-capita rate
    if effective_pop > 0:
        crime_rate = weighted_crimes / effective_pop * 10000
    else:
        crime_rate = 0  # Uninhabited area, use neighborhood average

    # Step 3: Normalize to 1-10 scale (inverted: lower crime = higher score)
    # Based on observed range: ~5 (safest suburbs) to ~500 (Kabukicho)
    # Use log scale because crime distribution is heavily skewed
    import math
    log_rate = math.log1p(crime_rate)
    # log1p(5) = 1.79, log1p(100) = 4.62, log1p(500) = 6.22
    raw_score = 10 - (log_rate - 1.5) * (9 / 5.0)
    raw_score = max(1.0, min(10.0, raw_score))

    # Step 4: Apply supplementary signals
    koban_bonus = 0.2 if station.koban_within_500m >= 1 else 0.0
    konbini_bonus = 0.15 if station.konbini_count >= 5 else (-0.1 if station.konbini_count == 0 else 0.0)

    final_score = raw_score + koban_bonus + konbini_bonus
    return max(1.0, min(10.0, round(final_score, 1)))
```

### Validation Checks

| Station | Expected Score | Crime Profile |
|---------|---------------|---------------|
| Chiyoda area (Tokyo) | 7-8 | Low street crime, very safe, inflated by commuters |
| Kabukicho (Shinjuku) | 3-4 | High assault, theft, nightlife crime |
| Setagaya residential | 8-9 | Low crime per capita, residential |
| Bunkyo-ku | 8-9 | University area, very low crime |
| Yokohama Nishi-ku | 5-6 | Moderate, station area |
| Kawasaki-ku | 4-5 | Higher crime area of Kawasaki |
| Nerima suburban | 8-9 | Very low crime residential |

## 8. Implementation Plan

### Phase 1: Data Collection (1-2 hours)

1. **Download Keishicho neighborhood crime CSV** (2024 annual)
   - URL: https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/ninchikensu.html
   - Parse CSV into structured data

2. **Query ArcGIS FeatureServer** for all 5,596 Tokyo neighborhoods with crime + population
   - Endpoint: CrimR6_tokyo FeatureServer
   - Download all features as GeoJSON (paginate at 2000 records per query)
   - This gives us geometry + crime breakdown + population in one dataset

3. **Download Tokyo daytime population** from census data
   - URL: https://www.toukei.metro.tokyo.lg.jp/tyukanj/2020/tj-20index.htm
   - Table 11 for ward-level day/night population

4. **Scrape Kanagawa prefecture crime page** (HTML table or PDF)
   - URL: https://www.police.pref.kanagawa.jp/tokei/hanzai_tokei/mesc0027.html
   - Extract municipality-level crime data with type breakdown

5. **Download Saitama + Chiba open data CSVs**
   - These are incident-level; aggregate by municipality for rates

### Phase 2: Station-to-Area Mapping (30 min)

1. **Tokyo stations**: ArcGIS point-in-polygon query for each station lat/lng
   - Returns exact neighborhood + crime data in one query
   - ~700 stations, can batch via API

2. **Non-Tokyo stations**: Nominatim reverse geocoding
   - ~800 stations at 1/sec = 13 minutes
   - Map to ward/city codes for prefectural crime data lookup

### Phase 3: Score Computation (1 hour)

1. Compute weighted crime scores per neighborhood/ward
2. Apply daytime population adjustment for commercial wards
3. Normalize to 1-10 scale
4. Add koban/konbini supplementary signals
5. Validate against known benchmarks (Chiyoda test, Kabukicho test)
6. Write to NocoDB

### Phase 4: Fallback Logic

For stations where point-in-polygon or reverse geocoding fails:
1. Try nearest-neighbor: find closest station with data, use its score +/- 0.5
2. If on same train line: interpolate between adjacent stations with data
3. Ultimate fallback: prefecture median score (only for truly remote stations)

## 9. Expected Coverage & Confidence Level

| Prefecture | Stations | Method | Granularity | Coverage | Confidence |
|-----------|----------|--------|-------------|----------|------------|
| Tokyo (23 wards) | ~450 | ArcGIS point-in-polygon | Neighborhood (町丁目) | 100% | Very High |
| Tokyo (Tama) | ~250 | ArcGIS point-in-polygon | Neighborhood (町丁目) | 100% | Very High |
| Kanagawa | ~400 | Nominatim + prefectural stats | Ward/City (区市) | ~95% | High |
| Saitama | ~200 | Nominatim + prefectural stats | City (市) | ~90% | Medium-High |
| Chiba | ~190 | Nominatim + prefectural stats | City (市) | ~90% | Medium-High |
| **Total** | **~1,493** | **Hybrid** | **Mixed** | **~97%** | **High** |

### Confidence Levels Explained
- **Very High**: Neighborhood-level data with crime type breakdown, population, and daytime adjustment. Every station gets its own unique neighborhood crime profile.
- **High**: Ward/city-level data with crime type breakdown. Stations in the same ward share a score, but wards are reasonably homogeneous.
- **Medium-High**: City-level data, some cities are large. Crime type breakdown available but less granular geographically.

### Improvement from Current State
- Current: 264 stations (18%) with ward-level data, no crime type weights, no daytime adjustment
- Proposed: ~1,450 stations (97%) with neighborhood or ward-level data, weighted crime types, daytime adjustment
- The Chiyoda problem is solved (score goes from ~1 to ~7-8)
- The Kabukicho vs Shinjuku Gyoen problem is solved (different neighborhoods get different scores)
- Bicycle theft no longer dominates safe suburban scores

## 10. Key URLs Summary

| Resource | URL |
|----------|-----|
| Keishicho cho-cho crime CSV | https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/ninchikensu.html |
| Keishicho crime occurrence CSV | https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/hanzaihasseijyouhou.html |
| ArcGIS FeatureServer 2024 | https://services.arcgis.com/wlVTGRSYTzAbjjiC/ArcGIS/rest/services/CrimR6_tokyo/FeatureServer/0 |
| ArcGIS FeatureServer 2023 | https://services.arcgis.com/wlVTGRSYTzAbjjiC/ArcGIS/rest/services/CrimR5_tokyo/FeatureServer/0 |
| Tokyo Open Data API Catalog | https://spec.api.metro.tokyo.lg.jp/spec/search?organizations=%E8%AD%A6%E8%A6%96%E5%BA%81 |
| Tokyo Daytime Population (2020) | https://www.toukei.metro.tokyo.lg.jp/tyukanj/2020/tj-20index.htm |
| Kanagawa crime by municipality | https://www.police.pref.kanagawa.jp/tokei/hanzai_tokei/mesc0027.html |
| Kanagawa open data CSV | https://www.police.pref.kanagawa.jp/tokei/hanzai_tokei/mesd0145.html |
| Saitama crime stats | https://www.police.pref.saitama.lg.jp/c0011/keihouhan.html |
| Saitama open data | https://www.police.pref.saitama.lg.jp/c0011/kurashi/0pendata2019/opendate-2019.html |
| Chiba open data | https://www.police.pref.chiba.jp/seisoka/safe-life_publicspace-statistics_00002.html |
| NPA open data links | https://www.npa.go.jp/toukei/seianki/hanzaiopendatalink.html |
| Nominatim reverse geocoding | https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&zoom=14 |
| e-Stat small area census | https://www.e-stat.go.jp/stat-search/files?tstat=000001136464&toukei=00200521 |
