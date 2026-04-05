# Nightlife Rating - Data Source Research

**Date:** 2026-04-04
**Status:** complete

---

## 1. Data Sources Found

### 1A. HotPepper Gourmet API (Already Available - Enhancement)

**URL:** https://webservice.recruit.co.jp/doc/hotpepper/reference.html
**Status:** Already in use for izakaya_count and bar_count. Major untapped feature discovered.

**Key Discovery - `midnight` parameter:**
The HP API has a `midnight=1` filter that returns only shops operating after 23:00. This was NOT used in the current scrape. Re-querying with `midnight=1` per station gives a **late-night establishment count** - a direct nightlife signal.

- Endpoint: `http://webservice.recruit.co.jp/hotpepper/gourmet/v1/`
- Parameters: `lat`, `lng`, `range` (1=300m, 2=500m, 3=1000m, 4=2000m, 5=3000m), `midnight=1`
- Genre Master API: `http://webservice.recruit.co.jp/hotpepper/genre/v1/` (returns all G-codes)
- Known codes: G001=居酒屋, G002=ダイニングバー・バー (covers bars and dining bars)
- Coverage: 100% of 1493 stations (already proven)
- Rate limit: Same as existing scrape (generous, ~100 req/min)
- Cost: Free with API key

**Action:** Re-run HP scrape with `midnight=1` to get `midnight_count` per station. Also query with `genre=G002` for pure bar count (current bar_count may use subgenre filter).

### 1B. OSM Overpass - Extended Tags

**URL:** https://overpass-api.de/api/interpreter
**Status:** Currently querying `amenity=bar|pub|nightclub`. Major expansion possible.

**New tags to add:**

| Tag | Greater Tokyo Count | Notes |
|-----|-------------------|-------|
| `amenity=nightclub` | ~136 | Sparse but high-signal. Concentrated in Roppongi/Shibuya/Shinjuku |
| `amenity=karaoke_box` | ~382 | Good coverage. Strong nightlife proxy |
| `amenity=music_venue` | ~14 | Very sparse. Livehouses rarely tagged in OSM |
| `amenity=bar` | ~3000+ | Already captured |
| `amenity=pub` | ~2000+ | Already captured |
| `tourism=hostel` | ~157 | Backpacker area proxy |
| `leisure=dance_hall` | <5 (est.) | Too rare to be useful |

**Recommended expanded query:**
```
amenity=bar|pub|nightclub|karaoke_box|music_venue
```
Plus separate hostel query: `tourism=hostel|guest_house`

**Coverage:** ~70% stations currently, will be 100% after full run. Karaoke data adds ~382 POIs that current query misses.

### 1C. Google Places API (New) - Nearby Search

**URL:** https://developers.google.com/maps/documentation/places/web-service/nearby-search
**Docs:** https://developers.google.com/maps/documentation/places/web-service/place-types

**Supported nightlife types (all in Table A, usable for Nearby Search filtering):**
- `night_club` - Direct club data
- `bar` - Bar listings
- `karaoke` - Karaoke venues
- `live_music_venue` - Live music
- `dance_hall` - Dance venues
- `comedy_club` - Comedy venues
- `sports_bar` - Sports bars

**Pricing (post-March 2025):**
- Free tier: 10,000 Essentials calls/month, 5,000 Pro calls/month
- Nearby Search (Essentials): Free for first 10,000 requests, then pay-as-you-go
- For 1493 stations x 1 query each = 1,493 calls. Well within free tier
- Can request multiple types in one call via `includedTypes: ["night_club", "bar", "karaoke"]`
- `openNow` parameter exists but only checks current time (not useful for batch)
- `currentOpeningHours` field available in response (Pro SKU) - could filter for late-night in post-processing

**Key advantage:** Google has the most comprehensive venue database in Japan. Likely has 10-50x more bars/clubs than OSM. Can differentiate between bar, night_club, karaoke precisely.

**Limitation:** Max 20 results per query (Nearby Search). Need to paginate with `pageToken` for dense areas. Areas with 100+ nightlife venues would need multiple calls.

### 1D. Clubberia (clubberia.com)

**URL:** https://clubberia.com/ja/venues/
**Status:** No API. Web scraping required.

**Structure:**
- Venue listing at `/ja/venues/` with region filter (`?area=tokyo`)
- ~10 venues per page, ~10 pages = ~100 venues nationwide for clubs/electronic music
- Tokyo-specific: estimated 40-60 venues
- Each venue page has: name, area, address, sometimes lat/lng in page metadata
- Venues are exclusively clubs and electronic music spaces (high nightlife signal)

