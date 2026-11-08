# Batch 5 findings — D-1 tier-B→A upgrades (9 entities) — 2026-11-08

Written at batch close (the F8 lesson applied — not reconstructed later).
Contract: full tier A (12–18 claims, ≥4 sources/≥3 families) · window
2024-11-05..2026-11-08 · snapshot `bkk-d6499618507e7561` · dispatched ≤2
concurrent background subagents per the plan's concurrency rule.

## Volumes

9 bundles · 164 sources (159 body-read) · 156 claims · 298 search-log
entries · assembly normalizations: **zero** (first fully contract-clean
batch — the prompt-template rules 10–12 and the fixed brief generator
eliminated the drift classes that hit every earlier batch).

## The batch's consequential findings (per entity)

- **st.sala-daeng**: rent blend = top of asking ranges (no signed-lease data
  exists corridor-wide); green 10 edge-only — Lumphini touches the catchment
  at its SW corner, park center outside (geometry-verified); Patpong scam
  externality documented but dated (2016 + FCDO), recency flagged.
- **st.siam**: the ~6 ha unnamed green decomposes to the Sra Pathum palace
  precinct + Wat Pathum Wanaram (royal/temple grounds — not public-park
  credit); rent bimodal (19–45k vs 50–120k clusters); crowd 1 event-structural
  (Countdown closures body-read; 2023 Paragon shooting + 2010 Wat Pathum
  killings in the core's record).
- **st.chit-lom**: the 120k override = Magnolias' ceiling for a standard 2-bed
  (ordinary cluster 45–70k); the "big bike protest" lead NOT confirmed —
  documented event history is 2006 vandalism / 2015 bombing (verdicts June
  2026) / 2010 crackdown / 2020-21 protests; transport 10 = skywalk
  engineering vs BMA's own sidewalk critique.
- **st.hua-lamphong**: pier confusion RESOLVED (Saen Saep has no stop here;
  the canal link is the Phadung Krung Kasem electric boat at MRT Exit 2);
  afterlife = 62 ordinary services + events, museum/park plans unverified;
  rent old-stock (~18.9k 1BR) below the app's 28.5k.
- **st.saphan-taksin**: NEW top risk — S6 is single-platform/single-track in
  the bridge median; double-track conversion (ordered 2017, ~1B THB/40mo)
  unstarted as of Aug 2026 → a 3-year closure risk on the Silom line's
  bottleneck; green 8 decomposes to unnamed 5.2 ha + pocket parks; Sathorn
  Unique corrected to "on hold, no plans announced" (survived the 2025-03-28
  quake) — "cancelled rebuild" phrasing fixed in the plan/notes.
- **st.victory-monument**: skywalk phase-1 "opened 1 Oct" = reported-not-
  confirmed (director post; contract overrun; recheck 2026-12-31) — this
  sharpened the C-1 recheck note; khet attribution is a genuine straddle
  (Gazette says Ratchathewi; the app's polygon plausibly captures the north
  side); rent blend plausible but old-stock-skewed (278-listing bimodal).
- **st.mo-chit**: the 529-stallholder clock-tower eviction = Chatuchak
  Section 30 (BMA non-renewal, court case) — NOT Or Tor Kor; market in
  structural decline (footfall halved, 1.2bn THB obligation, contracts
  expire 2027); stall counts kept as an explicit conflicting claim; transit
  anchors hardened (BTS–MRT walkway accepted 2026-07-17).
- **st.phra-ram-9**: Jodd Fairs successor is OUTSIDE the catchment (~2 km) —
  app food/nightlife 8 likely predate the demolition; GR9 "opens May 2026"
  traced to Central Khon Kaen (phased reopening from early 2028 per Central's
  own newsroom); rent baseline contradicted (21.9k/37k asking vs app
  14k/29.5k); station code BL20 per Wikipedia.
- **st.phetchaburi**: CODI lead corrected — no "Nimit Lang Ruea"; the real
  story is the ChamF Rim Bueng Makkasan Baan Mankong scheme (644 households,
  30-yr SRT lease, 169-unit phase 1); nightlife 9 has no local basis (guides
  call the corridor shopping-first); the 497-rai SRT estate carve-up (140-rai
  CP TOD concession ~฿50bn/50yr) + Orange Line tunneling + Pratunam overpass
  demolition (due 2026-03) define the area; rent refs are corridor blends.

## Gates at close

`validate.py` ALL OK ×9 (schema + semantic) · `audit.py` zero P1 (23 P2:
snippet-corroboration flags + advisory classes) · G20 injection sweep clean ·
G17 personal-data scan clean (0/0) · geometry spot-checks run (Lumphini
edge-only confirmed; Mo Chit 2 outside; ICONSIAM in-khet) · kit tests 33
green · one mid-batch strip applied to st.chit-lom (17 blocks; logged in
`../2026-11-08-batch5-strip-log.jsonl`).

## Status & what carries forward

All nine bundles sit at `ready_for_review` with `reviewer: null` — **agent
research only; the A-1 human gate covers batch 5 like every earlier batch.**
Three leads were contradicted by evidence (bike protest, "cancelled" tower,
CODI name) — recorded as findings, not smoothed. Open issues carried: park
polygon re-derivations (B-3/B-4 family), the S6 closure risk (pipeline ticket
candidate), Orange Line/GR9 rechecks in the C-waves.
