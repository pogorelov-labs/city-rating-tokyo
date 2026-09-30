# City Rating Tokyo

Interactive map of **1493** Greater Tokyo-area train stations. Adjust weights across ten categories (food, nightlife, transport, rent, safety, green, gym, vibe, crowd, daily essentials), filter by commute and budget, and open per-station pages with radar chart, ratings breakdown, and optional neighborhood copy.

**Live:** [city-rating.pogorelov.dev](https://city-rating.pogorelov.dev/?ref=github)  
**Repo / issues:** [github.com/ruspg/city-rating-tokyo](https://github.com/ruspg/city-rating-tokyo)

**Bangkok (since Sept 2026):** all **50 districts** (khet) with the BTS / MRT / ARL / SRT Red rail network on top — switch cities from the header; your weights carry over. See [Bangkok](#bangkok-district-layer) below.

## What it does

- **Map** — weighted composite score; heatmap by category; compare and explore modes (see app for current UX).
- **Filters** — presets, search, max commute (uses `transit_minutes` where present), rent band, min score.
- **Station pages (SSG)** — stats, hub strip, radar vs Tokyo median, ten rating bars with confidence dots when pipeline metadata exists, feedback widget.

## Bangkok (district layer)

- **Unit:** 50 districts (polygons), not stations — a quarter of Bangkok's districts have no rail inside.
- **Data:** OpenStreetMap + [Overture Maps Places](https://docs.overturemaps.org/guides/places/) (two independent POI sources, r ≈ 0.9 agreement), Wikidata (names, population), a door-to-door commute model to five hubs, Wikimedia Commons photos.
- **Honesty:** rent and safety are researcher estimates (no open district data) and scores are relative within Bangkok — a Bangkok 8 is not a Tokyo 8. See [`research/bangkok/00-overview.md`](research/bangkok/00-overview.md).
- **Rebuild:** `uv run scripts/bangkok/fetch.py && uv run scripts/bangkok/build.py`.

## Rating categories (default weights)

| Category | Weight | Notes |
|----------|--------|--------|
| Transport | 20% | Line count + passenger volume (MLIT S12 where available) |
| Affordability | 20% | Rent model: Suumo where scraped, else ward / regression |
| Food & Dining | 15% | HotPepper + OpenStreetMap |
| Nightlife | 10% | HotPepper + OSM extended |
| Safety | 10% | Police open data, 2024: Tokyo neighborhoods within 800 m; municipalities elsewhere |
| Parks & Green | 10% | OSM (area scrape pending — **CRTKY-42**) |
| Gym & Sports | 5% | OSM |
| Vibe | 5% | OSM cultural / pedestrian signals + AI overrides |
| Low Crowds | 5% | Passengers + fallbacks |

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

Dockerized Next.js standalone build — `app/Dockerfile`. Production: **Coolify** on a VPS with Traefik and TLS.

## Data sources (high level)

- **Stations / lines** — based on open railway-station datasets (see `SPEC.md` / `data/stations.json` provenance).
- **POI counts, green, gym, vibe inputs** — **OpenStreetMap** via Overpass → NocoDB.
- **Food / nightlife counts** — **HotPepper** API + OSM.
- **Passengers** — **MLIT** 国土数値情報 S12, FY2024 (`scripts/scrapers/ingest-mlit-s12.py` → `data/passengers/s12-passengers.json`; see `research/03-crowd.md`). 出典：「国土数値情報（駅別乗降客数データ）」（国土交通省）を加工して作成.
- **Crime** — 2024 police statistics from 警視庁 (町丁 CSV) and the Kanagawa, Saitama and Chiba prefectural police, with e-Stat population and boundaries (`scripts/scrapers/ingest-crime-open-data.py` → `data/crime/`; sources and attributions in `data/crime/sources.json`, see `research/02-safety.md`).
- **Rent** — **Suumo** scrape to `rent-averages.json`; ward and model fallbacks in compute (see `research/05-rent.md`).
- **~272 “AI-researched” stations** — human-reviewed text + integer ratings preserved in export; pipeline confidence merge for those slugs is **CRTKY-83**.

**Honesty:** “Every station has scores” does not mean every score uses the same evidence density. **Hub commute minutes** are a **placeholder (30m × 5)** for most exported computed rows until **CRTKY-81**. See **`CLAUDE.md` → Data readiness & coverage honesty** and **`research/VISION.md`** (critical readiness + backlog tables).

## Maintainer docs & task tracking

- **`CLAUDE.md`** — NocoDB table IDs, formulas, perf invariants, **data readiness** section.
- **`research/00-overview.md`** — pipeline phase checklist + confidence snapshot.
- **`research/VISION.md`** — product roadmap + Plane cross-links (**CRTKY-80** … **CRTKY-84**).
- **Plane** project **City Rating Tokyo (CRTKY)** — implementation tickets; epic **CRTKY-80** groups commute, crime export merge, crowd tail.

## License

MIT
