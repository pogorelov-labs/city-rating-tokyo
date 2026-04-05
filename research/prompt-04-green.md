# Research Prompt: Green/Parks Rating

## Context

You are researching how to improve the "green" rating (1-10) for 1493 train stations in Greater Tokyo. The rating should reflect access to parks, gardens, nature, trees, riverside walks — how green and nature-friendly the neighborhood feels.

## What We Already Have

**OSM Overpass** (~1000 stations, will be 1493):
- `green_count`: leisure=park|garden|nature_reserve within 1000m. Median=22, max=1073. 94% nonzero.
- `green_area_sqm`: **Currently 0 for all stations** — we ran with `--skip-area` flag.

**The Core Problem**:
`green_count` alone is misleading:
- Station near Yoyogi Park (54 hectares, one entry) → green_count maybe 3-5 (the park + a few small gardens)
- Station near 20 tiny pocket parks (each 100sqm) → green_count = 20

Without **area** data, the tiny-parks station rates higher than the Yoyogi Park station. This is wrong. A single huge park is far more valuable for "green" feeling than 20 planters.

## Research Tasks

### 1. Green Area Calculation from OSM

a) **Re-run Overpass with geometry**:
   - Current skipped query fetches `way` and `relation` objects with `out geom` to calculate area
   - Research: What's the most efficient Overpass query to get park **areas** (not just counts)?
   - Option 1: `out geom` → calculate area from polygon coordinates
   - Option 2: Use `[out:csv]` with `area` type for pre-calculated areas
   - Option 3: Use Overpass `is_in` areas

b) **Area calculation method**:
   - For `way` (closed polygon): calculate area from lat/lng coordinates using Shoelace formula
   - For `relation` (multipolygon, like large parks): need to handle outer/inner rings
   - Research: is there a simpler Overpass query that returns area directly? E.g., using `out count` with area filter?

c) **Test query for Yoyogi/Ueno/Shinjuku Gyoen**:
   - Write and test an Overpass query around Harajuku station (35.6702, 139.7027) that returns park areas
   - Validate: Yoyogi Park should show ~540,000 sqm, Meiji Shrine forest ~700,000 sqm

### 2. Additional Green Tags in OSM
Beyond `leisure=park|garden|nature_reserve`, what else captures "green"?

a) **Tree-lined streets**: `natural=tree_row` — research density in Tokyo
b) **Forests/woods**: `natural=wood`, `landuse=forest` — relevant for western Tokyo (Okutama, Takao)
c) **Riverbanks**: `waterway=river` + `leisure=park` combinations. Many Tokyo rivers (Tama, Sumida, Ara) have green walking paths
d) **Cemeteries with green space**: `landuse=cemetery` — Japanese cemeteries like Yanaka often feel like parks
e) **University campuses**: Large campuses (Todai, Waseda) have significant green space — `amenity=university` + green overlay?
f) **Shrine/temple grounds**: Meiji Shrine grounds are essentially a forest. `amenity=place_of_worship` + `leisure=garden`?

### 3. Japan-Specific Green Data

a) **National/Prefectural parks**: Research if there's a GeoJSON of designated parks
b) **Tokyo Metropolitan Parks database**: 東京都公園協会 has a park list — research format
c) **Green coverage ratio** (緑被率): Tokyo publishes ward-level green coverage percentages. Research:
   - Source: 東京都 みどり率調査
   - URL: research Tokyo Metropolitan Government environment data
   - This could directly give a green score per ward

### 4. Satellite/Land Use Data
Research whether satellite-derived vegetation indices are available:
a) **NDVI (Normalized Difference Vegetation Index)**: Measures actual green coverage from satellite
   - Is there a free API? Google Earth Engine? Copernicus?
   - Resolution needed: ~100m to distinguish neighborhoods
b) **Japan land use mesh data**: 国土数値情報 (National Land Numerical Info)
   - https://nlftp.mlit.go.jp/ksj/
   - Has 100m mesh land use classification including "parks/green" category
   - Research: format, download, and how to query by lat/lng

### 5. Proposed Green Score Components
Design a composite:
```
green_score = f(park_area, park_count, green_coverage_ratio, water_proximity)
```

Where:
- `park_area`: Total park sqm within 1km (heavily weighted — one big park > many small ones)
- `park_count`: Number of green spaces (secondary signal)
- `green_coverage_ratio`: Ward-level vegetation percentage (if available)
- `water_proximity`: River/canal within 500m (rivers with walking paths add green feeling)

### 6. Validation Points
- Kichijoji → 10 (Inokashira Park, one of Tokyo's best)
- Yoyogi → 10 (Yoyogi Park 54ha + Meiji Shrine forest)
- Ueno → 9 (Ueno Park 13ha)
- Koganei → 9 (Koganei Park 80ha — biggest in Tokyo)
- Akihabara → 2-3 (concrete electronics district)
- Shibuya → 4-5 (some green near NHK but mostly concrete)
- Ikebukuro → 3-4 (very little green)

## Output Format

Save findings to `/Users/ruslan/msc_1/git/city-rating/research/04-green.md` with sections:
1. Overpass Area Query (tested, working query)
2. Additional Green Tags (which add value, which don't)
3. Government Green Data Sources
4. Recommended Formula (with area weighting)
5. Implementation Plan
6. Validation Against Known Green Stations