**Assessment:** Small dataset (~50 Tokyo venues) but very high quality signal. Every venue on Clubberia is a genuine nightclub. However, too few venues to generate per-station granularity for 1493 stations. Better used as validation data than primary input.

**Scraping difficulty:** Medium. Standard HTML scraping. No API. Pagination is simple.

### 1E. Resident Advisor (ra.co)

**URL:** https://ra.co/clubs/jp/tokyo
**Status:** No official API. Undocumented GraphQL API exists.

**Data available:**
- Several hundred venues listed for Tokyo
- Alphabetical listing at `/clubs/jp/tokyo`
- Each venue has: name, area/neighborhood, address, events, popularity metrics
- GraphQL API at ra.co (discovered through browser DevTools, used by multiple open-source scrapers)

**Open-source scrapers:**
- https://github.com/djb-gt/resident-advisor-events-scraper (Python, uses GraphQL)
- https://github.com/ujaRHR/resident-advisor-scraper (Python, active)
- Apify actors available for RA scraping

**Assessment:** ~200-300 Tokyo venues. Higher quality than OSM for clubs/DJ bars. GraphQL API is undocumented and may break. Good for club density mapping. Scraping is feasible but RA may block excessive requests.

**Scraping difficulty:** Medium-Hard. GraphQL endpoint not documented. Existing scrapers may need adaptation.

### 1F. iFlyer (iflyer.tv)

**URL:** https://iflyer.tv/en/
**Status:** No API. Venue listing available.

**Structure:**
- Tokyo venue listings accessible via `/en/listing/venues/` paths
- Venue pages at `/en/{venue-slug}/events/`
- Verified venues include: ZEROTOKYO, Contact, V2 Tokyo, Garam, KGR(n), knot, ADM, Web
- Estimated 50-80 Tokyo club venues

**Assessment:** Similar to Clubberia - small high-quality club dataset. Not enough for per-station granularity. Useful for validation.

**Scraping difficulty:** Medium. Standard HTML scraping.

### 1G. Tabelog (tabelog.com)

**URL:** https://tabelog.com/
**Status:** No official API. Third-party scrapers exist.

**Late-night filter:** Tabelog has a 深夜営業 (late-night operation) filter in its search interface. The URL structure supports area/station-based search with feature filters.

**Scraping tools:**
- Apify Tabelog Scraper: https://apify.com/cloud9_ai/tabelog-scraper
- Python wrapper on GitHub: https://github.com/tma15/python-tabelog (supports station-based search)
- Kaggle dataset: https://www.kaggle.com/datasets/utm529fg/tokyo-restaurant-reviews-on-tabelog

**Assessment:** Tabelog has the deepest Japanese restaurant data. A scrape with 深夜営業 filter per station would yield late-night counts that complement HotPepper's `midnight` filter. However, scraping Tabelog at scale (1493 stations) is risky - aggressive anti-bot measures, CAPTCHAs, IP blocking.

**Scraping difficulty:** Hard. Requires headless browser, CAPTCHA solving, residential proxies. High risk of blocking.

### 1H. Yelp Japan / Yelp Fusion API

**URL:** https://www.yelp.com/developers/documentation/v3/business_search
**Status:** API available. Limited Japan coverage.

**Data:**
- Yelp Fusion API: 5,000 calls/day free. Business search supports lat/lng + radius + categories.
- Categories: `bars`, `nightlife`, `karaoke`, `musicvenues` available
- Japan coverage is LIMITED compared to HotPepper/Tabelog. Yelp is not dominant in Japan.
- Search results show listings exist for Tokyo nightlife but are skewed toward tourist-friendly venues

**Assessment:** Low priority. Coverage gap vs. HotPepper/OSM is not worth the integration effort. The 5,000 calls/day free tier is generous but the data wouldn't add much that HP+OSM doesn't already have.

### 1I. Live Music Venue Databases

**Super Nice! Livehouse Database:**
- URL: https://super-nice.net/
- 694 livehouses in Tokyo (2,300 nationwide)
- Organized by ward/area, with capacity data
- No API - would need scraping

**EVECOCO (イベここ):**
- URL: https://evecoco.net/livehouse/
- Comprehensive livehouse listings organized by Tokyo area (Shibuya, Shinjuku, Ikebukuro, etc.)
- Individual venue pages with capacity, address, access directions

**Tokyo Gig Guide:**
- URL: https://www.tokyogigguide.com/en/livehouses
- English-language livehouse database
- Searchable by area

**NAVITIME Livehouse listings:**
- URL: https://www.navitime.co.jp/category/0106009/13/
- Livehouse/club listings with address, maps, phone numbers

