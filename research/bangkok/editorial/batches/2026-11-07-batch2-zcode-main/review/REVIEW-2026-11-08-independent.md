# Independent review 2026-11-08 — batch 2 (6 bundles)

Reviewer: **agent review** (DeepSeek Harness / deepseek-flash), `reviewed_at`
2026-11-08T13:00:00+03:00. Not the human signatory (DEC-2/G10 open). Full
report: [`../../../2026-11-08-independent-review.md`](../../../2026-11-08-independent-review.md).

## Verdict — 1 approved / 5 blocked

| Bundle | Status | Reason |
|---|---|---|
| `pom-prap-sattru-phai` | **approved** | 24,000 2-bed below observed asks is pipeline CRTKY-141, not a copy fix |
| `phaya-thai` | **blocked** | F4: inline claim refs in preview/lead/every guide item; union preview claim_ids |
| `st.charoen-nakhon` | **blocked** | F4: inline refs; F12: all 12 QA notes empty |
| `st.nana` | **blocked** | F4: inline refs; F14 reviewer green note (non-blocking) |
| `st.ratchathewi` | **blocked** | F4: inline refs in guide items (preview/lead clean) |
| `st.wat-mangkon` | **blocked** | F7: A8 overstatement — the pilot's khet note is correct |

## What the blocks are (and are not)

- **F4** is mechanical: the batch-2 assembler extracted inline references into
  `claim_ids` but left them in `text_en`. The prose itself is good; strip the
  refs, keep per-block provenance, re-assemble, re-review. Preview/lead
  `claim_ids` are a union of the guide's claims (11–16 IDs), not the refs in
  that text — a P2 provenance-specificity issue across the batch.
- **F7** is a wording error, not a research error: Wikipedia places Wat Mangkon
  Kamalawat in **Pom Prap Sattru Phai** (outside Samphanthawong khet) and the
  PIP probe puts it inside `st.wat-mangkon`'s catchment — exactly the A8
  two-question rule. `scope_notes` and `c04` say the pilot note is
  "refuted/contradicted"; rewrite to "consistent with the pilot's khet note".
- **F12**: `st.charoen-nakhon` has claim references but empty notes for all 12
  questions.

## Verification performed

- Bumrungrad straddle: PIP main point `True` (13.7440/100.5540), geotag `False`
  (13.7463/100.5526) — matches `nana-c09`.
- Wat Mangkon Kamalawat: PIP 13.7419/100.5103 `True`; Wikipedia 13.743828/
  100.509552, Pom Prap Sattru Phai. Pilot note confirmed; do not "fix" it.
- BTS Phaya Thai/ARL outside the khet: PIP 13.75696/100.53475 `False`; inside
  ratchathewi `True`. (`phaya-thai-c03` is the claim; the packet's c05 pointer
  is stale.)
- Gold Line: 3 stations, 1.8 km, opened 2020-12-16 (Wikipedia); no river
  crossing — matches `charoen-nakhon-c01/c02` and scope_notes.
- Nana green: Overpass 406, but the OSM API shows the only named park
  intersecting the cell is the **สวนเพลินจิต / Phloen Chit Park** linear sliver
  (0.515 ha; OSM hours 05:00–22:00), plus 1.37 ha non-private `leisure=garden`
  — consistent with the "1.4 ha unidentified" gap and green 10 not
  reproducible as usable parkland.

No bundle content was changed by this review; only `review.*` fields were set.
