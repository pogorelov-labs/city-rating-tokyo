# Owner-amended Tokyo food shadow protocol

Status: owner scope accepted on 2026-10-15. Overture metadata ended incomplete;
its cache-only downstream admission is separate from source-phase completion.
HP development ended terminal/incomplete at its first request and its original
deadline has expired. Later phases remain stopped; the diagnostic-only option
below is disabled and requires a separate exact-head owner/root gate.
[Decision and verbatim approval](../../research/decisions/2026-10-15-preserved-rules-food-pilot-institutions.md).
No production ratings, confidence, nightlife, schema or refresh changes.

## Amendment and sample

Preserve the original complete census and insufficient 63-site design. The
owner changed only Tokyo: zero has 1 development + 1 holdout site, low-positive
has 3 + 3, middle and high have 2 + 2. Other prefectures retain 2 + 2 in each
cell. Total: 64 new sites, 32 development and 32 holdout. The original seed,
tied-count strata and old-16 exclusion stay unchanged. The implementation keeps
its stronger >1,600 m separation between all core centers, not only across splits.

The internal manifest binds exact station IDs/centers, original evidence hashes,
tile hashes, density boundaries, ordered reserves and spatial exclusions. The
separate challenge selects up to 32 rich and 32 sparse prescreens, alternating
groups in a frozen order. Within each group historical empty-food labels sort
first, then the same station hash; empty labels are **not HP zeros**. Challenge
centers are >1,600 m from core, old 16 and each other. Reserves are evidence of
ordering, not permission to exceed 64 prescreens or replace sites after outcomes.

The core census uses OSM nodes/way centers as previously declared. Core HP must
complete on UTC calendar dates October 15–21, 2026; later acquisition is outside
the frozen seven-calendar-date window. Provider release, source update, fetch
and independently established operation dates remain separate fields.

## Stages and holdout protection

1. Final manifest: amend allocation, validate with lane A, incorporate lane C's
   blinded audit procedure/budget, pin acquisition/analysis code hashes and send
   root the complete contract. Review code before target reads.
2. Read only development HP and Overture candidates; execute the separate HP
   prescreen order within its own limits. Report technical completeness and
   development diagnostics. Neither stage may expose holdout counts/rows/labels.
3. Freeze one primary candidate and its exact code/rules/input hashes after
   development. Default primary comparison is unweighted HP total800m versus
   Overture food800m with no fitted calibration. No nightlife substitution.
4. Acquire/evaluate holdout using the frozen candidate. Reproducibly select
   200 distinct candidate-food provider IDs from the union of holdout circles,
   using the one-time cryptographic seed and exact HMAC/Fisher–Yates rejection
   algorithm in the bound audit spec. The prior literal audit salt is superseded. If fewer exist, audit all and
   report the limitation. Do not use repeat station membership as a new record.
   Send blinded audit frames through root: no split, density, counts, disagreement
   or candidate-validity label in auditor packets. Up to 80 targeted records stay
   separate; their exact risk ordering and budget must be frozen before outputs.
5. Confirm initial complete HP-zero candidates with actual fresh complete reads
   24–72 hours after each first successful result. Retain eligible-from/to UTC
   timestamps and a durable resumption checkpoint. Do not simulate elapsed time.
   Select the first eight twice-confirmed cases per group in frozen order;
   shortages or unstable results remain insufficient for fallback decisions.
6. Consolidate reproducible results as GO / NO-GO / INSUFFICIENT, with quality,
   completeness, correlation, uncertainty and HP-zero conclusions separate.

Raw parquet row groups can contain unrelated places. They remain internal;
programmatic extraction emits only the permitted phase's circles. Do not inspect
holdout raw records or counts while refining development. Holdout acquisition is
not started until the primary candidate freeze is recorded. Any tuning after
unblinding consumes the holdout and requires a new decision/validation frame.

## Frozen source and counting contracts

