# City Rating Tokyo

Interactive map of **1493** Greater Tokyo-area train stations. Adjust weights across ten categories (food, nightlife, transport, rent, safety, green, gym, vibe, crowd, daily essentials), filter by commute and budget, and open per-station pages with radar chart, ratings breakdown, and optional neighborhood copy.

**Live:** [city-rating.pogorelov.dev](https://city-rating.pogorelov.dev/?ref=github)  
**Repo / issues:** [github.com/pogorelov-labs/city-rating-tokyo](https://github.com/pogorelov-labs/city-rating-tokyo)

**Latest release:** [v0.1.0 — Tokyo + Bangkok](https://github.com/pogorelov-labs/city-rating-tokyo/releases/latest) · [Changelog](CHANGELOG.md)

**Bangkok (since Sept 2026):** all **50 districts** (khet), **133 station areas** and a **200 m grid**, with the BTS / MRT / ARL / SRT Red rail network on top — switch cities from the header; your weights carry over. **EN/JA/RU** across both cities. See [Bangkok](#bangkok-district-layer) below.

## What it does

- **Map** — weighted composite score; heatmap by category; compare and explore modes (see app for current UX).
- **Filters** — presets, search, max commute (uses `transit_minutes` where present), rent band, min score.
- **Station pages (SSG)** — stats, hub strip, radar vs Tokyo median, ten rating bars with confidence dots when pipeline metadata exists, feedback widget.

## Bangkok (district layer)

- **Levels:** 50 districts (polygons), 133 walkable station areas and a 200 m grid — a quarter of Bangkok's districts have no rail inside.
- **Data:** OpenStreetMap + [Overture Maps Places](https://docs.overturemaps.org/guides/places/) (two independent POI sources, r ≈ 0.9 agreement), Wikidata (names, population), a door-to-door commute model to five hubs, Wikimedia Commons photos.
- **Rent provenance:** 10 central station areas use DooAsset's published condominium asking-rent medians by bedroom, across all floor areas, at **estimate** confidence. These are single-provider proxies with source dates/sample sizes, not fixed-size market rents. All district and grid rents remain **editorial**; other station areas use district blends. ComparePanel distinguishes these provenances. See the [central rent audit](research/bangkok/notes/2026-10-25-central-rent-audit-crtky141.md).
- **Honesty:** safety remains editorial; scores are relative within Bangkok — a Bangkok 8 is not a Tokyo 8. Evidence density differs by category and level. See [`research/bangkok/00-overview.md`](research/bangkok/00-overview.md).
- **Acquisition code:** [`scripts/bangkok/fetch-geofabrik.py`](scripts/bangkok/fetch-geofabrik.py) fetches OSM from a Geofabrik Thailand PBF without Overpass. The [pipeline guide](scripts/bangkok/README.md) covers this path, other API inputs and offline builds; the Overpass path remains available.
- **Refresh status:** **v0.1.0 excluded the full Bangkok spatial refresh**. It merged post-release in [PR #147](https://github.com/pogorelov-labs/city-rating-tokyo/pull/147) on **2026-10-27** at [ba7aa47](https://github.com/pogorelov-labs/city-rating-tokyo/commit/ba7aa477fb3e06ceada1fad5df2dc5954428cdf4), and its data is now on **main**. All 10 validation gates were resolved and tourism/Michelin/embassy facts preserved. See the [frozen-refresh evidence](research/bangkok/notes/2026-10-26-frozen-refresh.md) and [completed remediation](docs/DATA_REFRESH_REMEDIATION.md); the v0.1.0 tag/release remains unchanged.

## Rating categories (default weights)

| Category | Weight | Notes |
|----------|--------|--------|
| Transport | 18% | Tokyo lines/passengers; Bangkok rail + commute model |
| Affordability | 18% | Tokyo Suumo / e-Stat / regression; Bangkok editorial + 10 station-area proxies |
| Daily Essentials | 14% | Tokyo OSM; Bangkok Overture + OSM |
| Safety | 10% | Tokyo 2024 police open data; Bangkok editorial |
| Food & Dining | 12% | Tokyo HotPepper + OSM; Bangkok Overture + OSM |
| Parks & Green | 8% | OSM green signals |
| Gym & Sports | 4% | Tokyo OSM; Bangkok Overture + OSM |
| Vibe | 4% | Cultural / pedestrian signals + documented editorial overrides |
| Nightlife | 8% | Tokyo HotPepper + OSM; Bangkok Overture + OSM |
| Quietness | 4% | Tokyo passengers + fallbacks; Bangkok WorldPop (districts) / place density (finer levels) |

Weights match [`packages/schema/constants.json`](packages/schema/constants.json).

## Tech stack

- **Next.js 16** (App Router, Turbopack), **React 19**, **TypeScript**, **Tailwind 4**
- **Leaflet**, **recharts** (lazy-loaded on relevant surfaces), **Zustand**
- Static data at build time (no runtime DB)

## Project layout (short)

```
data/stations.json              # 1493 stations — master list
app/src/data/demo-ratings.ts    # Merged AI + computed ratings export
app/src/data/rent-averages.json # Suumo-backed rent where scraped
app/src/data/bangkok/           # Bangkok districts, geometry, rail overlay (generated)
app/src/app/                    # Routes: /, /station/[slug], /bangkok, /bangkok/district/[slug], /api/feedback
scripts/bangkok/                # Bangkok fetch + build pipeline (uv), tests
scripts/                        # Scrapers, compute-ratings.py, export-ratings.py
research/                       # Source research + VISION roadmap
CLAUDE.md                       # Pipeline IDs, formulas, data-readiness caveats
```

## Getting started

```bash
cd app
npm install
npm run dev
```

Open [localhost:3000](http://localhost:3000).

## Deployment

Dockerized Next.js standalone build — `app/Dockerfile`. Production: **Coolify** on a VPS with Traefik and TLS, auto-deployed from `main`. Static city data needs no runtime DB; v0.1.0 has no DB migration. See the [release runbook](docs/RELEASING.md).

## Data sources (high level)

- **Stations / lines** — based on open railway-station datasets (see `SPEC.md` / `data/stations.json` provenance).
- **POI counts, green, gym, vibe inputs** — **OpenStreetMap** via Overpass → NocoDB for Tokyo; Bangkok combines Geofabrik OSM + **Overture Places** in the frozen snapshot merged post-v0.1.0 in [PR #147](https://github.com/pogorelov-labs/city-rating-tokyo/pull/147).
- **Food / nightlife counts** — **HotPepper** API + OSM.
- **Passengers** — **MLIT** 国土数値情報 S12, FY2024 (`scripts/scrapers/ingest-mlit-s12.py` → `data/passengers/s12-passengers.json`; see `research/03-crowd.md`). 出典：「国土数値情報（駅別乗降客数データ）」（国土交通省）を加工して作成.
- **Crime** — 2024 police statistics from 警視庁 (町丁 CSV) and the Kanagawa, Saitama and Chiba prefectural police, with e-Stat population and boundaries (`scripts/scrapers/ingest-crime-open-data.py` → `data/crime/`; sources and attributions in `data/crime/sources.json`, see `research/02-safety.md`).
- **Rent** — Tokyo **Suumo** scrape to `rent-averages.json`, with **e-Stat** municipal and model fallbacks (see `research/05-rent.md`); Bangkok editorial district/grid estimates and 10 DooAsset station-area estimate proxies.
- **Bangkok context** — Wikidata / Wikimedia Commons names and credited photos; **WorldPop constrained 2020** district population model; **ThaiFloodRisk** flood inputs; separately added tourism, Michelin and institution facts. Per-source dates/licenses apply; the release date is not a data-refresh date. PR #147 completed the extract-specific Overture attribution review and retained the source-age, Wikimedia replay and legacy embassy provenance limits documented in the [evidence note](research/bangkok/notes/2026-10-26-frozen-refresh.md).
- **~272 “AI-researched” stations** — human-reviewed text + integer ratings preserved in export; pipeline confidence merge for those slugs is **CRTKY-83**.

**Honesty:** “Every station has scores” does not mean every score uses the same evidence density. Tokyo computed **hub commute minutes** use a calibrated geographic/line model; researched entries retain authored values, so these are not timetable routing results (CRTKY-81). See **`CLAUDE.md` → Data readiness & coverage honesty** and **`research/VISION.md`** (critical readiness + backlog tables).

## Maintainer docs & task tracking

- [**CHANGELOG.md**](CHANGELOG.md) · [**Release runbook**](docs/RELEASING.md) · [**v0.1.0 notes**](docs/releases/v0.1.0.md)
- [**Bangkok data-refresh remediation**](docs/DATA_REFRESH_REMEDIATION.md) — implemented and merged post-v0.1.0 in PR #147 (2026-10-27).
- **`CLAUDE.md`** — NocoDB table IDs, formulas, perf invariants, **data readiness** section.
- **`research/00-overview.md`** — pipeline phase checklist + confidence snapshot.
- **`research/VISION.md`** — product roadmap + Plane cross-links (**CRTKY-80** … **CRTKY-84**).
- **Plane** project **City Rating Tokyo (CRTKY)** — implementation tickets; epic **CRTKY-80** groups commute, crime export merge, crowd tail.

## License

MIT
