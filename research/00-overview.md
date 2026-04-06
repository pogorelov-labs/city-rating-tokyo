# Rating Data Research — Overview

Last updated: 2026-04-05

## Goal
Replace heuristic ratings (distance-from-center formula) with data-driven scores backed by real scraped data for 1493 Greater Tokyo stations.

## Research Status

| # | Category | File | Status | Key Finding |
|---|----------|------|--------|-------------|
| 1 | nightlife | `01-nightlife.md` | ✅ done | HP `midnight=1` param + OSM karaoke tag |
| 2 | safety | `02-safety.md` | ✅ done | ArcGIS FeatureServer: 5596 neighborhood polygons |
| 3 | crowd | `03-crowd.md` | ✅ done | MLIT S12 GeoJSON: 1 download → 94% coverage |
| 4 | green | `04-green.md` | ✅ done | landuse=religious captures Meiji Jingu; need area calc |
| 5 | rent | `05-rent.md` | ✅ done | LIFULL HOME'S station-level + Nominatim ward mapping |
| 6 | vibe | `06-vibe.md` | ✅ done | Cultural venue density 25:1 differentiation |

## What's Already Good (no research needed)
- **food**: HP total + OSM food, r=0.855, 100% coverage ✅
- **transport**: line_count, 100% coverage ✅
- **gym_sports**: OSM gym_count, 89% coverage ✅

## Data in NocoDB (city-rating-db) — as of 2026-04-05

| Table | ID | Records | Coverage | Source |
|-------|----|---------|----------|--------|
| osm_pois | mnnuqtldvt4jxlj | 1398 | 94% | Overpass API |
| hotpepper | mfk9j2qoj2bkeoo | 1493 | 100% | HotPepper API (+midnight_count column) |
| osm_extended | mrpqu8o796e6xzk | 1467 | 98% | Overpass (karaoke, cultural venues, pedestrian, hostels) |
| station_crime | mxwixub7d0q5i00 | 615 | Tokyo 100% | Keishicho ArcGIS point-in-polygon |
| crime_stats | mxitpnomlom3j3q | 91 | legacy | Hardcoded ward-level |
| passenger_counts | m36bbxcv8t0asur | 1409 | 94% | MLIT S12 + hardcoded |
| station_wards | m74rdmspn3trrqc | 1493 | 100% | Nominatim reverse geocoding |
| hostels | ms9awzjv9j6suh7 | 3 | test | Overpass (superseded by osm_extended.hostel_count) |
| computed_ratings | mkp046vo42kj55w | 1493 | 100% | Output of compute-ratings.py + confidence/sources/data_date |
| rent (file) | — | 274 | 18% | Suumo scrape (app/src/data/rent-averages.json) |

## Implementation Progress

| Phase | Description | Status | PR |
|-------|-------------|--------|-----|
| A1 | HP midnight scrape | ✅ done | #29 |
| A2 | OSM extended tags (karaoke, cultural, hostel) | ✅ done (1467/1493) | #35 |
| A3 | OSM green area re-scrape | ⏳ pending | — |
| B1 | MLIT S12 passenger download | ✅ done (1409 records) | #29 |
| B2 | Keishicho ArcGIS crime | ✅ done (615 Tokyo) | #29 |
| B3 | Nominatim reverse geocoding | ✅ done (1493/1493) | #29 |
| C1 | LIFULL HOME'S rent scrape | ⏳ pending | — |
| D | Rewrite compute-ratings.py with research formulas | ✅ done (v2, log-percentile) | #29 |
| D2 | Export confidence/sources/data_date metadata | ✅ done | #32, #33 |
| E | Export + verify + app build | ✅ done (1493 pages) | #29 |
| F | Re-run pipeline after OSM extended completed | ✅ done (vibe 62% data-driven) | #35 |
| G1 | Refresh-ratings.sh one-command script | ✅ done | #36 |
| G2 | Confidence badges UI (🟢🟡⚪) on station page | ✅ done | #34 (CRTKY-47) |
| G3 | Replace generic tooltips with data-source tooltips | ⏳ pending | — (CRTKY-48) |
| G4 | "How ratings work" section on station page | ⏳ pending | — (CRTKY-49) |
| G5 | /methodology page | ⏳ pending | — (CRTKY-50) |
| G6 | AI vs data-driven station badge + freshness | ⏳ pending | — (CRTKY-51) |

## Production Status (2026-04-06)

**Live at https://city-rating.pogorelov.dev** — HTTP 200, 1493 station pages.

Confidence metadata:
- food: strong 1247, moderate 124, estimate 122
- nightlife: strong 1165, moderate 129, estimate 199
- transport: strong 1400, moderate 93, estimate 0
- rent: strong 273, moderate 713, estimate 507
- safety: strong 615, moderate 187, estimate 691
- green: strong 0, moderate 1314, estimate 179 (waiting on green area scrape)
- gym_sports: strong 1244, moderate 0, estimate 249
- vibe: strong 0, moderate 932, estimate 561 (up from 168/1325)
- crowd: strong 1400, moderate 0, estimate 93

## Architecture Context
- All scraped data → NocoDB tables (nocodb.pogorelov.dev)
- `scripts/compute-ratings.py` reads NocoDB → log-percentile normalize → writes computed_ratings (with confidence/sources/data_date)
- `scripts/export-ratings.py` merges with AI-researched (252 stations) → demo-ratings.ts
- `scripts/refresh-ratings.sh` chains compute → export → build → commit → push
- Scrapers run as Docker containers on VPS (python:3.11-slim), incremental
- Confidence badges live on station page + ComparePanel
- See `/CLAUDE.md` for full dev guide with formulas and table IDs