Overture is pinned to release **2026-09-23.1**, places/place, with the already
retained 16-object listing hashed in the manifest. Verify complete listing,
object size and ETag before range reads; use If-Match and validate Content-Range.
A changed object/list or unsupported range stops acquisition. Inspect all object
footers; missing statistics retain row groups rather than excluding them. Use
conservative bbox extent statistics for selection, then actual WKB Point geometry
and inclusive haversine <=800 m for membership. Invalid or unsupported coordinates
block technical completeness; bbox midpoint is not a substitute for point data.

Initial Overture candidate: confidence >=0.6; operating_status open or null.
Null means unknown operation and is never audit-confirmed valid by default.
Food is hierarchy prefix food_and_drink followed by restaurant, casual_eatery or
non_alcoholic_beverage_venue, or any hierarchy level bakery, dessert_shop,
food_court or food_truck_stand. Record every filter count and unexpected schema
value. Deduplicate exact provider IDs; conflicting duplicates block admission.
Do not auto-merge physical businesses or add overlapping catalogs together.

HP uses the fixed 1 km query, 100 rows/page and stable ordering, followed by
coordinate-based <=800 m membership. Require all pages, stable declared totals,
start/returned-count consistency and unique-ID count equal to the declared total.
Conflicts, duplicate/missing IDs, API errors, bad coordinates or truncated pages
cannot establish a complete count or zero. Separate provider-zero from complete
1 km positive / 800 m zero. Keep error, missing, truncated, bad-coordinate and
unstable states distinct. The primary comparator is all HP gourmet genres;
its mismatch with the narrower Overture food universe is an explicit limitation.

## Candidate acquisition budgets

These ceilings are frozen before target outcomes and subject to root's consistency
check. Every logical page/range and retry counts. Each phase has one original wall
deadline, durable pre-I/O pending receipts, conservative byte reservations and no
reset on resume. Unknown consumption retains the full reservation. Byte ceilings
cover response bodies, excluding HTTP/TLS overhead. No silent budget transfer.

| Phase | Attempt cap | Page / row-group cap | Body / retained cap | Wall cap |
| --- | ---: | --- | --- | --- |
| HP development | 400 | 320 pages; <=50/station | 128 / 128 MiB | 30 min |
| HP prescreen | 400 | 320 pages; <=50/station | 128 / 128 MiB | 30 min |
| HP holdout | 400 | 320 pages; <=50/station | 128 / 128 MiB | 30 min |
| HP zero confirmation | 200 | 160 pages; <=50/station | 64 / 64 MiB | 30 min |
| Overture metadata | 80 | all 16 object footers + complete listing | 64 / 64 MiB | 10 min |
| Overture development | 2,048 | <=256 selected row groups | 512 / 512 MiB | 30 min |
| Overture holdout | 2,048 | <=256 selected row groups | 512 / 512 MiB | 30 min |
| Overture challenge | 1,024 | <=256 selected row groups | 256 / 256 MiB | 30 min |

HP: one concurrent request, >=0.6 seconds between starts, 20-second socket cap,
1 MiB per response. Overture: one concurrent request, >=0.1 seconds between starts,
20-second socket cap, 8 MiB per range. At most two attempts per exact page/range;
transient transport/5xx gets one retry after two seconds within the same ledger.
Auth rejection, HTTP429, schema failure or object change stops the phase. No TLS
bypass, account rotation, full parquet archive or dependency installation.

Total retained acquisition ceiling is 2 GiB, including receipts and derived
records; expected planning footprint is roughly 150–500 MiB, not a guarantee.
Stop if the hard ceiling or available space would be exceeded. Audit ceilings are separately frozen within that total: 1,200 deliberate
retrievals, eight aggregate active auditor-hours and 128 MiB retained. Random first
pass: 800 retrievals / five hours; targeted: 240 / two hours; second review and
adjudication: 160 / one hour / up to 40 cases. First-pass record limits are four
retrievals and three active minutes (targeted: three retrievals); global caps
prevail and there are no transfers or extensions. The final manifest embeds
lane C's exact schema/spec, hashes, seed, mandatory-review and targeted ordering.
Root accepted the 50 m branch/entrance matching convention only when 800 m circle
membership is certain, and operation evidence within 30 days or current read-only
operator service availability. Older/undated evidence stays unresolved. Confirmed
temporary/permanent closures count known-closed separately; these audit conventions
are not a production freshness SLA or a scoring-radius change.

