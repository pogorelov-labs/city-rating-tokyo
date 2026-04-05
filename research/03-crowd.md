# Research: Crowd Rating Data Sources

**Date:** 2026-04-04
**Status:** Complete
**Goal:** Find data sources to build a crowd rating (1-10, inverted: less crowded = higher) for 1493 Greater Tokyo stations. Currently 92 stations have passenger data (6% coverage).

---

## 1. Passenger Data Sources

### 1a. MLIT National Land Numerical Information (Best Single Source)

**Dataset:** 国土数値情報 駅別乗降客数データ (S12)
**URL:** https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-v3_1.html
**Coverage:** Nationwide — all railway operators who disclose data
**Format:** GML (JPGIS 2.1), GeoJSON (from FY2016+), Shapefile
**Years available:** FY2011 through FY2021 in current v3.1 dataset; FY2023 data was published June 2024; FY2024 data released June 2025
**File pattern:** S12-{YY}_GML.zip (e.g. S12-22_GML.zip for FY2021)
**Fields (approx 49):** station name, station code, group code, operating company, railway line, classification, annual passenger count per year (integer, persons/day), data availability flags, duplicate codes, remarks
**License:** Non-commercial use per railway operator agreements
**Expected coverage:** Likely 800-1200+ stations in Greater Tokyo (all operators who disclose). Some operators (notably JR Central, JR Shikoku) withhold data, but JR East and all major private railways in Tokyo area are included.

**Assessment:** This is the single most valuable dataset. One download gives station-level daily passenger counts for most stations across all operators. GeoJSON format means it includes lat/lng, making station matching straightforward. Should be priority #1 for implementation.

**Key limitation:** Some stations have missing data where operators opted out. The latest version available to download is FY2021 (v3.1 page), but newer versions (FY2023, FY2024) have been released on the download site — need to check exact URL for latest.

### 1b. ODPT Public Transport Open Data Center API

**URL:** https://developer.odpt.org/ (registration required, free)
**API type:** REST API, JSON-LD format
**Data type:** odpt:PassengerSurvey
**Fields:** @id, owl:sameAs, odpt:operator, odpt:station, odpt:railway, odpt:surveyYear, odpt:passengerJourneys (daily count)

**Operators providing passenger survey data via ODPT:**
1. Tokyo Metro
2. Toei (Tokyo Metropolitan Bureau of Transportation)
3. Yokohama City Transportation Bureau
4. TWR Rinkai Line
5. Tsukuba Express (Metropolitan Intercity Railway)
6. Tokyo Tama Intercity Monorail

**Also listed in ODPT catalog (separate datasets):**
- Keio Railway
- Keikyu Railway
- Tokyu Railway

**Assessment:** Good supplementary API source. Covers 6+ operators with structured JSON data. Requires free developer registration. The data is machine-readable and includes station identifiers that can be cross-referenced. However, coverage is limited to operators who participate — missing JR East, Seibu, Tobu, Odakyu, Keisei, Sotetsu from the core API.

### 1c. JR East Published Data

**URL:** https://www.jreast.co.jp/en/company/data/passenger/
**Coverage:** ALL JR East stations (hundreds in Greater Tokyo)
**Format:** HTML tables on website (need scraping)
**Data:** Daily average boarding passengers (乗車人員 — boarding only, multiply by 2 for bidirectional estimate)
**Structure:**
- Top 100 stations: https://www.jreast.co.jp/en/company/data/passenger/
- 101+ rank (page 1): https://www.jreast.co.jp/en/company/data/passenger/2024_01.html/
- 101+ rank (page 2): .../2024_02.html/
- 101+ rank (page 3): .../2024_03.html/
- 101+ rank (page 4): .../2024_04.html/
**Year:** FY2024 data published September 2025

