# Phaya Thai (st.phaya-thai) — research brief

**Derived view** of `profiles/st.phaya-thai.json` (authoritative bundle), batch `zcode-main (ZCode orchestrator + 6 light-pass subagents), 2026-11-07` era output. Status: **ready_for_review** — not independently approved. Drafted in English only; no translations manufactured.

- **Unit:** Station area (nearest-stop catchment, Voronoi ∩ 800 m disc). Aliases: —
- **Scope:** Nearest-stop catchment (Voronoi ∩ 800 m) around phaya-thai [bts_sukhumvit/arl]; districts: ratchathewi. Boundary claims are decided by the app polygons (coordinator checks apply).
- **App score context:** model 7.46 (display rounded), cohort rank 20 of 133, snapshot `bkk-d6499618507e7561`. Public popularity: **unmeasured** — No citywide popularity measure has been collected. Tier B selection used within-cohort rank; coverage recorded opportunistically per bundle.
- **Selection rationale:** Tier B (light pass): station-area rank 20/133, score 7.46.

## Card preview (proposed)
> Bangkok's BTS-ARL hinge: the Sukhumvit Line meets the airport rail ~120 m platform-to-platform in Ratchathewi district (yes, Phaya Thai station is not in Phaya Thai district), with Suan Pakkad Palace 350 m east and a 1907 SRT halt being rebuilt around a high-speed future.

## Guide lead (proposed)
Phaya Thai is the city's airport hinge: the ARL City Line terminates here against the BTS Sukhumvit Line (platforms ~121 m apart, skywalk since 2010), one stop from Siam and ~half an hour from Suvarnabhumi. The unit's identity is transport first - the station paradoxically sits in Ratchathewi district - with a practical street life of hospital and office traffic, plentiful food, Suan Pakkad Palace Museum ~350-400 m east inside the unit, and the 1909 Phaya Thai Palace ~1.3 km north, outside the catchment. Rents (25,000/43,500) match the catchment's 1-BR/2-BR medians well. What the score cannot show: no verifiable safety data behind the 5, an unidentified 1.1 ha park polygon, and a railway corridor being progressively cleared for the three-airport high-speed line.

## Strengths
- The only BTS-ARL interchange in the city core: one-stop Siam access plus a direct airport line, with 800 m catchment rents matching the app's stated figures. *[`phaya-thai-st-c03`, `phaya-thai-st-c08`]*
- A real heritage-green anchor inside the unit: Suan Pakkad Palace Museum (~350-400 m) with its five traditional houses and 450-year-old Lacquer Pavilion. *[`phaya-thai-st-c04`]*

