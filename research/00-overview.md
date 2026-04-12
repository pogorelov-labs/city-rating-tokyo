# Rating Data Research — Overview

Last updated: 2026-04-07

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

## Data in NocoDB (city-rating-db) — as of 2026-04-12

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
| osm_livability | m3vasnsm4y09xez | ~547→ | 37%→ | Overpass (supermarket, pharmacy, clinic, school, kindergarten, post_office, bank, laundry, dentist) |
| station_elevation | mkrugzx8z62hli4 | 1493 | **100%** | Open-Elevation API (bulk POST). Range: -2m to 741m |
| station_seismic | mhtnqvmi1kwbth9 | ~scraping | → | J-SHIS Y2024 (prob intensity ≥6.0/5.5/5.0 in 30yr, ground velocity) |
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

### New data directions (2026-04-12)

| Phase | Description | Status | Source |
|-------|-------------|--------|--------|
| H1 | Station elevation (flood risk signal) | ✅ done (1493/1493) | Open-Elevation API, CRTKY-85 |
| H2 | Seismic hazard (earthquake risk) | 🔄 running (~200/1493) | J-SHIS Y2024, CRTKY-86 |
| H3 | Daily essentials (livability) | 🔄 running (~547/1493) | Overpass (9 categories), CRTKY-87 |
| H4 | Station images (health check) | ✅ done (0 broken / 8963 URLs) | img.pogorelov.dev HEAD check |
| H5 | Green area (sqm geometry) | ⏳ queued (after H3) | Overpass `out geom`, CRTKY-42 |

**Транспорт / быт (не в таблице фаз A–G):** время до хабов в UI есть, но для большинства станций в экспорте стоит **заглушка 30m** (см. `scripts/export-ratings.py`); реальные минуты в основном у AI-станций. **Plane: CRTKY-81.** **Last train** — только placeholder в UI (**CRTKY-56**). Расширение **rent** — **CRTKY-43** + `research/05-rent.md`. Хвост пассажиров / обновление MLIT FY — **CRTKY-84**. Полный роадмап: **`research/VISION.md`**.

## Sourcing discipline (Phase 0)

Before betting on **commercial** transit or rent APIs: inventory **ODPT**, **GTFS-JP** / National Open Data Challenge, and **MLIT** rail/passenger disclosures; document **licenses** and weekday/season assumptions (**CRTKY-81**, **CRTKY-56**, **CRTKY-84** — see `research/03-crowd.md` section 1 / subsection 1b). For rent work, **e-Stat** / municipal open aggregates are **ward/prefecture validation only**, not station-level rent in the product (**CRTKY-43**). **Canonical wording** lives in each issue’s Plane **description**; child map and conflict rule (description beats comments) on epic **CRTKY-80**.

## Critical readiness (do not overstate)

- **Row coverage ≠ signal quality:** all 1493 slugs get scores, but rent/safety/crowd use different geographic and source depth (see `CLAUDE.md` **Data readiness & coverage honesty**).
- **`strong` counts:** green and vibe can show **0 strong** while OSM data exists — confidence reflects **compute rules**, not “plenty of parks on the map.”
- **Hub minutes:** until **CRTKY-81**, treat **Hubs** chips as **non-routing** for data-driven rows.
- **AI slugs (~272 with `description`):** ratings are editorial; pipeline `confidence` merge is **CRTKY-83** — see `CLAUDE.md` + `VISION.md` §3.1 gap text.

## Production Status (2026-04-07)

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
- `scripts/export-ratings.py` merges with AI-researched entries (~272 slugs with `description`) → demo-ratings.ts
- `scripts/refresh-ratings.sh` chains compute → export → build → commit → push
- Scrapers run as Docker containers on VPS (python:3.11-slim), incremental
- Confidence badges live on station page + ComparePanel
- See `/CLAUDE.md` for full dev guide with formulas and table IDs
