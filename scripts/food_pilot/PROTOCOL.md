# Owner-amended Tokyo food shadow protocol

Status: owner scope accepted on 2026-10-15. Overture metadata ended incomplete;
its cache-only downstream admission is separate from source-phase completion.
HP development ended terminal/incomplete at its first request and its original
deadline has expired. Its one-shot diagnostic was later spent without completing
that phase. The owner separately requested implementation and review of one
prospective HP development run. PR141 contains an offline implementation and
mocked regressions, but it has not been activated or run. Later phases remain
stopped.
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

One narrow response-representation compatibility case is accepted for a
successful first requested page only: no prior page for that station; HTTP 200,
complete EOF and no provider error under the existing checks; exact JSON
`results_available: 0` (integer), `results_returned: "0"` (canonical string),
`results_start: 0` (integer), and `shop: []`. The request still asks for
`start=1`; preserve both the requested start and observed `results_start=0` in
the page receipt. For this exact tuple V10 classifies the first page as
`complete_provider_zero`; the previous parser rejected it. This is an actual
local parser/classification behavior change based on one allowlisted diagnostic
shape, not a documented Recruit guarantee: the [official reference](https://webservice.recruit.co.jp/doc/hotpepper/reference.html)
defines these fields and shows start position 1 but does not specify the empty
JSON representation. Do not coerce or broaden this exact type tuple. Any
nonempty, malformed, contradictory, provider-error, missing, non-EOF, or later
page remains incomplete/rejected. This change never reinterprets the original
terminal HP ledger/result or diagnostic, emits a count from that history, or
authorizes a resume/request.

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

## Prospective HP development supplemental run (normative, not activated)

The owner approved preparation and review of one prospective HP development run
with one additional attempt for the exhausted first page, within the frozen
cumulative budgets (Plane CRTKY-194 comment
`9f7e6acd-0bce-462d-bfde-9e1f36a3648c`). This is a supplemental run with a new
wall window, not a reset, reopening, completion or relabeling of the expired
original HP phase. PR141 adds an offline supplemental runner and mocked
regressions for these controls; they are not an activation or an execution
receipt. The runner remains inert unless a new exact-manifest owner activation
and root release are supplied after review. This protocol amendment alone does
not authorize a run or any request.
Expiry of the original window does not block this expressly approved new
prospective window; the original deadline and terminal record remain immutable.
The only intended changes are this new 1,800-second window and the single
lifetime third attempt for the exact exhausted first-page identity. All other
sample, source, quality, quantitative-cap and product rules remain unchanged.

### Scope and immutable evidence

The supplemental run covers exactly the frozen 32-site development split in its
existing order, using the same IDs, centers, request order, category, canonical
query parameters and count contract. It starts from the beginning of that split
but must reuse already complete, identity-matched results rather than reacquire
successful request identities. The `gun-hatake` page-1 request must match the
full canonical request identity in the original ledger, including station,
endpoint, page/start, all credential-free frozen parameters and query
fingerprint. A mismatch stops before I/O.

Create a distinct append-only supplemental ledger/result in a new sibling
directory under the existing pilot artifact parent, outside the frozen current
49-file `target-v4` tree (SHA-256
`49df1e59182bfeb5a3c6eb25f6d53676a96b0cb93c312ff3ccf3d698c5c0af36`). The
historical 44-file pre-receipt subset has SHA-256
`68c125c986f388e56b2a23be3f76867ad41bf0c52cc45469c250f49db112d012`; preserve
both identities. Bind the supplemental ledger by path and SHA-256 to the original HP ledger
and result, the V9 diagnostic reservation/outcome, V10 protocol/parser contract,
sample and query hashes, and exact runtime/manifest hashes. Do not copy those
prior artifacts. The frozen current 49 files must remain byte-identical. Count every
physical supplemental file and any actual copy against both the HP development
retention ceiling and the 2 GiB global ceiling. The future runtime must aggregate
the original and supplemental locations; it must reject unaccounted or
ambiguous roots. The original HP ledger/result and diagnostic remain terminal,
incomplete or diagnostic-only exactly as recorded. A complete supplemental
result may describe only its own 32-site data; it cannot change those earlier
states.

This grant is HP-only. It creates no dependency on Overture metadata or cache
admission, and does not release Overture development, HP prescreen, holdout,
challenge, audit, zero confirmation or any later phase. The previous V6
metadata admission is not bound to V10 and is not an HP-run precondition.

### Single-use activation and prospective deadline

Before execution, the implemented supplemental runtime and tests must be
reviewed on an exact immutable code head/manifest and pass current native-review
and CI gates. Only then may a separate single-use owner activation and root
release bind the exact head/manifest/code-map, original evidence hashes,
sample/order/query fingerprints, output location and remaining budget snapshot.
The activation authorizes only this supplemental HP development run. It cannot
authorize the diagnostic again, another run, a changed request, or any other
phase. V10 approval alone is not activation. Missing, stale, reused or
mismatched activation fails closed. The first invocation consumes this one
prospective window, even if preflight fails. An interrupted same-run
continuation may use only the same activation, run journal, T0 and D before D
expires; that is not a new window. Any further prospective window requires a
new explicit owner amendment and a separate root release.

Enforce a single writer for the activation and both original/supplemental phase
accounting roots. The process must acquire and hold an exclusive lock from
before it validates or changes shared accounting through durable finalization.
Lock contenders cannot reserve budget or dispatch requests; any lock wait is
inside this same window. Loss of the lock before dispatch stops without I/O;
loss after a reservation leaves the request outcome unknown and charged.

T0 is a real, non-backdated UTC timestamp captured at command invocation after
the exact-head activation exists, but before preflight/input validation, lock
wait, reservation or finalization. Persist T0 and a monotonic-clock anchor as the
first supplemental journal record. Reject T0 at or after
`2026-10-22T00:00:00Z`. Define the absolute deadline as
`D = min(T0 + 1,800 seconds, 2026-10-22T00:00:00Z)`. Enforce both the
supplemental monotonic deadline and D throughout input/gate validation, lock
wait, reservation, request spacing, request dispatch, response read, parsing,
budget settlement and durable result finalization. Bound each request timeout by
the remaining interval. A request still in flight at D, or with an ambiguous
completion/receipt at D, is unknown/incomplete; it cannot be accepted as success.
A late failure tombstone may record the incomplete outcome, but it cannot permit
post-D I/O or claim success.

Any process continuation after interruption must use the same activation nonce,
run ID, append-only journal, T0, D and cumulative counters. It must check D before
recovery or validation work; that work consumes remaining time. It must never
grant a new 1,800-second interval or replay a reserved/unknown request. If a
required clock/checkpoint history is absent or UTC is earlier than the last
durable UTC checkpoint, fail closed. No result, page, body or output may be
finalized as successful after either deadline.

### Lifetime attempt exception

The frozen two-attempt lifetime ceiling remains in force for every request
identity except the one full `gun-hatake` page-1 identity above. That identity's
lifetime maximum becomes exactly three: original attempt + spent V9 diagnostic
attempt + one new supplemental attempt. The new attempt must be reserved durably
before dispatch. It has no retry, including after transient transport or HTTP
5xx failure, and no fourth attempt is permitted. A timeout, interruption, crash,
transport failure, ambiguous dispatch or unknown outcome after reservation
consumes this one allowance permanently. A prior or existing supplemental
reservation/outcome blocks another call.

Every other request identity retains its cumulative existing maximum of two
attempts, including attempts in earlier ledgers. Its current retry and terminal
rules remain unchanged: one retry after two seconds only for allowed transient
transport/HTTP 5xx failures; authentication rejection, HTTP 429, schema or
projection failure, request/object identity change, provider error and other
existing terminal outcomes stop under current policy. This exception grants no
additional attempt to page 2 or later, any other station, prescreen, or
confirmation.

### Cumulative counters, page slots and retained evidence

The phase ceilings do not increase: HP development remains capped at 400 total
attempts, 134,217,728 response-body bytes, 134,217,728 retained bytes, 320
successful-page slots and 50 pages per site. Preserve the original and diagnostic
charges and add supplemental attempts/reservations to the same lifetime
accounting. A request body is charged once per actual attempt, independent of
how many retained artifacts reference it; each physical retained copy counts
its actual bytes against retention. No phase budget is transferred or reset.

Verified pre-continuation accounting from the preserved records is 2/400
attempts and 214/134,217,728 body bytes. The phase-wide arithmetic remainder is
398 attempts and 134,217,514 body bytes. The one new request must reserve its
full 1,048,576-byte response maximum before I/O, leaving at most 133,168,938
bytes provisionally available while the outcome is unknown. Confirmed complete
EOF may settle that reservation to the actually observed body size, releasing
only the known unused bytes. If EOF or dispatch is uncertain, retain the full
reservation. These numbers are planning facts, not extra allowance.

The original ledger admits zero successful pages. The diagnostic reserved one
successful-page slot but ended `diagnostic_only/parser_rejected`; its receipt has
no explicit slot-release/admission field. Do not rewrite it, infer a refund, or
claim 320 slots are operationally available. Conservatively count that one
reservation as occupied; there are at most 319 other future admitted, pending
or unreleased slots under the 320-slot ceiling. Define occupancy as
`admitted + pending + unreleased reservations`; a pending-to-admitted transition
counts once. The exceptional `gun-hatake` attempt can produce at most one new
admitted page. If it succeeds, ordinary pagination and the remaining development
sites may proceed in frozen order within unchanged per-identity and phase
limits; page 2 and later get no attempt exception. The future runtime must
explicitly settle its page-slot reservation; an unknown result keeps it occupied.
It cannot retroactively settle the diagnostic slot.

The preserved HP development directory currently contains 14,579 bytes of its
134,217,728-byte cap (134,203,149 bytes of arithmetic headroom). The frozen
current 49-file target-v4 tree contains 41,468,376 bytes of the 2,147,483,648-byte
global cap (2,106,015,272 bytes of arithmetic headroom). The supplemental
directory and all its ledgers, receipts and results count against both
applicable retention caps. Before any request, reserve sufficient space for the
full body cap and a conservative bound on receipts/result bytes. If remaining
space or accounting cannot be proved, stop before opening a socket. Reading or
hashing an existing file does not create another request/body charge.
Every physical retained copy is a separate storage charge and counts in full.

### Outcomes, stops and required implementation acceptance

Keep every per-site/page status, timestamp, request fingerprint, observed
pagination field and byte/attempt/slot disposition. Record the supplemental
fetch/receipt dates separately; do not change source vintage or observation
dates. An incomplete station/page, invalid or changed response, terminal error,
exhausted shared cap, ambiguous dispatch or deadline crossing makes this
supplemental result partial/incomplete or terminal. Preserve partial evidence;
never omit failed evidence or turn missing/error/unknown into zero. V10's exact
empty-first-page representation remains a parser behavior change and may be
accepted only under its existing complete transport and no-provider-error
conditions; any genuine initial zero still requires its separate fresh
24–72-hour confirmation. Do not change production ratings, confidence, nightlife
or HP-zero rules.

The continuation consumer must pass these offline acceptance cases before any
activation:

| Case | Required behavior |
| --- | --- |
| Start at or after cutoff; 30-minute window crosses cutoff | Reject start at cutoff; use earlier of T0+1,800s and cutoff; do not start unbounded requests. |
| Validation, lock wait, recovery or finalization consumes time | Count it from T0; refuse I/O/success after D; resume retains the same T0/D. |
| Exact original `gun-hatake` page-1 identity | Permit at most the one third lifetime attempt; reservation consumes it; no retry or fourth attempt for any outcome. |
| Exceptional page succeeds | Continue ordinary pagination and remaining development sites in frozen order under existing page and phase caps; no later phase is unlocked. |
| Changed query, page, station, source input or run identity | Fail closed before network I/O; exception cannot transfer. |
| Any other request identity | Preserve existing cumulative two-attempt limit and transient-only retry behavior. |
| Reservation, crash, timeout or ambiguous dispatch | Persist before I/O; charge attempt and page slot; keep full 1 MiB on unknown; never blind replay. |
| Complete EOF and known outcome | Settle body to observed bytes; release only known unused reservation; settle page slot explicitly without double-counting transitions. |
| Original/diagnostic evidence and artifact tree | Verify original hashes and all 49 files in the frozen current target-v4 tree unchanged; link, do not duplicate; count every actual copy. |
| Shared cap or retained-space exhaustion | Stop before I/O or preserve partial/incomplete; no transfer or reset. |
| Holdout and unrelated stages | No Overture metadata/development, prescreen, holdout, challenge, audit or confirmation access; no automatic next phase. |
| Complete development zero | Preserve V10 pagination evidence; do not treat it as confirmed HP-zero without the separate 24–72-hour process. |

These are normative requirements, not claims that a pilot has run or passed.
V10 remains the predecessor without this consumer. PR141 adds an offline
implementation and mocked controls; it remains inactive until the exact
successor head and manifest pass native review and CI and a fresh owner
activation and root release are separately issued. The implementation task
creates no activation, execution receipt, or permission to acquire data.

## Historical one-request HP diagnostic exception (spent)

This section records a spent, historical one-request diagnostic, not an active
recovery path. The original `hp_development` phase remains terminal/incomplete:
its frozen start, finish, deadline, ledger and result are not resumed, rewritten
or relabeled. The original deadline was `2026-10-16T13:55:29.181380Z` and has
expired. The owner/root approvals and the one reservation/outcome were consumed
for this diagnostic only and do not authorize the supplemental run below.

The diagnostic ran once on `2026-10-17T18:01:17.376314Z`–
`2026-10-17T18:01:19.124398Z`: HTTP 200, complete EOF, 107 response-body bytes,
`diagnostic_only/parser_rejected`, reason `start_below_one`. Its allowlisted
structure was integer `results_available=0`, string `results_returned="0"`,
integer `results_start=0`, and empty `shop`. It produced no pilot count or
HP-zero confirmation. The discarded original 107-byte body remains unavailable;
neither it nor the diagnostic response establishes the earlier failure cause.

The diagnostic required a one-time owner exception and separate root gate under
the existing accounting tree, bound to its V9 code/manifest, original evidence
and request identity. Those exact gates and the diagnostic reservation/outcome
are preserved and spent. They cannot be reused for this protocol amendment or
for another request.

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

The historical diagnostic command was intentionally not called from
`food_pilot.run`. The invocation below is retained as historical documentation
only and must not be reused:

```sh
PYTHONPATH=scripts python -m food_pilot.diagnostic \
  --manifest /internal/current-v9-manifest.json \
  --owner-exception /internal/target-v4/owner-diagnostic-exception.json \
  --root-gate /internal/target-v4/root-diagnostic-gate.json
```

The API key arrived only through the existing scoped secret consumer as a
process environment value; it was not supplied in command arguments or receipt
files. The command printed only diagnostic state, receipt hash and charged body
bytes. Its HTTP adapter was mock-tested offline. The owner/root/reservation/
outcome receipts are preserved under the original HP evidence; they authorize
no further request, phase completion or zero classification.

## Current-manifest Overture cache-only admission (V20 contract)

The V20 contract adds a separate, disabled-by-default admission destination for
the preserved V4 Overture metadata cache. The cache source remains the exact
`target-v4/overture_metadata` directory and remains incomplete under its
original ledger, deadline and charged counters. A new admission receipt is
written only beneath the sibling
`v20-overture-metadata-admissions/` directory, with fresh current-manifest
owner/root files under its `authorizations/` child. This output is outside the
frozen `target-v4` tree. Source and output roots are independently resolved,
checked against the pinned contract, rejected on symlinks or path escape, and
bound into both authorization receipts and the resulting admission. The
loader requires those same explicit roots and current-manifest bindings; it
replays only the original cache and never opens a provider connection.

The V20 direct successor contract pins the V4 manifest, ledger and compact
diagnostic hashes, the V18 historical supplemental HP development handoff,
the exact source and admission paths, and the retention roots and limits.
Historical V6 admission remains V6-bound and is not authorization for V20.
Every V20 admission requires fresh owner/root receipts bound to the exact V20
manifest and runtime code map. No authorization or admission receipt is
created by the offline implementation or tests.

Retention is computed over physical files: metadata usage is the original
metadata source directory plus the external admission directory, bounded by
the inherited 64 MiB metadata ceiling; global usage is the frozen `target-v4`
tree, historical HP run and its authorization directory, plus the external
admission directory, bounded by the inherited 2 GiB ceiling. The V4 source
tree is counted once in global usage and is also included in metadata usage;
references and hash reads do not create a second charge, while every physical
copy does. The baseline source/global byte totals and exact roots are checked
before receipt creation and after loading. Admission does not rewrite source
files, complete the V4 phase, or release Overture development or any other
pilot phase. This section records a disabled historical-input handoff, not an
execution release.
