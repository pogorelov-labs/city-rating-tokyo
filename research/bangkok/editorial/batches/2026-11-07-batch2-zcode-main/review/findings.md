# Batch-2 review findings — 2026-11-07-batch2-zcode-main

Researcher self-report, **ready_for_review, not independently approved**. Six
entity bundles + axis-1 coverage scan, produced under the same contract as the
reviewed pilot batch (`2026-11-05-pilot-zcode-main`). No live application data
changed.

## 1. What was produced

| Entity | Kind | Score (rank) | Coverage band (axis 1) | Sources / claims | Conflicting Qs |
| --- | --- | --- | --- | --- | --- |
| st.charoen-nakhon | station_area | 7.96 (#2/133) | thin | 13 / 17 | Q09 |
| st.ratchathewi | station_area | 7.92 (#3/133) | some | 18 / 17 | Q09 |
| st.nana | station_area | 7.86 (#4/133) | thin | 18 / 18 | — |
| st.wat-mangkon | station_area | 7.70 (#10/133) | thin | 27 / 19 | — |
| pom-prap-sattru-phai | district | 8.16 (#3/50) | **broad** | 19 / 17 | — |
| phaya-thai | district | 8.00 (#4/50) | **broad** | 16 / 16 | — |

Selection memo: `selection.md` (three separate axes). Coverage census:
`raw/coverage-scan.json` (41 logged queries, window 2024-11-05→2026-11-07,
publisher-family dedup). Search log: `search-log.jsonl` (297 entries including
the scan and all failures). Deferred with reasons: st.phloen-chit (dated
in-window coverage all commercial), st.sam-yot (thin; queue as old-town themed
group), st.ha-yaek-lat-phrao + st.ratchaprarop (coverage unknown — scan first).

Claim provenance after assembly: 66 corroborated (≥2 publisher families), 36
proposed, 11 conflicted.

## 2. Coordinator verification pass (like the pilot's REVIEW-2026-11-07)

The orchestrator independently re-verified boundary claims before assembly:
11 point-in-polygon/haversine tests against the app's own polygons
(`station-geometry.json`, `geometry.json`) plus 3 targeted probes, using
Wikipedia/OSM coordinates. Corrections applied to the raw bundles before
assembly (`tools/raw_fixes.py`, assertion-guarded):

- **st.nana — Bumrungrad straddles the boundary** (frontage ~415–450 m inside
  the polygon; geotagged center ~710 m outside, clipped toward
  st.phloen-chit). Agent's "inside, 350–500 m" was half-right; claim and
  scope notes corrected. **Lumphini is ~1.6–1.7 km away, not the agent's
  0.7–0.8 km "boundary case"**; Benchasiri ~1.7 km (agent 1.1–1.3 km).
- **st.wat-mangkon — Golden Mount is ~0.91 km** (agent: 1.3 km). Soi Nana
  lane straddling CONFIRMED by polygon probe (NW end 414–447 m inside,
  midpoint outside).
- **phaya-thai — Victory Monument conflict documented**: the app's own khet
  polygon includes the roundabout while sources place it in Ratchathewi;
  claim marked conflicted.
- **st.charoen-nakhon — editorial "2-5 minute walk" rewritten** to
  bridge-entry phrasing (no radius→time conversions).
- **Enum normalization at assembly**: 40 polarity values (`positive`→
  `strength`, `negative`→`tradeoff`), ~60 source-type values (e.g.
  `encyclopedia`→`other`, `property_portal_data`→`commercial_property`), QA
  field variants (`q`/`claims`/`claim_refs`, `answer`, status `partial`)
  normalized, inline claim references in plain-string editorial items
  extracted into `claim_ids`.

Post-fix gates: `tools/validate.py` **6/6 PASS** (schema + semantic refs);
`tools/audit.py` 15 findings, all P2 = snippet-only sources used as
*corroboration* with mitigation strings on every such source record and no
claim relying solely on one (verified programmatically).

## 3. Highest-value findings

1. **The green-score question is now systemic, not per-entity noise.** Batch
   2 adds four cases where the green rating cannot be tied to in-unit public
   parkland: st.nana (green 10 with 1.4 ha unidentified; Benchasiri 1.7 km,
   Lumphini 1.6–1.7 km), st.ratchathewi (green 8, no named park inside),
   pom-prap-sattru-phai (green 9 with 0.7 ha; basis = Golden Mount compound +
   Khlong Ong Ang promenade, inference), phaya-thai (green 9; 14.8 ha likely
   Army/state land with controlled access, inference). Together with the
   pilot's st.ari and st.thong-lo findings, this is a **data-pipeline
   question** (how `park_ha` is computed and what `green` measures) for the
   integration boundary — not something per-entity research can settle.
2. **st.charoen-nakhon's transport 10 rests on piers + buses, not the Gold
   Line**: the line has 3 stations, never crosses the river (the app's own
   "BTS Gold" framing is fine but the pilot-era assumption of a river
   connection is not), ridership 8,390/day (Q4 2025) vs ~42,000 forecast;
   12+ named ferry terminals within 800 m on both banks (several
   private/closed). ICONSIAM verified inside and adjacent (~0.14 km). The
   local-street economy broke in 2021 (Khlong San Plaza closed on SRT lease
   expiry; pier contract lapsed) — what vibe/nightlife 9 mask.
3. **st.ratchathewi's safety 5 has no visible unit-specific basis** —
   documented negatives are traffic/flyover (closed 15–16 Jan 2025,
   reconstruction due Apr 2028) and adjacent-belt petty theft, not catchment
   crime. Transport 10 mechanism verified (bus stops 19 m/52 m from exits,
   canal-boat pier 305 m, ARL one stop north, planned MRT Orange Line
   interchange ~2030). Rent 21,500/38,000 sits inside all three independent
   asking-rent ranges.
4. **Boundary controls resolved cleanly**: st.wat-mangkon's catchment takes
   Wat Mangkon Kamalawat (~54 m, Pom Prap side) and the Maitrichit end of
   Chinatown Soi Nana, while Wat Traimit/Odean Circle fall to
   st.hua-lamphong and Khlong Ong Ang/Rommaninat to st.sam-yot. Note for
   reviewers: the pilot's Samphanthawong note ("temple attributed just
   outside the khet") is about KHET attribution and remains consistent —
   the temple is in Pom Prap AND inside st.wat-mangkon's catchment; the
   batch-2 agent's "refutes the pilot" phrasing overstates it.
5. **App-data observations surfaced for the integration boundary** (research
   does not edit them): wat-mangkon's record `district` field says
   "samphanthawong" while its own district split gives Pom Prap 51.4%;
   pom-prap's alias list includes Woeng Nakhon Kasem, which sources place in
   Samphanthawong; phaya-thai's description text says Victory Monument is
   "just past the southern edge" while the khet polygon includes it.
6. **Rent checks survive everywhere but stay asking-price only**: pom-prap's
   2-bed 24,000 editorial sits BELOW all 14 observed HipFlat 2-bed asks
   (25,000–32,000) — flagged for reviewers; nana's override is at the
   lower-middle of a luxury-skewed portal range; phaya-thai rents are
   softening (−1.9% YoY).

## 4. Unresolved claims and access gaps

- Overpass/OSM blocked all batch: mapped park hectares unidentified for
  nana (1.4 ha), ratchathewi (1.0 ha), wat-mangkon (0.5 ha),
  charoen-nakhon (0.8 ha); phaya-thai's 14.8 ha not decomposable.
- Conflicting and left as such: Princess Mother Memorial Park location
  (charoen-nakhon), ICS opening month + Gold Line fare, Nana Plaza bar count
  and closing hour, Wat Ratchanatdaram khet attribution, Khlong Ong Ang
  current promenade schedule (2021-era documentation only).
- Open operational questions logged with recheck flags: Khlong Thom Center
  post-fire status (28–29 Aug 2026 fire, Thai PBS body-read), market
  operating state, canal-park phases.
- Resident-voice still thin (Reddit/TripAdvisor blocked); snippet-only
  sources are flagged and never sole evidence.

## 5. Proposed batch 3 (axes kept separate)

- Score/rank: st.phloen-chit (7.78 #6), st.ha-yaek-lat-phrao (7.82 #5,
  coverage unknown — scan first), st.ratchaprarop (7.68 #12, calibration
  control).
- Coverage: st.sam-yot + old-town themed group (sanam-chai, itsaraphap,
  phra-nakhon) as one themed batch after a coverage scan.
- Research value: a **green-basis audit** across the dataset (pipeline
  question), and boundary-sensitive pairs the map will always show together
  (e.g., wat-mangkon/hua-lamphong, nana/phloen-chit).

## 6. Files changed by batch 2 (all inside the batch directory)

- `selection.md`, `manifest.json`, `search-log.jsonl` (297 entries)
- `raw/coverage-scan.json`, `raw/{six entities}.json` (post-fix)
- `profiles/{six entities}.json` — validated
- `briefs/{six entities}.md`
- `review/findings.md` (this file)
- `tools/{assemble.py,validate.py,audit.py,briefs_findings.py,raw_fixes.py}`

Live application data, scoring, filters, geometry, translations, image
registries and application code: **untouched** (git-verified).
