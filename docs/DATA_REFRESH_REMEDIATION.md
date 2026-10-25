# Bangkok data-refresh remediation plan

Status: **scoped, not implemented** (2026-10-26). The full Bangkok spatial
refresh is **not in v0.1.0**. The release tags the existing product and adds
release documentation; no regenerated spatial data is published by this plan.

## Why this exists

PR [#145](https://github.com/pogorelov-labs/city-rating-tokyo/pull/145) added the
Geofabrik Thailand PBF path and proved a full Bangkok build can run without
Overpass. The experimental 2026-10-24 snapshot completed a build, but publishing
it is blocked by:

- **10 validation failures** in the committed Bangkok/normalization suite.
- **Enrichment losses** when the existing full builder overwrites app data.
- **Data-quality and attribution reviews** before any public data refresh.

Evidence: [the committed refresh diff report](../research/bangkok/notes/bangkok-geofabrik-refresh-diff.md)
and its archived worker evidence bundle, `bangkok-geofabrik-refresh-evidence.tar.gz`.
These failures describe experimental refreshed output, not the unchanged
committed dataset released as v0.1.0. See the [release runbook](RELEASING.md).

## Scope

**In:** one reproducible full Bangkok data refresh, preservation/reapplication
of enrichments, resolution of the 10 gates, source/attribution review, a separate
data-refresh PR, and release-note updates after it passes.

**Out:** Tokyo changes, unrelated runtime/scoring changes, folding the refresh
into v0.1.0, and silently overwriting historical fixtures.

## A. Preserve or reapply enrichments

The full builder generates spatial ratings/facts but resets fields supplied
by separate enrichment pipelines. Add one deterministic post-build merge step
or explicit ordered stages in `build.py`, and validate the result.

| Enrichment | Source / output | Fields at risk | Preserved baseline |
|---|---|---|---|
| Tourism | `scripts/scrapers/fetch-tourism-counts.py` → `data/tourism/proximity.json` | `hotels_800m`, `attractions_800m`, `tourist_badge` on all 133 station areas | Nonzero hotels 99, attractions 66, badges 19; Nana 197 hotels, Asok 156 |
| Michelin | `scripts/michelin/compute-proximity.py` → `data/michelin/proximity.json` | `michelin_stars`, `michelin_bib` on 9 districts | Stored sums 8 stars and 12 Bib |
| Institutions | `scripts/institutions/compute-institutions.py` → `data/institutions/{district,station}-institutions.json` and `app/src/data/institutions/*` | `embassies_800m` on 5 districts | Stored sum 16 |

Acceptance: every enriched field is present and no lower than the preserved
baseline; the merge is covered by tests; source dates/hashes are recorded.

## B. Resolve the 10 validation failures

1. **Population snapshot/scope — 8 failures.**
   - `test_committed_population_snapshot_and_scope`: historical crowd raw
     6.5281 vs refreshed 6.5280.
   - `test_main_original_adoption_and_idempotent_replay` plus six
     parameterizations of `test_main_rejects_incompatible_snapshots_without_writes`:
     replay rejects changed district geometry before the expected guard.
   - Create a new immutable **refresh baseline** for the new geometry/crowd raw.
     Keep the historical adoption fixture. Make `rebuild-population.py` select
     a baseline explicitly; test old and new baselines separately. Do not
     overwrite historical signatures.
2. **Normalization golden — 1 failure.**
   - `test_bangkok_committed_aggregate_golden`: review the new aggregates and
     create a **new current baseline** golden for the refresh; retain the
     historical golden. Do not merely overwrite the old signatures.
3. **Transport median — 1 failure.**
   - `test_grid_medians_are_resident_weighted`: header reports transport median
     6; the decoded resident-weighted median is 5.
   - Decide the canonical value: compute the header from decoded/encoded weights
     consistently, or preserve enough weight precision to keep 6. Add a rounding
     regression and document the contract.

## C. Data-quality and attribution review

- **Green outliers:** Nong Khaem 2→5, Setthabutbamphen 2→7 and other large green
  shifts; `park_ha` changes in 25 districts/14 areas (Nong Chok 25.1→19.9).
  Inspect source geometry and sampling before accepting.
- **Nine polygon-vs-Wikidata area notices:** Bang Kho Laem, Bang Rak, Bang Sue,
  Chom Thong, Pom Prap Sattru Phai, Rat Burana, Sathon, Taling Chan, Yan Nawa.
  Choose and document the density denominator.
- **Overture attribution:** the experimental extract includes
  CDLA-Permissive-2.0, Apache-2.0 (Foursquare) and CC0-1.0 (AllThePlaces)
  material; update UI/docs attribution before publishing that refresh.
- **Source pinning:** record Geofabrik PBF SHA-256, Overture release,
  Wikidata/Commons revision IDs and WorldPop/flood hashes. Current WD/Commons
  fetches are live, not revision-pinned.
- **Station-area simplification:** the coverage fallback is known; confirm
  resulting geometries still match the intended baseline.

## D. Separate data-refresh PR and release gate

1. Freeze all inputs and hashes; archive exact refreshed outputs with the diff.
   Do not commit the roughly 329 MB PBF or raw caches.
2. Implement A; resolve B; complete C; add tests.
3. Regenerate from frozen inputs; run the full build, combined
   Bangkok/normalization suite, app build and visual QA.
4. Open a **separate data-refresh PR** with the complete diff, acceptance
   evidence and known limits. Do not fold it into v0.1.0 or a code/docs release.
5. Update release notes/changelog only after the data PR is accepted. A future
   release may then advertise the refresh.

## Sequence and acceptance

1. Enrichment merge tool and tests.
2. Population/normalization baseline versioning and transport rounding fix.
3. Green/area/attribution review.
4. Regeneration and data-refresh PR.

Acceptance: all 133 areas retain tourism fields; all 9 Michelin and 5 embassy
facts remain; the 10 gates pass with documented new baselines; anomalies and
attribution are reviewed; the full build is deterministic; the data PR is
separately reviewed. Any necessary pipeline changes are reviewed as code.
Tokyo and unrelated runtime/scoring changes remain out of scope.