## Accepted evaluation gates and production boundary

All 64 core pairs must be technically complete; do not silently drop failed
holdout sites. The random venue audit requires observed >=95% jointly confirmed
category/location/current-operation validity, <=2% redundant physical records and
<=2% known closed. Unknowns are neither confirmed-valid nor automatically closed;
report 95% intervals and unresolved-case bounds. Targeted systemic errors can
block a recommendation independently of the random average. Audit estimates
record precision, not citywide recall.

Holdout Pearson >=0.85 and Spearman >=0.80 screen count comparability only. Report
raw/log1p results, ties/zeros, geographic/density behavior and block sensitivity.
No correlation-only adoption, provider summation or automatic confidence uplift.
Full same-vintage 1,493-station score/rank/composite replay, attribution/rights,
freshness SLA, operator schema/recovery and explicit production rollout remain
separate gates. HP-zero policy stays unchanged even if the challenge succeeds.

## Disabled one-request HP diagnostic exception

The original `hp_development` phase remains terminal and incomplete: its frozen
start, finish, deadline, ledger and result are not resumed, rewritten or relabeled.
The deadline was `2026-10-16T13:55:29.181380Z` and has expired. A separate,
disabled diagnostic command exists only to make a possible narrowly scoped
owner decision reviewable. It is not a pilot phase or an enabled recovery path.
The prior v6/v8 approvals and ordinary pilot root receipts do not authorize it.

Activation would require both a fresh owner exception and a separate root gate,
stored under the existing `target-v4` accounting tree and bound to the exact
successor manifest SHA, code map and Git head, original HP ledger/result hashes,
and request identity. The root gate must record current-head native approval,
all CI green, the exact owner-exception hash, and an explicit permission for
only this one diagnostic. Neither gate may allow retries, redirects, pilot
counts, phase completion, metadata reads or a next request. Without both valid
files the command fails before reserving or opening a socket.

The command accepts no station, query, output-root or retry options. It fixes
the request to the first development station (`gun-hatake`), page 1, and the
credential-free query hash already in the terminal ledger. It permits at most
one request, with redirects rejected, a 20-second socket timeout, a hard
60-second diagnostic window and a 1 MiB response-body limit. The October 22
source cutoff is checked before the request, while reading, and before a result
is accepted. No raw body, venue rows, URL, headers, key or arbitrary provider
message is retained. The outcome contains only allowlisted HTTP/provider codes,
parser reason and structural pagination types/counts.

Before any possible request, the command writes and fsyncs an immutable
reservation beside the original HP evidence. It reserves one attempt, one page
slot, 1 MiB of response-body budget and 16 KiB of combined reservation/outcome
retention against the original phase and global caps. A complete EOF may release
unused body bytes in a separate additive outcome receipt; interrupted or
uncertain results keep the full 1 MiB charge. An existing reservation or
outcome blocks all later calls. Gate files and receipts count within the
existing 2 GiB global retained tree; diagnostic receipts also remain within the
HP phase retention limit. The original ledger/result and expired phase deadline
remain byte-identical. This diagnostic can never produce an HP count, establish
a zero, complete the phase or authorize another request.

The dedicated command is intentionally not called from `food_pilot.run`:

```sh
PYTHONPATH=scripts python -m food_pilot.diagnostic \
  --manifest /internal/current-v9-manifest.json \
  --owner-exception /internal/target-v4/owner-diagnostic-exception.json \
  --root-gate /internal/target-v4/root-diagnostic-gate.json
```

The API key must arrive only through the existing scoped secret consumer as a
process environment value; it is never supplied in command arguments or receipt
files. The command prints only diagnostic state, receipt hash and charged body
bytes. Its HTTP adapter is mock-tested offline. No owner exception/root gate is
present in this change, and no request has been made through this path.
