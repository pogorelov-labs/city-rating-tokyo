# Tokyo food shadow pilot: Stage 0 tools

CRTKY-194, under the accepted
[2026-10-15 ADR addendum](../../research/decisions/2026-10-15-preserved-rules-food-pilot-institutions.md).
This bounded slice prepares the sampling frame. It does not activate a food
source, compute production ratings, change confidence/nightlife, or read target
HP/Overture outcomes. All raw census and sample artifacts stay outside git.

## Historical inventory versus current census

Existing NocoDB projections can establish which stored rows/fields/dates are
available. Complete table pagination is **not** proof that each original source
request completed. In particular, old OSM count-slot padding, missing HP rows,
null-to-zero compute behavior and 1 km HP aggregates cannot establish verified
800 m zeros. Preserve original rows, order, nulls and names in an internal hashed
snapshot; apply canonical slug redirects only in a separate replay. Historical
fixtures for CRTKY-166 equivalence remain separate from this fresh census.

## Freeze queries, then acquire

Use Python 3.10+ on a POSIX host and the standard library. No dependency install
or production credentials are required for OSM. Choose a new directory in the
worker's internal artifact area, represented here by `$PILOT_ARTIFACT_DIR`:

```sh
python3 scripts/food_pilot/acquire_osm.py --output "$PILOT_ARTIFACT_DIR/osm" --plan-only
# Inspect/send the plan hash, bounds, tile query hashes and limits before acquisition.
python3 scripts/food_pilot/acquire_osm.py --output "$PILOT_ARTIFACT_DIR/osm" --acquire
```

The plan binds the station bytes, exact queries, eight tiles and limits. A
contiguous 2×4 partition covers the outward-rounded spherical envelopes of all
800 m station circles. Food features are OSM **nodes and ways** tagged
`restaurant`, `cafe` or `fast_food`; relations are outside this contract. Nodes
use their coordinates, ways their bounding-box centers, then inclusive
haversine ≤800 m. This is mapped-feature density, not verified physical-business
density or walkability. Way selection follows Overpass bbox semantics; center
placement and mapping omissions remain source limitations. Tile-edge duplicates
are removed by `(type, id)`; node/way representations of the same business are
not assumed physically deduplicated. Conflicting repeated IDs fail admission.

The established mirrors and normal TLS policy are unchanged. All attempts use
the fixed query; HTTP errors, JSON/runtime remarks, absent arrays, invalid
coordinates and timestamps outside seven days do not become zeros. A complete
empty feature array with a valid source timestamp is a query-level empty result,
not evidence that no real restaurant exists. No count slots are padded.

Limits: 24 cumulative attempts, 128 MiB of response bodies, 16 MiB per response,
256 MiB retained, 15 minutes wall time from the original start, 90-second provider
timeout and at most 110-second socket timeout. Response accounting excludes HTTP
headers/TLS overhead; report that distinction with observed bytes. Each attempt
is atomically saved and fsynced with a `pending` status and its
maximum response-byte reservation **before** network I/O. A confirmed complete
body releases the unused reservation; interrupted or uncertain transfers retain
the entire charge. Thus `wire_bytes` is a conservative budget charge after an
interruption, not necessarily measured traffic. SIGTERM/process death leaves a
pending receipt; resume marks it `interrupted` without refunding it. Ctrl-C also
records an explicit interrupted status. These receipts remain valid history for
offline replay once every tile has a successful receipt. A legacy status-less
receipt is charged an additional full response allowance rather than guessed.
No read exceeds its reservation; a response that fills it exactly is rejected
without an extra byte probe. A POSIX wall deadline
also bounds slow reads. Errors retain an attempt record, without credential or
environment output. Raw successful bodies and their hashes are retained; files
are never silently overwritten.

An explicitly invoked continuation preserves the **original** deadline and
cumulative counters, rather than treating another process as a fresh allowance:

```sh
python3 scripts/food_pilot/acquire_osm.py --output "$PILOT_ARTIFACT_DIR/osm" --acquire --resume
```

It saves the prior ledger and rejected stale payloads, validates retained hashes,
and retries only the same missing/rejected tiles. If the budget or required
coverage is exhausted, stop with `incomplete`. No target acquisition follows.

## Offline replay and feasibility

```sh
python3 scripts/food_pilot/freeze.py \
  --raw-dir "$PILOT_ARTIFACT_DIR/osm" \
  --old-sample /path/to/preserved/old16/sample.json \
  --output "$PILOT_ARTIFACT_DIR/core-feasibility.json"
```

Replay verifies station/query/response hashes, every tile receipt, source dates
and coordinates before counting any station. Tertile cutpoints are observed
positive-count quantiles; equal counts stay together. Zero and missing are
distinct. Insufficient distinct values cannot manufacture three positive strata.

The deterministic core selection orders each prefecture/stratum by
`SHA256(crtky194-food-v1|canonical_slug)`. This implementation conservatively
requires >1,600 m between **all** selected core centers, as well as from every
old diagnostic center; it is stronger than the protocol's cross-split minimum.
It takes four sites per cell, first two development and next two holdout. A
greedy shortfall is reported as failure of this fixed selection procedure, not
a mathematical proof that no alternative spatial allocation exists. It must
not be silently repaired after target outcomes. The artifact retains cell
counts, candidate reserve order and spatial exclusions.

`frozen` in this output means the **core design only** passed its checks. It does
not authorize target reads. The challenge prescreen order, category/status/time
contract, final acquisition budget and complete manifest still must be frozen
and reported before HP/Overture target results. The old 16 centers remain
diagnostic-only. Never inspect holdout outcomes to improve selection or rules.

## Subsequent gates remain outstanding

64 complete new core pairs, a separately bounded HP-zero challenge (including
24–72-hour confirmation), development freeze, 200 random **holdout** provider-ID
audits plus up to 80 targeted cases, accepted 95/2/2 observed quality thresholds,
correlation screening and uncertainty reporting remain separate steps. A source
catalog is not independent venue truth. Unknown operation is not confirmed-open;
provider IDs are not physical identity. No fallback or confidence promotion
follows from this tooling or a high correlation.

Full same-vintage 1,493-station baseline/candidate score-impact replay, publication
rights, attribution, freshness SLA and operator recovery/schema prerequisites
are later production gates. The pilot can conclude `INSUFFICIENT` without
closing all CRTKY-194 criteria.

## Tests

```sh
pytest -q scripts/test_food_pilot.py
```

Synthetic fixtures cover boundary coverage, missing tiles, query/hash tampering,
HTTP200 partial/stale payloads, missing/invalid coordinates, cross-tile duplicates,
failed zero inference, tied strata, spatial exclusion, reproducibility and
continuation-budget preservation, including a real SIGTERM in an isolated mocked
process and Ctrl-C followed by resume/offline replay. They do not supply pilot
observations.
