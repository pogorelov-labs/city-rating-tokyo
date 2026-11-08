# Gate verification — the schema gate was silently hollow until 2026-11-08

A P0 kit-integrity finding from the continuation work (plan v2.2 execution),
with the repairs that make the gates genuinely green for the first time.

## What happened

`kit/validate.py`'s `main()` called the schema validator with a **throwaway
error list**:

```python
validate(b, schema, fn, [])   # errors appended into a literal and discarded
semantic_checks(b, fn, errors)  # only these ever surfaced
```

So **every `ALL OK` printed since the pilot verified only the semantic
reference checks** (claim/source/QA closure), never the schema itself. The
discarded-errors bug was compounded by a second defect in the same function:
the `anyOf` branch never rolled back a failed variant's errors, so a value
that matched a later variant still carried the earlier variant's errors —
which made the one legit nullable case (tier-C `preview`/`guide_lead: null`,
legal in the handoff schema all along) look like a violation.

Neither bug produced false *passes* of the semantic layer — the audit
(`audit.py`) recomputes independently and its zero-P1 record stands — but the
schema dimension of the G1 gate was validation theater.

## How it was found

The B-11 registry build + the C-6 link-health wave surfaced `canonical_url`
values that are not URIs ("https://host + annotation" compounds, Overpass
query descriptions). Driving the validator directly on one of those bundles
produced schema errors the batch runs had never reported — which led to the
two root causes above.

## The true defect surface (all repaired 2026-11-08, logged)

[`kit/tools/contract_repair.py`](kit/tools/contract_repair.py) +
[`2026-11-08-contract-repair-log.jsonl`](2026-11-08-contract-repair-log.jsonl):

| Class | Count | Repair |
|---|---|---|
| `canonical_url`/`retrieved_url` carrying verbatim annotations | 18 field values | split to the leading URL token; annotation preserved verbatim in the source record's `limitations` (no provenance invented) |
| sam-yan's 4 Overpass records sharing one normalized endpoint | 3 records merged | one session record; each query annotation kept verbatim; evidence remapped |
| `temporal_scope.notes` / `geography.notes` = null | 134 | coerced to `""` |
| `commercial_context` booleans | 32 | `""` / `"commercial (boolean flag normalized)"` |
| `editorial.uncertainties` as `{text, claim_ids}` dicts | 34 | flattened to their text strings |

The tail manifest gap (batch had **no manifest at all**) was fixed earlier the
same day (d40c83c). **No schema change was needed** — the handoff schema
already permits null preview/guide_lead; the validator was the defect.

## Going-forward prevention

- `assemble.py` now normalizes all five classes at assembly time (URL
  annotation split, bool commercial_context, null notes, dict uncertainties),
  each counted in the manifest normalization log.
- `validate.py` error plumbing fixed; schema path pinned to the **in-repo**
  handoff schema (a stale external copy used to be preferred silently).
- Unit tests now cover the schema-error path, anyOf rollback, and each
  normalization (20 tests green).

## Gates after repair (2026-11-08, genuinely)

- `kit/validate.py`: **ALL OK ×5 batches** (schema + semantic, for real).
- `kit/audit.py`: **0 P1 across all five batches**; P2s are the documented
  snippet-corroboration / URL-scheme / advisory classes.

## C-6/G14 link-health wave 1 (same day)

[`2026-11-08-link-health-wave1.json`](2026-11-08-link-health-wave1.json) — 543
canonical URLs (post-repair): **485 × 200 OK**, 8 × 202 (bot-accepted),
27 × 403 + 1 × 402 + 1 × 406 + 4 × 429 (access-limited — the same walls
logged during research), 1 × 520 + 12 transient network/timeout.
**4 dead (404)**, flagged with archived-citation limitations on their source
records: CNN Sathorn Unique (already excluded from claims, B-6), the
parameterless Wikipedia REST summary URL (ratchaprarop anchor coordinates —
already in B-2's audit scope), HipFlat Chapter Chula Samyan (never retrieved;
F-2-class snippet provenance), lad.co.th Dutch-embassy land post (phloen-chit
c05/c10 — the conflicting figure survives in paraphrases; claim already cites
both sides). Wave 1 resolves URL *liveness only*; content re-reads stay with
the dated recheck waves (C-1..C-4) and C-7.

## Honest correction to the program record

Earlier statements that batches "passed `kit/validate.py` (ALL OK)" described
semantic-checks-only verification. The bundle *content* claims elsewhere in
the reviews rest on the independent audit + coordinator verification passes,
which are unaffected. The schema dimension is genuinely verified from
2026-11-08 onward.