**Assessment:** Extremely valuable. JR East operates the most stations in Greater Tokyo (Yamanote, Chuo, Sobu, Keihin-Tohoku, Saikyo, Joban, Yokohama, Tokaido, etc.). The English-language pages make parsing easier. Current scraper only captures 92 stations; JR East alone could provide 300+ stations in our coverage area.

### 1d. Private Railway Company Published Data

Each private railway publishes station-level data, usually as PDF or HTML:

| Operator | URL | Format | Stations (approx in Tokyo area) |
|----------|-----|--------|------|
| **Tokyo Metro** | https://www.tokyometro.jp/corporate/enterprise/passenger_rail/transportation/passengers/index.html | HTML ranking | ~130 stations |
| **Toei** | https://www.kotsu.metro.tokyo.jp/subway/kanren/passengers.html | HTML table + Tokyo Open Data API | ~106 stations (4 subway lines + Nippori-Toneri) |
| **Keio** | https://www.keio.co.jp/company/corporate/corporate_manual/number-of-passengers.html | PDF | ~69 stations |
| **Odakyu** | https://www.odakyu.jp/company/railroad/users/ | HTML/PDF | ~70 stations |
| **Tokyu** | https://www.tokyu.co.jp/railway/data/passengers/ | HTML | ~100+ stations |
| **Seibu** | https://www.seiburailway.jp/company/passengerdata/ | PDF (https://www.seiburailway.jp/file.jsp?company/passengerdata/file/2024joukou.pdf) | ~90 stations |
| **Tobu** | https://www.tobu.co.jp/corporation/rail/station_info/ | HTML + PDF (https://www.tobu.co.jp/pdf/corporation/passengers_2023.pdf) | ~130+ stations |
| **Keikyu** | https://www.keikyu.co.jp/ride/kakueki/pdf/train-info_kakueki_avr.pdf | PDF | ~50 stations |
| **Keisei** | https://www.keisei.co.jp/keisei/tetudou/2024_ks_joukou.pdf | PDF | ~69 stations |
| **Sotetsu** | https://cdn.sotetsu.co.jp/media/2025/sustainability/reports/joko2024.pdf | PDF | ~25 stations |
| **Yurikamome** | (via MLIT data / opendata-web.site) | — | ~16 stations |

**Assessment:** Collectively these cover almost every station in our dataset. The challenge is that each publishes in different formats (HTML table, PDF, ranking page). A scraper per operator would be needed, or better: use the MLIT unified dataset first, then fill gaps from operator sites.

### 1e. Japanese Wikipedia Station Pages

**URL pattern:** `https://ja.wikipedia.org/wiki/{station_name_jp}駅`
**Section:** 利用状況 (Usage Status) — contains passenger tables
**Table format:** Separate sub-tables per railway operator, organized by fiscal year. Headers typically: 年度 (fiscal year), 1日平均乗降人員 (daily average passengers), sometimes split by 乗車人員/降車人員.

**Example (Shibuya):**
- JR East 2024: 324,414/day
- Tokyu Toyoko Line 2024: 414,186/day
- Tokyu Den-en-toshi Line 2024: 604,246/day
- Tokyo Metro 2024: 751,998/day

**Parsing approach:** Use MediaWiki API (parse action) or `requests` + BeautifulSoup to extract tables. The `pandas.read_html()` function can parse tables from HTML. The `wptools` or `pymediawiki` libraries provide structured access to Wikipedia content.

**Assessment:** Wikipedia has passenger data for essentially every named station in Japan — potentially covering 1400+ of our 1493 stations. The data is usually sourced from the official operator publications and MLIT data, so it aggregates what we would otherwise need to scrape from 11+ individual operator sites. Main challenges: (1) table format varies slightly between articles, (2) station name matching (our slug vs Japanese name), (3) rate limiting when scraping 1400+ pages. This is the highest-coverage single approach but less reliable than official sources.

### 1f. Tokyo Metropolitan Open Data

