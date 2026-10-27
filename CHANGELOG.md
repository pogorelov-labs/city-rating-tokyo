# Changelog

Release tags use semantic versioning. Add user-visible changes here and keep each
published entry aligned with its [release notes](docs/releases/) and immutable
tag. The [release runbook](docs/RELEASING.md) defines the gates and commands.

## Unreleased — post-v0.1.0

### Bangkok spatial refresh — merged 2026-10-27

The separate [data PR #147](https://github.com/pogorelov-labs/city-rating-tokyo/pull/147)
merged to **main** at [ba7aa47](https://github.com/pogorelov-labs/city-rating-tokyo/commit/ba7aa477fb3e06ceada1fad5df2dc5954428cdf4),
after the v0.1.0 release commit `d7e2ddf`. **The v0.1.0 tag/release does not
contain this refresh**; this entry does not create a new version tag.

- Resolved all **10 validation gates** with preserved historical fixtures,
  explicit refresh baselines and grid summaries consistent with published weights.
- Froze **90 input files** with hashes/revisions in the [input manifest](data/bangkok/refresh-inputs.json).
- Preserved all **133 tourism areas** (99 with hotels, 66 with attractions,
  19 badges), all **9 Michelin district facts** (8 stars / 12 Bib) and all
  **5 legacy embassy district facts** (sum 16).
- Ratings change in **12/50 districts and 35/133 station areas**. Entity counts
  stay at **50 districts, 133 areas, 179 rail stations / 10 lines and 39,149
  grid cells**, with no gained/lost IDs or cells.
- Grid binary is now `grid-1d6ed2ef00c3.bin` (**143,925 bytes**). Grid rent/safety
  and crowd/hub-minute planes are unchanged; district/grid rents remain editorial
  and the existing 10 station-area rent proxies retain estimate confidence.
- Completed the extract-specific Overture attribution and geometry reviews,
  retaining notices/license copies and documented limitations. Source mapping
  changes are not evidence of real-world improvement; retained population,
  flood, rent and enrichment epochs were not advanced.

See the [committed evidence note](research/bangkok/notes/2026-10-26-frozen-refresh.md),
[complete aggregate/geometry review](research/bangkok/notes/2026-10-26-frozen-refresh-review.json)
and [completed remediation record](docs/DATA_REFRESH_REMEDIATION.md). The v0.1.0
entry below records the release's original scope and blockers at release time.

## v0.1.0 — 2026-10-26

First tagged release of City Rating: **Tokyo + Bangkok**. This entry describes
the existing product at the release commit; the release preparation changes
documentation only and does not regenerate data or bump package versions.

### Product

- Greater Tokyo: **1,493 train stations** with map exploration, station pages,
  category breakdowns, comparison, commute/rent dealbreakers and adjustable
  weights.
- Bangkok: **50 districts, 133 station areas and a 200 m grid**, with rail
  overlays, detail pages and modeled commute to five hubs. Preferences carry
  between cities; currency-specific filters are kept per city.
- **10 categories:** transport, affordability, daily essentials, safety, food,
  green, gym/sports, vibe, nightlife and quietness. **EN/JA/RU** interfaces and
  localized detail pages.
- Bangkok rent: **10 central station-area DooAsset proxies**, using published
  condominium asking-rent medians by bedroom count across all floor areas,
  at **estimate** confidence. District and grid rents remain editorial; other
  station areas retain district blends. ComparePanel distinguishes these
  provenances and shows source/date/sample information for the proxies.
- Existing context includes flood exposure, tourism, Michelin and institution
  facts, with source and coverage caveats in the methodology and research docs.

### Recent features and hardening

- Geofabrik Thailand OSM acquisition via
  [`scripts/bangkok/fetch-geofabrik.py`](scripts/bangkok/fetch-geofabrik.py),
  including provenance hashes and complete bbox-crossing geometry. This ships
  the **fetch path only**, without the experimental full spatial refresh.
- Shared Python normalization with equivalence/golden checks that preserve
  city-specific confidence rules; schema codegen and data-integrity gates.
- UI interaction tests, typed translation keys and EN/JA/RU message checks.
- Next.js 16.4.2 security update and MCP authentication fixes for fail-open,
  transport bypass and KeyStore-failure cases.
- HotPepper freshness/recovery tooling and the previously adopted Bangkok
  WorldPop district population model, with their documented source limits.

### Not in this release

The **full Bangkok spatial data refresh** remains blocked by **10 validation
failures** (8 population snapshot/scope, 1 normalization golden, 1 transport
median) and losses of **tourism, Michelin and embassy enrichments** in full
builder output. Green/area anomalies, source pinning and Overture attribution
also need review. The [scoped remediation plan](docs/DATA_REFRESH_REMEDIATION.md)
is **not implemented**. A refresh requires its own PR and acceptance evidence;
this release does not advance those source snapshots.

[GitHub release](https://github.com/pogorelov-labs/city-rating-tokyo/releases/tag/v0.1.0)
· [Release body](docs/releases/v0.1.0.md)
