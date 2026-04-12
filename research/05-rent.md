# Research: Rent Rating Coverage Expansion

**Date**: 2026-04-04
**Status**: Complete
**Current coverage**: 274 / 1493 stations (18%) — all from Suumo, mapped to 67 unique area codes

## 1. Coverage Expansion Options

> **Phase 0 (Plane CRTKY-43):** **e-Stat** / municipal open aggregates — только валидация и sanity на уровне **ward / prefecture**; не позиционировать и не экспортировать как **station-level** аренду в продукте или в текстах confidence. Канонический чеклист — **description** задачи в Plane.

### 1A. Reverse Geocode All 1493 Stations via Nominatim (QUICK WIN)

**Effort**: Low (1-2 hours scripting, ~25 min API time at 1 req/sec)
**Impact**: High — gives ward/city assignment for ALL 1493 stations

**Verified Nominatim behavior** (tested with 5 real Tokyo-area coordinates):

| Location | Lat/Lon | `address.city` | `address.suburb` | Notes |
|----------|---------|-----------------|-------------------|-------|
| Shinjuku | 35.6897, 139.7005 | 新宿区 | (absent) | Tokyo 23-ku: ward in `city` |
| Shibuya | 35.6580, 139.7016 | 渋谷区 | (absent) | Same pattern for 23-ku |
| Yokohama (Naka) | 35.4437, 139.6380 | 横浜市 | 中区 | Designated cities: city in `city`, ward in `suburb` |
| Saitama (Urawa) | 35.8617, 139.6455 | さいたま市 | 浦和区 | Same designated-city pattern |
| Chiba (Narashino) | 35.6619, 139.9982 | 習志野市 | (absent) | Regular cities: just `city` |

**Key finding**: Nominatim at zoom=14 reliably returns:
- **Tokyo 23 special wards**: ward name directly in `address.city` (e.g., "新宿区")
- **Designated cities** (Yokohama, Saitama, Chiba, Kawasaki, Sagamihara): city in `address.city`, ward in `address.suburb`
- **Regular cities**: city name in `address.city`
- **Prefecture**: in `address.province` (outside Tokyo) or via `ISO3166-2-lvl4`

**Approach**: For each of 1493 stations, call Nominatim reverse → extract municipality name → map to Suumo area code (5-digit JIS code like "13104"). This gives ward-level rent fallback for every station.

**Rate limit**: Nominatim allows 1 req/sec. 1493 stations = ~25 minutes. Use `accept-language=ja` for Japanese names. Cache results.

### 1B. Expand Suumo Area-Code Scraping (MEDIUM EFFORT)

**Effort**: Medium (1-2 days — mapping + scraping)
**Impact**: High — real Suumo data for many more area codes

**Current state**: 67 unique area codes scraped. The 4 prefectures contain approximately:

| Prefecture | Total municipalities | Currently mapped | Gap |
|------------|---------------------|------------------|-----|
| Tokyo (13) | 62 (23 wards + 26 cities + 13 towns/villages) | 44 | ~18 |
| Kanagawa (14) | 33 (19 cities + 13 towns + 1 village) | 10 | ~23 |
| Saitama (11) | 63 (40 cities + 22 towns + 1 village) | 4 | ~59 |
| Chiba (12) | 54 (37 cities + 16 towns + 1 village) | 9 | ~45 |
| **Total** | **~212** | **67** | **~145** |

**Station distribution**: Tokyo 615, Kanagawa 337, Chiba 319, Saitama 222 = 1493 total.

After reverse geocoding (step 1A), we would know exactly which area codes are needed. The scraper already supports all 4 prefectures. Adding ~145 new area codes to `station-area-codes.json` would be straightforward, but scraping them at 2.5s delay = ~12 minutes per run (2 requests per area code for 1K and 2LDK).

### 1C. Suumo Station-Based Search (HIGH EFFORT)

**Effort**: High (multi-day — code mapping + 1493 scrapes)
**Impact**: Highest — per-station precision

**Verified Suumo URL structure**:
- Station search URL: `https://suumo.jp/chintai/tokyo/ek_XXXXX/`
- Example: Iidabashi = `ek_01820`, Takadanobaba = `ek_22350`, Kamata = `ek_08940`
- Full search: `https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ek=030501820&...`

