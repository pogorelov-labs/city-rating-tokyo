# Editorial research batches — pipeline follow-ups (CRTKY-130 subtree)

**2026-11-07.** Ticket-ready drafts from two editorial research batches (12
place bundles with claim-level provenance,
[`editorial/batches/`](../editorial/batches/); contract
[`editorial/2026-11-05-handoff/HANDOFF.md`](../editorial/2026-11-05-handoff/HANDOFF.md)).
These are **data-layer items** — they change `build.py` inputs/records and go
through the repo's own build/replay gates, not through editorial research.

## 1. Green-rating basis audit (candidate ticket — pipeline question)

**Observation.** Six of twelve researched units cannot tie their green rating
to in-unit public parkland: `st.ari` (green 9, no named park inside its 800 m
polygon — every named park 1.8–3.7 km out), `st.nana` (green 10 with only
1.4 ha mapped, identity unresolved; Benchasiri 1.7 km, Lumphini 1.6–1.7 km),
`st.ratchathewi` (green 8, no named park inside), `pom-prap-sattru-phai`
(green 9, 0.7 ha — usable space is the Golden Mount compound + Khlong Ong Ang
promenade), `phaya-thai` (green 9, 14.8 ha likely Army/state land with
controlled access), `st.thong-lo` (green 2 — the honest low case).

**Explanation (documented design, not a bug).** Green = park hectares within
**1 km of each grid point** (points count 800–1,200 m) — see
[`00-overview.md`](../00-overview.md) Sources table. The unit polygon is
Voronoi ∩ 800 m. The mismatch is systematic.

**Proposed action.** Decide deliberately: (a) keep the 1 km basis and document
it in the UI honesty notes; or (b) add a catchment-interior green sub-signal
("park inside the unit" boolean/ha) so cards can distinguish "green area
nearby" from "park access at home". Either way, the state-land contribution
(Army compound, Channel 5) should be checked for `public access = false`
exclusion. **No score edit is proposed by research**; batches recorded the
mechanisms as claims instead.

**Evidence:** pilot `st.ari`/`st.thong-lo` bundles; batch-2
`st.nana`/`st.ratchathewi`/`pom-prap-sattru-phai`/`phaya-thai` bundles
(green claims + question_answers Q09); coordinator PIP checks in
`batch2/review/findings.md`.

## 2. Pom-prap 2-bed rent floor (CRTKY-141 adjacent)

**Observation.** The editorial district rent for pom-prap-sattru-phai is
1-bed 12,000 / 2-bed 24,000 THB (as-of 2026-09, confidence `editorial`).
Batch-2 found HipFlat's in-khet asking sample (n=14, condos): 1-bed
12,000–25,000 (app = observed floor ✓), 2-bed **25,000–32,000 — the app value
sits below every observed asking price**.

**Proposed action.** Re-run the CRTKY-141 calibration for pom-prap's 2-bed
value against current asking aggregates (keeping the fixed-size reference
band 60–70 m² in mind — the HipFlat sample makes no size filter, so treat as
a sanity check, not a median). Update via the same researcher-estimate
process that produced `editorial.json`; note the sample limits.

**Evidence:** batch-2 `pom-prap-sattru-phai` rent claims (HipFlat locator in
bundle sources); `app/src/data/bangkok/districts.json` rent record.

## 3. App-record inconsistencies (for the data layer's own checks)

Three small record-level conflicts surfaced during boundary verification. Fix
via the normal build path, not by hand-editing bundles:

1. **wat-mangkon `district` field** says `samphanthawong` while the record's
   own `districts` split gives pom-prap-sattru-phai 51.4%. Pick one rule
   (majority share) or carry both explicitly.
2. **phaya-thai khet polygon vs description text**: the polygon includes the
   Victory Monument roundabout; the record description says it sits "just
   past the southern edge". Sources attribute the monument to Ratchathewi.
   Decide the boundary convention (the 150 m border rule may explain it) and
   align description + polygon.
3. **pom-prap alias list** includes Woeng Nakhon Kasem, which sources place
   in Samphanthawong. Drop or mark cross-khet.

**Evidence:** batch-2 `review/findings.md` §3.5; coordinator PIP checks;
bundle claims `wat-mangkon-c03`, `phaya-thai-c05`, `pom-prap` boundary claims.

## 4. Evidence already routed to open tickets

See [`backlog.md`](../backlog.md) §"Evidence from editorial research batches"
— CRTKY-153 (red-light geography), CRTKY-147 (dated BMA walkability items),
CRTKY-141 (asking-vs-signed universality), CRTKY-139 (flood-catchment
protocol), CRTKY-152 (coverage-breadth instrument).


