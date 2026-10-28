# Changelog

Release tags use semantic versioning. Add user-visible changes here and keep each
published entry aligned with its [release notes](docs/releases/) and immutable
tag. The [release runbook](docs/RELEASING.md) defines the gates and commands.

Changelog entries are public-facing. Describe user-visible changes,
compatibility and user-impacting limits. Do not include internal infrastructure
or deployment details, host/service names, credentials, worker/session
identifiers, CI run IDs, hashes, manifests or internal gate lists. Put technical
evidence in research notes or the PR body and link it.

## v0.1.2 — 2026-10-28

### Added

- MCP profiles, filtered search and comparisons now support Bangkok's 50
  districts, keeping results and rent provenance specific to the selected city.
  These tools work without embeddings; Bangkok semantic search becomes available
  when its separate embedding artifact is deployed.

### Fixed

- The Bangkok grid panel now applies the flood-risk filter to its count and
  ranked hotspots, keeping them aligned with the map.
- Tokyo map selections can now be cleared with Escape. Hover highlights clear
  consistently across both cities.
- Map zoom controls on phones are no longer covered by the selected station card.
- MCP composite scores now round half-values in the same way as the website.

[GitHub release](https://github.com/pogorelov-labs/city-rating-tokyo/releases/tag/v0.1.2)
· [Release body](docs/releases/v0.1.2.md)

## v0.1.1 — 2026-10-27

Bangkok data refresh. This is a data-only release: no new features, API, URL,
schema or scoring changes. v0.1.0 remains the prior release and does not contain
this data.

### What changed

- Bangkok now uses the October 2026 OpenStreetMap/Overture snapshot across the
  50 districts, 133 station areas and 200 m grid.
- Ratings changed in 12 districts and 35 station areas, mainly green-space
  scores. The district/area structure, rail network and grid size are unchanged.
- Existing tourism, Michelin and institution facts are retained.

### What to expect

- Some Bangkok scores and map colours differ from v0.1.0. Scores remain relative
  within Bangkok; a Bangkok 8 is not a Tokyo 8.
- District and grid rents remain editorial estimates. The 10 central station-area
  rent proxies remain estimate-grade. Safety remains editorial.
- No action is required for users; the site is static.

See the methodology and evidence notes for source details and known limits.

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
