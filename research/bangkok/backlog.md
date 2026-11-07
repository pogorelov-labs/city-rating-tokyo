# Bangkok — backlog (Plane CRTKY-130 subtree, 131–153)

Owner map of the open Bangkok work, grouped by readiness. Plane is the source
of truth for live status; this file keeps the grouping, pointers and the
"why". Last aligned 2026-11-07 (adds editorial-research-batch evidence and one
candidate item). Overview and honesty notes:
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

## Evidence from editorial research batches (2026-11)

Twelve place bundles with claim-level provenance
([`editorial/batches/`](editorial/batches/), kit:
[`editorial/kit/`](editorial/kit/), contract:
[`editorial/2026-11-05-handoff/HANDOFF.md`](editorial/2026-11-05-handoff/HANDOFF.md)).
Evidence relevant to open tickets:

- **CRTKY-153** — red-light zone geography from bundles: Nana Plaza inside
  `st.nana` (~255–300 m, consolidation 39→24 bars), Soi Cowboy ~121 m inside
  `st.asok`, Patpong/Sala Daeng inside a bare 800 m of Chong Nonsi but
  outside its Voronoi catchment (belongs to `st.sala-daeng`).
- **CRTKY-147** — dated walkability items: Asok Montri footpath rebuild
  (announced 2025-03-16, 30-year-old sand-base tiles), Soi Thong Lo 26.3M
  THB rebuild (contracted 2025-07-04, 0% progress at 2025-09-23),
  Ratchathewi flyover closed 2025-01-15, reconstruction due 2028-04.
- **CRTKY-141** — asking-vs-signed rent gap is universal in public sources
  (two batches, no signed-lease series found); one anomaly for review:
  pom-prap 2-bed editorial 24,000 THB sits below all observed asks
  (25,000–32,000, n=14).
- **CRTKY-139** — a reusable flood-catchment protocol from the bundles:
  separate event date from publication date, check khet/catchment specificity
  (2011 tide-driven riverside edge vs dry commercial core; citywide 2026
  stories never naming the unit).
- **CRTKY-152** — the coverage-breadth method (fixed window 2024-11-05 →
  2026-11-07, publisher-family dedup, logged queries) is a candidate
  instrument; it is explicitly not a popularity measure.
- **New candidate items (pipeline, from the completed 183-entity program —
  plan: [`editorial/2026-11-08-continuation-plan.md`](editorial/2026-11-08-continuation-plan.md),
  receipts in [`notes/2026-11-07-editorial-batch-pipeline-followups-crtky130.md`](notes/2026-11-07-editorial-batch-pipeline-followups-crtky130.md)):**
  - **Ghost-station audit (high):** `st.sena-ruam` (rank #9/133) is a
    never-built BTS infill modeled as operating — audit all 139 stations.
  - **Anchor-convention audit (high):** app centers vs OSM nodes differ
    270–770 m on ≥8 units (saint-louis ≥720 m); document or correct.
  - **Green-rating basis decision (high):** buffer basis now proven across
    10+ entities (dusit 118.7 ha largely non-public; pathum-wan includes
    36.3 ha members-only RBSC; kamphaeng-phet 9 = parks in other units) —
    disclose in UI or add a catchment-interior sub-signal.
  - **Polygon quality pass (medium):** khlong-san 10-vertex polygon
    PIP-OUTs ICONSIAM; sathon polygon excludes all BTS nodes; thon-buri/
    Wongwian Yai; Victory Monument khet conflict.
  - **Rent semantics cleanup (medium):** dual Pathum Wan blends
    (33,500/74,000 vs 38,000/85,000); chit-lom 120k override is top-decile,
    not a median; pom-prap 2-bed below all observed asks (CRTKY-141).
  - **Recheck calendar (maintenance):** 201 dated flags from the bundles —
    [`editorial/2026-11-08-recheck-calendar.csv`](editorial/2026-11-08-recheck-calendar.csv);
    run as quarterly light-agent waves.

## Done in this subtree

- **CRTKY-130** — Bangkok district layer: 50 khet + Tokyo ⇄ Bangkok switch
  (2026-09, PR #112).
- **CRTKY-135** — levels of detail: 133 station areas + 200 m grid (39,149
  cells, ~140 KB packed) (2026-09, PR #118). Verification pass 2026-10-13:
  29/29 pipeline tests, 303/303 frontend tests, data matches spec, prod
  byte-identical with `main`.
