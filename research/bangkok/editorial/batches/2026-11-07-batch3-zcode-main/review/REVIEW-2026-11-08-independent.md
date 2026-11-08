# Independent review 2026-11-08 — batch 3 (10 bundles)

Reviewer: **agent review** (DeepSeek Harness / deepseek-flash), `reviewed_at`
2026-11-08T13:00:00+03:00. Not the human signatory (DEC-2/G10 open). Full
report: [`../../../2026-11-08-independent-review.md`](../../../2026-11-08-independent-review.md).

**Note on the missing batch record.** This batch has no
`review/findings.md` (and never had one in git), although the reviewer packet
and tier plan refer to "the batch findings files". The stakes below were
re-derived from the bundles, `review.notes`, and the batch-3 commit message;
the researcher's findings file is still owed (F8).

## Verdict — 9 approved / 1 blocked

| Bundle | Status | Reason |
|---|---|---|
| `chatuchak` | **approved** | 8 snippet-only corroboration sources, no sole reliance |
| `pathum-wan` | **approved** | 15 snippet-only corroboration sources, no sole reliance |
| `phra-nakhon` | **approved** | 13 snippet-only corroboration sources, no sole reliance |
| `ratchathewi` | **approved** | P3 `ratchathewi-d-cNN` prefix; legacy AI-summary source (P2) |
| `st.ha-yaek-lat-phrao` | **approved** | P3 short claim prefix; 5 snippet-only sources |
| `st.phloen-chit` | **approved** | legacy AI-summary source (P2); 5 snippet-only sources |
| `st.ratchaprarop` | **approved** | P3 "ARL-only control" jargon in copy |
| `st.sam-yan` | **approved** | 3 snippet-only corroboration sources |
| `st.sena-ruam` | **approved** | ghost-station finding verified; 2 snippet-only sources |
| `st.sam-yot` | **blocked** | F3: 11 claims rest solely on snippet-only sources |

## The one block — `st.sam-yot`

- 40 of 43 sources are `body_read: false`; 11 claims (c06, c08–c17) cite only
  unread sources. Their source records carry the line "corroboration only —
  every claim citing it also cites at least one fully read source", which is
  false for those claims.
- The commit message says a post-hoc pass upgraded c06/c14/c15/c16/c18 to
  body-read; the delivered profile does not reflect it.
- `review.checks` already says `sources: incomplete`, `claim_support: fail` —
  honest, but the bundle is not approvable at the stated evidence bar.
- The content is mostly recoverable by opening the cited bodies (Wongnai,
  Time Out, BMA pages, DOPA table, KTB/PropertyScout listings). Read them,
  flip `body_read` where true, correct or drop the affected claims, and update
  the source limitation lines.

## Verification performed

- Ghost station: `st.sena-ruam` is not an operating BTS station; the bundle's
  identity claims are well supported (Thai Wikipedia + Prachachat 2026-11-05).
  This is the program's highest-value data-layer finding and is **not** a
  reason to block the bundle.
- Geometry: `st.sena-ruam` cell / neighbour clipping, `st.sam-yot` Rommaninat
  note, `chatuchak` park totals — spot-checked against the app polygons.
- Claim provenance: canonical recorroboration recomputed; no P1 under the
  shipped rules. The new audit rules (§6 of the main report) pass all nine
  approved bundles.

## P2/P3 residuals (non-blocking)

- Claim-ID naming drift: `ratchathewi-d-cNN` (deliberate district/station
  disambiguation, mis-flagged by the audit rule), `ha-yaek-cNN` (short form).
- Legacy AI-summary-marked source in `ratchathewi` and `st.phloen-chit`
  (F-2 rule applies going forward; documented).
- Snippet-only sources are flagged and used as corroboration only in the nine
  approved bundles; no claim relies solely on one (verified).
- `st.ratchaprarop` preview/lead call the unit "the app's ARL-only control" —
  research jargon in product copy; rewrite before publication (P3).

No bundle content was changed by this review; only `review.*` fields were set.
