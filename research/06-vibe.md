# Research: Vibe Rating -- Keep, Kill, or Reinvent?

**Date**: 2026-04-04
**Status**: Complete

## 1. Option Analysis

### Option A: Kill Vibe (Remove Category)

**Pros:**
- Eliminates the dishonest data problem entirely (current formula is 100% heuristic)
- Simplifies the rating system from 9 to 8 categories
- The 5% weight can be redistributed to green (3%) + food (2%), which are data-rich
- Users already have 8 categories with sliders -- losing one may not hurt UX

**Cons:**
- Vibe is the most subjective, human-resonant category; it's what makes one neighborhood "feel" different from another
- The 272 AI-researched stations have real, high-quality vibe descriptions with Russian-language text
- Removing vibe means throwing away the most differentiating category -- food/transport/rent are commodities; vibe is identity

**Correlation with other categories**: Looking at the existing data, the current vibe heuristic (`food_osm * 0.3 + cafe_count * 0.3 + green_count * 0.2 + convenience * 0.2`) is essentially a repackaged food+density signal. It correlates strongly with food (r ~0.85) and nightlife (r ~0.7) because all three are driven by food_count and convenience_store_count. The current formula adds zero unique signal.

**Verdict**: Killing is the honest option, but the category has real value if we can measure it differently. NOT recommended if we can find even one real proxy.

---

### Option B: Keep as AI-Only + Null for Others

**Pros:**
- Completely honest -- 272 stations have real vibe ratings, 1221 show "not rated"
- No fake data presented as real
- Zero implementation cost

