# Batch 4 findings — tier B light bundles (24 entities)

> **Reconstructed 2026-11-08** (review F8/A-9): the batch closed without this
> findings file; it is rebuilt from the bundle review notes, search logs,
> manifests, the independent review, and the rework ledger. Nothing here is
> newly researched.

Batch: `2026-11-07-batch4-light-zcode-main` · tier B light contract (8–12
claims, ≥3 sources/≥2 families) · window 2024-11-05..2026-11-07 · snapshot
`bkk-d6499618507e7561` · entities: st.mo-chit, st.saphan-khwai,
st.kamphaeng-phet, st.siam, st.chit-lom, st.ratchadamri, st.national-stadium,
st.sala-daeng, st.saint-louis, st.victory-monument, st.phaya-thai,
st.phetchaburi, st.hua-lamphong, bang-sue, bang-phlat, bangkok-noi, din-daeng,
dusit, khlong-san, sathon, thon-buri, st.khlong-san, st.phra-ram-9,
st.saphan-taksin.

## What the batch established (the stakes)

1. **Two systemic assembly defects, both caught by the independent review and
   fixed in the A-8 rework:**
   - **F1 normalize damage (12 bundles, 60 entries):** the light adapter
     emitted `day_night`/`within_area_variation`/`uncertainties` as single
     objects where lists were required; iterating keys produced literal
     `"text"`/`"claim_ids"` placeholders in user copy. Rebuilt verbatim from
     `raw/` (72 fields).
   - **F2 exploded limitations (49 arrays):** the 2026-11-08 repair pass
     covered only all-single-char claim arrays; mixed claim arrays and
     source-level arrays remained. Joined in the rework (byte-checkable).
2. **sala-daeng merge finding (pre-flagged in the packet):** the app merges
   Sala Daeng + Si Lom ≤450 m apart into one unit; the bundle documents the
   nightlife-10 reality (Patpong/Lalai Sap) and the Lumphini Voronoi split.
3. **saint-louis anchor:** the app's anchor sits ~720 m from the real station
   node (the genuine S4 infill, opened 2021-02-08, was findable) — the
   sharpest B-2 anchor-audit case.
4. **sathon boundary sensitivity:** app anchors for Surasak/Chong Nonsi/
   Saint Louis all PIP-out of the khet polygon (the Sathorn-road edge) —
   correct for the app anchors, metres-sensitive by phrasing.
5. **khlong-san district error (F5, fixed):** the bundle's PIP claims had
   measured the **station cell** under the documented key-shadowing trap, not
   the khet ring; c02/c03 rewritten from `--khet` truth in the rework.
6. **hua-lamphong afterlife + phetchaburi/CODI displacement + victory-monument
   renovation + mo-chit market reorg + phra-ram-9 Jodd Fairs demolition** —
   all documented as D-1 upgrade candidates (contested/featured units).
7. **chit-lom 120,000 2-bed override** = top-decile luxury, not a median
   (B-5 pipeline item).

## Verification and gates

- The batch-4 `partial`→`answered` QA normalization was pre-flagged (A-7) and
  examined by the review.
- Gates at close: validate ALL OK; audit zero P1 under the rules then in
  force — the review's new rules then found 126 P1s (F1/F2/F3/F6 classes),
  all cleared by the A-8 rework; all 24 bundles now approved (agent-review
  provenance; human sign-off pending, DEC-2).
- Axis-1 coverage battery was skipped in this batch (C14) — folded into
  future light passes per D-5; editorial mention breadth is recorded in
  manifests going forward.

## Open issues carried forward

- st.nana green 10 / 1.4-ha unidentified park → resolved enough by the
  review's OSM audit (F14: สวนเพลินจิต linear park 0.515 ha in-cell + 1.37 ha
  non-private gardens) — green-basis disclosure question stays with B-3.
- Link-health wave 1 flagged the Sathorn Unique Tower CNN article dead
  (archived-citation status recorded).
