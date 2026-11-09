# A-1 reviewer packet — sign-off addendum (2026-11-09)

This is the **pre-flight addendum** for the human editorial sign-off (DEC-2/A-1).
It supersedes any per-bundle score/rank context printed in earlier packets:
**the bundle files on `main` are the single source of truth — review what is
in the repo now.**

## 1. What changed since the last packet you may have seen

- **Ghost-station removal (B-1, PR #182):** sena-ruam was a station that was
  never built; its area was removed via a deterministic pipeline replay of the
  frozen 2026-10-26 inputs. The station-area cohort is now **132** (was 133).
  The 50 districts are completely unchanged.
- **Re-anchor (D-4/D-3, PR #183):** every researched bundle's
  `selection_context` (model score, cohort rank, cohort size) was re-derived
  from the current snapshot: 23 bundles changed score by ±0.04–0.14, every
  station-area bundle's cohort size moved 133→132, district bundles are
  untouched. No claim text, guide copy, sources, or statuses were altered by
  these steps (details: `2026-11-08-continuation-plan.md` §15, 2026-11-09
  entries).

## 2. Flagged item for your decision — thong-lo-c19 (stale cohort citation)

`st.thong-lo` claim **thong-lo-c19** (batch `2026-11-05-pilot-zcode-main`,
`researcher_inference`) embeds a cohort size in prose:

> "The mid-table model score (**6.46, rank 51/133**) and the enthusiastic
> editorial coverage are measuring different things…"

The rank (51) and every per-dimension rating cited in the sentence are still
current; only the cohort size is stale (133 → 132).

**Proposed correction (one token):** `rank 51/133` → `rank 51/132`.

Everything else in the claim is verified unchanged. Please record your
decision in the `review_notes` column of your CSV row for `st.thong-lo`
(e.g. "c19: approve 133→132 correction") — the edit is applied only after
your sign-off, logged in the rework log.

## 3. Audit-denominator notes (no action needed)

- The B-2 anchor-audit receipts and B-4 polygon table still say "of 133".
  Conclusions are unaffected (geometry was untouched by B-1); the live
  denominator is 132.
- The served editorial chunks never contained rank prose; this item exists
  only in the research claim corpus.

## 4. sena-ruam row

The template contains a `st.sena-ruam` row (batch3, status `approved`).
The area no longer exists in the app, the bundle is retained as a historical
record, and nothing from it ships. Recommended decision: **`skip`**.

## 5. How to sign off

1. Review the bundle files for the entities you own (tier A/B/C:
   `research/bangkok/editorial/batches/<batch>/profiles/<key>.json` — guide
   copy, claims, sources, statuses, conflicts; batch 5 stakes recap lives in
   the reviewer-packet §3c of `2026-11-08-independent-review.md`).
2. Fill `decision` in [`a1-signoff-template.csv`](a1-signoff-template.csv):
   `approved` | `blocked` (with `review_notes`) | `skip` (rows left untouched).
   Unfilled rows fail validation — every row needs an explicit decision.
3. Hand the CSV back (or just tell me it's done). I apply it with
   `kit/tools/record_signoff.py --apply <csv> --reviewer "<your name>"`
   (dry-run first, then `--write`), the exporter re-runs so previews
   materialize for signed bundles, and the dark flag stays off until A-5/A-6
   clear. Going live with copy is a separate, explicit go.

`approved` sets `review.status=approved` with you as the human signatory
(agent-review provenance is superseded and logged, never counted as
copy-eligibility on its own — E-5).