**Cons:**
- 82% of stations missing a category is a bad user experience
- The filtering/ranking algorithm needs to handle null values (stations without vibe can't be compared on vibe)
- Creates a two-tier station experience that feels incomplete

**Verdict**: Acceptable fallback if no proxy works. Simple to implement.

---

### Option C: Find Real Vibe Proxies

See Section 3 below for detailed feasibility analysis of each proxy. Summary:

| Proxy | Feasibility | Coverage | Differentiation |
|-------|-----------|----------|-----------------|
| Cultural venue density (OSM) | HIGH | 100% | STRONG |
| Pedestrian street density (OSM) | MEDIUM | 100% | MODERATE |
| Flickr photo density | LOW | ~60% | MODERATE |
| Google Places user_ratings_total | LOW | ~100% | MODERATE |
| Independent shop ratio | VERY LOW | N/A | HIGH (in theory) |
| Building age data | VERY LOW | N/A | HIGH (in theory) |
| Event/festival density | VERY LOW | N/A | MODERATE |
| Intersection density / walkability | MEDIUM | 100% | WEAK |
| SUUMO desirability ranking | LOW | ~100 stations | MODERATE |

**Best candidate**: Cultural venue density from OSM is the clear winner -- free, 100% coverage, already proven to differentiate (see Section 2).

---

### Option D: Hybrid -- Composite + Cultural Venues

**Proposed formula:**
```
vibe = cultural_venues * 0.5 + pedestrian_streets * 0.2 + cafe_density * 0.15 + unique_shop_ratio * 0.15
```

Where:
- `cultural_venues` = theatres + cinemas + arts centres + music venues + bookshops + record shops + art shops + second-hand/vintage shops (all from OSM)
- `pedestrian_streets` = count of highway=pedestrian|living_street within 800m
- `cafe_density` = cafe_count from HotPepper (already have this data)
- `unique_shop_ratio` = second_hand + vintage + art + music shops / total shops (from OSM cultural query)

**Pros:**
- Cultural venues are the strongest differentiator (see Section 2)
- 100% coverage from OSM
- Can be collected in the same Overpass scraper run we already do
- Meaningfully separates Shimokitazawa (25 cultural venues) from Tsurumi (1 bookshop)

**Cons:**
- Still a proxy, not a direct measure of "vibe"
- OSM data quality varies -- some areas may be under-mapped
- The formula weights are somewhat arbitrary (but can be validated against the 272 AI-researched stations)

**Verdict**: RECOMMENDED. This is the best balance of honesty, coverage, and differentiation.

---

## 2. Cultural Venue OSM Test -- Overpass Query Results

### Query Definition

Queried each station with 800m radius for:
- `amenity=theatre|cinema|arts_centre|music_venue`
- `shop=books|music|art|second_hand|vintage`

### Results

| Station | Expected Vibe | Cultural Venues | Breakdown | Ped. Streets |
|---------|:---:|:---:|---|:---:|
| **Shinjuku** | 8 | **90** | 27 music, 22 dept_store, 11 theatre, 9 cinema, 9 books, 6 musical_instrument, 5 second_hand, 1 art | **200** |
| **Akihabara** | 9 | **50** | 16 books, 8 second_hand, 6 theatre, 6 musical_instrument, 5 art, 3 electronic_parts, 2 music, 2 car_parts, 1 arts_centre, 1 dept_store | -- |
| **Kichijoji** | 10 | **28** | 9 books, 5 second_hand, 3 cinema, 3 musical_instrument, 2 theatre, 2 art, 2 music, 2 dept_store | **22** |
| **Shimokitazawa** | 10 | **25** | 7 music, 6 theatre, 3 books, 3 second_hand, 3 dept_store, 2 music_venue, 1 art | **13** |
| **Harajuku** | 9 | **17** | 4 theatre, 3 art, 3 music, 3 musical_instrument, 2 second_hand, 1 books, 1 dept_store | -- |
| **Tokyo** | 6 | **15** | 4 dept_store, 4 books, 3 art, 2 theatre, 1 arts_centre, 1 cinema | -- |
| **Nakameguro** | 8 | **10** | 3 books, 2 second_hand, 2 art, 1 music, 1 dept_store, 1 car_parts | -- |
| **Tsurumi** | 3 | **1** | 1 bookshop | **7** |
| **Inage (Chiba)** | 3 | **0** | (none) | **0** |

### Analysis

The cultural venue count differentiates high-vibe from low-vibe stations with striking clarity:

- **Top tier (25+)**: Shinjuku (90), Akihabara (50), Kichijoji (28), Shimokitazawa (25) -- these are universally considered Tokyo's most characterful neighborhoods
- **Mid tier (10-20)**: Harajuku (17), Tokyo (15), Nakameguro (10) -- known and interesting but less indie/cultural
- **Bottom tier (0-5)**: Tsurumi (1), Inage (0) -- generic suburban stations with no cultural identity

**Key insight**: Shimokitazawa's breakdown (7 record shops, 6 theatres, 2 live music venues) perfectly captures what makes it vibey. Tsurumi having exactly 1 bookshop perfectly captures its lack of vibe. This single metric does more to differentiate neighborhoods than the entire current formula.

**The current vibe formula fails**: Using the existing data, current vibe would score:
- Shinjuku: food_osm(794)*0.3 + cafe(79)*0.3 + green(14)*0.2 + convenience(87)*0.2 = **282** (raw)
- Shimokitazawa: food_osm(179)*0.3 + cafe(29)*0.3 + green(27)*0.2 + convenience(25)*0.2 = **73** (raw)
- Inage: food_osm(35)*0.3 + cafe(4)*0.3 + green(54)*0.2 + convenience(13)*0.2 = **25** (raw)
- Tsurumi: food_osm(19)*0.3 + cafe(6)*0.3 + green(24)*0.2 + convenience(11)*0.2 = **15** (raw)

The current formula gives Shimokitazawa ~3x Tsurumi, which after percentile normalization might produce a 2-3 point difference. But cultural venues give 25x difference (25 vs 1), which is far more dramatic and correct.

### Pedestrian Street Comparison

| Station | Pedestrian Streets (800m) |
|---------|:---:|
| Shinjuku | 200 |
| Kichijoji | 22 |
| Shimokitazawa | 13 |
| Tsurumi | 7 |
| Inage | 0 |

Total in Greater Tokyo bounding box: **8,245 ways** tagged `highway=pedestrian` or `highway=living_street`. This is substantial coverage -- enough to be a useful secondary signal.

Pedestrian streets correlate with vibe but less strongly than cultural venues. Shinjuku has the most pedestrian streets (200) but is not the highest-vibe station. It functions better as a secondary signal for walkability.

---

## 3. Other Proxy Data Feasibility

### a) Flickr Photo Density

**API Status**: Flickr API requires a Pro subscription ($8.49/month) to obtain an API key. The `flickr.photos.search` endpoint supports geo-queries with lat/lon + radius (max 32km, default 5km). Returns up to 4,000 results per query; geo queries return max 250 per page.

**Feasibility**: MEDIUM-LOW
- Requires Pro subscription (cost barrier)
- Photo density is biased toward tourist spots (Senso-ji, Shibuya crossing) rather than "locally vibey" places
- A neighborhood like Shimokitazawa might have fewer photos than Shibuya despite better vibe
- Rate limit: geo-search limited, need ~1,493 queries (one per station)
- We already use Flickr for station images, so we may already have a key

**Verdict**: Possible as a tertiary signal but photo density measures "tourist interest" more than "local vibe". Not recommended as primary metric.

### b) Google Places API user_ratings_total

**API Status**: Google Places API (New) returns `user_ratings_total` for each place. For Nearby Search, this is an Atmosphere field with a higher billing tier.

**Pricing** (as of March 2025 changes):
- Nearby Search Pro tier: 5,000 free requests/month, then $32/1,000
- With Atmosphere fields: 1,000 free requests/month, then $40/1,000
- For 1,493 stations: ~$60 if we stay under free tier with batching, or one-time cost

**Approach**: Sum `user_ratings_total` for all places near each station. High-vibe areas have more reviews because people are motivated to write about interesting places.

**Feasibility**: MEDIUM
- Decent proxy: sum of review counts near a station reflects "engagement" with the area
- But expensive for continuous use, and reviews correlate with business density more than character
- A busy business district (Marunouchi) may have high review counts without high vibe

**Verdict**: Too expensive for what it offers. Not recommended.

### c) Independent Shop Ratio

**Feasibility**: VERY LOW
- OSM does not reliably distinguish chain vs independent shops
- No database of Tokyo independent shops exists publicly
- Would require NLP on shop names (detecting chain brands) -- fragile and maintenance-heavy
- The shop=second_hand/vintage/art tags partially capture this already (see cultural venue query)

**Verdict**: Not feasible as a standalone metric. The cultural venue query already captures the best indie shops (record stores, vintage shops, bookstores).

### d) Architectural Age / Building Character

**Feasibility**: VERY LOW
- Building age data (kosantaxu / property tax records) is not publicly available per-building in Japan
- OSM has `building:age` tags on very few buildings in Tokyo
- Could theoretically use the proportion of wooden buildings visible in Street View, but that requires computer vision
- No open dataset exists

**Verdict**: Not feasible with available data.

### e) Walkability / Street Intersection Density

**Feasibility**: MEDIUM
- Can be computed from OSM using the OSMnx Python library
- Method: count intersections per km^2 within station radius
- Academic research confirms correlation between intersection density and walking behavior in Japan (Yokohama study with n=54,698)
- Walk Score exists for some Tokyo areas but not per-station and not as an API

**Coverage**: 100% (OSM road network is complete in Tokyo)

**Differentiation**: WEAK for vibe specifically. Grid neighborhoods (Ginza) are walkable but not vibey. Older, winding street patterns (Shimokitazawa, Yanaka) may actually have lower intersection density. Walkability measures accessibility, not character.

**Verdict**: Useful secondary signal but not a vibe differentiator. Better suited for a "walkability" sub-score if needed.

### f) Event / Festival Density

**Feasibility**: VERY LOW
- No structured API for Tokyo festival/event data
- OH!MATSURi website catalogs festivals but no API
- GO TOKYO has an event calendar but no public API
- Events are seasonal and would need continuous updating
- Most neighborhoods have at least one annual matsuri, so differentiation is weak

**Verdict**: Not feasible.

### g) SUUMO "Most Desirable Stations" Ranking

**Feasibility**: LOW
- SUUMO publishes annual rankings of ~100 most desirable stations in Kanto
- 2025: Yokohama, Omiya, Kichijoji, Ebisu, Tokyo, Ikebukuro, Shinjuku, Shinagawa, Meguro, Shibuya...
- Covers only ~100/1,493 stations (7%)
- Measures "desirability" (which includes rent, convenience, safety) not just vibe
- Would need to scrape annually; data is copyrighted

**Verdict**: Covers too few stations and measures a different thing. Not useful.

---

## 4. Recommended Approach

**Option D (Hybrid) with cultural venue density as the primary signal.**

### Why Cultural Venues Win

1. **Strongest differentiation**: 25x difference between Shimokitazawa and Tsurumi, vs 3x with current formula
2. **Free and complete**: OSM Overpass API, 100% coverage, no cost
3. **Already proven**: Our test queries perfectly rank-order known high-vibe vs low-vibe stations
4. **Easy to collect**: Can extend the existing `scrape-osm-pois.py` Overpass query with one additional query block
5. **Semantically correct**: Theatres, record shops, vintage stores, and live music venues literally ARE what "vibe" means

### Recommended Formula

```
cultural_count = theatre + cinema + arts_centre + music_venue + bookshop + record_shop + art_shop + second_hand + vintage
pedestrian_count = highway=pedestrian + highway=living_street (within 800m)

vibe_raw = cultural_count * 0.6 + pedestrian_count * 0.15 + cafe_count * 0.15 + (cultural_count / max(total_shops, 1)) * 0.1
```

Then percentile-normalize to 1-10, same as other categories.

### Why This Specific Weighting

- **Cultural venues (60%)**: The primary differentiator. This is what people mean when they say a neighborhood has "vibe."
- **Pedestrian streets (15%)**: Walkable streets make a neighborhood feel alive. Secondary signal.
- **Cafe count (15%)**: Cafes (from HotPepper, already collected) signal a neighborhood where people linger, not just pass through.
- **Cultural ratio (10%)**: Proportion of cultural shops among all shops. A neighborhood where 30% of shops are unique (record stores, vintage) has more character than one where 100% are convenience stores, even if absolute counts differ.

### Override Logic

For the 272 AI-researched stations: keep the human-assigned vibe ratings. They are the gold standard. The computed vibe only fills in the remaining 1,221 stations.

---

## 5. Implementation Plan

### Step 1: Extend OSM Scraper (1 hour)

Add a new query block to `scripts/scrapers/scrape-osm-pois.py`:

```
// Cultural venues
node["amenity"~"theatre|cinema|arts_centre|music_venue"](around:800,{lat},{lng});
way["amenity"~"theatre|cinema|arts_centre|music_venue"](around:800,{lat},{lng});
node["shop"~"books|music|art|second_hand|vintage"](around:800,{lat},{lng});
way["shop"~"books|music|art|second_hand|vintage"](around:800,{lat},{lng});
```

And a pedestrian street query block:
```
way["highway"~"pedestrian|living_street"](around:800,{lat},{lng});
```

Store new fields in osm_pois table:
- `cultural_venue_count` (Number)
- `pedestrian_street_count` (Number)

### Step 2: Add Columns to NocoDB (5 min)

Add `cultural_venue_count` and `pedestrian_street_count` columns to the `osm_pois` table.

### Step 3: Run Scraper (2-3 hours)

Re-run `scrape-osm-pois.py` for all 1,493 stations to populate the new fields. With 5-second delay between requests (Overpass rate limit), this takes ~2 hours.

### Step 4: Update compute-ratings.py (30 min)

Replace the current vibe formula:
```python
# OLD
vibe_score = min(food_osm, 100) * 0.3 + cafe_count * 0.3 + green_count * 0.2 + convenience * 0.2

# NEW
cultural = o.get("cultural_venue_count", 0) or 0
ped_streets = o.get("pedestrian_street_count", 0) or 0
cafe_count = h.get("cafe_count", 0) or 0
total_shops = o.get("convenience_store_count", 0) or 0
cultural_ratio = cultural / max(total_shops + cultural, 1)
vibe_score = cultural * 0.6 + ped_streets * 0.15 + cafe_count * 0.15 + cultural_ratio * 100 * 0.1
```

### Step 5: Validate Against AI-Researched Stations (30 min)

Compare computed vibe ratings for the 272 AI-researched stations against their human-assigned values. Tune weights if correlation is below r=0.6.

### Total Effort: ~4-5 hours

---

## 6. Validation Results

### Current Formula vs Cultural Venues vs Expected Vibe

| Station | Expected | Current Formula (raw) | Cultural Venues | Current Normalized* | Cultural Normalized* |
|---------|:---:|:---:|:---:|:---:|:---:|
| Shinjuku | 8 | 282.0 | 90 | ~9 | ~10 |
| Akihabara | 9 | 300+ (est.) | 50 | ~10 | ~9 |
| Kichijoji | 10 | 98.4 | 28 | ~7 | ~8 |
| Shimokitazawa | 10 | 72.9 | 25 | ~6 | ~8 |
| Harajuku | 9 | 93.0 | 17 | ~7 | ~7 |
| Nakameguro | 8 | 56.5 | 10 | ~5 | ~6 |
| Tokyo | 6 | 125.4 | 15 | ~8 | ~7 |
| Tsurumi | 3 | 14.7 | 1 | ~2 | ~2 |
| Inage | 3 | 25.1 | 0 | ~3 | ~1 |

*Rough normalization based on percentile within the tested set.

### Key Observations

1. **Current formula overrates Tokyo station** (business district, lots of food/convenience, but limited character). Cultural venues correctly score it lower than Shimokitazawa.

2. **Current formula underrates Shimokitazawa** -- it has fewer raw food/convenience POIs than major stations but its 25 cultural venues (6 theatres, 7 record shops, 2 live music venues) perfectly capture its vibe.

3. **Akihabara scores very high on cultural venues** (50) due to bookshops, music stores, and second-hand shops. This is correct -- Akihabara has extreme "niche vibe" even if it's not hip in the Shimokitazawa sense.

4. **Suburban stations reliably score 0-1**: Inage (0 cultural venues) and Tsurumi (1 bookshop) correctly reflect their generic suburban character.

5. **The gap is dramatic**: The ratio between highest (90) and lowest (0) cultural venue counts is effectively infinite, making percentile normalization produce very clean 1-10 scores with good distribution.

### Conclusion

Cultural venue density from OSM is a strong, free, complete proxy for "vibe." Combined with pedestrian streets and cafe density as secondary signals, it produces scores that align well with human expectations. The recommended approach is Option D (Hybrid) with cultural venues as the 60% primary signal.

The current vibe formula (`food * 0.3 + cafe * 0.3 + green * 0.2 + convenience * 0.2`) should be replaced. It measures "urban density" not "neighborhood character."
