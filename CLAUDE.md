# City Rating Tokyo — Dev Guide

## Project Overview

Interactive map of Greater Tokyo (1493 stations) with data-driven neighborhood ratings across **10 categories**. Users set **hard dealbreaker filters** (max rent, max commute, per-category minimums) and **soft weight preferences** (food, nightlife, transport, rent, safety, green, gym, vibe, crowd, daily_essentials) independently. **Three languages:** EN/JA/RU via next-intl v4.

**Live**: https://city-rating.pogorelov.dev
**Stack**: Next.js 16 (App Router, Turbopack) + React 19 + Tailwind 4 + Leaflet + recharts + zustand + next-intl v4 (EN/JA/RU). Static JSON data, no DB at runtime.
**Deploy**: Coolify on VPS (217.196.61.98), GitHub App auto-deploy from `main`.

## Architecture

```
data/stations.json (1493 stations: slug, lat, lng, lines, line_count, prefecture)
     ↓
scripts/scrapers/ → NocoDB (nocodb.pogorelov.dev, base: city-rating-db)
     ↓
scripts/compute-ratings.py → NocoDB computed_ratings table
     ↓
scripts/export-ratings.py → app/src/data/demo-ratings.ts
     ↓
app/src/lib/data.ts merges: stations.json + demo-ratings.ts + rent-averages.json
```

## Data readiness & coverage honesty (maintainers)

Do **not** equate “every station has a number” with “every number is equally grounded.” This section is the project’s **anti–false-precision** memory.

