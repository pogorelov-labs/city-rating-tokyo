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
| osm_extended | mrpqu8o796e6xzk | ~180 (building) | 12% | Overpass (karaoke, cultural, hostel) |
| station_crime | mxwixub7d0q5i00 | 615 | Tokyo 100% | Keishicho ArcGIS point-in-polygon |
| crime_stats | mxitpnomlom3j3q | 91 | legacy | Hardcoded ward-level |
| passenger_counts | m36bbxcv8t0asur | 1409 | 94% | MLIT S12 + hardcoded |
| station_wards | m74rdmspn3trrqc | 1493 | 100% | Nominatim reverse geocoding |
| hostels | ms9awzjv9j6suh7 | 3 | test | Overpass |
| computed_ratings | mkp046vo42kj55w | — | — | Output of compute-ratings.py |
| rent (file) | — | 274 | 18% | Suumo scrape (app/src/data/rent-averages.json) |

## Implementation Progress

| Phase | Description | Status |
|-------|-------------|--------|
| A1 | HP midnight scrape | ✅ done (1493/1493) |
| A2 | OSM extended tags (karaoke, cultural, hostel) | 🔄 running on VPS (~180/1493) |
| A3 | OSM green area re-scrape | ⏳ pending |
| B1 | MLIT S12 passenger download | ✅ done (1409 records) |
| B2 | Keishicho ArcGIS crime | ✅ done (615 Tokyo stations) |
| B3 | Nominatim reverse geocoding | ✅ done (1493/1493) |
| C1 | LIFULL HOME'S rent scrape | ⏳ pending |
| D | Rewrite compute-ratings.py with research formulas | ✅ done (v2, log-percentile) |
| E | Export + verify + app build | ✅ done (1493 pages, build passes) |

## Architecture Context
- All scraped data → NocoDB tables (nocodb.pogorelov.dev)
- `scripts/compute-ratings.py` reads NocoDB → log-percentile normalize → writes computed_ratings
- `scripts/export-ratings.py` merges with AI-researched (272 stations) → demo-ratings.ts
- App reads demo-ratings.ts unchanged — no frontend changes needed
- Scrapers run as Docker containers on VPS (python:3.11-slim), incremental
- See `/CLAUDE.md` for full dev guide with formulas and table IDs