**Assessment:** Livehouse data is abundant but scattered across sites with no APIs. Super Nice has the best coverage (694 Tokyo venues). However, livehouse density correlates strongly with general nightlife density, so the incremental value over bar/pub counts is moderate. Worth scraping Super Nice if time permits.

### 1J. Karaoke Chain Store Locators

Major chains and store counts (nationwide):
- **Joysound (JOYSOUND):** 630+ locations nationwide. Store locator at joysound.com
- **Big Echo:** 500+ locations nationwide. Part of Daiichi Kosho group
- **Manekineko (まねきねこ):** 500+ locations. 24-hour operation common
- **Karaoke Kan:** Smaller chain, concentrated in Tokyo

**Assessment:** OSM already has 382 karaoke_box entries in Greater Tokyo. Chain store locators could supplement this but most major locations are already on OSM. Not a priority data source since OSM karaoke_box gives 80%+ coverage.

---

## 2. Test Results

### 2A. Overpass API - Station Comparison (800m radius)

Queried `amenity=bar|pub|nightclub|karaoke_box|music_venue` around key stations:

| Station | bar | pub | nightclub | karaoke_box | music_venue | TOTAL |
|---------|-----|-----|-----------|-------------|-------------|-------|
| **Kabukicho** (35.6938, 139.7035) | 135 | 116 | 12 | 13 | 0 | 276 |
| **Shinjuku** (35.6896, 139.7006) | 133 | 123 | 12 | 13 | 1 | 282 |
| **Shibuya** (35.6580, 139.7016) | 157 | 78 | 21 | 15 | 1 | 272 |
| **Roppongi** (35.6627, 139.7314) | 54 | 27 | 9 | 1 | 0 | 91 |
| **Shimokitazawa** (35.6614, 139.6681) | 26 | 24 | 2 | 0 | 2 | 54 |

**Key observations:**
1. Roppongi scores 91 vs. Shibuya's 272 and Kabukicho's 276. This is the known **Roppongi gap** - Roppongi's nightlife is concentrated in clubs (not izakayas/pubs), and many Roppongi bars may not be on OSM
2. The `nightclub` tag somewhat compensates: Shibuya has 21 nightclubs (highest), Kabukicho/Shinjuku have 12, Roppongi has 9
3. `karaoke_box` is well-distributed: Kabukicho/Shinjuku 13, Shibuya 15, but Roppongi only 1
4. `music_venue` is too sparse to be useful (0-2 per station)
5. Shimokitazawa (known indie/live music hub) scores 54 total, 2 music_venues - reasonable for a smaller district
6. Note: pub counts include some false positives from regex matching "pub" in "public_bath" (3 in Roppongi) - the exact-match query `^(pub)$` should be used in production

### 2B. Greater Tokyo OSM Tag Totals

| Tag | Count | Notes |
|-----|-------|-------|
| `amenity=nightclub` | ~136 | Concentrated in central Tokyo |
| `amenity=karaoke_box` | 382 | Good spread across suburbs |
| `amenity=music_venue` | 14 | Very sparse - livehouses not tagged |
| `tourism=hostel` | 157 | Backpacker corridor proxy |
| `leisure=dance_hall` | <5 | Not useful |

### 2C. HotPepper `midnight` filter (not yet queried)

The `midnight=1` parameter was discovered during this research but has not been tested yet against the API. Expected to return late-night establishment counts that strongly correlate with nightlife quality. This is the single most impactful new data point because:
- Already integrated (just add parameter to existing scraper)
- 100% station coverage
- Specifically captures the "open after 23:00" signal missing from current data

---

## 3. Recommended Formula

### Primary Data Sources (Tier 1 - Use These)

| Source | Field | Weight | Rationale |
|--------|-------|--------|-----------|
| HotPepper API | `midnight_count` (shops open after 23:00) | 0.30 | Direct late-night signal, 100% coverage |
| HotPepper API | `izakaya_count` (existing) | 0.15 | Izakaya density is nightlife proxy |
| HotPepper API | `bar_count` (existing, G002) | 0.10 | Bar density |
| OSM Overpass | `nightlife_count` (bar+pub+nightclub) | 0.20 | Independent venue count, covers non-HP venues |
| OSM Overpass | `karaoke_count` (karaoke_box) | 0.10 | Karaoke is core Tokyo nightlife |
| OSM Overpass | `nightclub_count` (nightclub only) | 0.10 | High-signal club indicator |
| OSM Overpass | `hostel_count` (tourism=hostel) | 0.05 | Backpacker/party area proxy |

