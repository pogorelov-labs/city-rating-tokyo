# Research Prompt: Nightlife Rating

## Context

You are researching data sources for a "nightlife" rating (1-10) for 1493 train stations in Greater Tokyo (Tokyo, Kanagawa, Saitama, Chiba prefectures). The rating should reflect how good the area is for going out at night — bars, izakayas, clubs, live music, late-night food.

## What We Already Have

**HotPepper Gourmet API** (1493 stations, 100% coverage):
- `izakaya_count`: median=9, max=930. 80% stations have at least 1.
- `bar_count`: median=1, max=219. Only 53% nonzero — bars are undercounted.
- HotPepper is a *restaurant reservation platform*. It's strong for izakayas but **doesn't list clubs, live houses, karaoke, or late-night establishments** that don't serve full meals.

**OSM Overpass** (~1000 stations, will be 1493):
- `nightlife_count` (amenity=bar|pub|nightclub): median=5, max=774. 76% nonzero.
- OSM has the `nightclub` tag but very few entries in Japan. Most bars on OSM are tagged as `bar` generically.

**Hostel data** (only 3 test stations):
- Shinjuku=13, Tokyo=7, Yokohama=1 hostels (OSM tourism=hostel|guest_house).
- Hostel density is a reasonable proxy for "backpacker/party area" but needs full scrape.

**Known Problem — Roppongi Gap**:
Roppongi is the #1 club district in Tokyo. AI rating=10 for nightlife. But:
- HP izakaya=130 (rank ~57th — not that high, because Roppongi is clubs, not izakaya)
- HP bar=? (probably higher but bars are 53% coverage)
- We don't capture: clubs, live music venues, late-night karaoke density

## Research Tasks

### 1. Japanese Nightlife Data Sources
Research what data sources exist for Tokyo nightlife beyond restaurants:

a) **Club/event platforms**: Are there APIs or scrapeable sites?
   - Clubberia (clubberia.com) — Japan's main club listing site
   - Resident Advisor (ra.co) — global club/DJ event listings, has Tokyo section
   - iFlyer (iflyer.tv) — Tokyo nightclub events
   - Do any of these have APIs? Can their venue counts be scraped per area/station?

b) **Late-night establishment databases**:
   - Google Maps/Places API — can filter by `opening_hours` to find places open past midnight. Research: is there a free way to query "establishments open at 2am within 800m of lat/lng"?
   - Yelp Japan — does it exist? What's the API situation?
   - Tabelog — has "late night" (深夜営業) filter. Can we get counts?

c) **Karaoke chains**: Karaoke density is a nightlife signal.
   - OSM has `amenity=karaoke_box` — check how many are tagged in Tokyo
   - Major chains: Karaoke Kan, Big Echo, Joysound, Manekineko — do they have store locators?

d) **Live music venues** (ライブハウス):
   - livehouse.com or similar listing sites
   - OSM `amenity=music_venue` — check coverage

### 2. OSM Deep Dive
The Overpass query currently uses `amenity=bar|pub|nightclub`. Research additional OSM tags that capture nightlife:
- `amenity=karaoke_box`
- `amenity=nightclub` (how many in Greater Tokyo?)
- `leisure=dance_hall` (rare?)
- `shop=alcohol` or `shop=wine` (late-night liquor stores as proxy?)
- Bars with `opening_hours` containing times past midnight
- `tourism=hostel|guest_house` (current hostel query — what's the full coverage like?)

Write a test Overpass query for Roppongi (35.6627, 139.7314) and Kabukicho (35.6938, 139.7035) and compare results to validate.

### 3. Google Maps Approach
Research the Google Maps Places API (Nearby Search):
- Can we search for `type=night_club|bar` with a free tier?
- What's the free quota? (probably $200 free credit = ~10000 calls)
- Is there a way to get "open now" filtered results?
- Alternative: Places API (New) has `includedTypes` parameter

### 4. Proposed Formula
Based on research findings, propose:
- Which data sources to use and with what weights
- How to normalize (log scale? raw percentile?)
- How to handle stations with zero nightlife (rural/suburban — should be rating 1-2)
- How to validate against known nightlife hubs: Roppongi, Kabukicho, Shibuya Center-gai, Golden Gai, Nakameguro, Shimokitazawa

### 5. Implementation Estimate
For each proposed data source:
- Scraping difficulty (easy/medium/hard)
- Rate limiting concerns
- Expected runtime for 1493 stations
- Whether it needs headless browser or just HTTP requests

## Output Format

Save findings to `/Users/ruslan/msc_1/git/city-rating/research/01-nightlife.md` with sections:
1. Data Sources Found (with URLs, API docs, coverage assessment)
2. Test Results (actual queries against Roppongi/Kabukicho/Shinjuku)
3. Recommended Formula
4. Implementation Plan (ordered by effort/impact)
5. Expected Coverage & Confidence Level
