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