1. **“100%” / full rows:** Often means **all 1493 slugs participate** in normalization, not that each category uses the same spatial granularity or primary data quality everywhere (Tokyo safety polygons vs ward/prefecture outside Tokyo; rent Suumo vs ward vs regression).
2. **Rent:** Real Suumo-backed station averages cover a **minority** of slugs (`rent-averages.json` + merge rules); most stations use ward average or distance regression — see `confidence.rent` in exported metadata and `research/05-rent.md`.
3. **Safety:** Keishicho ArcGIS is **neighborhood-level** for Tokyo; other prefectures may be **municipality/ward** or legacy tables until **CRTKY-82** lands — see `research/02-safety.md`.
4. **Green / vibe:** OSM signals can exist while **pipeline `confidence` still shows no `strong`** for that category (check `research/00-overview.md` snapshot counts) — strong/moderate/estimate reflect **source rules in compute**, not “map looks green.”
5. **`transit_minutes` estimates (CRTKY-81):** `scripts/compute-transit-times.py` generates per-station travel times using geographic distance + line connectivity, calibrated against 252 AI-researched ground-truth values (MAE 5.5 min, 85% within 10 min). AI-researched entries keep hand-authored times. Computed entries use the calibrated model. Output in `data/transit-times.json`, consumed by `export-ratings.py`. **Upgrade path:** replace with GTFS+RAPTOR (TokyoGTFS) for timetable-based routing.
6. **Missing confidence keys in export:** `export-ratings.py` defaults absent per-category keys to **`estimate`** when building TS — verify NocoDB JSON is complete if counts look wrong.
7. **AI-researched slugs (~252):** Integer ratings and `description` are editorial. Since **CRTKY-83**, `export-ratings.py` merges per-category confidence via comparison: matching categories inherit computed metadata, differing ones get `editorial` level. See NocoDB section for full merge policy.
8. **HotPepper API** is a **single-vendor** dependency for food/nightlife signals; no automated fallback is implemented.
9. **Last train times (CRTKY-115):** Sourced from [mini-tokyo-3d](https://github.com/nagix/mini-tokyo-3d) (MIT). Computed as `MAX(departure)` per station per day type via coordinate matching (200m) → 1483/1493 coverage (99.3%). Caveats: (a) Sat/Sun/Holiday combined in source (no separate Sunday breakdown), (b) post-midnight times show as 00:xx with no 24:00+ convention, (c) arrival-only terminal stops excluded (not boardable), (d) refresh by re-running `scrape-last-trains.py` against current MT3D master — no auto-refresh. 10 stations uncovered (Hakone cable car, Toden Arakawa tram, a few edge stations with coordinate collisions).
10. **Live camera streams (CRTKY-116):** Follow-up to CRTKY-115 from same MT3D ecosystem. Source: [`nagix/mt3d-plugin-livecam`](https://github.com/nagix/mt3d-plugin-livecam) endpoint `https://mini-tokyo.appspot.com/livecam` — 64 YouTube channel-live feeds today (set fluctuates), geotagged `[lng,lat]`, MIT plugin code (streams are 3rd-party YouTube). Match radius **300m** → **29 stations / 32 camera rows** matched today (sparse, hub-concentrated — shibuya, tokyo, akihabara, shinjukunishiguchi-has-3, etc.). Streams themselves belong to third-party YouTube channels (NOT MT3D) — embed only, attribute MT3D in footer. Refresh manually via `python scripts/scrapers/scrape-livecams.py` (not in `refresh-ratings.sh`; livecam data is independent of rating pipeline). **API returns no thumbnails or video IDs** — channel-live URLs resolve at view time to whatever is live, or YouTube's own offline placeholder. No auto-monitoring of dead channels yet; consider a `check-livecams.py` if feed rot becomes common.

**Docs to keep aligned:** `research/VISION.md` (Layer 1 + backlog tables), `research/00-overview.md`, this file, **Plane CRTKY-80** subtree (81–84) and **CRTKY-116** subtree (117–119, livecams).

## Data Pipeline

### NocoDB Tables (city-rating-db, base ID: ph4flgay4kmcgk4)

| Table | ID | Records | Source |
|-------|----|---------|--------|
| osm_pois | mnnuqtldvt4jxlj | 1398 | Overpass API (food, nightlife, green count, gym, convenience) |
| hotpepper | mfk9j2qoj2bkeoo | 1493 | HotPepper Gourmet API (+ midnight_count, dining_bar_count) |
| osm_extended | mrpqu8o796e6xzk | 1467 | Overpass (karaoke, nightclub, cultural venues, pedestrian streets, hostels) |
| station_crime | mxwixub7d0q5i00 | 615 | Keishicho ArcGIS FeatureServer (Tokyo neighborhood-level) |
| crime_stats | mxitpnomlom3j3q | 91 | Hardcoded ward-level (legacy fallback for non-Tokyo) |
| passenger_counts | m36bbxcv8t0asur | 1409 | MLIT S12 GeoJSON (94% coverage, was 6%) |
| station_wards | m74rdmspn3trrqc | 1493 | Nominatim reverse geocoding |
| hostels | ms9awzjv9j6suh7 | 3 | Overpass (test only — superseded by osm_extended.hostel_count) |
| computed_ratings | mkp046vo42kj55w | 1493 | Output of compute-ratings.py (includes confidence/sources/data_date columns) |
| osm_livability | m3vasnsm4y09xez | 1493 | Overpass (supermarket, pharmacy, clinic, school, kindergarten, post_office, bank, laundry, dentist) |
| station_elevation | mkrugzx8z62hli4 | 1493 | Open-Elevation API bulk POST. Range: -2m to 741m, avg 43m |
| station_seismic | mhtnqvmi1kwbth9 | 1493 | J-SHIS Y2024 probabilistic seismic hazard (prob_i60_30yr, prob_i55_30yr, intensity, ground velocity) |
| feedback | mwuwwlko3278wrk | — | User feedback from site |

### Local JSON data files (non-NocoDB)

| File | Records | Source | Purpose |
|------|---------|--------|---------|
| `app/src/data/stations.json` | 1493 | ekidata | Master station list (slug, name_en, name_jp, lines[], lat/lng, prefecture). Mirrored to `data/stations.json` for scripts. |
| `app/src/data/line-names.json` | 127 | ekidata lookup | `{line_id: {name_ja, name_en, operator_ja, operator_en, color, type}}` — PR #90 |
| `app/src/data/ward-data.json` | 1493 | NocoDB export | `{slug: {city_name, ward_name, prefecture_name}}` for station detail page — PR #90 |
| `app/src/data/last-trains.json` | 1483 | mini-tokyo-3d | `{slug: {weekday, holiday, sources, data_date}}` — PR #93 |
| `app/src/data/rent-averages.json` | 1100 | Suumo + e-Stat | 274 real Suumo listings + 826 e-Stat govt averages — PR #91 |
| `app/src/data/environment-data.json` | 1493 | station_elevation + station_seismic | Derived: `{elevation_m, elevation_tier, seismic_prob_i60, seismic_risk_tier}` |
| `app/src/data/station-thumbnails.json` | 1155 | VPS-generated | 320px thumb URL + LQIP base64 per station |
| `app/src/data/station-images-all.json` | 1155 | Wikimedia + Unsplash | Gallery full-res images |
| `app/src/data/station-places.json` | 273 | curated | Nearby places for station detail |
| `app/src/data/slug-redirects.json` | 334 | CRTKY-113 | `{old_wapuro_slug: new_hepburn_slug}` for 301 redirects + data key renames |
| `data/transit-times.json` | 1493 | `compute-transit-times.py` | Per-station transit times to 5 hubs |
| `data/station-datamart.json` | 1493 | `build-datamart.py` (gitignored, 15 MB) | Joined JSON of all signals for CRTKY-109 LLM pipeline |

**Important:** When renaming slugs, update **every** file keyed by slug using `slug-redirects.json`. See memory `feedback_rename_data_sync.md`.

`computed_ratings` has 3 metadata columns alongside the 10 rating numbers:
- `confidence` (LongText) — JSON: `{"food":"strong","vibe":"estimate",...}`
- `sources` (LongText) — JSON: `{"food":["hotpepper","osm"],...}`
- `data_date` (SingleLineText) — e.g. `2026-04`

These feed the `ConfidenceBadge` UI component. NocoDB API token is data-only — schema changes (new columns) must be done manually in the NocoDB UI.

**AI-researched stations — confidence merge policy (CRTKY-83):** ~252 slugs in `demo-ratings.ts` have `description` (and integer ratings) from human researchers. Since CRTKY-83, `export-ratings.py` merges confidence metadata for these entries using a per-category comparison:

- **Category rating matches computed** → inherits pipeline `confidence` + `sources` (data backs the researcher's judgment). E.g. Gakugei-Daigaku food:8 matches computed → `strong` with `['hotpepper','osm']`.
- **Category rating differs from computed** → `editorial` level, sources `['ai_research']` (human chose a different value than data alone suggests). E.g. Mitaka food:7 differs from computed → `editorial`.
- **No computed data for slug** → all categories get `editorial`.

The `editorial` confidence level is distinct from `estimate` (formula/proxy). UI label: **”Curated”** with 藤色 fuji-iro (`#8B6DB0`) dot. Types: `ConfidenceLevel = 'strong' | 'moderate' | 'estimate' | 'editorial'`. All 252 AI-researched stations now show confidence dots and the chip legend.

### NocoDB Access
```
URL: https://nocodb.pogorelov.dev
Token: 3hUf86bwbyw-OSJTlNwGOc1w8AcwrrgAkOuyIaTt
API: /api/v2/tables/{TABLE_ID}/records
```

### HotPepper API
```
Key: b20f206ef29b9f48 (also in Coolify env vars)
Docs: https://webservice.recruit.co.jp/doc/hotpepper/reference.html
Important param: midnight=1 (returns places open after 23:00)
```

## Rating Formulas (v3, absolute caps + rent regression)

All categories use **log-then-percentile** normalization across 1493 stations, then pass through **absolute caps** that gate the 8/9/10 tiers by raw value. The cap only decreases ratings, never increases.

### Absolute caps (`ABSOLUTE_CAPS` in `scripts/compute-ratings.py`)

| Category | Raw signal | 8 requires | 9 requires | 10 requires |
|---|---|---|---|---|
| transport | line_count | ≥2 | ≥3 | **≥5** |
| rent | source quality (2=suumo, 1=ward, 0=regression) | — | ≥1 | ≥2 |
| food | hp_total + osm_food | ≥100 | ≥400 | ≥1000 |
| green | green_count | ≥25 | ≥50 | ≥80 |
| gym_sports | gym_count | ≥7 | ≥12 | ≥20 |
| vibe | cultural_venue_count | ≥8 | ≥20 | ≥50 |
| nightlife | hp_midnight | ≥20 | ≥100 | ≥300 |

Effect: "10" means something specific and explainable. Before v3, top 5.6% of every category (~83 stations) auto-rounded to 10. After v3, top-10 count dropped to 15–64 per category (5 for rent).

Categories listed in **life-first UI order** (transport → rent → essentials → safety → food → green → gym → vibe → nightlife → crowd):

### transport (18% default weight)
```
raw = line_count * 2 + log(1 + daily_passengers) * 0.5
```
Sources: station line_count (100%), MLIT S12 passengers (94%).

### rent (18%, inverted: cheaper = higher)
```
raw = suumo_1k                                             # real (273 stations)
    || ward_average                                         # Nominatim-matched (713 more)
    || exp(12.394 - 0.02453 * distance_km)                  # log-linear regression (rest)
rating = round(10 - 9 * (raw - 80000) / (300000 - 80000))   # linear, floor ¥80k
```
Source-quality cap ensures only Suumo-backed stations can surface as rating 10; ward caps at 9; regression caps at 8. `RENT_FLOOR = ¥80k` is synced between backend `compute-ratings.py` and frontend `app/src/lib/scoring.ts`.

### daily_essentials (14%)
```
raw = log(1 + supermarket) * 0.25 + log(1 + pharmacy) * 0.15
    + log(1 + clinic + dentist) * 0.20 + log(1 + bank) * 0.10
    + log(1 + laundry) * 0.10 + log(1 + post_office) * 0.05
    + log(1 + school + kindergarten) * 0.15
```
Sources: OSM osm_livability table (1493/1493 stations, 9 subcategories). Fallback: convenience_store_count proxy.

### safety (10%, inverted: safer = higher)
```
weighted_crimes = violent*3 + assault*2 + burglary*2 + purse_snatch*2
                + pickpocket*1.5 + bike_theft*0.3 + fraud*0.2
rate = weighted_crimes / adjusted_population * 10000
```
Sources: Keishicho ArcGIS neighborhood polygons (Tokyo, 615 stations), prefectural police (others). Daytime population adjustment for commercial wards (Chiyoda ÷12, Chuo ÷4, Minato ÷3.6).

### food (12%)
```
raw = log(1 + HP_total) * 0.6 + log(1 + OSM_food) * 0.4
```
Sources: HotPepper total_count (100%), OSM food_count (94%). Correlation r=0.855.

### green (8%)
```
raw = log(1 + green_area_sqm) * 0.55 + green_count * 0.25
    + large_park_bonus * 0.1 + water_proximity * 0.1
```
Sources: OSM leisure=park|garden|nature_reserve + landuse=religious|forest + natural=wood. Area calculation from polygon geometry.

### gym_sports (4%)
```
raw = OSM gym_count
```
Sources: OSM leisure=fitness_centre|sports_centre|swimming_pool.

### vibe (4%)
```
raw = log(1 + cultural_venues) * 0.6 + log(1 + pedestrian_streets) * 0.15
    + log(1 + cafe_count) * 0.15 + cultural_shop_ratio * 0.1
```
Sources: OSM theatre|cinema|arts_centre + shop=books|music|art|vintage; pedestrian streets. AI-researched override for 272 stations.

### nightlife (8%)
```
raw = log(1 + HP_midnight) * 0.25 + log(1 + HP_izak) * 0.2
    + log(1 + HP_bar*3) * 0.15 + log(1 + OSM_night) * 0.2
    + log(1 + karaoke*5) * 0.1 + log(1 + hostel*10) * 0.1
```
Sources: HP midnight_count, izakaya_count, bar_count; OSM nightlife + karaoke; hostel count.

### crowd (4%, inverted: fewer = higher)
```
raw = daily_passengers (MLIT/hardcoded) || HP_total * 300 + line_count * 10000
```
Sources: MLIT S12 (94%), HotPepper total as fallback.

## Override Hierarchy
1. **AI-researched** (272 stations with `description` field in demo-ratings.ts) — never overwritten
2. **Computed data-driven** — from NocoDB pipeline
3. **Heuristic fallback** — only where real data unavailable

## Color System (akane↔kon diverging palette)

Five traditional Japanese pigments on a diverging scale, used in two ways:

| Pigment | Hex | Role in composite (map, ranked list) | Role in per-category bar (station card) |
|---|---|---|---|
| 茜 akane | `#8C2926` | `score ≤ p5` (strongly below) | `value − median ≤ −4` |
| 珊瑚 sango | `#B3574E` | `p5 .. p50` | `−4 .. −2` |
| 生成り kinari | `#D9C9A8` | `p50` (neutral pivot) | `deviation = 0` |
| 浅葱 asagi | `#6A8999` | `p50 .. p95` | `+2 .. +4` |
| 紺 kon | `#2C4A5F` | `score ≥ p95` (strongly above) | `deviation ≥ +4` |

**Key insight:** the bar color encodes *deviation from the Tokyo median for that category*, NOT raw value. A long bar does not mean a blue bar — e.g. Affordability `8 / 10` when `CITY_MEDIANS.rent = 8` paints kinari cream, not blue, because the station is exactly average for rent.

**Data-quality icons (separate channel):** per-category confidence uses "Data Depth" SVG icons (`ConfidenceIcon` in `ConfidenceBadge.tsx`) where **shape encodes level** (readable without color). Muted Japanese pigments from `CONFIDENCE_DOT_COLORS` add a second redundant channel:

| UI label | Level key | Shape | Pigment | Hex |
|---|---|---|---|---|
| Measured | `strong` | ◉ bullseye (dot + ring) | 苔色 koke-iro | `#6A8059` |
| Partial | `moderate` | ● solid circle | 山吹 yamabuki | `#C9A227` |
| Estimate | `estimate` | ○ dashed circle | 鈍色 nibi-iro | `#828A8C` |
| Curated | `editorial` | ◆ diamond (菱形 hishigata) | 藤色 fuji-iro | `#8B6DB0` |

### Why two APIs

- **`compositeToColor(score, anchors)`** — map markers and ranked list. Uses `computeCompositeAnchors(stations, weights)` to percentile-stretch across the current weighted distribution (`p5 / p50 / p95`). This is recomputed as the user drags weight sliders so the palette always spans the actual data range. Homepage call sites defer it via `useDeferredValue` to keep INP low.
- **`categoryDeviationColor(value, median)`** — per-category bars on the station detail page. Uses the hardcoded `CITY_MEDIANS` constant — no sort needed, no weights needed. Deviation maps linearly from `[−5, +5]` onto the 5 palette stops.

`pigmentName(deviation)` returns `{ jp, en, tone }` for microcopy on the bar hover tooltip ("Painted in 浅葱 asagi (pale blue-green)").

### Color literacy affordances (CRTKY-68)

The station Ratings card teaches the "deviation, not value" rule through five visual affordances, no words required:

1. **Median tick** — 1 px `slate-300` hairline at `median * 10%` on every bar (Tufte reference line)
2. **Two-tone empty track** — warm `#F5F1EC` cream left of median, cool `#EFF2F4` slate right
3. **Direction arrow** — `↑ / ↓ / −` after the value in the bar color at 65 % opacity
4. **Confidence shape icons** — `ConfidenceIcon` SVG: bullseye (Measured) / solid circle (Partial) / dashed circle (Estimate) / diamond (Curated). Shape encodes level; color (koke-iro / yamabuki / nibi-iro / fuji-iro) adds redundant channel
5. **Optional `?` on `Tooltip`** — default is a plain `text-gray-300` `?` (no grey pill) when `showHelpIcon` is true. On `/station/[slug]` Ratings, category labels use `showHelpIcon={false}` and `cursor-help` on the text so hover opens the same definition + median block without a second glyph (CRTKY-79).

Tooltips on the Ratings card: **dot** hover (Measured / Partial / Estimate + sources), **category label** hover (category copy + median vs this station), **bar** hover (score + deviation + pigment line). A single muted caption under the title for every station with ratings (bar vs median + hover hints); if `station.confidence` exists, one extra clause points to dots and the chip key below — no second italic footer (avoids duplicating Uchisaiwaichō-style copy). AI-only rows without pipeline metadata have empty dot slots but the same bar explanation as computed stations.

### Station Overview radar vs Tokyo median (CRTKY-76, PR #51)

The single-station `RadarChart` (lazy-loaded via `RadarChartWrapper`) draws **two polygons**: a faint slate **Tokyo median** reference from `CITY_MEDIANS` (drawn first, `dot={false}`) and **this station** in blue on top, plus a micro-legend under the chart and the default recharts hover tooltip. Same deviation story as the rating bars, without per-axis pigment splits (recharts `Radar` is one stroke per series). The compare radar (`CompareRadarChart`) does not add the median overlay yet — avoids clutter with 2–3 station polygons.

### Heatmap layer (unchanged)

The map's heatmap mode still uses `CATEGORY_PALETTES` in `scoring.ts` — per-dimension 2-stop palettes (food → amber/orange, nightlife → lavender/purple, etc). That layer's job is *orientation* ("which dimension am I viewing"), not insight, so category hues still serve it. Explicitly out of scope for CRTKY-66.

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Public repo intro: 1493 stations, real stack, data sources, **honesty** pointers (hub stub CRTKY-81, CLAUDE Data readiness, Plane CRTKY-80–84) |
| `app/src/data/demo-ratings.ts` | All ratings (AI + computed). ~7700 lines. |
| `app/src/data/rent-averages.json` | Suumo rent data (274 stations) |
| `app/src/data/station-thumbnails.json` | **Three-tier image data** — `{slug: {thumb, lqip}}` for 1488 stations (99.7%). `thumb`: 320px VPS thumbnail URL (`img.pogorelov.dev/thumb/...`). `lqip`: 8×6 base64 JPEG (~877 chars) for instant blur-up on hover. Generated by `scripts/generate-thumbnails.py` on VPS. Replaces old `station-images.json` (deleted). 1426 KB raw, **67 KB gzipped**. |
| `app/src/data/station-images-all.json` | Self-hosted (img.pogorelov.dev) full-res photos — **8,827 images across 1488 stations (99.7%)**. Used by station detail `ImageGallery`. Metadata: url, alt, attribution, photographer, license, source. SSL cert valid (Let's Encrypt, expires 2026-07-01). **Privacy-cleaned** (CRTKY-97): 136 portrait/face images removed via OpenCV DNN detection + human review. |
| `app/src/data/environment-data.json` | Elevation + seismic data for 1493 stations. Generated by `scripts/export-environment.py` from NocoDB. |
| `app/src/data/line-names.json` | **127-entry line mapping** — ekidata ID → name_ja/name_en/operator/color/type. Copy of `data/line-names.json`. Researched from Wikipedia + operator sites. |
| `app/src/data/ward-data.json` | Ward/city/prefecture for 1493 stations. Generated by `scripts/export-wards.py` from NocoDB `station_wards`. |
| `app/src/data/last-trains.json` | **1483/1493 stations** with `{weekday, holiday, sources, data_date}`. Generated by `scripts/scrapers/scrape-last-trains.py` from [mini-tokyo-3d](https://github.com/nagix/mini-tokyo-3d) timetables. MIT license. |
| `app/src/lib/data.ts` | Merges stations + ratings + rent + environment + **line names + ward data** at build time |
| `app/src/lib/types.ts` | TypeScript interfaces (StationRatings, EnvironmentData, SeismicRiskTier, ElevationTier, **FilterState**, **LineInfo**, **WardInfo**, etc.) |
| `app/src/lib/store.ts` | Zustand store: weights, **`filters: FilterState`** (maxRent, maxCommute, categoryMins), `hideFloodRisk`, `hideHighSeismic`, `selectedStation`, `hoveredStation`, compare list, heatmap |
| `app/src/lib/scoring.ts` | Weighted score, affordability, **diverging akane↔kon Japanese palette** (CRTKY-66), **`applyDealbreakers()`** hard filter function. APIs: `compositeToColor(score, anchors)` for weighted-score surfaces with percentile-stretched anchors; `categoryDeviationColor(value, median)` for per-category bars via `CITY_MEDIANS`; `pigmentName(dev)` returning `{jp, en, tone}` for microcopy; `scoreToColor(score, dim)` is a thin heatmap-only shim. Five stops: 茜 akane / 珊瑚 sango / 生成り kinari / 浅葱 asagi / 紺 kon |
| `app/src/lib/url-state.ts` | Encode/decode URL state: weights (`w`), filters (`mr`/`mc`/`cm`), selectedStation, compareStations, heatmap |
| `data/stations.json` | Master station list (1493 entries) |
| `scripts/station-area-codes.json` | Station → ward code mapping (274 entries) |
| `scripts/scrapers/utils.py` | Shared NocoDB client, rate limiter, station loader |
| `scripts/scrapers/scrape-osm-pois.py` | OSM POI scraper (food, nightlife, green, gym) |
| `scripts/scrapers/scrape-hotpepper.py` | HotPepper restaurant/izakaya/bar scraper |
| `scripts/compute-ratings.py` | Normalizes all sources → 1-10 ratings + confidence metadata |
| `scripts/export-ratings.py` | NocoDB computed → demo-ratings.ts (with confidence/sources/data_date). Transit times from `data/transit-times.json` (CRTKY-81); missing per-category confidence keys default to **`estimate`** in generated TS |
| `scripts/compute-transit-times.py` | Geographic transit estimation: Haversine + line connectivity + calibration against 252 AI ground truth. Output: `data/transit-times.json`. Run with `--calibrate` for grid search. (CRTKY-81) |
| `data/transit-times.json` | Pre-computed transit times for 1493 stations to 5 hubs. Generated by `compute-transit-times.py`. |
| `scripts/export-environment.py` | Exports NocoDB elevation + seismic → `environment-data.json` with tier classifications |
| `scripts/export-wards.py` | Exports NocoDB `station_wards` → `ward-data.json` (city_name, ward_name, prefecture_name) |
| `scripts/scrapers/scrape-last-trains.py` | Fetches [mini-tokyo-3d](https://github.com/nagix/mini-tokyo-3d) timetables, matches MT3D station IDs → our slugs via Haversine distance (<200m), computes `MAX(departure)` per day type. Output: `data/last-trains.json` + `app/src/data/last-trains.json`. Uses `--cache-dir` to avoid re-downloading 174 files. |
| `data/line-names.json` | Master line name mapping (127 entries). Source of truth; copied to `app/src/data/` for Next.js import |
| `data/livecams.json` | Per-station YouTube livecam metadata (29 stations, 32 rows today). Source of truth; copied to `app/src/data/` for import |
| `app/src/data/livecams.json` | Frontend-imported livecams. `{slug: [{id, name_en, name_ja, channel_id, embed_url (youtube-nocookie), watch_url, distance_m, source: 'mini-tokyo-3d', data_date}]}`. ~15 KB. Merged into `Station.livecams` via `getStation()`. |
| `scripts/scrapers/scrape-livecams.py` | Scraper for `https://mini-tokyo.appspot.com/livecam` (MT3D, MIT). 300m Haversine match vs 1493 slugs; allows multiple cameras per slug sorted by `distance_m`. Flags: `--cache-dir`, `--dry-run`, `--debug`. Not auto-run on rating refresh (independent cadence). |
| `app/src/components/LiveCameras.tsx` | Click-to-load facade → iframe on user click. 16:9 aspect, tab strip when 2+ cameras, ✕ dismiss overlay, `role="tabpanel"` + `aria-labelledby`, `youtube-nocookie.com` embed with `autoplay=1&mute=1`. `next/dynamic` not needed — already `'use client'` and conditionally rendered (only stations with livecams mount it). |
| `scripts/scrapers/scrape-elevation.py` | Open-Elevation bulk POST scraper (all 1493 in 3 requests) |
| `scripts/scrapers/scrape-seismic.py` | J-SHIS Y2024 seismic hazard scraper (1 req/sec, ~25 min) |
| `scripts/scrapers/check-image-urls.py` | Bulk HEAD check of image URLs (concurrent, VPS-friendly) |
| `scripts/scrapers/scrape-osm-livability.py` | Daily essentials scraper (9 categories). Incremental. 1493/1493 complete. |
| `scripts/refresh-ratings.sh` | One-command chain: compute → export → build verify → commit → push |
| `app/src/app/[locale]/methodology/page.tsx` | `/methodology` page: data sources, pipeline, confidence, color system, limitations |
| `app/src/i18n/routing.ts` | next-intl v4 locale config: `['en', 'ja', 'ru']`, default `'en'` |
| `app/src/i18n/navigation.ts` | Locale-aware `Link`, `redirect`, `usePathname`, `useRouter` |
| `app/src/lib/station-name.ts` | `stationDisplayName(station, locale)` → `{primary, secondary}`, `stationPrimaryName()` → single string. EN: name_en/name_jp, JA: name_jp/name_en, RU: name_ru\|\|name_en/name_jp |
| `app/src/messages/{en,ja,ru}/common.json` | 190+ key dictionaries per locale. All UI strings, rating labels, tooltips, confidence, feedback, station page |
| `app/src/components/LocaleSwitcher.tsx` | EN/JA/RU toggle button group in header |
| `app/src/app/station/[slug]/page.tsx` | Station detail Ratings: fixed-width icon column (`w-6`), `ConfidenceBadge` (SVG shape icons) before label when `confidence` exists, category `Tooltip` with `showHelpIcon={false}`, bar `Tooltip` with `wrapper="div"` + `flex-1`. Legend chips use `ConfidenceIcon` at 10px. Caption always explains bars; icon clause + chip key only when `station.confidence` (CRTKY-79 + AI-only stations without metadata) |
| `app/src/components/ConfidenceBadge.tsx` | **"Data Depth" SVG icons** — shape encodes confidence level (bullseye = Measured, solid circle = Partial, dashed circle = Estimate, diamond 菱形 = Curated). Colors unchanged (koke-iro / yamabuki / nibi-iro / fuji-iro). Exports `ConfidenceIcon` (reusable SVG, 14×14 viewBox) + `CONFIDENCE_DOT_COLORS` + `SOURCE_LABELS`. 400 ms enter delay on desktop (CRTKY-67); **tap-to-toggle on touch** via `useIsTouch()` with enlarged tap target (p-3 padding). Label wording is "Measured / Partial / Estimate / Curated" (CRTKY-67 + CRTKY-83) |
| `app/src/components/RatingBar.tsx` | Presentational bar for the station Ratings card: two-tone empty track (warm left of median, cool right), colored fill via `categoryDeviationColor`, 1 px slate-300 median tick hairline. Wrapped by `<Tooltip wrapper="div" showHelpIcon={false}>` at the call site for the three-line pigment tooltip (CRTKY-68) |
| `app/src/components/Tooltip.tsx` | Generic tooltip wrapper. API: `content: ReactNode` (not just string), `showHelpIcon` opt-out, `wrapper: 'span' \| 'div'` for block children, `className` escape hatch for flex sizing. **Desktop:** 400 ms enter delay + 150 ms leave delay (hover). **Touch:** tap-to-toggle via `useIsTouch()`, tap-outside closes (pointerdown listener). Plain `?` glyph (no pill background) when `showHelpIcon` is true (CRTKY-68); station Ratings labels opt out (CRTKY-79) |
| `app/src/lib/use-is-touch.ts` | `useIsTouch()` hook — `useSyncExternalStore` + `matchMedia('(hover: none)')`. SSR-safe (returns false on server). Used by Tooltip, ConfidenceBadge, Map for touch-specific behavior branching. |
| `app/src/components/NaturalEnvironment.tsx` | Station detail: elevation badge (flood-risk warning <5m) + seismic risk dot (Low/Moderate/High/Very High with J-SHIS tiers) + tooltips + legend. Uses `EnvironmentData` from types.ts. Seismic dot colors: koke-iro (low), yamabuki (moderate), sango (high), akane (very high). |
| `app/src/components/TransportLines.tsx` | Station detail: railway line names with official color dots, operator labels, ward/city location. Locale-aware (EN/JA/RU). Collapse toggle at 6+ lines. Sort: subway → JR → private. Type legend when mixed. Uses `LineInfo[]` + `WardInfo` from types.ts. |
| `app/src/components/Map.tsx` | Leaflet map with **`preferCanvas`** (Canvas renderer for 1493 markers; halo + top-5 pulse forced to SVG via `renderer={getSvgRenderer()}`). **Smart flyTo:** adaptive zoom target (pan-only when ≥13, instant setView for short hops, 0.4–0.6s duration with `easeLinearity: 0.4`), `isFlying` ref guard, `onFlyStart`/`onFlyEnd` callbacks. **Tile prefetch:** `prefetchTilesAroundStation()` fires `<link rel="prefetch">` for 3×3 tile grid at z14 on marker hover. **FlyTo canvas fade:** `.map-flying` class on container fades canvas to `opacity:0` during zoom animation (hides Leaflet's CSS `scale(2^Δzoom)` artifact, #6050). `useLayoutEffect` ensures SVG halo hidden before paint. `closePopup()` + `autoPan={false}`. Highlights `selectedStation`/`hoveredStation` with brand-blue border + pulsating `.station-halo` ring (keyframes in `globals.css`). **Map `mouseover`/`mouseout`** call `setHoveredStation` (150ms debounced clear on `mouseout`) so list↔map hover stays linked (CRTKY-59). Highlighted marker radius **×1.4** vs base. Uses `compositeToColor` + `computeCompositeAnchors` deferred via `useDeferredValue` (CRTKY-61). **Three-tier image loading:** `StationTooltipHero` shows LQIP blur instantly (inline base64), crossfades to 320px VPS thumbnail (prefetched on `mouseover`), gradient fallback if no imagery. **Dealbreaker filters:** `applyDealbreakers()` from `scoring.ts` applies rent/commute/category-min/environment filters → `visibleStations` memo. Rent-unknown stations render at `fillOpacity: 0.35` + `opacity: 0.3` + `weight: 0.5` (full border+fill fade; suppressed on highlight/compare). Composite anchors computed on FULL dataset (pre-filter) for stable colors. **Z-order (CRTKY-90):** `sortedForRender` memo sorts ascending by score so high-rated stations paint on top (canvas paint order = DOM order). Top-5 pulse derives from the same sorted array (one sort, not two). **Touch adaptations (PR #69):** marker radius +4px on `(hover: none)`, Leaflet Tooltip suppressed (touch users get enriched Popup with image+snippet), `TouchZoomControls` component (+/− buttons bottom-right). |
| `scripts/generate-thumbnails.py` | VPS Docker script: reads `station-images-all.json`, generates 320px thumbnails + 8×6 LQIP base64 for each station. Output: thumbnails on disk at `/docker-volume/img/thumb/`, JSON at `/tmp/station-thumbnails.json`. Deps: Pillow. **Must mount `-v /tmp:/tmp`** to persist JSON output. |
| `scripts/detect-faces.py` | OpenCV DNN face detection on all images. Runs on VPS Docker (`opencv-python-headless`). Flags images with prominent faces (area >2% or confidence >70%). Output: `flagged-faces.json`. |
| `scripts/generate-face-review.py` | Generates self-contained HTML contact sheet from `flagged-faces.json`. Grid of flagged images with checkboxes, filters, "Export Removals JSON" button. Runs locally. |
| `scripts/remove-flagged-images.py` | Removes confirmed face images from `station-images-all.json` + VPS disk. Derives disk path from URL (not `local_path`, which omits `flickr/` prefix). Supports `--dry-run`. |
| `app/src/components/FilterPanel.tsx` | **Dealbreakers** (rent slider, commute slider, per-category min buttons, flood/seismic checkboxes, match counter) + weight sliders + presets + search + Top Ranked. Search section `hidden md:block` (mobile uses `MobileSearchPill`). Presets apply both weights + filters. Category mins in collapsible `<details>` with "N set" badge. Live match counter ("423 of 1493 match"). Ranked list shows `(rent unconfirmed)` for unknown-rent stations when rent filter active. Deferred ranking via `useDeferredValue(weights)` (CRTKY-61). |
| `app/src/components/MobileSearchPill.tsx` | `md:hidden` floating search pill over the map (Google Maps style). Magnifying glass icon + input + clear + results dropdown. On result tap: `setSelectedStation` → map flies, search clears. Self-contained search logic (duplicated from FilterPanel, ~10 lines). Position: `absolute top-2 left-3 right-24 z-[999]`. Input `text-base` (16px) to prevent iOS Safari auto-zoom. |
| `app/src/components/MapControls.tsx` | Heatmap toggle button + dimension select. `.map-control-btn` class for 44px touch targets on `(pointer: coarse)`. Position: `absolute top-3 right-3 z-[1000]`. |
| `app/src/components/RadarChart.tsx` | Single-station recharts radar: median ghost + station polygon + micro-legend (CRTKY-76). |
| `app/src/components/RadarChartWrapper.tsx` | `next/dynamic` for `RadarChart` with `ssr: false` on station detail only — avoids SSR/hydration issues with recharts (same lazy pattern as other chart entry points). |
| `app/src/components/FeedbackWidget.tsx` | Station/general feedback form. Prior-submit state comes from **`useSyncExternalStore`** reading `localStorage` (server snapshot `false`); same-tab updates use a tiny `window` event (`city-rating-feedback-ls-sync`) because `storage` events do not fire in the active tab. Avoids `useEffect`+`setState` for initial hydrate (eslint `react-hooks/set-state-in-effect`). Surfaces **`error` JSON** from `/api/feedback` (e.g. 429 rate limit) instead of a single generic line. |
| `app/src/app/api/feedback/route.ts` | POST → NocoDB `feedback` table. **IP rate limit:** minimum **2.5s** between requests per IP (was 10s and blocked legitimate “Add another tip”). Returns **429** + `Retry-After` + `{ error }` when under cooldown. |
| `app/src/i18n/routing.ts` | Locale config: `['en','ja','ru']`, default `en`. Exports `Locale` type. |
| `app/src/i18n/request.ts` | Server-side `getRequestConfig` — loads `messages/{locale}/common.json` per request. |
| `app/src/i18n/navigation.ts` | Locale-aware `Link`, `redirect`, `usePathname`, `useRouter`. **All internal links must use this, not `next/link`.** |
| `app/src/proxy.ts` | next-intl middleware (Next.js 16 convention). Accept-Language detection, NEXT_LOCALE cookie, locale redirect. API routes excluded. |
| `app/src/messages/{en,ja,ru}/common.json` | Translation dictionaries (~190 keys each). Single file per locale. EN is source of truth. |
| `app/src/components/LocaleSwitcher.tsx` | EN/JA/RU toggle button group. Uses `useRouter().replace()` from i18n/navigation. In homepage + station detail headers. |

## i18n (CRTKY-98 epic)

Three locales: **English** (default, no URL prefix), **Japanese** (`/ja/`), **Russian** (`/ru/`).

### Stack
- **Library:** `next-intl` v4.9.1 (App Router native)
- **Proxy:** `src/proxy.ts` (Next.js 16 renamed middleware → proxy)
- **Config:** `src/i18n/routing.ts` (locale list), `src/i18n/request.ts` (message loading), `src/i18n/navigation.ts` (locale-aware Link/router)
- **Dictionaries:** `src/messages/{en,ja,ru}/common.json` (~190 keys per locale, single file)
- **Plugin:** `next.config.ts` wrapped with `createNextIntlPlugin`

### Route structure
```
app/src/app/
  layout.tsx                    → Root shell (no <html>, no locale)
  [locale]/
    layout.tsx                  → <html lang={locale}>, NextIntlClientProvider, fonts, Umami
    page.tsx                    → /{locale} homepage
    station/[slug]/page.tsx     → /{locale}/station/:slug
    error.tsx                   → Error boundary
  api/feedback/route.ts         → POST /api/feedback (no locale)
  global-error.tsx              → Global fallback (no locale)
```

### Translation patterns

| Context | API | Example |
|---------|-----|---------|
| Server component | `const t = await getTranslations()` | Station detail page |
| Client component | `const t = useTranslations()` | FilterPanel, Map, ConfidenceBadge |
| Namespaced | `useTranslations('feedback')` | FeedbackWidget |
| Dynamic keys | `t(\`ratings.${key}\`)` | Rating labels, hub labels |
| ICU plurals (RU) | `{count, plural, one {# линия} few {# линии} many {# линий}}` | Station count, lines |
| Rich text styling | `t.rich('key', { bold: (c) => <span>{c}</span> })` | Match counter bold number |
| Internal links | `import { Link } from '@/i18n/navigation'` | **NOT** `next/link` — preserves locale |

### Fonts
- Inter: `subsets: ['latin', 'cyrillic']` (~20 KB addition for Cyrillic)
- JP: system font stack in `--font-sans`: `'Hiragino Sans', 'Yu Gothic', 'Meiryo', system-ui` (zero load cost)

### SEO
- `next-sitemap.config.js` generates hreflang alternates for all 3 locales on every URL
- `<html lang={locale}>` set per locale
- JSON-LD includes `inLanguage` field
- Default locale (EN) has no URL prefix — existing indexed URLs unchanged

### Build: 4486 pages in ~9s (7 workers)

### Station naming convention (CRTKY-111, not yet implemented)

Current: `name_en` hardcoded as primary everywhere. Correct pattern:

| Locale | Primary (bold) | Secondary (gray) | Notes |
|--------|---------------|-------------------|-------|
| EN | name_en | name_jp | Current behavior |
| JA | name_jp | name_en | Kanji primary, romaji helper |
| RU | name_ru | name_jp | Cyrillic primary, kanji for context |

Kanji (`name_jp`) always visible — users are physically in Tokyo and see kanji on station signs. `name_ru` requires CRTKY-107 (Polivanov transliteration + Wikipedia override for top 100).

### Known limitations
- `dynamic()` loading callbacks ("Loading map...") can't use hooks — left as EN
- Snippets (`description.atmosphere`) are Russian-only — shown in all locales until CRTKY-109 generates multilingual descriptions. CRTKY-111 gates display to RU-only as interim fix.
- `RATING_LABELS` / `RATING_TOOLTIPS` constants still exported from `types.ts` for key iteration — display strings come from `t()`, but the Record objects remain for `Object.keys()` loops

## Recent UI (post–CRTKY-68)

| PR | Plane | What shipped |
|----|-------|----------------|
| #49 | CRTKY-77 | FilterPanel: `Tooltip` with `content` prop; confidence legend chips + `Confidence:` prefix on badges (`ConfidenceBadge` + station page). |
| #50 | CRTKY-71 | Map tooltip: `StationTooltipHero` falls back to score gradient when Wikimedia `img` fires `onError` (Umami retained). |
| #51 | CRTKY-76 | Station Overview radar: `CITY_MEDIANS` slate ghost under blue station shape + legend + tooltip. |
| #56 | CRTKY-83, 81 | AI confidence merge (`editorial` level, fuji-iro dot) + transit times (geographic model, MAE 5.5 min). |
| #57 | CRTKY-64/65, 48, 42 | Distribution fixes (safety/gym gaps) + data-source tooltips + green area scraper. |
| — | CRTKY-85, 86 | Natural hazard data: elevation + seismic info layer (`NaturalEnvironment.tsx`) + binary safety filters on map/ranked list. Commit `e165ff9`. |
| #60 | CRTKY-88 | **Dealbreaker filters:** hard constraints (max rent, max commute, per-category minimums) independent of soft weights. Presets set both weights + filters. URL-serialized (`mr`/`mc`/`cm`). Rent-unknown stations pass but render dimmed. Match counter. |
| #61 | CRTKY-89 | **UX polish:** dual-range sliders (min+max) for rent & commute, "Low Crowds" → "Quietness" label, top-5 ranked stations get subtle pulse on map (`top-ranked-pulse` CSS, 2.4s, composite color). |
| #62 | — | Gallery LQIP blur-up on station detail `ImageGallery` (inline base64 → sharp crossfade). `generate-gallery-lqip.py`. |
| #64 | CRTKY-90 | **Map z-order + unknown fade:** high-rated stations paint on top (ascending score sort); `rentUnknown` stations fade border (opacity 0.3, weight 0.5) not just fill. |
| #67 | — | **FlyTo UX optimization:** Canvas renderer (`preferCanvas`) for 1493 markers, smart flyTo (adaptive zoom + 0.4–0.6s duration + easeLinearity), tile prefetch on hover (3×3 z14 grid via `<link rel="prefetch">`), SVG override for animated overlays (halo + top-5 pulse). |
| #69 | — | **Mobile touch UX:** viewport meta, `useIsTouch()` hook, tap-to-toggle tooltips (Tooltip + ConfidenceBadge), map markers +4px on touch, enriched Popup with image+snippet on touch, mobile zoom +/− buttons, gallery swipe+keyboard, slider thumbs 24px on `(pointer: coarse)`, search input hints, safe-area-inset, touch-aware CSS. |
| #71 | CRTKY-93 | **Confidence "Data Depth" SVG icons:** replace colored dots with shape-encoded icons — bullseye (Measured), solid circle (Partial), dashed circle (Estimate), diamond 菱形 (Curated). Shape readable without color (accessibility). `ConfidenceIcon` exported for legend chip reuse. |
| #72 | CRTKY-94 | **Mobile header + search pill:** responsive header ("Tokyo Explorer" on mobile, full name on desktop, icon-only Share, hide Scatter Plot/Feedback/count/credit). `MobileSearchPill` component — Google Maps-style floating search over map (`md:hidden`). FilterPanel search hidden on mobile. |
| #73 | — | **FlyTo cleanup:** hide halo + close popup during flyTo (`isFlying` state guard, `useLayoutEffect`, `closePopup()`, `autoPan={false}`). |
| #75 | CRTKY-91 | **FlyTo canvas fade:** `.map-flying` CSS class fades canvas to `opacity:0` during flyTo zoom animation (Leaflet #6050 CSS-scaling, confirmed 4× via MutationObserver). Tiles stay visible. Markers fade back in after `moveend` (0.15s transition). |
| #76 | CRTKY-95 | **iOS Safari fixes:** search input `text-base` (16px) prevents auto-zoom, search pill `right-24` clears Heatmap button, root `overflow-x-hidden`, zoom buttons safe-area-aware `calc(80px + env(safe-area-inset-bottom))`. |
| #78 | CRTKY-96 | **Safari 26 Liquid Glass hardening:** `h-screen` → `h-dvh` (dynamic viewport tracks toolbar), `html` background-color for toolbar tint, MobileDrawer `display:none` when closed (two-phase rAF open/transitionend close), Heatmap button 44px touch target gated by `@media (pointer: coarse)`, ComparePanel mobile-only bottom spacer for dynamic toolbar clearance. |
| #79 | CRTKY-97 | **Privacy: face/portrait image removal.** OpenCV DNN face detection on 8,963 images → 199 flagged → 136 confirmed removals across 101 stations. Deleted from `station-images-all.json` + VPS disk. 18 station thumbnails regenerated. Scripts: `detect-faces.py`, `generate-face-review.py`, `remove-flagged-images.py`. |
| #80 | CRTKY-97 | **Privacy: face/portrait image removal.** OpenCV DNN face detection on 8,963 images → 199 flagged → 136 confirmed removals across 101 stations. |
| #81 | CRTKY-87, 50 | **Daily Essentials (10th category)** end-to-end: `scrape-osm-livability.py` (1493/1493), compute + export pipeline, frontend types/weights/presets rebalanced, `/methodology` page, OG images on 1488 station pages. Docs refresh (00-overview, VISION). Plane triage: 14 stale issues closed. |
| #82 | CRTKY-98, 111 | **i18n: EN/JA/RU multi-language support.** next-intl v4, `[locale]` routing, proxy.ts, 190-key dictionaries, 15 components migrated to `t()` calls, `LocaleSwitcher`, hreflang sitemap, 4486 pages. `stationDisplayName()` + `stationPrimaryName()` helpers for locale-aware station names across all display sites. |
| #83 | CRTKY-34, 106 | **GDPR privacy footer** (desktop-only, cookie-free analytics notice in EN/JA/RU). **Methodology page** moved under `[locale]` routing (was 404). Livability scraper 1493/1493 complete (last 2 retried). |
| #90 | CRTKY-54, 52, 112 | **Transport lines + ward/city on station pages.** 127 ekidata line IDs → name/operator/color mapping (`line-names.json`). 1493 ward records from NocoDB (`ward-data.json`). `TransportLines` component: color dots, locale-aware names, collapse at 6+ lines, type legend. `Station.lines` resolved from `string[]` to `LineInfo[]` at build time. `MapStation` unchanged. |
| #91 | CRTKY-43 | **Rent expansion 274 → 1100 (18% → 74%)** via e-Stat govt statistics. `scripts/scrapers/scrape-estat-rent.py` + `merge-estat-rent.py`. Suumo actual listings keep priority; e-Stat fills ward-average fallback. `source` field: `suumo` \| `estat` \| old `ward_average` retired. |
| #92 | — | **Ratings refresh (2026-04-14)** — green area scraper completion unlocks 428 more stations at `strong` confidence. `computed_at: 2026-04-15` in NocoDB `computed_ratings`. |
| #93 | CRTKY-115 | **Last train times.** Scraped from mini-tokyo-3d (1483/1493 = 99.3%). `last-trains.json`: `{weekday, holiday, sources, data_date}`. 4th StatCard on station detail with tooltip caveat. Disambiguated weekday/holiday separately. Translated tooltip prose in EN/JA/RU. |
| #94 | CRTKY-114 | **Map interaction UX overhaul.** Auto-open popup on desktop marker click, mobile bottom-card pattern (`MobileStationCard`), removed dead-end interactions. Design doc: `.claude/design-map-interaction-ux.md`. |
| #95 | CRTKY-116/117/118/119 | **Live YouTube camera streams on station pages.** Scraper (`scrape-livecams.py`) fetches 64 MT3D livecams, Haversine-matches at 300m → 29 stations / 32 rows. `LiveCamera` type + `Station.livecams`. `LiveCameras.tsx` component: click-to-load facade, 16:9, tab strip for multi-cam (shinjukunishiguchi gets 3), ✕ dismiss overlay, `youtube-nocookie.com` embed with `autoplay=1&mute=1`, `role="tabpanel"` ARIA. 📹 badge on map tooltip + touch popup (emoji-only, no palette overload). `FilterState.hasLiveCamera` dealbreaker + `hasLiveCamera?: boolean` on `MapStation` (optional-spread so no-cam stations add zero bytes). URL param `lc=1`. i18n in en/ja/ru. |

## Description Generation Pipeline (CRTKY-109, in progress)

Data-driven LLM pipeline to produce 4-field descriptions (atmosphere / landmarks / food / nightlife) for all 1493 stations in EN/JA/RU.

### Artifacts
- `HANDOFF.md` (repo root) — runbook for parallel LLM agents (Claude Code, Codex, Cursor). Self-contained; each agent picks slugs via filesystem-claim.
- `research/description-generation-rules.md` — voice rules, signal→prose mapping, confidence awareness, what NOT to say
- `scripts/build-datamart.py` — joins 10 NocoDB tables + 7 local JSON into `data/station-datamart.json` (15 MB, gitignored). Run: `python3 scripts/build-datamart.py` (~60s).
- `scripts/build-prompts-dir.py` — generates one self-contained `data/prompts/<slug>.md` per station (1486 files, gitignored). Re-run safely; `--all` forces regeneration.
- `scripts/queue-status.py` — progress dashboard. Flags: `--next N` for next slugs, `--failed` for broken outputs.
- `scripts/merge-descriptions.py` — merges all `data/descriptions/*.json` → `data/generated-descriptions.json` with validation.
- `data/descriptions/<slug>.json` — **committed** per-station output. Shape: `{en:{atmosphere,landmarks,food,nightlife}, ja:{...}, ru:{...}}`
- `data/generated-descriptions.json` — **committed** merged result for frontend integration.

### Pipeline
```
NocoDB (10 tables) + local JSON (7 files)
    ↓  build-datamart.py
data/station-datamart.json (1493 stations, score-desc order, with `generation_order` field)
    ↓  build-prompts-dir.py
data/prompts/<slug>.md (1486 self-contained prompt files — voice + few-shot + data)
    ↓  LLM agents (Claude Code, Codex, Cursor) in parallel, filesystem-claim
data/descriptions/<slug>.json (one per station)
    ↓  merge-descriptions.py
data/generated-descriptions.json (merged, validated)
    ↓  Phase 6 — separate integration PR
app/src/data/demo-ratings.ts schema change: description becomes {en,ja,ru} × 4 fields
```

### Status (2026-04-15)
- Phase 1 (research): ✅ rules doc
- Phase 2 (datamart): ✅ builder runs, pulls all 17 sources
- Phase 3 (prompt engineering): ✅ validated with 8 pilot stations (haiku ~7s/station, quality good)
- Phase 4 (batch generation): 🚧 scaffolding merged, run via UI agents against main per `HANDOFF.md`
- Phase 5 (merge + validate): pending (after Phase 4)
- Phase 6 (frontend integration): **separate PR** — schema change + component wiring

### Generation order
Composite score descending (from `datamart["generation_order"]`). **All 1493 stations are regenerated** — including the ~252 that previously had a single-field RU editorial `description`. Scope reversal on 2026-04-15: single consistent voice across the whole dataset beats preserving legacy 1-field text, and the output structure is different (4 fields × 3 locales vs 1 field × 1 locale). `has_existing_description` flag stays in the datamart as metadata only; no script branches on it.

### Running (paths are always relative to repo root)
Scripts use `Path(__file__).resolve().parent.parent` → work from any cwd. For UI agents: open the editor **in the repo/worktree root** so Read/Write tool calls resolve relative paths. See `HANDOFF.md` → Block 1 for the paste-in prompt for UI agents.

## Dealbreaker Filters (PR #60, #61)

The sidebar now has two independent control axes:
- **Weights** (soft) — "what matters more" → affects ranking order
- **Dealbreakers** (hard) — "absolute requirements" → hides stations that fail

### Architecture

`FilterState` in `types.ts`: `{ minRent, maxRent, minCommute, maxCommute, categoryMins }` with `DEFAULT_FILTERS` (all wide open). PR #61 added min endpoints for dual-range sliders.

Filter chain in Map.tsx + FilterPanel.tsx:
```
stations → scoredStations (useMemo, deferredWeights) → filteredStations (applyDealbreakers) → render
```

`applyDealbreakers()` in `scoring.ts`: O(n) filter on `MapStation[]`. Null-safe: unknown rent/commute/ratings **pass** (don't penalize missing data). Rent-unknown stations flagged with `rentUnknown: true` → dimmed markers (35% opacity) + "(rent unconfirmed)" in ranked list.

`compositeAnchors` computed on FULL dataset (pre-filter) — colors stay stable when filters narrow the view.

### Preset filters

`PresetProfile.filters?: Partial<FilterState>` — presets now set both weights AND dealbreakers:
- Young Pro: rent ≤ ¥150k, commute ≤ 30 min
- Family: commute ≤ 40 min, safety ≥ 7
- Foodie Budget: rent ≤ ¥120k
- Digital Nomad: rent ≤ ¥130k

### URL params

Filter state serialized alongside weights for shareable links:
- `nr=100000` — min rent (only if raised above ¥80k)
- `mr=130000` — max rent
- `nc=20` — min commute (only if raised above 10)
- `mc=30` — max commute (minutes)
- `cm=safety:7,green:6` — category minimums

### Top-5 map pulse (PR #61)

Top-5 ranked visible stations get a subtle `top-ranked-pulse` CSS animation in their composite color. 2.4s period, max stroke-opacity 0.35 (much subtler than the 1.6s selected-station halo). Hidden in heatmap mode, suppressed when station is already highlighted.

### Label: "Low Crowds" → "Quietness" (PR #61)

`RATING_LABELS.crowd = 'Quietness'` (was "Low Crowds"). Category min buttons use `CATEGORY_SHORT_LABELS` map for compact unambiguous labels.

## Running Scrapers on VPS

Scrapers run as detached Docker containers on VPS to avoid laptop sleep issues:

```bash
# SSH to VPS (use Coolify localhost key)
ssh -i ~/.ssh/coolify_vps root@217.196.61.98

# Launch a scraper
docker run -d --name SCRAPER_NAME --restart=no \
  -e NOCODB_API_URL=https://nocodb.pogorelov.dev \
  -e NOCODB_API_TOKEN=3hUf86bwbyw-OSJTlNwGOc1w8AcwrrgAkOuyIaTt \
  -e HOTPEPPER_API_KEY=b20f206ef29b9f48 \
  -v /tmp/SCRIPT.py:/app/scraper.py:ro \
  -v /tmp/stations.json:/app/data/stations.json:ro \
  python:3.11-slim bash -c "pip install --quiet requests && python3 -u /app/scraper.py"

# Check logs
docker logs --tail 20 SCRAPER_NAME

# Check all scraper containers
docker ps -a --format "{{.Names}}\t{{.Status}}" | grep -E "osm|hp|arcgis|mlit|nominatim"
```

All scrapers are incremental — they skip stations already in NocoDB. Safe to restart.

## Research Documents

Detailed data source research in `research/`:
- `00-overview.md` — Status summary
- `01-nightlife.md` — HP midnight, karaoke, club sources
- `02-safety.md` — ArcGIS crime polygons, daytime population, crime weights
- `03-crowd.md` — MLIT S12 dataset, railway company data
- `04-green.md` — Park area calculation, landuse=religious, NDVI
- `05-rent.md` — LIFULL HOME'S, Nominatim ward mapping
- `06-vibe.md` — Cultural venue density, pedestrian streets

## Build & Deploy

```bash
cd app && npm run build  # Verify after export-ratings.py
git push origin main     # Coolify auto-deploys
```

**Branch protection (since 2026-04-12):** `main` requires the `build` status check (CI: `tsc --noEmit` + `npm run build` + `npm audit`) to pass before merge. No force push, no deletion. Admin bypass enabled for emergencies. All changes must go through PRs.

## Refreshing ratings data

Use the one-command script instead of running compute/export/build manually:

```bash
scripts/refresh-ratings.sh              # interactive: prompts before commit
scripts/refresh-ratings.sh --auto --push  # hands-off on a feature branch
scripts/refresh-ratings.sh --dry-run    # preview without writes
scripts/refresh-ratings.sh --no-build   # skip build verification
```

Safety: the script refuses to run with unrelated dirty files and refuses to push directly to main without `--force-main`. Never uses `--amend` or force push.

**Note:** the frontend bakes ratings into static HTML at build time. Re-running scrapers alone does NOT update the live site — you must also run the refresh chain so `demo-ratings.ts` gets rewritten and committed.

## Homepage performance (CRTKY-61 — PR #44)

Three optimizations landed in the homepage initial-load path. If you touch these call sites, preserve the patterns below or the gains regress:

1. **Lazy chunks for `recharts` consumers.** `ScatterPlotExplorer` (in `HeaderActions.tsx`) and `ComparePanel` (in `MapWrapper.tsx`) are loaded via `next/dynamic({ ssr: false })`. `ComparePanel` is additionally gated on `compareStations.length >= 2` so its ~450 KB chunk never downloads until the user compares. Don't static-import `recharts` anywhere else or the chunk lands in the initial bundle.
2. **`MapStation.confidence` dropped from the RSC payload.** `getMapStations()` in `lib/data.ts` does NOT copy `confidence` — it shipped 226 KB of repetitive metadata into every homepage load for zero UI benefit. Confidence lives only on `Station` (via `getStation()`), which is used by `/station/[slug]` pages. If you need confidence metadata on a homepage surface, lazy-fetch a `confidence-by-slug.json` from inside the component, don't put it back on `MapStation`.
3. **`useDeferredValue(weights)` in Map, FilterPanel, ComparePanel, ScatterPlotExplorer.** Scoring 1493 stations + sorting percentile anchors on every slider frame was a 2× INP regression. Defer BOTH `scoredStations` AND `computeCompositeAnchors` calls so the palette range stays coherent with the (also deferred) score values mid-drag. The slider itself still reads live `weights` so the thumb never detaches from the pointer.

Baseline → after: initial JS 1086 → 642 KB (−41 %), HTML 895 → 616 KB (−31 %), RSC flight 755 → 523 KB (−31 %).

### Map flyTo optimization (PR #68)

Four runtime optimizations for the station-select fly animation:

1. **Canvas renderer** (`preferCanvas` on `MapContainer`). All 1493 CircleMarkers render on a single `<canvas>` element inside `leaflet-overlay-pane` instead of 1493 individual SVG `<path>` elements. Eliminates SVG layout thrashing during flyTo. Animated overlays (station-halo, top-5 pulse) forced to SVG via `renderer={getSvgRenderer()}` so CSS keyframe animations still work.
2. **Smart flyTo** in `FlyToStation`. Adapts zoom target (no zoom change when ≥13 → cheaper pan-only), uses `setView` for very close hops (<0.01°), and adaptive duration (0.4s close, 0.6s far) with `easeLinearity: 0.4` to minimize time at intermediate zoom levels where tiles aren't cached.
3. **Tile prefetch on hover** — `prefetchTilesAroundStation()` fires `<link rel="prefetch">` for a 3×3 grid of z14 Carto tiles around the hovered station. By click time (400ms tooltip delay + decision time), tiles are warm in browser cache.
4. **`isFlying` ref** — set during flyTo, cleared on `moveend`. Guard for suppressing non-critical work during animation.

**Production perf test (2026-04-12):** Default zoom 12 → Akihabara (ranked list click). MessageChannel-based 83kHz sampling:
- 315,020 samples, **p95 interval 0.1ms** — butter-smooth after React commit
- 3 jank frames >50ms (142ms max) — all during React's initial state commit (`setSelectedStation` → `flyTarget` memo → `FlyToStation` render → `useEffect`)
- 24 busy samples >5ms out of 315,020 (0.008%)
- Canvas renderer confirmed: 0 SVG marker paths, 5 SVG overlay paths (halo + pulse)

Use `.claude/skills/perf-capture/` to reproduce these measurements.

### FlyTo visual glitch fix (PR #73 + #75)

During `flyTo` with zoom change, Leaflet CSS-transforms the canvas by `scale(2^Δzoom)` (by design, Leaflet #6050/#6409). Zoom 12→14 = 4× scale, making every CircleMarker appear enormous on mobile.

Three-layer fix:
1. **Canvas opacity fade** (PR #75) — `.map-flying` CSS class toggled on the container by `FlyToStation`. CSS rule `opacity: 0` with 0.15s transition. Tiles stay visible (separate pane). Markers fade back in after `moveend`. Verified: MutationObserver test captured 45 scale mutations (1.05→4.0×) on `canvas.style.transform`; with fix, canvas opacity=0 during all scaled frames.
2. **SVG halo/pulse hidden** (PR #73) — `isFlying` state guard (`!isFlying &&` conditional render). `useLayoutEffect` in `FlyToStation` so `setIsFlying(true)` fires before browser paint.
3. **Popup suppression** (PR #73) — `map.closePopup()` before flyTo + `autoPan={false}` on all Popups.

Use `.claude/skills/flyto-visual-test/` for MutationObserver-based regression testing.
