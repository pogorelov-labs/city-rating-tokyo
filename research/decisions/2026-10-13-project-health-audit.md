# Project health audit — 2026-10-13

Full-project review requested by the owner: how the project is run, doc gaps,
missing cross-links, tests, task process, acceptance criteria, refactor
candidates. Method: process/docs/git analysis by the coordinator + two
read-only deep code reviews (frontend `app/`, pipelines `scripts/` + `mcp/`).
Action items are ticketed under the Plane epic **CRTKY-154 (Project health
2026-10)**; this note keeps the evidence.

## Verdict

The project is **run unusually well for a solo effort** — honest-data doctrine
in CLAUDE.md, SHA-pinned ingests, a real CI with a codegen drift gate, PR-based
flow (86% of merges), strong committed-artifact tests for Bangkok — but it has
outgrown three of its own structures: the **MCP service has zero tests and
three real auth bugs**, the **frontend test suite never runs in CI and
component tests are structurally impossible**, and **docs have drifted** after
the second city shipped. The failure mode is not sloppiness; it is *silent
gaps that the process believes it has covered* (CI comments literally say
"nobody noticed lint crashing for two months").

## 1. Critical findings (bugs, security)

| # | Finding | Where | Confidence |
|---|---|---|---|
| C1 | **MCP auth fails OPEN when misconfigured.** `validate()` returns `(True, "ok")` for any bearer when unconfigured, while the startup log claims "will reject every request" and the code comment says "we never silently bypass" | `mcp/src/city_rating_mcp/auth.py:199-203`, wired at `server.py:378-384` | high |
| C2 | **SSE transport bypasses auth entirely** — middleware only constructed inside `_serve_http()` | `mcp/src/city_rating_mcp/server.py:423-426` | high |
| C3 | **KeyStore background refresh can die permanently and silently** (initial refresh outside try/except; malformed row kills the task; lifespan cancels without observing) | `mcp/src/city_rating_mcp/auth.py:186-194` | medium |
| C4 | **Tokyo map: tapping touch zoom buttons clears the selection** — `MapClickHandler` checks only `.leaflet-interactive`; the Bangkok twin already checks `.leaflet-control` too (the copies diverged, as they do) | `app/src/components/Map.tsx:129-140` vs `DistrictMap.tsx:162-179` | high |
| C5 | **Otemachi safety canary is print-only** — spot-check prints ⚠️ and exits 0; the refresh chain commits corrupted output | `scripts/compute-ratings.py:647-657` | high |
| C6 | **Silent 30-min transit default** under `--allow-missing` fabricates commutes in shipped TS | `scripts/export-ratings.py:272-274` | high (behavior) |

## 2. Tests & CI

What exists and is good: 4 CI jobs (app build with lint+tsc+build+audit;
schema codegen drift + pipeline pytest; mcp ruff+import; bangkok math);
Bangkok `test_bangkok.py` decodes the committed grid binary (rare and good);
lib-level vitest coverage is genuinely solid; zero TODO/FIXME markers in the
codebase.

Gaps:

- **`npm run test` (vitest, 303 tests) is not in CI.** The build job runs
  lint/tsc/build/audit only. Every frontend test is local-only.
- **Component tests are structurally impossible**: `vitest.config.ts` includes
  `src/**/*.test.ts` (not `.tsx`), `environment: 'node'`, no jsdom, no
  `@testing-library/*`. A contributor writing `FilterPanel.test.tsx` watches
  it silently not run.
