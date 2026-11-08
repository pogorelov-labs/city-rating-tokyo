# Fourth review — superseded-bundle handling was the gap (2026-11-08)

Triggered by "review critically again" after batch 5 + the integration
review. The previous passes audited claims, gates, and my own corrections;
this pass audited **the state that batch 5 created** — and found one genuine
structural miss plus its downstream shadows. All verified empirically before
writing, and all fixed in this same pass unless marked open.

## The structural miss: 9 entities now have TWO bundles, and nothing declared precedence

D-1 upgraded 9 entities in place — but the superseded tier-B bundles (batch
4, `approved` at their tier) still exist. Empirically confirmed: 9 duplicate
bundle-pairs; **no doc or tool declared which record wins.** Consequences,
all confirmed:

1. **recheck registry double-counted**: 668 items included **65 stale rows**
   from the superseded tier-B bundles (old claims, old recheck flags) — an
   owner working the calendar would re-verify facts the tier-A record
   replaced. Fixed: `kit/recheck-due.py --supersede later:earlier` precedence
   flag (basename comparison — the first run dropped 0 due to a
   path-vs-basename mismatch, caught by the expected-count check); registry
   regenerated **668 → 603** (253 flags + 399 open issues; 65 dropped = the
   probe's exact prediction).
2. **B-11 registry predated batch 5** (generated 00:21Z; batch 5 researched
   13:15–15:27Z): 543 URLs missing the upgrades' contributions. Fixed:
   rebuilt over all six batches → **666 URLs** (70/52/42 field
   inconsistencies — the adapter consults the rebuilt file).
3. **Link-health never ran on batch-5 sources** (wave 1 predated the batch).
   Fixed: wave 2 over batch 5's 162 URLs → 152 OK, 6 known-wall 403/429,
   1 transient 520 (also seen in wave 1), **zero dead**.
4. **E-7 corridor sweeps are stale for the 9 upgraded units** — they read the
   tier-B framings (e.g. sala-daeng in the Silom corridor, siam/chit-lom in
   Sukhumvit-core). Marked in the E-7 doc as a **pre-E-2 re-sweep scoped to
   the 9 units**; not silently treated as covered.
5. **Precedence now declared** in E-1 §2 (exporter takes highest tier per
   entity, records `superseded_by` provenance) and §6b of the integration
   review — without it, the evidence drawer and every future aggregation
   would double-count the same way the registry did.

## Stale program documents (found, fixed)

- `2026-11-08-continuation-plan.md` §0 still said **22/24/137** and the
  pre-batch-5 source totals → corrected to **31/15/137** and the honest
  totals across all researched records (830 sources / 693 body-read / 819
  claims / 666 distinct URLs, with the precedence note).
- `2026-11-08-final-review.md` completion-state line → same correction.

## Missing pipeline receipts (found, routed)

Batch 5 produced two green-family findings that were sitting in the batch
findings doc but never routed to the pipeline notes: **siam's ~6 ha green
decomposes to the Sra Pathum palace precinct + temple grounds** (B-3 family)
and **sala-daeng's new Suan Dusit Arun rooftop park** (opened 2025-09-03,
partially offsets the edge-only Lumphini basis). Routed as items 8–9.

## Integration-review gaps (found, amended in place)

- No precedence rule (above).
- `recheck_due` was specified as data but given no UI rendering — the
  "facts due recheck" chip is now in the card table (§6b.2).
- `data_date` (scores, 2026-10) vs `as_of` (editorial, 2026-11) are different
  clocks; UI must label them separately or imply scores moved when only
  research did (§6b.3).
- CI coupling: the exporter reads the research tree at build time; the
  digest-verified manifest + feature flag keep CI safe (§6b.4).

## Also checked and found sound (so later passes don't re-litigate)

- Tier-plan counts (31/15/137) and per-row statuses — correct, including the
  stale sala-daeng "blocked" fix from the batch-5 update.
- G17/G20/audit/validate on batch 5 — clean (run at assembly, re-verified).
- Review-record semantics: batch-5 bundles `ready_for_review` with
  `reviewer: null` — correct; no agent sign-off leakage.
- The fourth-pass fixes introduced one new bug themselves (the `--supersede`
  basename mismatch, dropped 0) — caught by checking the drop-count against
  the independent probe before accepting the result. The machine-gates
  lesson again: verify the fix's *effect*, not its exit code.

## Open (unchanged, for the record)

DEC-2/A-1 named reviewer (55 bundles) · A-5/A-6 human passes · sena-ruam
replay on the build machine · TG handles · the 41 B-2 missing areas (20
HTTP-error articles likely don't exist — diminishing returns).