**URL:** https://catalog.data.metro.tokyo.lg.jp/dataset/t000018d0000000030
**Coverage:** Toei subway stations (Asakusa, Mita, Shinjuku, Oedo lines) + Nippori-Toneri Liner
**Format:** Dataset via Tokyo Open Data API (CSV/JSON)
**Also:** https://portal.data.metro.tokyo.lg.jp/visualization/annual-number-of-passengers-per-railway-station/ — visualization of annual data from Tokyo Statistical Yearbook (JR, Metro, private railways, Toei), but data is FY2022.

### 1g. Third-Party Aggregator Sites

- **opendata-web.site:** https://opendata-web.site/station/ — CSV download available (station name, line, prefecture, passenger count), source: MLIT S12 data. Can download up to 1000 records per query. Good for quick access without parsing GeoJSON.
- **statresearch.jp:** https://statresearch.jp/traffic/train/passengers_whole_ranking.html — Time-series data 2011-2022 per station, sourced from MLIT. Good for visualization, harder for bulk download.

---

## 2. Area Crowdedness Proxies

### 2a. POI Density (Already Available)

We already have in NocoDB:
- **HotPepper:** HP_total_count (restaurants) — 1493 stations, 100% coverage
- **OSM POIs:** convenience_store_count, food_count, shop_count — running, will be 100%

High restaurant + convenience store density strongly correlates with foot traffic. This is our best "free" crowd proxy.

**Proposed formula:**
```
commercial_density = HP_total * 0.5 + OSM_convenience * 2 + OSM_food * 0.3
```

### 2b. NTT Docomo Mobile Spatial Statistics (Expensive)

