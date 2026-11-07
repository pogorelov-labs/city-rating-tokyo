# Pilot batch review findings — 2026-11-05-pilot-zcode-main

Researcher self-report, **ready_for_review, not independently approved**. An
independent reviewer must still verify identity/geography, source
quality/recency, claim support, contradictions and copy. Translation and
image-rights approvals are separate gates. No live application data, scoring,
filters, geometry, translations or application code were changed.

## 1. What was produced

| Entity | Kind | Sources (families) | Claims | Conflicting Qs | Brief |
| --- | --- | --- | --- | --- | --- |
| st.asok | station_area | 10 (8) | 19 | — | briefs/st.asok.md |
| st.chong-nonsi | station_area | 22 (14) | 18 | — | briefs/st.chong-nonsi.md |
| samphanthawong | district | 17 (11) | 18 | — | briefs/samphanthawong.md |
| bang-rak | district | 22 (17) | 18 | Q05 | briefs/bang-rak.md |
| st.thong-lo | station_area | 17 (9) | 19 | Q11 | briefs/st.thong-lo.md |
| st.ari | station_area | 10 (6) | 20 | — | briefs/st.ari.md |

96 distinct canonical URLs; 2 URLs shared across bundles
(Wikipedia Chong Nonsi Canal Park; Wikipedia Benjakitti Park) resolve to
identical source IDs, so cross-bundle deduplication works as designed.
Claim provenance: 55 corroborated (≥2 publisher families), 20 proposed
(single-source), 9 conflicted. All 12 Q01–Q12 answered per entity, with
`bang-rak` Q05 (Silom Walking Street schedule) and `st.thong-lo` Q11 (Soi 38
night market status) marked **conflicting**.

## 2. Highest-value findings and score-relevant disagreements

1. **Green ratings rest on geometry that "leafy" copy hides.** The Asok
   catchment only touches Benjakitti Park's northeast tip (~460 m); the main
   entrances and most of the 72 ha park lie beyond the radius, and
   Benchasiri (~958 m) is outside. Ari has **no verifiable public park inside
   its 800 m** — every named park (Phaya Thai Palace ~1.80 km, Santiphap
   ~1.87 km, Rot Fai ~3.7 km) is outside — yet the app shows green 9 and
   guides sell "leafy". Thong Lo's green 2 (0.1 ha) is the honest opposite.
   The app's `park_ha` figure for Ari (5.1 ha) could not be matched to any
   named public space (Overpass blocked). Reviewer action: reconcile Ari's
   green input with the map layer before any guide copy is approved.
2. **Chong Nonsi's #1 rank is real but conditional.** Independent accounts
   support transit stacking, food density and landmark proximity — but five
   sources describe a weekday-heavy rhythm with "ghost town" weekends. The
   2-bed rent median (72,000 THB) is composition-skewed (published typical
   2-bed size 93.3 m², above the 60–70 m² reference band). *(Corrected in the
   2026-11-07 quality review — see review/REVIEW-2026-11-07.md F1: Sala Daeng
   BTS ~730 m and Patpong ~657 m lie within a bare 800 m of the stop but
   OUTSIDE the app's nearest-stop catchment, which the separately rated
   st.sala-daeng takes; the nightlife 10 rests on the unit's own venue
   density, not Patpong membership.)*
3. **"Chinatown" is measurably wider than Samphanthawong khet.** Soi Nana's
   bar strip (Pom Prap), Khlong Thom and River City (Bang Rak) are outside;
   MRT Wat Mangkon station straddles the boundary. The #1 district ranking
   also masks residential precarity: Charoen Chai eviction pressure
   documented to 2016, 26 of ~7,000 shophouses heritage-listed, and a live
   May 2026 citywide vendor crackdown threatens the street-food economy
   behind food 10.
4. **Walkability is the evidenced weak link on two high-scoring units.**
   BMA's 2025 Asok Montri footpath rebuild (30-year-old collapsing tiles)
   and the 26.3M THB Soi Thong Lo sidewalk rebuild (contracted 2025-07-04,
   0% physical progress at last public report 2025-09-23) are the kind of
   dated, specific facts a reviewer can check. Note: a widely circulated
   "Thonglor sidewalk crackdown" release is actually about Sukhumvit Soi 23
   (outside the catchment) — good example of corridor-vs-catchment error.