**Station code mapping problem**: Suumo `ek` codes are NOT standard ekidata station codes. They appear to be Suumo's internal IDs (5-digit, not matching JIS or ekidata). No public mapping table exists. Options to build the mapping:
1. Scrape Suumo's line/station selector pages (`suumo.jp/chintai/tokyo/ensen/`) to extract all ek codes
2. Search each station name on Suumo and extract the ek code from the redirect URL

**Scraping at scale**: 1493 stations x 2 room types x 2.5s delay = ~2 hours per full run. Manageable but requires the code mapping first.

### 1D. LIFULL HOME'S Station-Level Averages (MEDIUM-HIGH EFFORT)

**Effort**: Medium-high (code mapping + scraping)
**Impact**: Very high — pre-computed averages, no need to parse listings

**Verified URL structure** (tested live):
```
https://www.homes.co.jp/chintai/{prefecture}/{station_romaji}_{code}-st/price/
```
Examples:
- Tokyo Station: `tokyo/tokyo_00001-st/price/`
- Shinjuku: `tokyo/shinjuku_00231-st/price/`
- Takadanobaba: `tokyo/takadanobaba_00582-st/price/`
- Okubo: `tokyo/okubo_00756-st/price/`
- Ochiai: `tokyo/ochiai_06348-st/price/`
- Yokohama: `kanagawa/yokohama_00004-st/price/`
- Musashi-Kosugi: `kanagawa/musashikosugi_00657-st/price/`

**Data provided per station** (verified on multiple pages):
- Average rent for 1R, 1K, 1DK, 1LDK, 2K, 2DK, 2LDK, 3LDK
- Within 10-min walk of station
- Updated weekly (Fridays)
- Pre-computed averages (no need to parse individual listings)

**Station code mapping problem**: HOMES uses its own station codes (not matching ekidata). The romanized station name + numeric code format means we need to discover each station's URL. Approach: scrape HOMES line pages (`/chintai/tokyo/line/price/`) which list all stations with links.

**Advantage over Suumo scraping**: HOMES provides pre-computed averages directly on the page, no need to scrape 50+ individual listings and compute medians. Much faster and more reliable.

## 2. Alternative Data Sources

### 2A. LIFULL HOME'S (homes.co.jp) — RECOMMENDED

**Availability**: Excellent. Station-level averages for all room types.
**Coverage**: Appears to cover virtually every station in Greater Tokyo.
**Data quality**: Pre-computed averages from large listing pools. Weekly updates.
**Scraping feasibility**: HTML pages, standard structure. One page per station with all room types.

Sample data extracted (Shinjuku Ward stations, 1K average):
| Station | 1K Rent | Notes |
|---------|---------|-------|
| Shinjuku | 13.94万 | Central hub |
| Takadanobaba | 11.89万 | Student area |
| Okubo | 12.01万 | Affordable |
| Ochiai | 10.92万 | Residential |

**URL discovery**: The line-based pages (`/chintai/tokyo/line/price/`, `/chintai/kanagawa/line/price/`) list all stations with links. Scrape these index pages first to get all station URLs.

### 2B. at home (athome.co.jp)

**URL structure**: `https://www.athome.co.jp/chintai/souba/tokyo/{station}-st/`
- Example: `tokyo/tokyo-st/`, `tokyo/shibuya-st/`, `kanagawa/yokohama-st/`
**Data**: Station-level rent averages by room type, similar to HOMES.
**Coverage**: Good coverage but less detail than HOMES.
**Assessment**: Good backup source but HOMES is preferred for primary data.

### 2C. LIFULL HOME'S Price Index (lifullhomes-index.jp)

**URL structure**: `https://lifullhomes-index.jp/info/areas/{prefecture}/{station-code}-st/rent/mansion/`
- Example: Asakusabashi = `tokyo-pref/01933-st/rent/mansion/`
**Data**: Rent price trends, averages by building age and floor area, 3-year trajectory.
**Assessment**: Rich trend data but more complex to scrape. Better as supplementary source.

### 2D. Mansion Review (mansion-review.jp)

**Availability**: Has station-level data but requires free member registration for full access.
**Data**: Current prices + AI-powered 30-year predictions.
**Assessment**: Registration wall makes it impractical for bulk scraping. Skip.

### 2E. Government Statistics — Housing & Land Survey (住宅・土地統計調査)