**URL:** https://www.docomo.ne.jp/biz/service/spatial_statistics/
**Provider:** Docomo Insight Marketing (subsidiary of NTT Docomo)
**Data type:** Population counts per mesh area, 24/7, by gender/age/residential area
**Format:** XLSX/CSV via API or bulk
**Pricing:** Enterprise/B2B — requires commercial license, pricing not public. Likely tens of thousands USD/year.
**Open data subset:** Some data was provided via Tokyo Open Data Challenge (https://ckan-tokyochallenge.odpt.org/en/dataset/o_mobile_spatial_statistics-dcmim) but likely limited/expired.

**Assessment:** Gold standard for area foot traffic, but cost-prohibitive for this project. Skip unless a free academic access path exists.

### 2c. Agoop Location Data (Expensive)

**Provider:** Agoop Corp (SoftBank subsidiary)
**Data type:** Point-type and mesh-type mobile population data from smartphone apps
**Pricing:** Commercial — not publicly listed, requires inquiry
**Assessment:** Similar to Docomo — high quality but enterprise pricing. Skip.

### 2d. Google Popular Times (Partially Viable)

**Official API:** Google does NOT provide Popular Times data through the Places API. There is a long-standing feature request (Google Issue Tracker #35827550) that remains unresolved.

**Unofficial options:**
- **populartimes** (Python library): https://github.com/m-wrzr/populartimes — scrapes Google Maps for popular times data. Returns hourly popularity (0-100) per day of week. Works but violates Google ToS and may be rate-limited.
- **BestTime.app:** https://besttime.app/ — commercial API that provides foot traffic forecasts for venues, available for Japan. Pricing starts at $29/month. Could query multiple POIs around each station. Coverage in Japan confirmed.

**Assessment:** The unofficial `populartimes` library could provide area-level "busyness" data by querying popular places near each station (e.g., the station building itself, nearby shopping malls). However, querying 1493 stations x multiple POIs = thousands of requests, which is fragile. BestTime.app is a cleaner option but adds recurring cost. Consider as a secondary enrichment, not primary source.

### 2e. Yahoo Japan Crowdedness

**Status:** No public API found for area crowdedness data. Yahoo Japan provides crowdedness info within Yahoo Maps app but no developer API identified.

---

## 3. Tourist Factor Data

### 3a. OSM Tourism Tags (Free, Immediate)

**Approach:** Overpass API query for tourism=attraction|museum|viewpoint|artwork|gallery within radius of each station.

**Example Overpass query:**
```
[out:json][timeout:25];
(
  node["tourism"~"attraction|museum|viewpoint"](around:800,35.7104,139.8103);
  way["tourism"~"attraction|museum|viewpoint"](around:800,35.7104,139.8103);
);
out count;
```

**Expected results (validated concept):**
- Asakusa area: Senso-ji temple, multiple museums, Tokyo Skytree -> high tourist tag count
- Harajuku: Meiji Shrine, Takeshita-dori shops -> high tourist tag count
- Hodogaya: residential -> near-zero tourist tags

An OSMnx test query for Minato ward with tourism tags (museum, hotel, attraction) returned 1304 elements — confirming substantial tag density in tourist areas.

**Assessment:** Excellent free proxy for tourist crowding. Can be added to our existing OSM scraper as new tag categories. Expected to differentiate tourist-heavy stations (Asakusa, Harajuku, Ueno, Odaiba) from commuter stations (Shimbashi, Tamachi).

### 3b. Flickr Photo Density (Research-grade)

**API:** https://www.flickr.com/services/api/flickr.photos.geo.photosForLocation.html
**Approach:** Count geotagged photos within radius of each station. High photo density = tourist area.
**Dataset:** A pre-built dataset of Tokyo geotagged Flickr images exists on Kaggle.

**Assessment:** Academically interesting but Flickr usage has declined significantly since ~2015. Photo density would be biased toward older tourist patterns. Lower priority than OSM tourism tags.

### 3c. Instagram/Social Media

Instagram API is severely restricted — no geolocation search available for public posts. Not viable.

---

## 4. Temporal Crowdedness: Train Congestion Rate Data

### 4a. MLIT Congestion Rate Survey (混雑率)

**URL:** https://www.mlit.go.jp/report/press/tetsudo04_hh_000138.html
**Data (FY2024):** Published July 2025
**Download:** PDF only (3 documents):
- 資料1: Average congestion rate trends for 3 metro areas (423KB)
- 資料2: Per-line congestion rates for main sections (123KB) — https://www.mlit.go.jp/tetudo/content/001903146.pdf
- 資料3: Peak congestion sections (142KB)

**Format:** Table with columns: operator name, line name, section (most crowded), time period, transport capacity (persons), transported persons, congestion rate (%)

**Key Tokyo lines and congestion rates (FY2024):**
- Nippori-Toneri Liner (Akatsuka Elementary -> Nishi-Nippori): 177% (worst)
- JR Saikyo Line: 163%
- Tokyo Metro Hibiya Line: 163%
- Tokyo Metro Tozai Line: 156%
- JR Chuo-Sobu (local): 152%
- JR Yokosuka Line: 149%
- JR Joban Line: 148%
- Tokyo average across all lines: 139%

**Assessment:** Useful as a per-LINE modifier (not per-station). A station on a highly congested line (like Tozai Line at 156%) feels more hectic than a station on a less crowded line. This could be a multiplier factor: stations served by highly congested lines get a crowdedness boost. Data requires manual extraction from PDF since it is not machine-readable.

---

## 5. Recommended Composite Formula

The crowd score should combine multiple signals that capture different types of crowdedness:

```python
# Inputs (all normalized 0-1 within dataset)
passenger_norm     # Station daily passenger count (normalized log scale)
commercial_norm    # HP_total + OSM convenience + food (normalized)
tourist_norm       # OSM tourism tag count (normalized)
congestion_norm    # Line congestion rate (normalized, per-line)

# Weights
crowd_raw = (
    passenger_norm  * 0.45 +   # Station throughput (dominant signal)
    commercial_norm * 0.25 +   # Commercial/foot traffic density
    tourist_norm    * 0.20 +   # Tourist crowding factor
    congestion_norm * 0.10     # Rush hour overcrowding
)

# Convert to 1-10 rating (inverted: less crowded = higher)
crowd_rating = 10 - round(crowd_raw * 9)  # 1 = most crowded, 10 = quietest
```

**Key design decisions:**
- **Log-scale normalization** for passenger counts: The range spans 5,000 to 775,000 — linear would compress most stations. Use `log(passengers)` to spread the distribution.
- **Passenger count is 45% weight** because it is the most reliable, direct measure of station busyness.
- **Commercial density at 25%** captures daytime foot traffic that passenger counts miss (e.g., people who drive or bus to shopping areas).
- **Tourist factor at 20%** ensures Harajuku/Asakusa score appropriately crowded even if their station passenger counts are moderate.
- **Congestion rate at 10%** adds a rush-hour penalty for stations on packed commuter lines.

**Fallback for missing data:** For stations without passenger counts, estimate from:
1. First: check if MLIT dataset has the count
2. Second: use `line_count * 20000` as rough heuristic (better than current `line_count * 15000`)
3. Clamp the estimate based on station type (e.g., monorail/new transit stations cap at 30,000)

---

## 6. Validation Against Known Stations

Expected results from the composite formula:

| Station | Passenger Count | Commercial | Tourist | Congestion Lines | Expected Rating |
|---------|----------------|------------|---------|-----------------|----------------|
| Shinjuku | 775,000 | Very high | Medium | High (Chuo, Saikyo) | 1-2 |
| Shibuya | 366,000+ (combined: ~2M+) | Very high | High | High (Tozai) | 2 |
| Harajuku | 75,000 (JR) | High | Very high (Meiji Shrine) | Medium | 2-3 |
| Asakusa | ~50,000 (combined) | High | Very high (Senso-ji) | Low | 3 |
| Nakameguro | 98,000 | Medium | Low | Medium | 5-6 |
| Kichijoji | 143,000 | High | Low | Medium | 5 |
| Sugamo | 53,000 | Medium-low | Low | Low | 6-7 |
| Todai-mae | ~15,000 | Low | Low | Low | 8 |
| Hodogaya | 15,000 | Low | None | Low | 9 |

The formula should naturally produce these results because:
- Shinjuku/Shibuya: max passenger + max commercial = minimum rating
- Harajuku: moderate passenger but very high tourist tags push it down
- Asakusa: tourist factor compensates for lower station throughput
- Nakameguro: high passenger but moderate commercial, no tourist tags
- Hodogaya: minimal everything = high (quiet) rating

---

## 7. Implementation Plan

### Phase 1: MLIT Dataset (Priority: HIGHEST)
1. Download 国土数値情報 S12 dataset (GeoJSON format, latest year available)
2. Parse GeoJSON — extract station name, operator, line, daily passenger count
3. Match to our 1493 stations by name + operator + lat/lng proximity
4. **Expected result:** 800-1200 stations with passenger data (50-80% coverage)
5. **Effort:** 1-2 hours — single file download + parser

### Phase 2: JR East Complete Data (Priority: HIGH)
1. Scrape all 5 pages of JR East station data (Top 100 + 4 pages of 101+)
2. Parse HTML tables for station name + daily boarding count (multiply by 2)
3. Fill gaps not covered by MLIT data (if any)
4. **Expected result:** 300+ JR East stations confirmed
5. **Effort:** 1-2 hours — HTML scraping

### Phase 3: OSM Tourism Tags (Priority: HIGH)
1. Add tourism=attraction|museum|viewpoint|gallery to existing OSM scraper
2. Query Overpass API with 800m radius around each station
3. Store as `tourism_poi_count` in NocoDB
4. **Expected result:** 1493 stations with tourist POI counts
5. **Effort:** 30 min — extend existing scraper

### Phase 4: Congestion Rate Data (Priority: MEDIUM)
1. Manually extract per-line congestion rates from MLIT PDF
2. Create mapping: line_name -> congestion_rate
3. Assign to each station based on which lines serve it (max congestion of any line)
4. **Expected result:** Coverage for all stations on major commuter lines (~60-70 lines)
5. **Effort:** 1-2 hours — manual PDF extraction + mapping

### Phase 5: Gap Filling via Operator Sites (Priority: LOW)
1. For any stations still missing after Phase 1+2, scrape individual operator PDFs/pages
2. Priority operators for gap filling: Tobu (130 stations), Tokyo Metro (130), Seibu (90), Odakyu (70)
3. **Effort:** 3-5 hours total (PDF parsing is harder than HTML)

### Phase 6: Wikipedia Fallback (Priority: LOW)
1. For remaining gaps, query Japanese Wikipedia per station
2. Parse 利用状況 section tables
3. **Effort:** 3-4 hours (rate limiting + table format variations)

---

## 8. Expected Coverage & Confidence Level

| Data Source | Stations | Coverage | Confidence |
|-------------|----------|----------|------------|
| MLIT S12 (GeoJSON) | 800-1200 | 54-80% | High (official govt data) |
| JR East direct | 300+ | 20% | Very high (operator data) |
| ODPT API (Metro, Toei, etc.) | 250+ | 17% | High (structured API) |
| OSM tourism tags | 1493 | 100% | Medium (proxy measure) |
| Commercial density (HP+OSM) | 1493 | 100% | Medium (proxy measure) |
| Congestion rate | ~1000 | 67% | High (official, but per-line not per-station) |
| Operator PDFs (gap fill) | 50-100 | 3-7% | High |
| Wikipedia (final fallback) | 50-100 | 3-7% | Medium (community-maintained) |

**Combined passenger count coverage estimate:** After Phase 1 (MLIT) + Phase 2 (JR East), expect 85-95% of stations to have actual passenger data. The composite formula using all signals (passenger + commercial + tourist + congestion) will cover 100% of stations with reasonable confidence.

**Improvement over current state:** From 92 stations (6%) to 1200+ stations (80%+) with real passenger data, plus 100% coverage of proxy signals.

---

## Key URLs Summary

| Resource | URL |
|----------|-----|
| MLIT S12 Download | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-v3_1.html |
| ODPT Developer Portal | https://developer.odpt.org/ |
| JR East Passengers | https://www.jreast.co.jp/en/company/data/passenger/ |
| Tokyo Metro Passengers | https://www.tokyometro.jp/corporate/enterprise/passenger_rail/transportation/passengers/index.html |
| Toei Passengers | https://www.kotsu.metro.tokyo.jp/subway/kanren/passengers.html |
| Tokyo Open Data (Toei) | https://catalog.data.metro.tokyo.lg.jp/dataset/t000018d0000000030 |
| Keio Passengers | https://www.keio.co.jp/company/corporate/corporate_manual/number-of-passengers.html |
| Odakyu Passengers | https://www.odakyu.jp/company/railroad/users/ |
| Tokyu Passengers | https://www.tokyu.co.jp/railway/data/passengers/ |
| Seibu Passengers (PDF) | https://www.seiburailway.jp/company/passengerdata/ |
| Tobu Passengers | https://www.tobu.co.jp/corporation/rail/station_info/ |
| Keikyu Passengers (PDF) | https://www.keikyu.co.jp/ride/kakueki/pdf/train-info_kakueki_avr.pdf |
| Keisei Passengers (PDF) | https://www.keisei.co.jp/keisei/tetudou/2024_ks_joukou.pdf |
| Sotetsu Passengers (PDF) | https://cdn.sotetsu.co.jp/media/2025/sustainability/reports/joko2024.pdf |
| MLIT Congestion Rate | https://www.mlit.go.jp/report/press/tetsudo04_hh_000138.html |
| Congestion Rate PDF | https://www.mlit.go.jp/tetudo/content/001903146.pdf |
| opendata-web.site | https://opendata-web.site/station/ |
| BestTime.app (foot traffic) | https://besttime.app/ |
| Overpass API (OSM) | https://overpass-api.de/api/interpreter |