### Enhancement Source (Tier 2 - Add If Budget Allows)

| Source | Field | Weight | Rationale |
|--------|-------|--------|-----------|
| Google Places API | `google_nightlife_count` (night_club+bar+karaoke) | bonus | Most comprehensive venue DB. Can validate/supplement OSM |

### Normalization

1. **Log transform** all counts: `score = log2(count + 1)`. Nightlife counts are heavily right-skewed (Kabukicho=276 vs. suburban station=0). Log scale compresses the top end.

2. **Weighted composite:** `raw_score = 0.30*log(midnight+1) + 0.15*log(izakaya+1) + 0.10*log(bar+1) + 0.20*log(nightlife+1) + 0.10*log(karaoke+1) + 0.10*log(nightclub+1) + 0.05*log(hostel+1)`

3. **Percentile mapping to 1-10:** Map composite score to 1-10 using percentile buckets:
   - Stations with zero across ALL nightlife fields: rating = 1
   - 1st-20th percentile (of nonzero): rating = 2
   - 20th-40th: rating = 3
   - 40th-55th: rating = 4
   - 55th-70th: rating = 5
   - 70th-80th: rating = 6
   - 80th-88th: rating = 7
   - 88th-94th: rating = 8
   - 94th-98th: rating = 9
   - Top 2% (Kabukicho, Shibuya, Shinjuku, Roppongi, Ikebukuro): rating = 10

4. **Validation targets:**
   - Roppongi: 10 (must be top tier despite lower bar count)
   - Kabukicho / Shinjuku: 10
   - Shibuya: 10
   - Nakameguro: 7-8 (trendy bars, not massive club scene)
   - Shimokitazawa: 7-8 (live music, indie bars)
   - Golden Gai area: captured by Shinjuku station
   - Typical suburban station: 1-3

### Handling the Roppongi Gap

The `nightclub_count` (weighted 0.10) and `midnight_count` from HotPepper (weighted 0.30) should close the Roppongi gap. Roppongi's clubs and late-night establishments will score high on `midnight_count` even if izakaya count is moderate. The `nightclub` OSM tag (9 in Roppongi) is proportionally very high relative to most stations (median ~0). If Roppongi still doesn't reach 10 after the formula, increase `nightclub_count` weight to 0.15 and reduce `izakaya_count` to 0.10.

---

## 4. Implementation Plan

### Phase 1: HotPepper Midnight Scrape (Highest Impact, Lowest Effort)

- **What:** Add `midnight=1` parameter to existing HP scraper. Re-query all 1493 stations.
- **Effort:** Easy. 1-2 hours. Same API, same code, one new parameter.
- **Rate limiting:** Same as existing (~100 req/min). ~15 min runtime.
- **Expected output:** `midnight_count` column in NocoDB hotpepper table
- **Also:** Query `genre=G002` (ダイニングバー) specifically for dedicated bar count

### Phase 2: OSM Overpass Extended Tags (High Impact, Low Effort)

- **What:** Expand existing Overpass query to include `karaoke_box`, and keep `nightclub` as separate count
- **Query template per station:**
  ```
  [out:json][timeout:30];
  (
    nwr["amenity"~"^(bar|pub|nightclub|karaoke_box)$"](around:800,{lat},{lng});
  );
  out count;
  ```
  Plus separate query for nightclub-only and karaoke-only counts:
  ```
  [out:json][timeout:30];
  nwr["amenity"="nightclub"](around:800,{lat},{lng});
  out count;
  ```
- **Effort:** Easy. Modify existing scraper script. 2-3 hours including hostel query.
- **Rate limiting:** Overpass allows ~10,000 queries/day. 1493 stations x 3 queries = 4,479 queries. Feasible in one day with 5-10s delays.
- **Expected output:** `karaoke_count`, `nightclub_count`, `hostel_count` columns in osm_pois table
- **Runtime:** ~6-8 hours with rate limiting (conservative)

### Phase 3: Google Places API Nightlife Query (Medium Impact, Medium Effort)

- **What:** Query Google Places Nearby Search (New) for `includedTypes: ["night_club", "bar", "karaoke", "live_music_venue"]` per station
- **Effort:** Medium. Need Google Cloud project, API key, billing setup. ~4 hours for implementation.
- **Free tier:** 10,000 Essentials calls/month. 1493 stations = 1,493 calls (well within free tier)
- **Rate limiting:** Generous (no per-second limit, just monthly quota)
- **Expected output:** `google_nightlife_count` per station. Max 20 results per call, but count is what matters.
- **Runtime:** ~30 min (fast API, no throttling needed)
- **Key value:** Google data is the most comprehensive for Japan. Will reveal venues OSM misses (especially bars and karaoke). Particularly strong for validating/filling Roppongi gap.