- **MCP: zero unit tests** (CI comment admits it; smoke-test needs the 2.2 GB
  model and can't run in CI). C1–C3 shipped because of this.
- **`scripts/bangkok/build.py` never executes in CI** (needs
  numpy/shapely/duckdb); untested: geometry assembly fallbacks, FFT rasters,
  POI category mapping, rail/Dijkstra, interchange union-find, grid packing
  (the last only indirectly via the binary gate).
- **No i18n key-parity check** across en/ja/ru (only `sources.*` keys are
  asserted); key counts match today by discipline. No next-intl `AppConfig`
  augmentation, so `t('typo')` compiles.
- No E2E at all (Leaflet interactions, popup flows untestable otherwise).

## 3. Refactor candidates (frontend)

- **The score→anchors→dealbreakers→top-N pipeline exists in 5 copies**
  (Map.tsx:231-272, DistrictMap.tsx:336-430 ×3, FilterPanel.tsx:174-199,
  ScatterPlotExplorer.tsx:71, GridRanking.tsx:43-64). A past prod bug
  (Map.tsx:250-253 comment) was exactly a divergence between copies. On
  mobile FilterPanel mounts twice → the 1493-station scoring runs twice per
  weight change. → extract `useScoredAreas()` in `lib/scoring-react.ts`.
- **Area-card markup ×5** (tooltip/popup bodies, DistrictPopupBody,
  StationAreaPopupBody, MobileStationCard); the compare toggle alone ×3 while
  a shared `CompareButton` already exists unused.
- **Ratings-breakdown section ×3** across the three detail pages (~90%
  identical), plus header bar, Wikipedia links (verbatim ×2), facts grid.
- **DistrictMap.tsx = 4 components** (1046 lines): scoring pipelines, label
  geometry (pure, immediately testable if extracted), interaction plumbing,
  7 render panes.
- **Map ↔ DistrictMap controller duplication**: FlyToStation/FlyToBounds,
  MapClickHandler/DeselectHandlers (already diverged → C4), delayed
  hover-clear ×3, popup suppression. `map-shared.tsx` exists for exactly this
  and is underused.
- Perf is otherwise good (verified: data files stay server-side, recharts
  dynamic everywhere, canvas rendering deliberate).

## 4. Refactor candidates (pipelines / MCP)

- **`build.py` 1696 lines, `main()` ≈ 810** — split into
  geom/rasters/sources/rail/areas/gridpack modules; closures over shared state
  (`near`/`both`/`commute_at`) → `SignalGrid` dataclass; module-global
  `RAIL_RELATIONS` mutation is an import-order trap.
- **Normalization duplicated across three codebases**: midpoint-percentile is
  a verbatim copy (compute-ratings.py:58-103 ↔ bangkok/ratings.py:24-46);
  rent→affordability ×2; a **third mirror in mcp/scoring.py**. The
  two-source-confidence rules **have already diverged semantically** (Bangkok
  `moderate` for OSM-only vs Tokyo `estimate` when HotPepper=0) with no
  documentation of intent. → `packages/schema/python/.../normalize.py`
  (stdlib-only; Bangkok CI installs just pytest).
- Robustness cleanups: crime-ingest dashboard cache poisons itself on partial
  API responses; `scripts/scrapers/utils.py` exits at import time without
  `NOCODB_API_TOKEN` (breaks `--help`); Bangkok fetch.py Wikidata/Commons
  fetchers lack retry; non-atomic delete+insert of `computed_ratings`;
  `--calibrate` calibration file lives in `/tmp`;
  `run-image-pipeline.sh` references a phantom Phase 3 and stale
  `FLICKR_API_KEY`.

## 5. Docs: gaps and broken links

- `research/00-overview.md` (Tokyo) — **last updated 2026-04-13**; six months
  stale while CLAUDE.md moved on.
- CLAUDE.md Key Files table rotted: `demo-ratings.ts` "~7700 lines" (actual
  12,220); SSL cert "expires 2026-07-01" (renewed since; dates don't belong
  in docs); title still "City Rating Tokyo — Dev Guide" for a two-city app.
- README ↔ CLAUDE.md disagree on AI-researched station count (272 vs 252);
  README intro line still frames the product as Tokyo-only.
- No fresh-clone prerequisites documented: the Tokyo pipeline needs
  `NOCODB_API_TOKEN` and the specific NocoDB instance
  (`nocodb.pogorelov.dev` hardcoded in `scripts/scrapers/utils.py:18`) — a
  line in README, not a code change.
- `research/decisions/` exists (2 ADRs, good practice) but the convention is
  undocumented; Bangkok pipeline decisions live only in code comments.
- No CONTRIBUTING/PR-checklist doc; CLAUDE.md is de-facto both dev guide and
  agent instructions (works, but should be stated).

## 6. Task process (Plane)

Strengths: sub-issue trees for epics (80, 116, 130); spec-packet comments on
selected tickets; honest naming; the Bangkok subtree now labeled and mapped
(`research/bangkok/backlog.md`).

Gaps:

- **No acceptance-criteria convention.** Pre-2026-09 tickets are one-liners;
  newer ones carry questions/deliverables but "done when" is rarely explicit;
  the strong ones (CRTKY-83, 116-subtree, 130) got their rigor from the
  research docs, not the tickets.
- **Done without verification records.** Historically nothing on a Done
  ticket says what was checked (first such record: CRTKY-135, 2026-10-13).
  The compute spot-check doctrine exists but is print-only (C5).
- The **Todo state is unused** (everything is Backlog → In Progress → Done),
  no estimates, no assignees (solo — fine), cycles never used.
- Stale draft PR #119 (ratings refresh) sitting since 2026-09-30 — the
  CRTKY-128 vibe fix only takes effect when it merges.
- Sync-merge noise is low (10 of 75 merges) — healthy.

## Action map

Epic **CRTKY-154** (children created 2026-10-13): MCP auth hardening
(urgent), Tokyo map deselect fix, vitest-in-CI, component-test infra + first
tests, i18n hardening, pipeline integrity gates, pipeline robustness
cleanups, MCP unit-test suite, `useScoredAreas` extraction, area-card/detail
page extraction, DistrictMap decomposition + map-shared, build.py
modularization, shared normalization, docs alignment pass, ticket-AC
convention + Playwright smoke.