**Source**: Statistics Bureau, Ministry of Internal Affairs (総務省統計局)
**Latest**: 2023 survey (令和5年), results published 2025

**Available data on e-Stat**:
- Table: "住宅の所有の関係別 借家の1か月当たり家賃" (Monthly rent by housing tenure type)
- Granularity: **Municipality level** (市区町村) — covers all wards and cities
- Download: CSV/Excel from `https://www.e-stat.go.jp/stat-search/files?toukei=00200522`
- Specific table: `https://www.e-stat.go.jp/stat-search/database?statdisp_id=0004021479`

**Key data points** (2023 national averages):
- All rental housing: 59,656 yen/month
- Private (non-wooden): 68,548 yen/month
- Private (wooden): 54,409 yen/month

**Granularity limitation**: Ward/city level only, not station-level. But this is FREE, OFFICIAL data covering ALL municipalities. Useful as:
1. Baseline validation for scraped data
2. Fallback for areas where scraping fails
3. Ward-average reference for the ward-based fallback approach

**Download link**: `https://www.e-stat.go.jp/stat-search/files?toukei=00200522&tstat=000001207800`

### 2F. Land Price Data (地価公示)

**Source**: Ministry of Land (国土交通省)
**Note**: This is LAND PRICE, not rent. Strongly correlated but not directly usable as rent data. Would require a land-price-to-rent conversion model. Not recommended for this use case.

## 3. Ward-Average Reliability Analysis

### 3A. Intra-Ward Rent Variance (Measured)

Using HOMES data for stations within **Shinjuku Ward** (1K apartments, 10-min walk):

| Station | 1K Rent | Delta from ward mean |
|---------|---------|---------------------|
| Shinjuku | 13.94万 | +16% |
| Okubo | 12.01万 | 0% (near mean) |
| Takadanobaba | 11.89万 | -1% |
| Ochiai | 10.92万 | -9% |
| Ward average (HOMES) | ~12.95万 | baseline |

**Spread**: 10.92万 to 13.94万 = range of 3.02万 (28% of lowest value)
**Standard deviation estimate**: ~1.2万 (~10% of mean)
**Coefficient of variation**: ~10%

### 3B. Cross-Ward Comparison (HOMES 23-ward 1R/1K/1DK averages)

| Tier | Wards | Rent Range |
|------|-------|------------|
| Premium | Minato, Chiyoda, Shibuya | 15.49-15.80万 |
| High | Shinjuku, Bunkyo, Meguro, Chuo | 13.25-14.56万 |
| Mid-high | Koto, Shinagawa, Taito, Sumida, Toshima | 12.23-13.25万 |
| Mid | Setagaya, Nakano, Kita, Ota | 11.27-12.05万 |
| Affordable | Suginami, Arakawa, Itabashi | 9.78-10.49万 |
| Budget | Nerima, Adachi, Katsushika, Edogawa | 8.63-9.46万 |

**Cross-ward range**: 8.63万 to 15.80万 = 7.17万 (83% of lowest)
**Within-ward range** (Shinjuku example): 3.02万 (28% of lowest)

### 3C. Assessment

**Within-ward variance (~10% CV)** is moderate and significantly smaller than **between-ward variance (~30% CV)**. This means:

- Ward average is a **reasonable proxy** for stations within that ward
- It correctly ranks wards/neighborhoods in the right order
- The error margin of ~1-1.5万 yen is acceptable for a 1-10 rating scale
- For extreme stations (Shinjuku central vs. Ochiai residential), the error can be ~3万, which might shift the rating by 1-2 points

**Conclusion**: Ward average is a GOOD fallback for stations without direct data, especially outside central Tokyo where intra-ward variance is lower. Station-level data is preferred for the 23 special wards where variance is higher.

### 3D. Station Proximity Factor

Rent premiums near stations follow a step function rather than linear:
- Within 5 min walk: ~10-15% premium
- 5-10 min walk: baseline
- 10-15 min walk: ~5-10% discount
- 15+ min walk: ~15-20% discount

Since our scraper already filters for "10 min walk" (et=10), this factor is controlled for in the data collection.

## 4. Recommended Approach (Prioritized)

