# Batch 3 findings — tier A full bundles (10 entities)

> **Reconstructed 2026-11-08** (review F8/A-9): the batch closed without this
> findings file; it is rebuilt from the bundle review notes, search logs,
> manifests, the independent review, and the coordinator verification passes.
> Nothing here is newly researched — it is a record of what the batch
> established, with pointers to the authoritative artifacts.

Batch: `2026-11-07-batch3-zcode-main` · tier A full contract (12–18 claims,
≥4 sources/≥3 families) · window 2024-11-05..2026-11-07 · snapshot
`bkk-d6499618507e7561` · entities: st.ha-yaek-lat-phrao, st.phloen-chit,
st.sam-yan, st.sam-yot, st.sena-ruam, st.ratchaprarop, ratchathewi,
phra-nakhon, chatuchak, pathum-wan (din-daeng/khlong-san districts deferred
to tier B).

## What the batch established (the stakes)

1. **Ghost station (program-level finding).** `st.sena-ruam` (rank #9/133)
   is a planned-but-never-built BTS infill (N6) modeled as operating; the
   bundle documents the Prachachat 2026-11-05 council hearing as the live
   hook. Routed to pipeline item B-1 (139-station audit). The bundle itself
   is approved — it describes the app's data honestly, including the defect.
2. **sam-yot provenance was below contract** — the independent review (F3)
   found 11 of 18 claims resting solely on unread sources, and the "post-hoc
   verification pass" referenced in the batch commit message was not
   reflected in the delivered bundle. **Fixed in the A-8 rework (2026-11-08):**
   9 surviving claims body-read (fetch + term-match ledger), 2 claims removed
   with substance preserved in review.notes.
3. **ha-yaek park geometry** — the app's 38.1-ha green polygon matches none of
   the published park areas (30.4/22/60 ha); provenance unknown; Wikipedia
   geocodes disagree internally by up to ~500 m. Polygon-question (B-4
   family), recorded not fixed.
4. **phloen-chit polygon relations** — clip lines at Chit Lom/Nana, the
   southern boundary against the lumphini unit, and the pier-count question
   (Wireless pier confident; Chidlom vs Nana Nuea ambiguous) unresolved; OSM
   blocked in that pass.
5. **pathum-wan One Bangkok** — consistent facts across four bundles
   (opening 25 Oct 2024, TCC Assets + Frasers, SOM masterplan); hotel opening
   dates conflicted across source generations (recorded, unresolved).
6. **chatuchak khet** — PIP cross-check of 57 landmark points against the app
   ring agreed with OSM on every tested point (no boundary conflict found);
   the `chatuchak` key-shadowing trap documented here is the same one that
   later caused the batch-4 khlong-san error (fixed by kit `--khet`, B-8).
7. **ratchathewi** — the "1 Michelin star" app fact was corrected to two
   one-star venues in-khet (Signature at VIE, Wana Yook) via B-6; district
   rent blend semantics recorded.

## Verification and gates

- Coordinator verification passes ran on the batch's boundary claims; the
  sam-yot below-contract state was flagged honestly in the bundle
  (`review.checks.claim_support = fail`) rather than hidden — and was the
  review's sharpest F3 finding.
- Five editorial sets in this batch were coordinator-drafted after agent
  output fell short (pre-flagged for reviewer attention, A-7).
- Gates at close: validate ALL OK; audit zero P1 under the rules then in
  force. Post-review state: all 10 bundles approved after the A-8 rework
  (agent-review provenance; human sign-off pending, DEC-2).

## Open issues carried forward

- `kit/recheck-due.py` registry (C-5) carries this batch's `recheck_by`
  flags; C-1 wave items (Wat Saket fair, canal-park progress) are tracked
  there.
- khlong-ton/ICONSIAM straddle and the phaya-thai Victory-Monument khet
  conflict remain open by design (B-4).
- The batch-3 `tools/normalize.py` five-shape adapter is superseded by
  `kit/assemble.py`; kept for the record.