5. **Rent is asking-price everywhere.** Every independent rent observation
   found (DooAsset station tables, HipFlat feeds, portal listings) is an
   asking-price aggregate; no signed-lease series exists for any pilot unit.
   The app's editorial district blends sit inside independent ranges
   (e.g., Bang Rak 1-bed ~28–29k vs app 26,000; HipFlat in-khet Chinatown
   sample 12,000–17,000 vs app 14,000) but all samples are small and
   condos-only. No rent claim in the bundles is a median observation of
   signed contracts.
6. **Fresh, dated change items are now available for reviewers:** Hua
   Lamphong lost long-distance rail 2023-01-19 (Samphanthawong); canal park
   first 200 m opened 2021-12-25, phases stalled (Chong Nonsi); BTS evening
   rush failure 2026-09-25 packed Asok platform-to-gates (single event, not
   a recurring risk label); One Bangkok operating since 2024-10-25 (outside
   Bang Rak khet, across Rama IV).

## 3. Unresolved claims and access gaps

- **Overpass/OSM ground truth unavailable** (406/TLS resets/timeouts) — POI
  identities and the Ari park mismatch could not be machine-verified.
- **Resident-voice evidence is thinner than ideal**: Reddit r/Bangkok,
  TripAdvisor and ExpatForum threads blocked (403/paywall redirect; not
  followed per method rules). Several entities rely on editorial guides +
  one resident quote.
- **Soi 38 night market status conflicting** (closed-street vs ~20-stall
  continuation claimed by a 2026-updated page) — recheck recommended.
- **Silom Walking Street**: no authoritative 2024–2026 schedule; frequency
  sources conflict (3rd Sunday vs alternate Sundays); copy deliberately
  refuses to promise it.
- **Canal park hours and the 4.2 ha within-800 m figure (Chong Nonsi)**:
  unverified; EN/TH Wikipedia disagree on phase numbering.
- **Charoen Chai status after 2016**, Yaowarat full-road walking-street
  schedule, reported 2026 CNY cancellation, Blue Line loop completion date,
  district-level safety data: snippet-level only, quarantined as open
  issues — no bundle claim depends on them.
- 3 thong-lo sources are exa-highlight corroboration only (`body_read:
  false`); no claim relies solely on them (verified programmatically).

## 4. Validation commands and actual results

From the batch directory (`research/bangkok/editorial/batches/2026-11-05-pilot-zcode-main`):

- `python3 -I tools/assemble.py` — assembled 6 bundles from raw agent JSON;
  normalizations applied (scope/kind field fixes, QA conflict statuses).
- `python3 -I tools/validate.py` — **6/6 PASS** against
  `entity-research.schema.json` (structure, enums, patterns, required fields,
  URI/date-time formats, uniqueness) plus semantic checks (unique claim ids,
  evidence→source resolution, no dangling claim refs in QA/editorial).
