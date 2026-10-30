# City Rating — Tokyo + Bangkok

Interactive neighborhood ratings for **Greater Tokyo and Bangkok** in **EN/JA/RU**. Explore **1,493 Tokyo train stations** or Bangkok's **50 districts, 133 station areas and 200 m grid**. Adjust weights across **10 categories**, filter by commute and budget, and open localized guides with comparison plots, commute bars, area maps and expandable source information.

**Live:** [city-rating.pogorelov.dev](https://city-rating.pogorelov.dev/?ref=github)  
**Repo / issues:** [github.com/pogorelov-labs/city-rating-tokyo](https://github.com/pogorelov-labs/city-rating-tokyo)

**Latest release:** [v0.1.2 — Bangkok MCP tools and map fixes](https://github.com/pogorelov-labs/city-rating-tokyo/releases/latest) · [Changelog](CHANGELOG.md)

**Release candidate:** [v0.2.0 — Station and district guides](docs/releases/v0.2.0.md).

**Bangkok (since Sept 2026):** all **50 districts** (khet), **133 station areas** and **39,149 grid cells** at **200 m**, with **179 rail stations on 10 lines** — switch cities from the header; your weights carry over. See [Bangkok](#bangkok-district-layer) below.

## What it does

- **Map** — weighted composite score; heatmap by category; compare and explore modes (see app for current UX).
- **Filters** — presets, search, max commute (uses `transit_minutes` where present), rent band, min score.
- **Station and district guides (SSG, EN/JA/RU)** — clear rent cohorts and provenance, category comparisons against the correct city/level median or nearby areas, selectable commute bars, geographic scope, and expandable local facts and sources. Desktop, hover and touch map cards share one compact presentation; weights survive detail and locale navigation.

## Bangkok (district layer)

- **Levels:** 50 districts (polygons), 133 walkable station areas and a 200 m grid — a quarter of Bangkok's districts have no rail inside.
- **Data:** OpenStreetMap + [Overture Maps Places](https://docs.overturemaps.org/guides/places/) (two independent POI sources, r ≈ 0.9 agreement), Wikidata (names, population), a door-to-door commute model to five hubs, Wikimedia Commons photos.
- **Rent provenance:** 10 central station areas use DooAsset's published condominium asking-rent medians by bedroom, across all floor areas, at **estimate** confidence. These are single-provider proxies with source dates/sample sizes, not fixed-size market rents. All district and grid rents remain **editorial**; other station areas use district blends. ComparePanel distinguishes these provenances. See the [central rent audit](research/bangkok/notes/2026-10-25-central-rent-audit-crtky141.md).
- **Honesty:** safety remains editorial; scores are relative within Bangkok — a Bangkok 8 is not a Tokyo 8. Evidence density differs by category and level. See [`research/bangkok/00-overview.md`](research/bangkok/00-overview.md).
- **Acquisition code:** [`scripts/bangkok/fetch-geofabrik.py`](scripts/bangkok/fetch-geofabrik.py) fetches OSM from a Geofabrik Thailand PBF without Overpass. The [pipeline guide](scripts/bangkok/README.md) covers this path, other API inputs and offline builds; the Overpass path remains available.
- **Refresh status:** **v0.1.1 packages the Bangkok data refresh** merged after v0.1.0 in [PR #147](https://github.com/pogorelov-labs/city-rating-tokyo/pull/147) (2026-10-27). **v0.1.0 did not include this data.** See the [methodology](https://city-rating.pogorelov.dev/methodology) and [evidence note](research/bangkok/notes/2026-10-26-frozen-refresh.md) for source details and known limits.

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
| Less crowding | 4% | Tokyo passengers + fallbacks; Bangkok WorldPop (districts) / place density (finer levels) |

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
app/src/lib/scoring-react.tsx   # Shared named-area scores, anchors, filters, ranking
app/src/lib/scoring-grid-react.ts # Bangkok resident-weighted grid adapter
app/src/components/bangkok/     # Bangkok layers, popups and grid panel
app/src/components/area-card.tsx # Shared popup/touch metadata and actions
app/src/app/                    # Locale routes and shared detail sections
app/src/test/                   # App unit/component harness; browser suite is root e2e/
scripts/bangkok/                # Bangkok fetch + build pipeline (uv), tests
scripts/                        # Scrapers, compute-ratings.py, export-ratings.py
research/                       # Source research + VISION roadmap
CLAUDE.md                       # Current module map, contracts and data-readiness caveats
```

Use the [developer module index](CLAUDE.md#key-files) to navigate scoring,
map controllers, shared cards/details and the app/browser test boundaries.

## Getting started

Use **Node.js 20 and npm**, matching [CI](.github/workflows/ci.yml). From a fresh
clone, the map and detail pages use the committed datasets; Python, datastore
credentials and raw acquisition caches are not required for this preview.

```bash
cd app
npm ci
npm run dev
```

Open [localhost:3000](http://localhost:3000). Optional app configuration is
listed in [app/.env.example](app/.env.example); keep real values in untracked
local environment files. Service-backed forms need their own authorized
configuration. See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and invariants.

## Running the data pipelines

Pipeline work is separate from the frontend preview:

- **Tokyo ingest / compute / export:** use Python 3.12 (the CI version).
  Compute/export need `requests`; [scripts/requirements-ingest.txt](scripts/requirements-ingest.txt)
  also includes the PDF/shapefile ingest dependencies. Obtain authorized
  datastore access and the matching table/schema configuration from a maintainer.
  Set `NOCODB_API_URL` explicitly and supply `NOCODB_API_TOKEN` privately.
  Legacy helpers have an environment-specific fallback endpoint; a clone does
  not provision the datastore or make that fallback portable. Source acquisition
  may additionally require `HOTPEPPER_API_KEY` or other source-specific access.
  The [Tokyo refresh runbook](research/notes/2026-10-15-hotpepper-resilience-runbook.md)
  covers the approved source-age policy (`--max-source-age-days=N`), preflight
  and rollout. Even a live dry run requires datastore access.
- **Tokyo live cameras:** between the roughly weekly MT3D refreshes, run
  `python scripts/check-livecams.py --threshold 0` (requires `requests`). It
  checks each distinct shipped video ID once, with a 0.2-second delay and a
  10-second request timeout. Exit 0 means no more missing thumbnails than the
  threshold, 1 means the threshold was exceeded, and 2 means input or network
  results were incomplete. After three consecutive errors it stops and marks
  remaining IDs unknown; rerun when connectivity is restored. HTTP 404 is a
  missing thumbnail, not proof of why a video is unavailable; HTTP 200 does
  not prove a stream is live or embeddable. This is report-only: investigate
  failures and run `python scripts/scrapers/scrape-livecams.py` when a refresh
  is appropriate. `--offline` validates the input and explicitly skips network;
  it is not a live health pass. No response cache is retained, so each run
  reflects its own observation.
- **Bangkok acquisition / rebuild:** install `uv`; the scripts declare their
  Python and geospatial dependencies in their script metadata. The [Bangkok
  pipeline guide](scripts/bangkok/README.md) covers acquisition and cache setup.
  A frozen replay requires the recorded raw inputs, which are not in a fresh
  clone. The published JSON and grid are already committed for the app.
- **MCP development:** the service exposes Tokyo stations and Bangkok districts. It requires Python
  3.11 or newer, the shared schema package and a datamart; semantic tools also
  require the separately generated embeddings. These generated artifacts are
  not supplied by a fresh clone. See [MCP development](CONTRIBUTING.md#mcp-server-development)
  and [the MCP guide](mcp/README.md). Pipeline tests and their complete dependencies
  are defined in [CI](.github/workflows/ci.yml).

Deployment access and credentials are maintained outside this public repository.
Current coverage and evidence limits are in the [developer guide](CLAUDE.md)
and [Bangkok overview](research/bangkok/00-overview.md).

## Deployment

Next.js standalone build — `app/Dockerfile` (build context: `app/`). Production deployment is automated from `main`; static city data needs no runtime DB; v0.1.2 has no DB migration. See the [release runbook](docs/RELEASING.md).

## Data sources (high level)

- **Stations / lines** — based on open railway-station datasets (see `SPEC.md` / `data/stations.json` provenance).
- **POI counts, green, gym, vibe inputs** — **OpenStreetMap** via Overpass → NocoDB for Tokyo; Bangkok combines Geofabrik OSM + **Overture Places** in the frozen snapshot merged post-v0.1.0 in [PR #147](https://github.com/pogorelov-labs/city-rating-tokyo/pull/147).
- **Food / nightlife counts** — **HotPepper** API + OSM.
- **Passengers** — **MLIT** 国土数値情報 S12, FY2024 (`scripts/scrapers/ingest-mlit-s12.py` → `data/passengers/s12-passengers.json`; see `research/03-crowd.md`). 出典：「国土数値情報（駅別乗降客数データ）」（国土交通省）を加工して作成.
- **Crime** — 2024 police statistics from 警視庁 (町丁 CSV) and the Kanagawa, Saitama and Chiba prefectural police, with e-Stat population and boundaries (`scripts/scrapers/ingest-crime-open-data.py` → `data/crime/`; sources and attributions in `data/crime/sources.json`, see `research/02-safety.md`).
- **Rent** — Tokyo **Suumo** scrape to `rent-averages.json`, with **e-Stat** municipal and model fallbacks (see `research/05-rent.md`); Bangkok editorial district/grid estimates and 10 DooAsset station-area estimate proxies.
- **Bangkok context** — Wikidata / Wikimedia Commons names and credited photos; **WorldPop constrained 2020** district population model; **ThaiFloodRisk** flood inputs; separately added tourism, Michelin and institution facts. Per-source dates/licenses apply; the release date is not a data-refresh date. PR #147 completed the extract-specific Overture attribution review and retained the source-age, Wikimedia replay and legacy embassy provenance limits documented in the [evidence note](research/bangkok/notes/2026-10-26-frozen-refresh.md).
- **251 “AI-researched” Tokyo entries** — the preserved block in [demo-ratings.ts](app/src/data/demo-ratings.ts), alongside **1,242 computed entries**, covers all **1,493 station slugs**. Pipeline confidence merge for researched entries is **CRTKY-83**; this count describes the committed export, not the completeness of every category.

**Honesty:** “Every station has scores” does not mean every score uses the same evidence density. Tokyo computed **hub commute minutes** use a calibrated geographic/line model; researched entries retain authored values, so these are not timetable routing results (CRTKY-81). See **`CLAUDE.md` → Data readiness & coverage honesty** and **`research/VISION.md`** (critical readiness + backlog tables).

## Maintainer docs & task tracking

- [**CHANGELOG.md**](CHANGELOG.md) · [**Release runbook**](docs/RELEASING.md) · [**v0.1.0 notes**](docs/releases/v0.1.0.md)
- [**Bangkok data-refresh remediation**](docs/DATA_REFRESH_REMEDIATION.md) — implemented and merged post-v0.1.0 in PR #147 (2026-10-27).
- [**CLAUDE.md**](CLAUDE.md) — data contracts, formulas, performance invariants and data readiness.
- [**research/00-overview.md**](research/00-overview.md) — archived Tokyo research snapshot, with current-status pointers.
- [**research/bangkok/00-overview.md**](research/bangkok/00-overview.md) — Bangkok levels, sources and honesty notes.
- [**research/VISION.md**](research/VISION.md) — product roadmap and tracker cross-links.
- **Plane** project **City Rating Tokyo (CRTKY)** — implementation tickets; epic **CRTKY-80** groups commute, crime export merge, crowd tail.

## License

MIT
