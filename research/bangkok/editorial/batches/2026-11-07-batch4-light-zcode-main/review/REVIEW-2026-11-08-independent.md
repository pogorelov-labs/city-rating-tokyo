# Independent review 2026-11-08 — batch 4 light (24 bundles)

Reviewer: **agent review** (DeepSeek Harness / deepseek-flash), `reviewed_at`
2026-11-08T13:00:00+03:00. Not the human signatory (DEC-2/G10 open). Full
report: [`../../../2026-11-08-independent-review.md`](../../../2026-11-08-independent-review.md).

**Note on the missing batch record.** This batch has no `review/findings.md`
and no `selection.md`, although the packet/tier plan refer to batch findings.
The stakes below were re-derived from bundles and `review.notes`; the
researcher's findings file is still owed (F8).

## Verdict — 6 approved / 18 blocked

The blocks are mechanical (normalize damage) plus one provenance class and a
handful of copy/provenance items. The underlying light-pass research is often
usable; the defects are in how it was assembled.

| Bundle | Status | Reason |
|---|---|---|
| `st.mo-chit` | **approved** | P2 "coordinator" only in uncertainties; P3 date annotations |
| `st.saphan-khwai` | **approved** | P3 date annotations |
| `st.kamphaeng-phet` | **approved** | P3 date annotations |
| `st.siam` | **approved** | P2 claim refs/coordinator only in uncertainties |
| `st.chit-lom` | **approved** | P2 c06 removed at assembly (documented); P3 "live page 2026" date |
| `st.ratchadamri` | **approved** | P2 "brief" only in uncertainties; P3 "live page 2026" date |
| `bang-phlat` | **blocked** | F1 day_night/within placeholders + uncertainties char-explosion |
| `bang-sue` | **blocked** | F1 same |
| `bangkok-noi` | **blocked** | F1 same |
| `din-daeng` | **blocked** | F1 + F2 (2 claim limitation arrays) |
| `dusit` | **blocked** | F1 same |
| `khlong-san` | **blocked** | F1 + F5 false ICONSIAM/G2 polygon claim |
| `sathon` | **blocked** | F1 + F2 (6 claim arrays); boundary phrasing metres-sensitive |
| `st.hua-lamphong` | **blocked** | F1 + F2 (1 claim + 10 source arrays) + F3 (c02/c12) + F6 |
| `st.khlong-san` | **blocked** | F1 + F2 (1 claim + 6 source arrays) |
| `st.phra-ram-9` | **blocked** | F1 + F2 (1 claim + 8 source arrays) |
| `st.saphan-taksin` | **blocked** | F1 + F2 (1 claim + 8 source arrays) + F6 + false claim_support=pass |
| `thon-buri` | **blocked** | F1 + F2 (5 claim arrays) |
| `st.national-stadium` | **blocked** | F10 "the batch's lowest" in guide lead |
| `st.sala-daeng` | **blocked** | F3 (c11/c12); F10 "this batch" in strengths |
| `st.saint-louis` | **blocked** | F3 (c10/c12) + F10 "brief … needs re-checking" in preview/lead |
| `st.victory-monument` | **blocked** | F10 "coordinator must settle" in guide lead |
| `st.phaya-thai` | **blocked** | F3 (c06/c08) |
| `st.phetchaburi` | **blocked** | F3 (c05/c07); F10 "this batch" in tradeoffs |

## The two systemic batch-4 defects

**F1 — normalize damage (12 bundles).** `editorial.day_night` and
`editorial.within_area_variation` carry literal `"text"` / `"text_en"` /
`"claim_ids"` placeholders; `editorial.uncertainties` is either the placeholder
pair or a character list. Raw copies preserve the prose, so the fix is a
lossless reconstruction from `raw/` (the same class as the limitations repair).
The shipped graph gates never looked at these fields.

**F2 — the limitations repair missed mixed and source arrays (7 bundles, 49
arrays).** The 2026-11-08 pass repaired only claim arrays whose entries were
*all* single characters. It missed (a) mixed arrays (a character prefix plus a
trailing sentence) and (b) **all source-level arrays**. Join the character
prefixes and re-verify against `raw/`.

## Other batch-4 blocks

- **F3** (sole-unread claims): `st.hua-lamphong` c02/c12, `st.phaya-thai`
  c06/c08, `st.phetchaburi` c05/c07, `st.saint-louis` c10/c12,
  `st.sala-daeng` c11/c12. Read the cited bodies or downgrade/remove the
  claims and the copy that cites them.
- **F5** (`khlong-san` district): the "district polygon excludes ICONSIAM"
  claim is false. The 10-vertex object is the **station cell**
  (`station-geometry.json["khlong-san"]`); the 50-vertex **khet** contains
  ICONSIAM and G2 and excludes River City. Re-run with `--khet` and correct
  c02/c03/scope_notes and the program final review §2.4.
- **F6**: `st.hua-lamphong` c11/c12 and `st.saphan-taksin` c08/c12 attach
  app-data locators to unrelated web sources (an X museum post; the Sathorn
  Unique Tower article). Cite the app anchor as a non-web source or move the
  statement to limitations.
- **F10**: internal/research voice in user-facing copy (national-stadium,
  victory-monument, saint-louis, sala-daeng, phetchaburi).

## Verification performed

- Sathon: app anchors for Surasak/Chong Nonsi/Saint Louis all PIP-out (the
  Sathorn-road edge; Saint Louis flips inside a few metres south) — the
  batch's "three BTS nodes outside" is correct for the app anchors but should
  be phrased as boundary-sensitive.
- Khlong-san: `--khet` PIP puts ICONSIAM and G2 inside; the station cell puts
  them outside. The bundle's own review note ("10 vertices, ~1.0×1.5 km bbox")
  matches the station cell exactly — the root-cause proof.
- 6 approved bundles have no P1 under the new audit rules; their previews are
  clean, their sources cover ≥3 families, and no claim relies solely on a
  snippet.

No bundle content was changed by this review; only `review.*` fields were set.