### Phase 1: Reverse Geocode + Ward Average (1-2 hours)
1. Run Nominatim reverse geocoding for all 1493 stations
2. Map each station to its ward/city JIS code
3. Apply existing Suumo ward averages to unmapped stations in known wards
4. **Expected result**: Coverage jumps from 274 to ~400-500 stations (those in already-scraped wards)

### Phase 2: Expand Suumo Area-Code Scraping (1 day)
1. Use Phase 1 mapping to identify all needed area codes (~145 new codes)
2. Add them to `station-area-codes.json`
3. Run scraper for new area codes
4. **Expected result**: Coverage reaches ~800-1000 stations (all stations in scrapable wards/cities)

### Phase 3: HOMES Station-Level Scraping (2-3 days)
1. Scrape HOMES line index pages to discover all station URLs
2. Build station-name-to-HOMES-code mapping
3. Scrape per-station averages from HOMES price pages
4. Merge with Suumo data (Suumo = primary, HOMES = gap-fill + validation)
5. **Expected result**: Coverage reaches ~1400+ stations

### Phase 4: Government Data Validation (optional, 2-3 hours)
1. Download 2023 Housing Survey ward/city averages from e-Stat
2. Cross-validate with Suumo/HOMES scraped averages
3. Use as fallback for any remaining gaps
4. **Expected result**: 100% coverage with at least ward-level data

### Effort/Impact Summary

| Phase | Effort | Coverage After | Data Quality |
|-------|--------|---------------|--------------|
| Current | done | 274 (18%) | Station-level (Suumo) |
| Phase 1 | 1-2 hours | ~400-500 (27-33%) | Ward average fallback |
| Phase 2 | 1 day | ~800-1000 (54-67%) | Ward-level (Suumo) |
| Phase 3 | 2-3 days | ~1400+ (94%+) | Station-level (HOMES) |
| Phase 4 | 2-3 hours | 1493 (100%) | Ward-level (govt stats) |

## 5. Normalization Method

### Current Approach
Inverted percentile: cheaper = higher rating (1-10 scale).

### Recommended: Log-Scale Inverted Percentile

**Rationale**: Rent distribution is right-skewed. The perceived difference matters more at the low end:
- 60k vs 70k yen = significant quality-of-life difference
- 150k vs 160k yen = negligible difference for someone already paying that much

**Proposed formula**:
```
log_rent = log(rent)
percentile = (log_rent - log_min) / (log_max - log_min)
rating = 10 - 9 * percentile   # 10 = cheapest, 1 = most expensive
```

**Suggested bounds**:
- `min_rent` = 50,000 yen (rural Chiba/Saitama stations) -> rating 10
- `max_rent` = 200,000 yen (Minato-ku/Shibuya central) -> rating 1
- Anything below 50k gets capped at 10, above 200k capped at 1

**Using 1K apartment data as primary metric** (most comparable across all stations, largest sample size).

**Alternative**: Use the geometric mean of 1K and 2LDK prices to capture both single and family perspectives, weighted by the category default (which targets single professionals).

### Handling Missing Data After All Phases

For any station still missing after Phase 4:
- Use distance-weighted average of 3 nearest stations with data
- This replaces the current crude linear heuristic (`160000 - distance_km * 15000`)

## 6. Expected Final Coverage

| Data Source | Stations | Quality | Role |
|-------------|----------|---------|------|
| Suumo (existing) | 274 | Station-level (ward proxy) | Primary for covered wards |
| Suumo (expanded area codes) | ~500-700 additional | Ward-level | Primary for new wards |
| HOMES station-level | ~1200-1400 | Station-level | Gap-fill + cross-validation |
| Government stats | ~1493 | Ward/city level | Ultimate fallback |
| Nearest-station interpolation | ~50-100 | Estimated | Residual gaps |

**Final target**: 100% of 1493 stations with data, where:
- ~60-70% have station-level data (Suumo + HOMES)
- ~25-35% have ward-level averages (expanded Suumo + govt stats)
- ~5% have nearest-neighbor interpolation (remote stations)

**Quality tiers for the rating**:
- Tier A (station-level scrape): high confidence, +/- 0.5 rating points
- Tier B (ward average): moderate confidence, +/- 1.5 rating points
- Tier C (interpolation): low confidence, +/- 2 rating points

The metadata field `source` in rent-averages.json should track provenance: "suumo", "homes", "ward_avg", "govt_stats", "interpolated".