- Copy gate: banned-phrase scan ("vibrant", "hidden gem", "something for
  everyone") — clean; three walking-time conversions in editorial copy were
  found and rewritten to distance phrasing (asok preview, thong-lo
  conditional_fit[0], bang-rak day_night[1]).
- Digest gate: all 9 required data files matched sender `source-manifest.json`
  SHA-256 in the receiver clean checkout (HEAD 894324a; data identical to
  sender HEAD 72cfa5d0).
- `git status` after the batch shows only the new batch directory (plus a
  pre-existing untracked `mcp/.gitignore`); no tracked file modified.

## 5. Proposed next research order (separate axes, not a universal score)

**Axis 1 — evidence of public interest (independent coverage breadth):**
the pilot's strongest independently covered entities were Thong Lo, Ari,
Asok and Samphanthawong (multiple families each). Candidates lacking pilot
measurement: `st.nana`, `pathum-wan`, `phra-nakhon`, `st.wat-mangkon`.
Coverage breadth must be measured with a fixed search window, publisher-family
dedup and logged queries — not SEO hit totals.

**Axis 2 — score/rank coverage of the model's own top tier:** after the two
#1s, the untested top-5 are `st.charoen-nakhon` (7.96), `st.ratchathewi`
(7.92), `st.nana` (7.86), `st.ha-yaek-lat-phrao` (7.82), `st.phloen-chit`
(7.78); districts `pom-prap-sattru-phai` (8.16, the Chinatown-adjacent khet
the pilot repeatedly brushed against) and `phaya-thai` (8.0, Ari's district).

**Axis 3 — research value:** (a) popular-but-contested: `st.nana` (nightlife
reputation vs residential blocks), `patpong`-adjacent corridors inside
Bang Rak; (b) high-score/low-coverage: `st.charoen-nakhon`, `st.sam-yot`,
`st.sena-ruam`; (c) control/disagreement set: `st.wat-mangkon` (straddles
Samphanthawong boundary — direct test of corridor-vs-catchment), and one
deliberately mid-table area (e.g., `st.ratchaprarop` 7.68) as a calibration
control.

Proposed next batch (10–12 entities, same contract): st.nana,
st.charoen-nakhon, st.ratchathewi, pom-prap-sattru-phai, phaya-thai,
st.wat-mangkon, st.phloen-chit, st.sam-yot, pathum-wan, phra-nakhon,
st.ha-yaek-lat-phrao + 1 control (st.ratchaprarop).

For later product browsing, keep separate: (a) score under current weights;
(b) documented editorial mention breadth with its date window; (c) evidenced
themes (quiet evenings, everyday services). Group district vs station-area
rankings separately; research priority ≠ public sorting.

## 6. Small integration proposal (separate reviewed change)

1. Keep research corpus out of the map bundle. Add a small localized preview
   index (entity key → short approved preview string per locale) loaded with
   the map; fetch full guide narrative, claim/evidence disclosure and gallery
   only on demand (per-entity JSON chunk).
2. Adapter contract: `bundles → {short copy (EN/JA/RU after separate
   translation gate), structured guide sections, sources/limitations
   disclosure}`. Entity keys are the existing `st.*` / district slugs; never
   map research into `districts.json`/`stations.json`/rent references.
3. Treat all article-derived text as untrusted plain text: render as text,
   never inject HTML; link out to canonical sources.
4. Existing app checks apply (lint, tests, TypeScript, build, e2e) — none of
   them were run here because this batch changed no application code.

## 7. Later image-search plan (plan only — no assets fetched)

- Phase-one decision recorded in every bundle: `images: []`.
- Candidate hunt order per entity: station entrance → neighborhood street →
  usable park/green → landmark → night context. Prefer Wikimedia Commons
  (license page as proof URL), then open-licensed agency photos; tourism
  promo photos are candidates only with explicit license proof.
- Record per candidate: source page, actual image URL, creator, exact
  license/version, proof URL, commercial/derivative rights, required credit,
  capture date, geographic match (inside/partial/outside_context), intended
  role, crop/focal notes, caption claim IDs, alt draft. Unknown rights block
  publication (`rights_status: unknown`).
- Known leads already in app data (Wikimedia thumbs on stations.json /
  district records) are leads, not blanket approval: Asok/Thong Lo/Ari/Chong
  Nonsi thumbs are station photos (good `station_entrance` role candidates
  but must be re-verified for current license version); district records
  carry their own images. Global station-thumbnails/station-images-all.json
  are Tokyo registries — not Bangkok sources.
- Card crop: current code consumes 600×220; measure real responsive slots
  before producing final crops; judge readability at card size; keep first
  map load preview-only (one small image per card).

## 8. Files changed by this batch (all inside the batch directory)

- `manifest.json`, `search-log.jsonl` (170 entries)
- `profiles/{st.asok,st.chong-nonsi,samphanthawong,bang-rak,st.thong-lo,st.ari}.json`
- `briefs/{…same six…}.md`
- `review/findings.md` (this file), `review/REVIEW-2026-11-07.md` (quality
  review with 6 corrections/fixes documented)
- `raw/{…six…}.json` (researcher output from subagents)
- `tools/{assemble.py,validate.py,briefs_findings.py,audit.py,review_fixes.py}`
  (batch tooling)

Live application data, scoring, filters, geometry, translations, image
registries and application code: **untouched** (git-verified).
