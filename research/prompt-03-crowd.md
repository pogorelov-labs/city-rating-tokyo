# Research Prompt: Crowd Rating

## Context

You are researching data sources for a "crowd" rating (1-10, inverted: less crowded = higher) for 1493 train stations in Greater Tokyo. The rating should reflect how crowded/hectic the area feels day-to-day — packed stations, busy streets, tourist hordes vs quiet residential calm.

## What We Already Have

**Passenger counts** (92 stations, 6% coverage):
- Hardcoded from JR East/Tokyo Metro annual reports
- Range: 15,000 (Hodogaya) to 775,000 (Shinjuku) daily
- Only covers major stations. Missing: all Tobu, Seibu, Keikyu, Keisei, Sotetsu, Yurikamome, monorails, and most Tama/suburban stations

**Current fallback**: `line_count * 15000` — pure heuristic. Shinjuku estimate would be 195k vs real 775k.

**Known Problems**:

1. **94% of stations have NO passenger data** — the fallback dominates, making this not data-driven
2. **Passenger count ≠ area crowdedness**: Shinjuku station has 775k but the *area* around it has different crowdedness depending on exit (west side = office towers, east = Kabukicho). Passenger count measures station throughput, not neighborhood feel.
3. **Tourist crowding not captured**: Asakusa and Harajuku feel extremely crowded due to tourists, not commuters. Neither has high station passenger counts relative to Shinjuku.

## Research Tasks

### 1. Comprehensive Passenger Count Data

a) **Wikipedia scraping** (most promising):
   - Almost every Tokyo station Wikipedia page has a 乗降客数 (daily passengers) table
   - Japanese Wikipedia format: `https://ja.wikipedia.org/wiki/{station_name_jp}駅`
   - Research: Parse the passenger count table from Wikipedia infoboxes
   - Check: `https://ja.wikipedia.org/wiki/渋谷駅` — what format is the data in?
   - This could expand coverage from 92 to 500+ stations

b) **Railway company published data**:
   - JR East: https://www.jreast.co.jp/passenger/ (already captured top stations)
   - Tokyo Metro: https://www.tokyometro.jp/corporate/enterprise/passenger_railway/transportation/
   - Toei (都営): research their published stats
   - Keio: https://www.keio.co.jp/group/traffic/
   - Odakyu: research annual passenger stats
   - Tokyu: research
   - Seibu, Tobu, Keikyu, Keisei, Sotetsu — research each

c) **国土交通省 (MLIT) station statistics**:
   - Ministry of Land publishes station-level passenger data annually
   - Research: https://www.mlit.go.jp/sogoseisaku/transport/
   - Data name: 「駅別乗降客数」or similar

d) **ekidata.jp**: Research whether they have passenger count data (they have station codes and line data)

### 2. Area Crowdedness Proxies (beyond station passengers)

Station passenger count is one signal, but "crowdedness" is about the *neighborhood*:

a) **Foot traffic / mobile data**:
   - Agoop (agoop.co.jp) — sells mobile location data for Japan. Too expensive?
   - NTT Docomo モバイル空間統計 — publishes area population data. Research availability.
   - Yahoo Japan crowdedness API — research if public

b) **POI density as crowd proxy**:
   - We already have: `HP_total_count` (restaurants = foot traffic), `OSM_convenience_store_count`
   - High restaurant + convenience store density = high foot traffic = crowded
   - Formula: `crowd_proxy = HP_total * 0.5 + OSM_convenience * 2 + OSM_food * 0.3`

c) **Google Popular Times**:
   - Google Maps shows "popular times" for places. Research: can this be queried via API?
   - Alternatively: average "popular times" data for several POIs near a station

d) **Instagram/social media post density**:
   - Areas with many Instagram posts (Harajuku, Asakusa) feel crowded due to tourists
   - Research: is there any API or proxy for this? Instagram API is restricted.
   - Alternative: Google Trends location data? Flickr photo density?

e) **Tourist attraction density**:
   - OSM `tourism=attraction|museum|viewpoint` count
   - This would capture Asakusa (Senso-ji), Harajuku (Meiji Shrine), etc.
   - Test Overpass query for tourism tags around known tourist stations

### 3. Temporal Crowdedness
Some stations are only crowded during commute hours (Shimbashi, Tokyo) while others are crowded all day (Shibuya, Harajuku):
- Research: is there any data on peak vs off-peak crowding?
- Train congestion rates (混雑率) are published per line — these show morning rush overcrowding

### 4. Composite Crowd Score
Design a composite that captures different kinds of crowdedness:
- **Station throughput**: passenger_count (commuter crowd)
- **Commercial density**: HP_total + convenience stores (daytime/shopping crowd)
- **Tourist factor**: tourism POI count (tourist crowd)
- **Residential density**: lack of commercial = quiet

### 5. Validation Points
The formula should produce these results:
- Shinjuku → crowd rating 1-2 (busiest station in the world)
- Shibuya → 2-3 (iconic crossing, always packed)
- Harajuku → 2-3 (tourists, even if station isn't massive)
- Asakusa → 3 (tourist temple district)
- Nakameguro → 5-6 (trendy but not overwhelming)
- Kichijoji → 5 (busy but pleasant)
- Sugamo → 6-7 (old people shopping street, calm)
- Todai-mae → 8 (university area, quiet)
- Hodogaya → 9 (suburban, quiet residential)

## Output Format

Save findings to `/Users/ruslan/msc_1/git/city-rating/research/03-crowd.md` with sections:
1. Passenger Data Sources (with URLs, expected coverage expansion)
2. Area Crowdedness Proxies (feasibility, data quality)
3. Tourist Factor Data
4. Recommended Composite Formula
5. Implementation Plan (which sources to scrape first)
6. Validation Against Known Stations
7. Expected Coverage & Confidence Level
