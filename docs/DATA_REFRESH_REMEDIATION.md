# Bangkok data-refresh remediation plan

Status: **implemented and merged in [PR #147](https://github.com/pogorelov-labs/city-rating-tokyo/pull/147)**
at [ba7aa47](https://github.com/pogorelov-labs/city-rating-tokyo/commit/ba7aa477fb3e06ceada1fad5df2dc5954428cdf4)
on **2026-10-27**. The refreshed data is now on **main**. The full spatial
refresh was **not included in v0.1.0**: PR #147 was based on release commit
`d7e2ddf5c5d906e155e0f310015f45441360fa06` and merged afterwards. The v0.1.0
tag, GitHub release and release body remain unchanged.

## Remediation evidence

The separate refresh uses the [90-file frozen input manifest](../data/bangkok/refresh-inputs.json)
and [exact enrichment preservation baseline](../data/bangkok/enrichments-baseline.json).
See the [completed evidence note](../research/bangkok/notes/2026-10-26-frozen-refresh.md)
and [complete aggregate/geometry review](../research/bangkok/notes/2026-10-26-frozen-refresh-review.json).

| Workstream | Status / evidence |
| --- | --- |
| A | Automatic full-build enrichment stage; all 133 tourism areas (99 with hotels, 66 with attractions, 19 badges), 9 Michelin districts and 5 embassy districts preserved exactly; idempotent and missing-input/join tests pass. Embassy metric provenance gap is explicit. |
| B | All 10 original gates resolved. Historical population baseline and golden unchanged and separately tested; current refresh baseline/golden added. Header summaries use published integer weight units (transport median 5); cell normalization unchanged. |
| C | All 25 district/14 area park changes reconstructed; green outliers and nine area notices reviewed with limits. All 133 station geometries byte-identical. All Overture source entries inventoried; three-license attribution, notices and license copies retained. Wikimedia exact payload hashes/revision IDs frozen; HTTP fetch remains live. |
| D | Full frozen build repeats byte for byte (6.21s / 6.22s); 649 full-script tests, 141 Bangkok tests, 399 app tests pass; TypeScript, lint and production build pass. Separate data PR #147 merged on 2026-10-27; v0.1.0 remains unchanged. |

Ratings change in **12/50 districts and 35/133 station areas**. Entity counts
remain **50 districts, 133 areas, 179 rail stations / 10 lines and 39,149 grid
cells**, with no gained/lost IDs or cells. The new binary is
`grid-1d6ed2ef00c3.bin` (**143,925 bytes**); grid rent/safety and crowd/hub-minute
planes are unchanged. These are source-snapshot changes, not verified
real-world improvements. The evidence note retains the nine area discrepancies,
live Wikimedia replay limits, source epochs and legacy embassy provenance gap.

**Narrow scope exception authorized by city-rating-9:** normal institutions and
noise exporters update embedded Bangkok input hashes in shared/Tokyo metadata.
The only Tokyo diff is three Bangkok input-hash lines in each copy of
`station-institutions.json`; all counts, ratings, facts, station/district and
noise values remain unchanged. Shared noise calibration changes only its
Bangkok station-input hash. Regression fingerprints exclude only these exact
authorized hash fields and pin everything else to the release snapshot. No
legacy fingerprints are substituted. This does not authorize other Tokyo work.

## Original blockers and acceptance criteria

The remaining sections retain the original remediation requirements for
traceability. They are completed by PR #147 as recorded above, rather than an
unimplemented plan or a list of current validation blockers.

PR [#145](https://github.com/pogorelov-labs/city-rating-tokyo/pull/145) added the
Geofabrik Thailand PBF path and proved a full Bangkok build can run without
Overpass. The initial experimental 2026-10-24 snapshot completed a build, but
publication was blocked by:

- **10 validation failures** in the committed Bangkok/normalization suite.
- **Enrichment losses** when the original full builder overwrote app data.
- **Data-quality and attribution reviews** before any public data refresh.

Evidence: [the committed refresh diff report](../research/bangkok/notes/bangkok-geofabrik-refresh-diff.md)
and its archived worker evidence bundle, `bangkok-geofabrik-refresh-evidence.tar.gz`.
These failures describe experimental refreshed output, not the unchanged
committed dataset released as v0.1.0. See the [release runbook](RELEASING.md).

## Scope

**In:** one reproducible full Bangkok data refresh, preservation/reapplication
of enrichments, resolution of the 10 gates, source/attribution review, a separate
data-refresh PR, and release-note updates after it passes.

**Out:** Tokyo value changes (the provenance-only exception above is explicit),
unrelated runtime/scoring changes, folding the refresh
into v0.1.0, and silently overwriting historical fixtures.

## A. Preserve or reapply enrichments

The original full builder generated spatial ratings/facts but reset fields
supplied by separate enrichment pipelines. PR #147 added and validated the
deterministic enrichment stage in `build.py` before output writes.

| Enrichment | Source / output | Fields at risk | Preserved baseline |
|---|---|---|---|
| Tourism | `scripts/scrapers/fetch-tourism-counts.py` → `data/tourism/proximity.json` | `hotels_800m`, `attractions_800m`, `tourist_badge` on all 133 station areas | Nonzero hotels 99, attractions 66, badges 19; Nana 197 hotels, Asok 156 |
| Michelin | `scripts/michelin/compute-proximity.py` → `data/michelin/proximity.json` | `michelin_stars`, `michelin_bib` on 9 districts | Stored sums 8 stars and 12 Bib |
| Legacy embassy field | `data/bangkok/enrichments-baseline.json`, exact release-commit district facts; original calculation not independently proven | `embassies_800m` on 5 districts; not the institutions pipeline's polygon-containment metric | Stored sum 16 |

Acceptance: every enriched field is present and exactly matches the preserved
snapshot unless an evidence-backed improvement is separately reviewed; the
merge is covered by tests; source dates/hashes and provenance gaps are recorded.

## B. Resolve the 10 validation failures

All ten are resolved. The original failures and required remedies below are
retained as acceptance history; the evidence table records their implementation.

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
  Wikidata/Commons revision IDs and WorldPop/flood hashes. PR #147 records the
  exact payload hashes/revisions; HTTP acquisition remains live, so exact replay
  requires the archived payloads.
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
