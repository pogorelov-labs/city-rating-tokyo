# City Rating Tokyo

Interactive map of **1493** Greater Tokyo-area train stations. Adjust weights across nine categories (food, nightlife, transport, rent, safety, green, gym, vibe, crowd), filter by commute and budget, and open per-station pages with radar chart, ratings breakdown, and optional neighborhood copy.

**Live:** [city-rating.pogorelov.dev](https://city-rating.pogorelov.dev/?ref=github)  
**Repo / issues:** [github.com/ruspg/city-rating-tokyo](https://github.com/ruspg/city-rating-tokyo)

## What it does

- **Map** — weighted composite score; heatmap by category; compare and explore modes (see app for current UX).
- **Filters** — presets, search, max commute (uses `transit_minutes` where present), rent band, min score.
- **Station pages (SSG)** — stats, hub strip, radar vs Tokyo median, nine rating bars with confidence dots when pipeline metadata exists, feedback widget.

## Rating categories (default weights)

| Category | Weight | Notes |
|----------|--------|--------|
| Transport | 20% | Line count + passenger volume (MLIT S12 where available) |
| Affordability | 20% | Rent model: Suumo where scraped, else ward / regression |
| Food & Dining | 15% | HotPepper + OpenStreetMap |
| Nightlife | 10% | HotPepper + OSM extended |
| Safety | 10% | Tokyo: police ArcGIS polygons; others: ward/prefecture fallbacks (improving) |
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
app/src/app/                    # Routes: /, /station/[slug], /api/feedback
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
- **Passengers** — **MLIT** 国土数値情報 S12 (+ operator disclosures; see `research/03-crowd.md`).
- **Crime (Tokyo)** — **Keishicho** ArcGIS / open data (see `research/02-safety.md`).
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
