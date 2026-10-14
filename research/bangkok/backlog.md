# Bangkok — backlog (Plane CRTKY-130 subtree, 131–153)

Owner map of the open Bangkok work, grouped by readiness. Plane is the source
of truth for live status; this file keeps the grouping, pointers and the
"why". Last aligned 2026-10-13. Overview and honesty notes:
[`00-overview.md`](00-overview.md).

## Ready to start — no blockers

| Ticket | What | Priority | Grounded source |
|---|---|---|---|
| CRTKY-139 | Research: open flood data without Traffy registration — **may unblock CRTKY-131** | **high** | [ThaiFloodRisk](https://thaifloodrisk.com/en/open-data) per-district CSVs (BMA Drainage Dept 2021–2026); GISTDA polygons; WRI Aqueduct |
| CRTKY-146 | Research: air quality as a new category — seasonal PM2.5 | medium | [Air4Thai (PCD)](https://gdcatalog.go.th/dataset/gdpublish-air-quality-bangkok-metropolitan-region) hourly JSON API, no registration |
| CRTKY-150 | Research: safety data — BMA risk-area registry, police presence, road safety, homeless services | medium | [บัญชีพื้นที่เสี่ยง 2568](https://data.bangkok.go.th/en/group/d4) — district-level risk spots, surveyed 2025 |
| CRTKY-151 | Research: time-aware noise (day vs night) | medium | [PCD Noise Monitor](https://gdcatalog.go.th/en/dataset/gdpublish-noise-monitor) — hourly Leq, roadside vs community stations |
| CRTKY-140 | Research: 100 m population raster for resident weighting + station/grid quietness | medium | WorldPop constrained 2020 (CC-BY-4.0) / GHS-POP R2023A |
| CRTKY-132 | Implementation: MCP server — expose Bangkok districts (`city` param, methodology caveats, re-embed descriptions) | low | existing `mcp/` datamart |

## Category enrichment — research

| Ticket | Topic | Priority |
|---|---|---|
| CRTKY-145 | Institutions & landmarks: embassies, international hospitals/schools, coworking, attractions | medium |
| CRTKY-153 | Nightlife character & red-light zones — geofenced entertainment zones (Soi Cowboy, Nana, Patpong, Huai Khwang…), family filter chip or nightlife sub-signal | medium |
| CRTKY-142 | Food & café quality: Michelin / Bib Gourmand per district, café depth, cuisine diversity | low |
| CRTKY-143 | Fitness & movement: dance/yoga/Muay Thai studios, boutique fitness | low |
| CRTKY-144 | Shopping & markets: malls (OSM+Wikidata), wet/weekend/night markets | low |
| CRTKY-147 | Urban fabric: walkability (sidewalk coverage), main-road exposure, cleanliness | medium |
| CRTKY-148 | Housing stock context: condo inventory, height mix, new-supply pipeline — feeds 136/141 | low |
| CRTKY-149 | Health-conscious food nearby: tags → bilingual keyword markup → LLM/website enrichment; KBJU stays chain-page facts at most | low |
| CRTKY-152 | Tourist load: hotel density + attraction gravity as `estimate` label or page facts | low |

## Rent anchors — research

- **CRTKY-141** — published rent aggregates (Knight Frank / JLL / C&W / CBRE
  quarterly, segments not districts) as citable anchors for
  `editorial.json → _meta`. Feeds CRTKY-136.

## Blocked / event-driven

| Ticket | Blocked by |
|---|---|
| CRTKY-131 | Traffy Fondue monthly CSV export registration (owner action: name/org/email form) — CRTKY-139 may make this an enrichment path instead of the blocker |
| CRTKY-136 | rent: a portal API/export opening (FazWaz, DDproperty, Hipflat all 403); station-level premium is its step 2 |
| CRTKY-137 | Foursquare OS Places: accepting Hugging Face terms (owner action) |
| CRTKY-138 | rail line openings: Orange East, Purple South, Grey |

## Done in this subtree

- **CRTKY-130** — Bangkok district layer: 50 khet + Tokyo ⇄ Bangkok switch
  (2026-09, PR #112).
- **CRTKY-135** — levels of detail: 133 station areas + 200 m grid (39,149
  cells, ~140 KB packed) (2026-09, PR #118). Verification pass 2026-10-13:
  29/29 pipeline tests, 303/303 frontend tests, data matches spec, prod
  byte-identical with `main`.
