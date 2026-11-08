# Canonical publisher-family relabel (B-10/G21) — 2026-11-08

Execution record for plan item **B-10** and gate **G21**. The kit now computes
corroboration independence over **canonical publisher families**
([`kit/canonical.py`](kit/canonical.py)): Wikipedia language editions and
Wikimedia projects are one publisher family (Thai Wikipedia routinely
translates English Wikipedia), OpenStreetMap and Overpass are one (Overpass is
a query API over the same database), portal casing/snippet variants merge
(HipFlat / "HipFlat (via search snippet)" / "Hipflat / property portals"), plus
named-publisher variant merges (Time Out, Thai PBS, BK Magazine, Nation Group,
One Bangkok, Condoreviews, DDproperty/PropertyGuru, …). Agent-generic buckets
(`news-media`, `real_estate_portal`, `transit-operator`, `user-generated`, …)
are deliberately **not** merged with named publishers — that would be
speculative.

## Deterministic result

- **23 of 422 corroborated claims relabel to `proposed`** → corpus status
  counts: **399 corroborated / 228 proposed / 40 conflicted** (pre: 422/205/40).
- 21 of the 23 are English-Wikipedia + Thai-Wikipedia pairs; 2 are HipFlat
  casing/snippet variants (phra-nakhon-c12, sam-yan-c14).
- Per-claim ledger: [`2026-11-08-canonical-relabel-log.jsonl`](2026-11-08-canonical-relabel-log.jsonl)
  (94 lines: 23 relabels + 71 limitations repairs, below).
- Reconciliation: the deep review's in-session estimate was 27 relabels under
  an unrecorded mapping; the committed rule set is authoritative and
  reproducible (`canon_families()` is unit-tested). The deterministic count is
  **23**; the plan's "27 → 395" figure is corrected to "23 → 399" wherever it
  appears.

## Re-gate results (post-relabel)

- `kit/validate.py`: **ALL OK ×5 batches** — note: at relabel time this still
  ran with the discarded-schema-errors bug (see
  [`2026-11-08-gate-verification.md`](2026-11-08-gate-verification.md)); the
  ALL OK was re-verified genuinely later the same day after the contract
  repair pass.
- `kit/audit.py` (now canon-aware + G20/G24): **zero P1 across all five
  batches**; findings are the documented P2 classes (snippet-corroboration
  `body_read=false` flags, ha-yaek claim-prefix advisories, 1 radius→time
  advisory, G24 URL/provenance notes).

## Second defect found and fixed by the re-gate: exploded limitations arrays

The new limitations-integrity rule (P1) caught **71 claims in batch 4** whose
`limitations` arrays had been exploded into single characters by the batch-4
normalize step (e.g. `["r","e","v","e","n","u","e",…]`). All 71 were repaired
by joining the characters back — verified byte-exact against the raw agent
output (e.g. khlong-san-c03 → "app khlong-san polygon is too coarse to contain
most of these points …"). This is a normalize-bug class the old audit could
not see; the rule is now standing so it cannot recur silently. Reviewers
(A-1) should spot-check a handful of batch-4 claims' limitations against their
cited sources, per the packet note.

## Method invariants (asserted by `kit/tools/relabel_canonical.py`)

1. Relabels only ever move `corroborated → proposed` (canonical families are a
   subset of raw families — merging can only reduce independence).
2. `conflicted`, `approved`, `rejected` statuses are untouched.
3. Stored `publisher_family` strings remain raw (provenance preserved);
   canonicalization happens only in the corroboration computation.
4. The pass is idempotent (marker-checked review note; manifest stamp
   overwrites deterministically).

Bundles are edited in place — **never re-run `kit/assemble.py` over closed
batches** (raw/ predates the coordinator corrections applied to profiles/
after assembly).