## Trade-offs
- Safety 5 has no evidence base either way in this pass - it stays an unanchored dataset value rather than a documented condition. *[`phaya-thai-st-c07`]*
- The green story is thinner than the 8 suggests: no named public park inside the catchment was found, and the 1.1 ha polygon is unmatched (Suan Pakkad's grounds are a ticketed museum). *[`phaya-thai-st-c09`, `phaya-thai-st-c04`]*

## Day / night
- The interchange dominates mornings and evenings with commuter and airport flows; midday belongs to hospital/office errands and food stalls; evenings and weekends are low-key. *[`phaya-thai-st-c06`, `phaya-thai-st-c10`]*

## Within-area variation
- The station-and-skywalk block is the loudest node; the Si Ayutthaya/Suan Pakkad side east is calmer, and the SRT/rail-corridor edge west carries the clearance works. *[`phaya-thai-st-c04`, `phaya-thai-st-c11`]*

## Conditional fit
- Strong fit: frequent flyers and BTS commuters priced out of Siam/Ratchathewi proper - the rent medians here are the interchange's own. *[`phaya-thai-st-c03`, `phaya-thai-st-c08`]*
- Poor fit: households wanting leafy park-side living or destination nightlife; neither exists in this catchment. *[`phaya-thai-st-c09`, `phaya-thai-st-c06`]*

## Explicit unknowns
- rating safety (5): no unit-level statistics found; unanchored in this pass (phaya-thai-st-c07).
- Park identity: the app's 1.1 ha polygon did not match any named OSM park within 900 m of the stations (phaya-thai-st-c09).
- Anchor sits ~340 m north of the BTS node; edge memberships toward Victory Monument need polygon re-check (phaya-thai-st-c02).
- ARL headway (~10 min peak) is snippet-level only; the Wikipedia body documents fares and the 2014 express suspension but not current headways (phaya-thai-st-c03).
- Railway-corridor displacement affects the corridor generally; overlap with this specific Voronoi cell is undetermined (phaya-thai-st-c11).

## Question coverage
- **Q01 — answered**: BTS (1999) + ARL terminus (2010) + SRT Eastern Line halt (1907), ~121 m apart, in Ratchathewi district despite the Phaya Thai name; anchor ~340 m north of the station.
- **Q02 — answered**: Commuter-junction practicality: interchange flows, hospital and office traffic, street food, quiet evenings.
- **Q03 — answered**: Transport 10 = unique BTS-ARL interchange + airport line; DE 9 = dense everyday services; rent 5 = mid-band medians matching the app figures.
- **Q04 — answered**: The safety-5 'test' found no evidence either way; the only documented criticism is of the SRT halt's physical condition.
- **Q05 — answered**: Peak-hour commuter waves; calmer weekends; low-key evenings.
- **Q06 — answered**: Skywalk-linked interchange ~121 m platform-to-platform; bus hub one stop north; no sidewalk data found.
- **Q07 — answered**: Daily-life anchors: street food, Victory Monument institutions one stop north, hospitals and offices along the corridor; Suan Pakkad museum ~364 m east.
- **Q08 — answered**: App figures (25,000/43,500) match the 800 m 1-BR/2-BR medians (23,450/41,500) closely - one of the best-verified rent sets in this batch, though via flagged portal sources.
- **Q09 — answered**: 1.1 ha park unidentified in OSM; Suan Pakkad's gardens are museum grounds; nearest public park ~1.45 km.
- **Q10 — answered**: Strong fit: frequent flyers, BTS commuters, value-seekers; poor fit: those wanting leafy quiet or destination nightlife.
- **Q11 — answered**: Rail-land clearance and the 2024 Bueng Makkasan relocation phase reshape the railway corridor; The Extro Phayathai-Rangnam (2025) adds stock.
- **Q12 — answered**: Outside the score: no safety data, unidentified park polygon, anchor offset; the name paradox itself (Ratchathewi district) is worth stating on the card.

## Evidence base

| Source | Publisher (family) | Type | Published | Read |
| --- | --- | --- | --- | --- |
| [Queries: Phaya Thai stations (wide radius + name), Suan Pakkad, Phaya Thai Palace, subd…](https://overpass-api.de/api/interpreter) | OpenStreetMap via Overpass API (OpenStreetMap via Overpass API) | other | — | yes |
| [Phaya Thai station](https://en.wikipedia.org/wiki/Phaya_Thai_station) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Suan Pakkad Palace](https://en.wikipedia.org/wiki/Suan_Pakkad_Palace) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Phaya Thai Palace](https://en.wikipedia.org/wiki/Phaya_Thai_Palace) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Airport Rail Link (Bangkok)](https://en.wikipedia.org/wiki/Airport_Rail_Link_(Bangkok)) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [BTS Phaya Thai / ARL Phaya Thai: Area Guide](https://dooasset.com/en/area/bts-phaya-thai/) | DooAsset (real_estate_portal) | other | — | partial |
| [Phaya Thai Bangkok: Area Guide & Rent 2026](https://www.bkkoracle.com/area/phaya-thai) | BKK Oracle (real_estate_content) | editorial_guide | — | partial |
| [Condos for Rent in Phaya Thai](https://propertyscout.co.th/en/bangkok/phaya-thai/rentals/condo/) | PropertyScout (real_estate_portal) | other | — | partial |
| ["ชุมชน ชมฟ.ริมบึงมักกะสัน" ความสำเร็จอีกขั้น แก้ไขปัญหาที่อยู่อาศัยคนจนเมือง](https://theactive.thaipbs.or.th/news/urban-housing-20240929) | The Active (Thai PBS) (thai_public_broadcast) | news | 2024-09-29 | yes |

## Claim index

- `phaya-thai-st-c01` **[corroborated·strength·entire_unit]** The unit is a three-way rail knot with a name paradox: BTS Phaya Thai (N2, opened 5 December 1999 with the Sukhumvit Line), ARL Phaya Thai (terminus of the City Line, opened 23 August 2010 'along with a skywalk connecting it to the BTS station'), and an SRT Eastern Line halt dating to 24 January 1907 - all located in Ratchathewi District, not Phaya Thai district. OSM puts the BTS node at 13.75696, 100.53382 and the ARL node at 13.75671, 100.53491 - ~121 m apart. _(scope: station_area — Phaya Thai interchange (Ratchathewi district))_
- `phaya-thai-st-c02` **[proposed·neutral·entire_unit]** Anchor offset: the app's '@13.7600-ish' latitude sits ~340 m north of the OSM BTS node (13.75696). The interchange itself is unaffected, but catchment-edge claims toward Victory Monument (which is ~1.4 km from the BTS node in any case) or northward should be checked against the app polygon. _(scope: station_area — Phaya Thai interchange)_
- `phaya-thai-st-c03` **[corroborated·strength·entire_unit]** Transport 10's mechanism: this is the only BTS-ARL meeting point - the ARL City Line's northern terminus feeding the Sukhumvit Line one stop from Siam. City Line fares are 15-45 THB, the airport express has been suspended since September 2014 (all trains stop at all eight stations), and the line is slated to extend from Phaya Thai toward Krung Thep Aphiwat and Don Mueang while also carrying the future Don Mueang-Suvarnabhumi-U-Tapao high-speed rail. Current headways of roughly 10 minutes peak (12-15 off-peak) are snippet-level only. _(scope: station_area — Phaya Thai interchange)_
- `phaya-thai-st-c04` **[corroborated·strength·inside]** Suan Pakkad Palace Museum is inside the unit: Wikipedia says it is 'located nearby to the east of the station', and OSM places the museum (way 1410385850, open 09:00-16:00) ~364 m east of the BTS node (~307 m by its node). The 1952-opened museum of five traditional Thai houses holds 4,000-year-old Ban Chiang pottery and the 450-year-old Lacquer Pavilion - so the batch-2 '811 m from st.ratchathewi' figure belongs to the district unit, not this station unit. _(scope: venue — Suan Pakkad Palace Museum (Si Ayutthaya Rd))_
- `phaya-thai-st-c05` **[corroborated·neutral·outside]** Phaya Thai Palace is outside the unit: it stands on the banks of Khlong Samsen on Rajavithi Road in Ratchathewi District (built 1909 under Rama V, later the Phramongkutklao Hospital site), and computes to ~1,322 m from the BTS node - verifying the brief's '~1.3 km' and excluding it from the 800 m catchment. _(scope: venue — Phaya Thai Palace (Rajavithi Rd))_
- `phaya-thai-st-c06` **[proposed·neutral·entire_unit]** Everyday character is 'more practical than picturesque' (rental guide): weekday flows of interchange commuters, Ramathibodi-bound staff and patients, and office workers along Phaya Thai and Si Ayutthaya roads; plentiful street food; the boat-noodle stalls around Victory Monument described as a local institution; low-key evenings and weekends when residents head to Siam or Ari. _(scope: district — Phaya Thai / Ratchathewi corridor)_
- `phaya-thai-st-c07` **[proposed·neutral·entire_unit]** Safety 5 could not be tested against evidence: no unit-level crime statistics or location-specific safety reporting surfaced in this pass. The only 'neglect' finding in sources concerns the SRT Eastern Line halt - 'criticised for neglect and poor maintenance by the SRT' as tracks hand over to the high-speed rail project - which is infrastructure condition, not personal safety. _(scope: station_area — Phaya Thai interchange)_
- `phaya-thai-st-c08` **[corroborated·strength·entire_unit]** Affordability vs stated figures (25,000/43,500, station_override 2026-10-10): an 800 m catchment median from a listings portal (data dated 29 Oct 2026) shows 1-BR median 23,450 THB (middle half 20,000-26,500, typical 34.5 sqm) and 2-BR median 41,500; a portal district average gives 1-BR 23,871 and 2-BR 39,160; a guide band puts 1-BRs at 16,000-28,000. Both app figures align with the 800 m medians (25,000 near the 1-BR median; 43,500 at the 2-BR median). _(scope: station_area — Phaya Thai interchange catchment)_
- `phaya-thai-st-c09` **[proposed·neutral·unknown]** The app's 1.1 ha park could not be matched to a named park: OSM within 900 m of the interchange shows only small unnamed garden ways (Suan Pakkad's museum grounds among them) and no public park of ~1 ha; the nearest major green (Santiphap Park) computes to ~1.45 km. Identity of the 1.1 ha polygon is an open issue for the coordinator. _(scope: station_area — Phaya Thai interchange catchment)_
- `phaya-thai-st-c10` **[corroborated·neutral·entire_unit]** Crowd 2 is consistent with the catchment being an interchange-plus-office catchment rather than a residential density peak: flows concentrate at peak hours in the paid areas (commuters, airport passengers), while the surrounding blocks mix older apartments, hospital compounds and the SRT/rail corridor; no pedestrian-count data was found, so the rating stays an inference. _(scope: station_area — Phaya Thai interchange)_
- `phaya-thai-st-c11` **[corroborated·neutral·partial]** 2024-2026 changes around the unit are rail-driven: the SRT halt's tracks are being handed to the Don Mueang-Suvarnabhumi-U-Tapao high-speed project (with the ARL extension Phaya Thai to Don Mueang part of the same programme), and the associated land clearance has been displacing railway-corridor communities along the Rama VI to Phaya Thai stretch - five communities totalling 644 households, with a first-phase 169-household relocation housing project opening its sign at Bueng Makkasan beside Santiphap Park on 29 September 2024. Newer condo stock near the station includes The Extro Phayathai-Rangnam (completed 2025, per listings portal). _(scope: corridor — Rama VI - Phaya Thai railway corridor / Bueng Makkasan)_
- `phaya-thai-st-c12` **[corroborated·strength·entire_unit]** Walkability is interchange-first: BTS and ARL platforms are ~121 m apart and linked by the 2010 skywalk, with buses at the adjacent stops and Victory Monument's bus hub one BTS stop north; no sidewalk-width or crossing data was found for the surrounding Phaya Thai/Si Ayutthaya blocks, and no radius-to-time conversions are used here. _(scope: station_area — Phaya Thai interchange)_

## Reviewer notes from the researcher
- Researcher self-checks only; independent review still required (batch review/findings.md).
- 1 claim(s) carry relation_to_entity=unknown as an honest gap: phaya-thai-st-c09.
- 2 claim(s) carry explicit recheck_by flags for volatile facts.
- open issue: Identify the app's 1.1 ha park polygon for st.phaya-thai (candidates within ~1.5 km: none named in OSM; Suan Pakkad gardens are private museum grounds) (phaya-thai-st-c09).
- open issue: Confirm the app anchor latitude (13.7600) vs OSM BTS node 13.75696 and re-run edge memberships (phaya-thai-st-c02).
- open issue: Body-read a current ARL timetable/headway source to firm up the transport-10 mechanism (phaya-thai-st-c03).
- open issue: Safety 5 remains untested - no usable statistics located for this unit (phaya-thai-st-c07).
