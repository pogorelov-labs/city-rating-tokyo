# City Rating — Tokyo + Bangkok Dev Guide

## Start here

- [README: setup and pipeline prerequisites](README.md#getting-started)
- [Contributor invariants, public-copy rules and verification](CONTRIBUTING.md)
- [Release runbook](docs/RELEASING.md) and [changelog](CHANGELOG.md)
- [Bangkok methodology](research/bangkok/00-overview.md), [historical Tokyo research](research/00-overview.md) and [roadmap](research/VISION.md)

The Next.js app serves Greater Tokyo and Bangkok in EN/JA/RU from committed
build-time data. Tokyo has 1,493 station slugs: 251 researched entries and 1,242
computed entries. Bangkok has 50 districts, 133 station areas, 179 rail stations
on 10 lines and 39,149 grid cells at 200 m. Coverage is not uniform evidence
quality; see [data readiness](#data-readiness--coverage-honesty-maintainers).
Deployment details and operational access are maintained outside this public repository.

Bangkok defaults to MapLibre with a standard-map fallback. Renderer state is local
to the view; scoring, selection, comparison and URLs remain shared. The
[map guide](docs/BANGKOK_MAP.md) documents worker packaging, recovery, CSP, the
build-time renderer default and the opt-in comparison lab.

## Architecture

[CityHome](app/src/components/CityHome.tsx) composes the shared homepage with
city context, area lists and `ScoredAreasProvider`. Tokyo uses a station-point
map; Bangkok uses district/station-area polygons and an optional grid. Both
consume the same city registry, store and named-area scoring contract.

```text
CityHome → city context + area lists + ScoredAreasProvider
            ├─ Map (Tokyo) / BangkokMapRenderer (3D or standard)
            ├─ desktop FilterPanel + mobile drawer FilterPanel
            └─ ScatterPlotExplorer
Bangkok grid → useScoredGrid → GridTextureLayer / GridLayer + GridRanking + useGridHotspots
Detail routes → DetailHeader + RatingsBreakdown; Bangkok also uses DetailFacts
```

### Named-area scoring

[scoring-react.tsx](app/src/lib/scoring-react.tsx) owns deferred weights,
full-population scores/anchors, dealbreaker filtering and ranked results.
`ScoredAreasProvider` shares primary-area and optional station-area calculations
across the map and both mounted responsive panels. Consumers identify the
`primary` or `station` level through `useScoredAreas`; its standalone fallback
is for consumers without shared results, not an extra homepage calculation.

Preserve these boundaries:

- Pure score/filter/color functions stay in [scoring.ts](app/src/lib/scoring.ts).
- Anchors use the full unfiltered rated population, so narrowing filters does
  not recolor the remaining areas. Unrated entries retain null scores.
- Soft weights change ranking; hard dealbreakers select passing areas.
  Unknown rent/commute/category values pass where the existing policy permits;
  `rentUnknown` controls the corresponding disclosure and dimming.
- City-specific defaults and environmental/adult-zone flags come from the city
  context/store, not duplicated component defaults. Tie ordering and deferred
  updates are covered by [scoring-react tests](app/src/lib/scoring-react.test.tsx).

### Grid scoring

[scoring-grid-react.ts](app/src/lib/scoring-grid-react.ts) adapts the packed
Bangkok grid using bounded, identity-keyed caches. Score/anchor work is separate
from filter-mask work. Grid anchors are resident-weighted; named-area percentiles
are not interchangeable with them.

The map and ranking panel must pass the same areas, deferred weights, filters,
defaults and `hideFloodRisk` value to `useScoredGrid`. The flood flag is part of
both memoization and mask identity. `useGridHotspots` derives hotspots from the
same scored result and passing mask; do not recreate a panel-only filter path.
See [grid adapter tests](app/src/lib/scoring-grid-react.test.tsx) and the
[panel flood regression](app/src/components/bangkok/GridRanking.test.tsx).

### Maps, selection and performance

[DistrictMap](app/src/components/DistrictMap.tsx) coordinates Bangkok layers;
it no longer owns their polygon, rail, outline, legend or popup implementations.
[Map](app/src/components/Map.tsx) remains the Tokyo point-map entry point.

- [map-selection.tsx](app/src/components/map-selection.tsx) owns point/bounds
  flight lifecycles and `MapDeselect`. Tokyo retains point flights; Bangkok
  retains bounds flights and bottom-inset framing. Preserve cleanup and
  `isFlying` completion when a selection changes during animation.
- Background clicks and Escape share the dismissal controller. Keep the
  `.leaflet-interactive` / `.leaflet-control` guard so controls do not clear a selection.
- [use-delayed-hover.ts](app/src/lib/use-delayed-hover.ts) owns the shared hover
  clear delay and cancellation used by Tokyo markers and Bangkok named areas.
- [map-shared.tsx](app/src/components/map-shared.tsx) provides resize handling,
  touch zoom controls, image fallback and the SVG overlay renderer.
  [map-resize.ts](app/src/lib/map-resize.ts) observes viewport changes.
- Tokyo's main marker population uses Canvas; animated halo/pulse overlays use
  SVG. Selection flight code suppresses popups/overlays and fades the Canvas
  during zoom transitions. Preserve these behaviors when moving controllers.
- Keep chart consumers lazy through [HeaderActions](app/src/components/HeaderActions.tsx),
  [MapWrapper](app/src/components/MapWrapper.tsx) and [RadarChartWrapper](app/src/components/RadarChartWrapper.tsx).
  [getMapStations](app/src/lib/data.ts) keeps the homepage payload lightweight;
  full descriptions and confidence belong to detail data.
- Basemap selection and permitted prefetch behavior live in [basemap.ts](app/src/lib/basemap.ts).
  Image errors fall back to the score gradient, not a permanently blurred placeholder.

Historical UI/benchmark receipts are in Git history and PR validation records;
this section describes current ownership rather than a sequence of past refactors.

### Shared area cards and detail sections

[area-card.tsx](app/src/components/area-card.tsx) exports `AreaCardMeta`,
`AreaCardActions` and `CompareToggle` for Tokyo/Bangkok popups and the
[mobile card](app/src/components/MobileStationCard.tsx). Callers provide localized
names, scores, comparison state and actions. Preserve compact-popup versus touch
styles, the ability to remove an existing comparison, and routing through the
city/area contract.

[DetailHeader](app/src/components/DetailHeader.tsx) shares navigation, names,
map links, locale controls and score presentation. Its Tokyo/Bangkok variants
preserve their existing heading and badge markup.
[RatingsBreakdown](app/src/components/RatingsBreakdown.tsx) is server-translated:
`kind` selects Tokyo, district or station-area copy; callers supply the correct
medians, confidence, sources, dates and rent provenance. Preserve the different
rent metrics, captions and tooltip disclosures. [DetailFacts](app/src/components/DetailFacts.tsx)
exports `FactsGrid` and `WikiLinks`, retaining the caller's fact and language order.

## Key Files

### State, data and scoring

| Module | Responsibility |
|---|---|
| [CityHome](app/src/components/CityHome.tsx), [city context](app/src/lib/city-context.tsx), [area lists](app/src/lib/area-lists.tsx) | Shared shell and provider boundaries; reuse immutable city lists. |
| [cities](app/src/lib/cities.ts), [types](app/src/lib/types.ts) | City units, paths, defaults, currencies and shared data contracts. |
| [store](app/src/lib/store.ts), [area keys](app/src/lib/area-key.ts), [URL state](app/src/lib/url-state.ts) | Shared weights; per-city filters/selection/compare; district, station-area and cell keys; shareable state. |
| [Tokyo data](app/src/lib/data.ts), [Bangkok data](app/src/lib/bangkok-data.ts) | Build-time assembly and lightweight map adapters. |
| [pure scoring](app/src/lib/scoring.ts), [named-area React adapter](app/src/lib/scoring-react.tsx) | Composite scores, anchors, dealbreakers and shared deferred named-area results. |
| [grid primitives](app/src/lib/bangkok-grid.ts), [grid React adapter](app/src/lib/scoring-grid-react.ts) | Packed-grid decoding, resident weighting, masks, counts and hotspots. |
| [Bangkok label helpers](app/src/lib/bangkok-labels.ts) | Escaping, pixel fitting and localized district/station-area label descriptors without Leaflet. |

### Maps and shared presentation

| Module | Responsibility |
|---|---|
| [Tokyo Map](app/src/components/Map.tsx), [Bangkok DistrictMap](app/src/components/DistrictMap.tsx) | City-specific map composition, not duplicate scoring engines. |
| [map selection](app/src/components/map-selection.tsx), [shared map controls](app/src/components/map-shared.tsx), [hover hook](app/src/lib/use-delayed-hover.ts) | Flight, dismissal, resize/zoom and hover lifecycle ownership. |
| [DistrictLayer](app/src/components/bangkok/DistrictLayer.tsx), [StationAreaLayer](app/src/components/bangkok/StationAreaLayer.tsx), [GridLayer](app/src/components/bangkok/GridLayer.tsx) | Bangkok level-specific rendering. |
| [BangkokOutlines](app/src/components/bangkok/BangkokOutlines.tsx), [BangkokRailLayer](app/src/components/bangkok/BangkokRailLayer.tsx), [MapLegend](app/src/components/bangkok/MapLegend.tsx) | Selection/compare outlines, rail overlay and legends. |
| [Bangkok popups](app/src/components/bangkok/popups.tsx), [GridRanking](app/src/components/bangkok/GridRanking.tsx) | District/station/cell details and the grid's ranked panel. |
| [area-card family](app/src/components/area-card.tsx), [MobileStationCard](app/src/components/MobileStationCard.tsx) | Reusable card metadata/actions with city and interaction variants. |
| [DetailHeader](app/src/components/DetailHeader.tsx), [RatingsBreakdown](app/src/components/RatingsBreakdown.tsx), [DetailFacts](app/src/components/DetailFacts.tsx) | Shared detail sections with explicit city-specific props. |
| [FilterPanel](app/src/components/FilterPanel.tsx), [ScatterPlotExplorer](app/src/components/ScatterPlotExplorer.tsx), [ComparePanel](app/src/components/ComparePanel.tsx) | Scoring consumers and comparison/provenance presentation. |
| [ConfidenceBadge](app/src/components/ConfidenceBadge.tsx), [RatingBar](app/src/components/RatingBar.tsx), [Tooltip](app/src/components/Tooltip.tsx) | Evidence shape icons, median-relative bars and touch/hover disclosure. |

## Scoring and compatibility contracts

- [schema constants](packages/schema/constants.json) own rating-key order,
  defaults, rent bounds and absolute caps. [codegen](packages/schema/scripts/gen.ts)
  emits the shared language copies and the [vendored app constants](app/src/lib/schema/constants.ts).
  The app build context is `app/`; imports must not escape it.
- The URL weight vector is positional. Keep the legacy decoding/order rules in
  [url-state.ts](app/src/lib/url-state.ts) and the [contributor invariants](CONTRIBUTING.md#load-bearing-invariants-breaking-these-silently-corrupts-data-or-urls).
  Never sort the category/default-weight keys to make output look tidy.
- Digit-prefixed rent keys (`1k_1ldk`, `2ldk`) are data contracts. Preserve aliases,
  source provenance, source-quality caps and labeled municipal/model fallbacks.
- [Python normalization](packages/schema/python/city_rating_schema/normalize.py)
  is shared by the pipelines. Formula/rounding reuse does not unify city-specific
  source/confidence policies. [Tokyo compute](scripts/compute-ratings.py),
  [Bangkok ratings](scripts/bangkok/ratings.py) and [MCP scoring](mcp/src/city_rating_mcp/scoring.py)
  remain explicit consumers; review parity and golden tests when changing them.
  Fractional/half-value scores must retain site/MCP parity; see the shared
  [composite-score fixtures](packages/schema/fixtures/composite-score.json).
- Composite colors use full-population score anchors. Category bars use deviation
  from the supplied city/level median, not raw value. Keep `compositeToColor`
  distinct from `categoryDeviationColor`; confidence shapes are a separate evidence channel.
- Weights are shared between cities; dealbreakers are per city because units and
  currencies differ. Preserve comparison/selection area keys and the existing
  URL encoding for Bangkok level and cell selection.
- Rename slugs through [redirect data](app/src/data/slug-redirects.json), update
  every slug-keyed artifact and use [canonical slug lookup](scripts/scrapers/slugs.py)
  for older datastore rows. Naming helpers are in [station-name.ts](app/src/lib/station-name.ts).

## Data readiness & coverage honesty (maintainers)

Full row coverage does not imply equal spatial precision, current source dates
or uniformly strong confidence. Current coverage comes from committed artifacts;
[historical research](research/00-overview.md) is not a live inventory.

- The researched Tokyo block still has 251 `daily_essentials` fallbacks. The
  [live-data invariant](app/src/lib/__tests__/data-invariants.test.ts) pins that
  cohort and the assembled fallback value. An authorized re-export must change
  the committed inputs and update the invariant together; merging backfill code
  does not establish that an export ran.
- Researched ratings/descriptions are editorial. Matching computed categories
  can inherit pipeline metadata; differing ratings use `editorial`. Missing
  confidence keys remain a separate coverage limit. See [export policy](scripts/export-ratings.py).
- Tokyo rent may be a station-listing value, municipal average or model fallback.
  Only station-level evidence supports the strongest tier; area-level values
  retain their labels/caps and are not recomputed by the frontend.
- Tokyo safety uses the published police-data scope; neighborhood and municipal
  observations have different granularity. Traffic/other contextual facts are
  not interchangeable with the safety score. See [safety research](research/02-safety.md).
- Tokyo food confidence preserves the HotPepper/OSM source rules: the HP-zero
  compatibility case remains estimate with an empty source list. Bangkok uses
  its own two-source thresholds and retains both source names when neither qualifies.
  Strong/moderate/estimate are source-policy outcomes, not judgments from map color.
- Commute values are calibrated geographic/line-model estimates, not timetable
  routing. [Transit metadata](data/transit-times.json) records the historical
  calibration cohort separately from today's researched export count.
- Last-train and camera inputs are snapshots. Video IDs and availability can
  expire; a populated field is not a live stream or timetable verification.
  See [last-train acquisition](scripts/scrapers/scrape-last-trains.py) and
  [camera acquisition](scripts/scrapers/scrape-livecams.py).
- Source freshness, schema preflight and recoverable Tokyo refreshes follow the
  [resilience runbook](research/notes/2026-10-15-hotpepper-resilience-runbook.md).
  Datastore configuration and credentials are supplied privately; an app clone
  does not provision that environment.

## Bangkok (district layer)

Districts, walkable station areas and the 200 m grid are distinct scoring
populations. A Bangkok score is relative within its city/level, not a Tokyo
score. Outer areas may be less well mapped; grid resolution is not evidence
that every category is measured locally.

All district/grid rents and safety remain editorial. Ten central station areas
use single-provider, all-size asking-rent bedroom medians at estimate confidence;
other station areas use district blends. [Rent provenance helpers](app/src/lib/bangkok-rent.ts),
[RentNote](app/src/components/bangkok/RentNote.tsx) and the shared ratings section
must preserve those metric/source/date/sample distinctions.

District quietness uses the WorldPop constrained 2020 model; displayed
registration facts are a different measure. Finer-level quietness uses mapped
place density. Population is not a current census or daytime visitor count.
See the [full methodology and honesty notes](research/bangkok/00-overview.md).

The [Bangkok acquisition/build guide](scripts/bangkok/README.md) is the pipeline
entry point. Its [build entry module](scripts/bangkok/build.py) coordinates
source, geometry, raster, district, area and output modules. Frozen replay
requires recorded raw inputs that are not supplied by a fresh clone. The
[completed remediation record](docs/DATA_REFRESH_REMEDIATION.md) retains the
refresh's validation and source limits. Data refreshes remain separate reviewed work.

## Routes, localization and descriptions

| User surface | Route module |
|---|---|
| Tokyo homepage and locale prefixes | [Tokyo page](app/src/app/%5Blocale%5D/page.tsx) |
| Tokyo station detail | [station page](app/src/app/%5Blocale%5D/station/%5Bslug%5D/page.tsx) |
| Bangkok homepage/levels | [Bangkok page](app/src/app/%5Blocale%5D/bangkok/page.tsx) |
| Bangkok district / station-area details | [district page](app/src/app/%5Blocale%5D/bangkok/district/%5Bslug%5D/page.tsx), [station-area page](app/src/app/%5Blocale%5D/bangkok/station/%5Bid%5D/page.tsx) |

[routing.ts](app/src/i18n/routing.ts) owns EN/JA/RU and the as-needed locale
prefix. Use [locale-aware navigation](app/src/i18n/navigation.ts), typed literal
message keys and [guarded data labels](app/src/i18n/message-key.ts) for external IDs.
The [locale layout](app/src/app/%5Blocale%5D/layout.tsx) filters server-only
Bangkok messages from the client provider; shared server-translated detail
components do not make those namespaces available to arbitrary client hooks.

[Tokyo data assembly](app/src/lib/data.ts) loads committed multilingual
[generated descriptions](app/src/data/generated-descriptions.json); the old
RU-only demo text is not the current description source. Authoring rules live
in [description-generation-rules.md](research/description-generation-rules.md).
[Datamart construction](scripts/build-datamart.py), [prompt generation](scripts/build-prompts-dir.py),
[description merge](scripts/merge-descriptions.py) and [embedding build](scripts/build-embeddings.py)
are separate pipeline steps, not a dated progress checklist. Datamarts, prompts
and embeddings are generated artifacts; describe their prerequisites rather
than linking to untracked local handoffs. Changes to the description corpus
invalidate embeddings and require the separately managed artifact refresh.

## Tests and verification

| Boundary | Source / convention |
|---|---|
| App unit/component suites | [Vitest config](app/vitest.config.ts) splits `.test.ts` Node tests from `.test.tsx` jsdom tests. [Test guide](app/src/test/README.md), [providers](app/src/test/providers.tsx), [setup/cleanup](app/src/test/setup.ts) and [animation-frame helper](app/src/test/animation-frames.ts) own the harness. |
| Scoring adapters | [named-area tests](app/src/lib/scoring-react.test.tsx), [grid tests](app/src/lib/scoring-grid-react.test.tsx), [grid-panel regression](app/src/components/bangkok/GridRanking.test.tsx). |
| Map lifecycle/labels | [selection tests](app/src/components/map-selection.test.tsx), [hover tests](app/src/lib/use-delayed-hover.test.tsx), [label tests](app/src/lib/bangkok-labels.test.ts). |
| Shared presentation | [area-card tests](app/src/components/area-card.test.tsx), [facts tests](app/src/components/DetailFacts.test.tsx), [ratings tests](app/src/components/RatingsBreakdown.test.tsx). |
| Real browser interaction | Root [Playwright config](playwright.config.ts), [e2e guide](e2e/README.md) and [map-interaction smoke](e2e/map-interactions.spec.ts). The app lives in `app/`; the browser harness lives at the repository root. |
| Pipeline and cross-language contracts | [CI workflow](.github/workflows/ci.yml), [schema parity](scripts/test_schema_parity.py), [normalization tests](scripts/test_normalization.py) and [MCP tests](mcp/tests/). |

Colocate tests with the behavior they protect. Component tests use the real
store/i18n harness with controlled timers/animation frames; jsdom is not a
layout, paint or pixel-regression claim. Keep test state and mocks isolated.
The required browser CI check tests actual pointer/keyboard/touch behavior
without retries. Report its result alongside the other checks. Follow
[CONTRIBUTING.md](CONTRIBUTING.md#testing) for commands and
[the ticket convention](#ticket-workflow-and-verification) for actual results/limits.

The MCP service exposes Tokyo stations and Bangkok districts, with Tokyo as
the default city. [MCP implementation](mcp/src/city_rating_mcp/server.py),
[district views](mcp/src/city_rating_mcp/views.py), [scoring](mcp/src/city_rating_mcp/scoring.py),
[semantic tools](mcp/src/city_rating_mcp/tools/semantic.py) and [usage](mcp/USAGE.md)
define its API. Preserve city-specific rent units/provenance, district-wide
facts and rejection of Tokyo-only filters for Bangkok. Unit fixtures are
separate from the [artifact-dependent smoke test](mcp/scripts/smoke-test.py);
semantic tools need separately generated, city-bound embeddings and fail
explicitly when Bangkok's artifact is absent. No model, source or operator
activity is implied by a docs change or a green unit suite.

## Ticket workflow and verification

Every implementation ticket needs a problem, context/accepted scope, explicit
**Done when:** criteria and a verification plan before work starts. Keep the
canonical description current when an owner-approved scope decision changes
those criteria. Use the [ticket and verification templates](CONTRIBUTING.md#tickets-and-verification).

Before marking Done, add a verification comment naming the shipped scope,
tested PR/commit, checks actually run and their results, and any unverified
production or operator steps. A merge or green CI alone does not establish
source acquisition, publication rights, data refresh or rollout. Record an
accepted scope split and link every unresolved tail with its blocker, required
owner/action and reopen condition; do not silently drop acceptance criteria.

During status reviews, draft PRs older than **14 days** need a dated decision
comment: merge, close, or blocked with owner/action/reopen condition. Execute
merge/close only within current authorization. An already merged/closed trigger
needs its outcome recorded, not a new triage action. **Todo** may identify
accepted, next-up work; adopting this convention does not require bulk state changes.

## Research Documents

Use [research/decisions/](research/decisions/) for decision records and the
[roadmap](research/VISION.md) for future work. Current setup belongs in the
[README](README.md), invariants/process in [CONTRIBUTING](CONTRIBUTING.md),
source methodology in [research/](research/), and user-facing version history
in [CHANGELOG](CHANGELOG.md) / [release notes](docs/releases/). Keep these aligned;
old handoffs and dated implementation checklists are not architecture contracts.

### Architecture decision records

Use [research/decisions/](research/decisions/) for consequential choices about
scoring, evidence/confidence, source rights, identity/merge rules, city/domain
boundaries or shared contracts. Follow the existing `YYYY-MM-DD-topic.md`
convention: record context, decision/status, alternatives, consequences,
evidence and conditions for revisiting it. Link the ADR from the implementation
ticket and PR; mark an owner decision accepted only when that decision exists.
Routine fixes and copy edits can use the ticket/PR record. Apply the public-copy
rules in [CONTRIBUTING.md](CONTRIBUTING.md#public-repository-and-changelog-rules);
private operational details and internal verification artifacts stay outside
public ADRs.

## Area guide rollout (2026-10-30)

All Tokyo station, Bangkok station-area and Bangkok district detail routes use
`components/area/AreaGuide.tsx`, with server data normalized by
`lib/area-guide-data.ts`. The adopted design is retained under
`components/prototype/cards/` as a reference. The main guide uses one category
comparison plot, destination-specific commute bars and a lazy area map; the
former radar/bar pair is no longer its default view. Supplemental descriptions,
photos, cameras, noise references, institutions and air context remain available
through `AreaGuideExtras.tsx`.

`CompactAreaCard` is shared by desktop popups, hover previews and the touch-card
wrapper. Keep the latter's flight/animation lifecycle intact. Full source and
confidence arrays still stay off `MapStation`; only `rent_source` and
`rent_updated` were added for accurate Tokyo rent labels. Detail links use the
existing `w` format, and locale navigation preserves query context.

The crowd-proxy category is labeled **Less crowding** (EN/JA/RU); modeled
**Outdoor quietness** remains a separate fact. A source's raw numeric value,
provenance, geographic scope and source-specific date must not be silently
converted into a different metric. Presentation summaries for reviewed examples
live in `data/area-guide-copy.json`; other places use localized factual leads
and retain their existing long descriptions under local notes.