### Phase 4: Resident Advisor Venue Scrape (Low Impact, Medium Effort)

- **What:** Scrape RA Tokyo venue list (~200-300 venues) with location data. Map to nearest station.
- **Effort:** Medium. Need to reverse-engineer GraphQL API or use existing open-source scraper.
- **Expected output:** Binary flag or count per station: `ra_club_count`. Most stations will be 0, top ~50 stations will have 1-5.
- **Runtime:** ~1 hour
- **Value:** Marginal over OSM nightclub tag. Only do this if Roppongi still underscores after Phase 1-3.

### Phase 5: Livehouse Database Scrape (Low Impact, Medium Effort)

- **What:** Scrape Super Nice livehouse database (694 Tokyo venues), geocode, map to stations
- **Effort:** Medium. HTML scraping + geocoding. ~6 hours.
- **Value:** Fills the `music_venue` gap (only 14 on OSM vs. 694 real livehouses). Helps Shimokitazawa/Koenji/Shimo-Kitazawa score correctly.
- **Recommended only if:** Music venue density is needed as a separate rating component, or if stations known for live music are underscoring.

### NOT Recommended

| Source | Reason |
|--------|--------|
| Tabelog scrape | Too risky (anti-bot), too slow (headless browser), data largely overlaps with HotPepper |
| Clubberia scrape | Too few venues (~50 Tokyo) for per-station granularity |
| iFlyer scrape | Too few venues (~60 Tokyo), overlaps with RA and Clubberia |
| Yelp API | Low Japan coverage, data overlaps with HP and Google |
| Karaoke chain locators | OSM karaoke_box (382) already covers this adequately |

---

## 5. Expected Coverage & Confidence Level

### After Phase 1-2 (Minimum Viable):

| Metric | Value |
|--------|-------|
| Station coverage | 100% (1493/1493) |
| Data sources | 2 (HotPepper + OSM) |
| Unique signals | 7 (midnight_count, izakaya, bar, nightlife, karaoke, nightclub, hostel) |
| Confidence for top nightlife areas | High (Kabukicho, Shibuya, Shinjuku will score 9-10) |
| Confidence for Roppongi | Medium-High (midnight_count should close gap) |
| Confidence for suburban/rural | High (correctly low scores) |
| Roppongi gap risk | Low if midnight_count works as expected |
| Implementation time | ~1 day |

### After Phase 1-3 (Recommended):

| Metric | Value |
|--------|-------|
| Station coverage | 100% |
| Data sources | 3 (HotPepper + OSM + Google Places) |
| Unique signals | 8 (+ google_nightlife_count) |
| Confidence for all areas | High |
| Roppongi gap risk | Very low (Google has comprehensive Roppongi club data) |
| Implementation time | ~2 days |
| Cost | Free (within Google's 10K calls/month free tier) |

### Validation Approach

After computing ratings, validate against known ground truth:
1. **Must be 10:** Kabukicho, Roppongi, Shibuya Center-gai, Shinjuku
2. **Must be 8-9:** Ikebukuro, Ebisu, Nakano, Kichijoji, Ueno
3. **Must be 6-8:** Shimokitazawa, Nakameguro, Sangenjaya, Koenji
4. **Must be 1-3:** Suburban commuter stations (most Saitama/Chiba stations)
5. **Must be 1:** Rural/residential stations with no nightlife

If any of these fail, adjust weights iteratively.

---

## Appendix: Overpass Query Templates

### Main nightlife query (per station):
```
[out:json][timeout:30];
(
  nwr["amenity"~"^(bar|pub|nightclub|karaoke_box)$"](around:800,{lat},{lng});
);
out count;
```

### Nightclub-only count:
```
[out:json][timeout:30];
nwr["amenity"="nightclub"](around:800,{lat},{lng});
out count;
```

### Karaoke-only count:
```
[out:json][timeout:30];
nwr["amenity"="karaoke_box"](around:800,{lat},{lng});
out count;
```

### Hostel count:
```
[out:json][timeout:30];
nwr["tourism"="hostel"](around:800,{lat},{lng});
out count;
```

### HotPepper midnight query:
```
GET http://webservice.recruit.co.jp/hotpepper/gourmet/v1/
  ?key={API_KEY}
  &lat={lat}&lng={lng}
  &range=3
  &midnight=1
  &count=1
  &format=json
```
(Use `count=1` and read `results_available` from response for total count without fetching full results)
