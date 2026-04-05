# Research Prompt: Vibe Rating — Keep, Kill, or Reinvent?

## Context

You are deciding what to do with the "vibe" rating (1-10) for 1493 train stations in Greater Tokyo. Vibe is supposed to capture the "atmosphere" or "soul" of a neighborhood — is it trendy, cozy, characterful, boring?

## The Problem

**Vibe has 0% real data.** The current proposal is a composite formula:
```
vibe = cafe_count * 0.3 + convenience_store * 0.2 + green_count * 0.2 + diversity * 0.3
```
This is a dressed-up heuristic. It says "vibe = cafes + shops + parks + variety" which might correlate with vibe but doesn't measure it.

**Why it's hard**: Vibe is subjective. Shimokitazawa has amazing vibe (indie theaters, vintage shops, live houses) while a generic suburban station with similar cafe/green numbers has zero vibe. There's no "vibe API".

**AI-researched override**: 272 stations already have human-assigned vibe ratings with Russian-language descriptions. These are the gold standard but only cover 18% of stations.

## Research Tasks — Three Options

### Option A: Kill Vibe (Remove Category)

Research whether removing vibe simplifies things without losing value:
- Redistribute its 5% weight to other categories
- Users already have 8 other categories with sliders
- Is "vibe" actually a differentiator, or does it track food/nightlife/green anyway?
- Check correlation: among AI-researched stations, how much does vibe correlate with other categories?

### Option B: Keep as AI-only + Zero for Others

- 272 stations keep their human-assigned vibe
- Remaining 1221 stations get vibe=null or vibe=5 (neutral)
- Frontend shows "vibe not rated" for unresearched stations
- Pro: honest, no fake data
- Con: 82% of stations lose a category

### Option C: Find Real Vibe Proxies

Research data sources that correlate with "neighborhood character":

a) **Instagram hashtag density**:
   - Areas with many tagged photos feel "alive" and "instagrammable"
   - Research: Instagram API restrictions, alternative approaches
   - Alternative: Flickr API (we already use Flickr for images) — photo density per area

b) **Google Reviews sentiment**:
   - Average review sentiment for all businesses near a station
   - Research: Google Places API review data availability
   - Could we get "positive adjective frequency" from reviews?

c) **Independent shop ratio**:
   - Areas with unique/indie shops (vintage, gallery, craft) have more vibe than chain-dominated areas
   - OSM `shop=*` with non-chain names? Very hard to distinguish programmatically.
   - Research: is there a database of independent shops in Tokyo?

d) **Cultural venue density**:
   - Theaters, galleries, live houses, bookstores, record shops
   - OSM tags: `amenity=theatre|cinema|arts_centre`, `shop=books|music|art`
   - These differentiate Shimokitazawa (many) from generic Koto-ku station (zero)
   - **Test this with Overpass**: Query cultural venues for known high-vibe stations

e) **Architectural age / character**:
   - Old wooden neighborhoods (Yanaka, Shimokitazawa) have more character
   - Research: is building age data available? 固定資産税 data?

f) **Walkability score**:
   - Walkable neighborhoods feel better. Research:
   - Street intersection density from OSM (more intersections = more walkable grid)
   - Pedestrian street/shopping street density: `highway=pedestrian|living_street`

g) **Event/festival density**:
   - Neighborhoods with festivals and events feel alive
   - Research: is there a Tokyo event calendar API?

### Option D: Hybrid — Composite + Cultural Venues

If cultural venue data from OSM is decent, combine:
```
vibe = cultural_venue_count * 0.4 + cafe_count * 0.2 + walkability * 0.2 + indie_shop_count * 0.2
```
This would at least distinguish Shimokitazawa (theaters, live houses, indie shops) from a suburban nothing-station.

## Key Validation Stations

Any proposed formula must handle:
| Station | Expected Vibe | Character |
|---------|--------------|-----------|
| Kichijoji | 10 | Park, cafes, indie shops, artists |
| Shimokitazawa | 10 | Theaters, vintage, live music, youth |
| Harajuku | 9 | Fashion, street culture, unique |
| Yanaka-Nishi-Nippori | 8 | Old Tokyo, wooden houses, craft shops |
| Nakameguro | 8 | Trendy cafes, river walk, galleries |
| Akihabara | 9 | Unique niche (anime/tech), not generic |
| Tokyo | 6 | Business district, efficient but soulless |
| Shinjuku | 8 | Chaotic, neon, mixed — has character |
| Random Chiba suburban | 3 | Chain stores, nothing distinctive |
| Narita Airport | 2 | Not a neighborhood |

## Decision Framework

For each option (A/B/C/D), evaluate:
1. **Honesty**: Does it avoid presenting fake data as real?
2. **Differentation**: Does it meaningfully separate stations?
3. **Effort**: Implementation cost
4. **Coverage**: How many stations get a real score?

## Output Format

Save findings to `/Users/ruslan/msc_1/git/city-rating/research/06-vibe.md` with sections:
1. Option Analysis (A/B/C/D with pros/cons)
2. Cultural Venue OSM Test (actual Overpass query results)
3. Other Proxy Data Feasibility
4. Recommended Approach
5. Implementation Plan (if keeping)
6. Validation Results