---

## 2026-11-08 update — pipeline items from batches 3–4 (full tier A + light tier B)

The tiered program completed all 183 entities (`editorial/2026-11-08-tier-plan.md`:
22 full, 24 light, 137 data-only placeholders). New data-layer items, in priority order:

1. **Ghost station (HIGH):** `st.sena-ruam` is a planned-but-never-built BTS infill
   (N6, between Ari and Saphan Khwai) modeled in `rail.json` as an operating
   `bts_sukhumvit` station — and it ranks #9/133 by score. Sources: Thai Wikipedia
   disambiguation, BK Magazine 2018 "grayed-out station", Prachachat 2026-11-05
   council hearing (BTS "will coordinate" before the 2029 concession handover).
   **Recommended: audit all 139 stations for operating status.**
2. **App anchor vs OSM node offsets:** batch-4 measured 270–770 m offsets on eight
   units (mo-chit +300, saphan-khwai +270, kamphaeng-phet +770, victory-monument +550,
   phetchaburi 120–310, phaya-thai ~340, saint-louis ≥720 — the real Saint Louis infill
   station is at 13.72082/100.52669), while sala-daeng and all four batch-4 river/east
   units matched to five decimals. Likely a unit-centroid convention — needs a documented
   rule; also Wikipedia/OSM carry displaced coords for BTS Chit Lom and Victory Monument.
3. **Green-basis confirmations (batch 3–4 decompositions):** pathum-wan 102.7 ha =
   Lumphini 57.6 + Centenary 4.5 + One Bangkok ~8 + **Royal Bangkok Sports Club 36.3 ha
   members-only** + royal Sa Pathum 7.9 → ~60–65% publicly usable; phra-nakhon ~19–20 ha
   public vs 38.5 app (balance = temple/palace grounds); chatuchak 149.2 OSM vs 167.1;
   ratchathewi 17.8 = 8.81 named public + institutional gardens; din-daeng OSM ~3 ha vs
   app 15.5; **dusit 118.7 ha largely NON-public** (zoo fenced since 2018, Sanam Suea Pa
   royal). Feeds the green-basis audit candidate from the 2026-11-07 note.
4. **Polygon coarseness:** 🔄 **CORRECTED 2026-11-08 (independent review F5 + `--khet` PIP
   probes):** the earlier khlong-san claim here conflated the **station cell** with the
   **khet** — the app's khlong-san khet polygon (`geometry.json`, 50 vertices) **CONTAINS**
   ICONSIAM and G2 Charoen Nakhon and excludes River City; the 10-vertex object the agent
   measured is `station-geometry.json["khlong-san"]` (the documented B-8 key-shadowing trap).
   Remaining genuine items: the sathon boundary is metres-sensitive (app anchors for
   Surasak/Saint Louis sit on the line — "all three BTS nodes outside" holds for the app
   anchors and should be phrased as boundary-sensitive); thon-buri does NOT contain BTS
   Wongwian Yai (khlong-san, per station infobox + PIP).
5. **Rent semantics:** phloen-chit station record blends 33,500/74,000 while the pathum-wan
   district record says 38,000/85,000 — two different "Pathum Wan blends" in the app;
   chit-lom's 120,000/— 2-bed override (highest in the app) is a top-decile luxury asking
   figure, not a median (FazWaz Pathum Wan 2-bed avg 99,600 n=1,114; corridor median ~40k).
6. **Fact corrections for the data layer:** ratchathewi district "1 Michelin star"
   undercounts (two one-star venues verify in-khet: Signature at VIE, Wana Yook);
   ratchathewi "0 piers" vs Pratunam pier nodes PIP-in-khet; chit-lom "5 piers" = 4
   duplicate OSM nodes + 1 distinct; hua-lamphong "2 piers" = canal (Khlong Phadung
   Krung Kasem), not river; Four Seasons Bangkok was a 2015 rebrand, not 2024.
7. **Counter-evidence events logged with dates** (for any future risk labeling):
   Or Tor Kor shooting 2025-07-28 (5 dead); din-daeng = noisiest PCD monitoring station
   (71.6–81.6 dB(A), 182/182 days over) + Rocket Media Lab rank 50/50; BTS Asok evening-
   rush failure 2025-09-25; 529-stallholder clock-tower eviction 2025; Jodd Fairs Rama 9
   demolished 2025-01; Khlong San Plaza closed 2021.
8. **Kit TODO:** `check_geometry.py` prefers station-geometry keys over district keys
   (`chatuchak` exists in both) — needs an explicit `--khet` flag; found by the batch-3
   chatuchak agent, worked around by direct OSM queries.
