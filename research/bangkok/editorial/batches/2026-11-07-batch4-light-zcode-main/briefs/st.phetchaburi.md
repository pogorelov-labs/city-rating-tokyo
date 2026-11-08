# Phetchaburi / Makkasan (st.phetchaburi) — research brief

**Derived view** of `profiles/st.phetchaburi.json` (authoritative bundle), batch `zcode-main (ZCode orchestrator + 6 light-pass subagents), 2026-11-07` era output. Status: **ready_for_review** — not independently approved. Drafted in English only; no translations manufactured.

- **Unit:** Station area (nearest-stop catchment, Voronoi ∩ 800 m disc). Aliases: —
- **Scope:** Nearest-stop catchment (Voronoi ∩ 800 m) around phetchaburi/makkasan [mrt_blue/arl]; districts: ratchathewi, watthana, huai-khwang. Boundary claims are decided by the app polygons (coordinator checks apply).
- **App score context:** model 7.42 (display rounded), cohort rank 23 of 133, snapshot `bkk-d6499618507e7561`. Public popularity: **unmeasured** — No citywide popularity measure has been collected. Tier B selection used within-cohort rank; coverage recorded opportunistically per bundle.
- **Selection rationale:** Tier B (light pass): station-area rank 23/133, score 7.42.

## Card preview (proposed)
> The quietest core unit in the dataset hides a triple rail identity: MRT Phetchaburi and ARL Makkasan 312 m apart under a covered walkway, an 'Asok' SRT halt between them, three Khlong Saen Saep piers within 500 m - and a railway corridor being cleared for the three-airport high-speed line.

## Guide lead (proposed)
Phetchaburi/Makkasan is the app's connector unit: MRT Blue Line BL21 under the Asok-New Phetchaburi junction, the Airport Rail Link's Makkasan station 312 m away via a covered footpath (fares not integrated), and an SRT halt called Asok at ground level - three names, one block. The canal adds three piers (Asoke-Petchaburi, Prasanmit, Nana Chard) and a 05:30-20:30 boat commute. Rents run mid-band (800 m 1-BR medians 25-29.5k; the app's 21,000 fits older Makkasan-Road stock). What the score glosses: nightlife 9 rests on hotel bars and the Pratunam night-market belt - guides call this area no nightlife district at all - the 0.5 ha park is unidentified, and the railway corridor along the unit's edge is being progressively cleared, with 644 households affected and the first 169 rehoused beside Santiphap Park in September 2024.

## Strengths
- Three-rail access plus a boat: merged MRT-ARL interchange with airport line service and three canal piers inside ~500 m - a genuinely multi-modal transport set for the price band. *[`phetchaburi-c01`, `phetchaburi-c03`]*
- Rents still sit below the Asok towers next door: 800 m medians of 25-29.5k THB against the app's 21,000 for older stock. *[`phetchaburi-c07`]*

## Trade-offs
- Nightlife 9 is the least defensible rating in this batch: with 11 mapped venues, the number borrows from hotel bars and the Pratunam belt that guides explicitly do not consider a nightlife district. *[`phetchaburi-c05`]*
- The street layer is rough: narrow pavements on Asok-Din Daeng, single-in/out sois that back up at peak, and an unresolved 0.5 ha park. *[`phetchaburi-c09`, `phetchaburi-c08`]*

## Day / night
- Canal boats and office peaks own the morning (first boats 05:30); the block quiets after work, leaving evenings to the Pratunam night-market belt one district west. *[`phetchaburi-c03`, `phetchaburi-c05`]*

## Within-area variation
- The station-and-walkway block is transit-busy; eastward toward the piers the canal side is quieter, and the railway-corridor edge carries the clearance works and pending land plans. *[`phetchaburi-c03`, `phetchaburi-c04`, `phetchaburi-c12`]*

## Conditional fit
- Strong fit: Asok/Rama 9 office workers and frequent flyers who want multi-modal access at rents below the neighbouring Asok towers. *[`phetchaburi-c01`, `phetchaburi-c07`]*
- Poor fit: nightlife-led renters and green-space seekers - both headline ratings trace to buffers, not to this block's own amenities. *[`phetchaburi-c05`, `phetchaburi-c08`]*

## Explicit unknowns
- rating nightlife (9): mechanism inferred (hotel bars + Pratunam buffer); guides counter it directly (phetchaburi-c05).
- rating green (6): 0.5 ha park polygon unmatched in OSM (phetchaburi-c08).
- rating rent (6): all comparison medians are exa-highlight-level portal data; the 'ratchathewi blend' label may mean a district rather than catchment figure (phetchaburi-c07).
- Anchor offset (~120 m from ARL node, ~310 m from MRT node) plus unknown longitude; edge memberships toward the Phra Ram 9 cell unverified (phetchaburi-c02).
- Which of the five displaced railway communities, if any, falls inside the app polygon (phetchaburi-c04).

## Question coverage
- **Q01 — answered**: MRT Phetchaburi (BL21) + ARL Makkasan (A6) merge at ~312 m node-to-node with a covered footpath; Asok Halt adjacent; khwaeng Makkasan, Ratchathewi; anchor ~120 m from the ARL node.
- **Q02 — answered**: Practical connector block: office-worker population, MetroMall, street market, canal piers; not a retail core.
- **Q03 — answered**: Transport 9 = merged MRT+ARL with airport access and three canal piers; DE 8 = MetroMall + market + Pratunam belt; rent 6 = mid-band medians slightly above the app's 21,000.
- **Q04 — answered**: Nightlife 9 vs 11 venues: guides deny nightlife-district status; the 9 is likely buffer + hotel-bar aggregation.
- **Q05 — answered**: Canal boats 05:30-20:30 weekdays shape the morning; office peaks; Pratunam's evening market belt to the west.
- **Q06 — answered**: Covered MRT-ARL walkway and piers vs narrow pavements and single-in/out sois.
- **Q07 — answered**: MetroMall, SUP Street Market, piers, Bangkok Hospital east; supermarket gap in OSM flagged.
- **Q08 — answered**: 21,000/45,500: 21,000 fits older-stock 1-BR (medians 25-29.5k, Lumpini Suite 15.25k); 45,500 fits upper 2-BR band.
- **Q09 — answered**: 0.5 ha park polygon unidentified in OSM; no named public park within 900 m.
- **Q10 — answered**: Strong fit: Asok/Rama 9 office workers and frequent flyers wanting lower rents than Asok; poor fit: nightlife-first and park-seeking renters.
- **Q11 — answered**: Rail-corridor clearance with 644 affected households; 169-household first phase signed 29 Sep 2024; HSR works continue; railway-land plans pending.
- **Q12 — answered**: Outside the score: nightlife-9 buffer artifact risk, unnamed park polygon, anchor offset toward Makkasan, and the displacement story invisible to amenity counts.

## Evidence base

| Source | Publisher (family) | Type | Published | Read |
| --- | --- | --- | --- | --- |
| [Queries: stations + ferry terminals around 13.7520,100.5650; parks; supermarkets](https://overpass-api.de/api/interpreter) | OpenStreetMap via Overpass API (OpenStreetMap via Overpass API) | other | — | yes |
| [Phetchaburi MRT station](https://en.wikipedia.org/wiki/Phetchaburi_MRT_station) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Khlong Saen Saep boat service](https://en.wikipedia.org/wiki/Khlong_Saen_Saep_Express_Boat) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Airport Rail Link (Bangkok)](https://en.wikipedia.org/wiki/Airport_Rail_Link_(Bangkok)) | Wikipedia (English) (Wikimedia) | other | — | yes |
| ["ชุมชน ชมฟ.ริมบึงมักกะสัน" ความสำเร็จอีกขั้น แก้ไขปัญหาที่อยู่อาศัยคนจนเมือง](https://theactive.thaipbs.or.th/news/urban-housing-20240929) | The Active (Thai PBS) (thai_public_broadcast) | news | 2024-09-29 | yes |
| [รฟท.เร่งเคลียร์มักกะสัน สร้างที่พักรองรับย้ายชุมชน](https://www.bangkokbiznews.com/business/1009342) | BangkokBizNews (thai_business_press) | news | 2022-06-11 | partial |
| [MRT Phetchaburi / ARL Makkasan: Area Guide](https://dooasset.com/en/area/mrt-phetchaburi/) | DooAsset (real_estate_portal) | other | — | partial |
| [Condos for rent near Phetchaburi MRT, Makkasan](https://www.fazwaz.com/condo-for-rent/thailand/bangkok/ratchathewi/makkasan/near-phetchaburi-mrt) | FazWaz (real_estate_portal) | other | — | partial |
| [Condos for Rent near MRT Phetchaburi](https://www.eastblueth.com/en/station/mrt-phetchaburi) | Eastblue (real_estate_portal) | other | — | partial |
| [Pratunam Area Guide 2026](https://roavara.com/pratunam-area-guide/) | Roavara (real_estate_content) | editorial_guide | 2026-07-31 | partial |
| [Pratunam - Shopping & Street Food Guide](https://www.nomadotravel.app/en/places/pratunam) | Nomado Travel (lifestyle_blog) | editorial_guide | — | partial |
| [10 Dazzling Places To Enjoy Nightlife in Pratunam](https://traveltriangle.com/blog/nightlife-in-pratunam/) | TravelTriangle (lifestyle_blog) | editorial_guide | 2023-06-21 | partial |

## Claim index

- `phetchaburi-c01` **[corroborated·strength·entire_unit]** Merge semantics resolved: the unit pairs MRT Phetchaburi (BL21, Blue Line, under the junction of Asok and New Phetchaburi Road) with ARL Makkasan (opened 23 August 2010; every ARL station except Suvarnabhumi and Ratchaprarop sits above an Eastern Line station), which Wikipedia connects via 'a covered-elevated footpath' with fares and ticket systems 'not integrated'. OSM nodes are ~312 m apart - inside the <=450 m merge rule - and an area portal treats them as a single interchange (codes BL21 / A6). A third rail element, the SRT Eastern Line's Asok Halt at ground level, sits adjacent (OSM halt node ~200 m from the MRT node). _(scope: station_area — MRT Phetchaburi / ARL Makkasan (khwaeng Makkasan, Ratchathewi))_
- `phetchaburi-c02` **[proposed·neutral·entire_unit]** Anchor offset: the app's '@13.7520-ish' sits ~310 m north of the MRT Phetchaburi node (13.74919) but only ~120 m from the ARL Makkasan node (13.75091) - a moderate offset consistent with the batch-4 300-700 m pattern; it suggests the app may anchor the merged unit nearer Makkasan. Edge memberships toward Rama IX (MRT Phra Ram 9 cell) should be re-checked against the polygon. _(scope: station_area — MRT Phetchaburi / ARL Makkasan)_
- `phetchaburi-c03` **[corroborated·strength·inside]** The app's '3 piers' are identified and none is named Makkasan: on the Khlong Saen Saep NIDA Line they are Asoke-Petchaburi (~157 m from the MRT node - Wikipedia: 'near Phetchaburi MRT station and the old site of the Japanese embassy'), Prasanmit (~321 m, at Srinakharinwirot University's Prasarn Mit campus) and Nana Chard (~474 m, Sukhumvit Soi 15). The boat service has run since 1 October 1990 over an 18 km route, operating 05:30-20:30 weekdays and to 19:00 weekends at 8-22 THB with ~60,000 daily passengers, running parallel to Phetchaburi Road. _(scope: corridor — Khlong Saen Saep piers (Asoke-Petchaburi, Prasanmit, Nana Chard))_
- `phetchaburi-c04` **[corroborated·tradeoff·partial]** The SRT railway-community relocation to Bueng Makkasan is real and dated: on 29 September 2024 the 'ชุมชน ชมฟ.ริมบึงมักกะสัน' community - railway-track households displaced by the Don Mueang-Suvarnabhumi-U-Tapao high-speed rail, which reuses the ARL corridor with ARL Makkasan as its EEC gateway - unveiled its sign on ~7 rai leased from the SRT beside Santiphap Park in Ratchathewi. Phase 1 covers 169 households of the 644 affected across five communities stretching along the Rama VI to Phaya Thai corridor (บุญร่มไทร 129, แดงบุหงา 151, หลัง รพ.เดชา 182, หมอเหล็ง 124, RCA 58); a cabinet programme of 14 March 2023 funds housing for 27,084 rail-affected households nationwide (2023-2027), and a separate NHA 315-unit block at Bueng Makkasan was reported in 2022 with construction from 2024. The relocation site computes to ~2.3 km from the MRT Phetchaburi node - outside this unit - though the cleared corridor edges approach it. _(scope: corridor — Rama VI - Phaya Thai railway corridor / Bueng Makkasan (Ratchathewi))_
- `phetchaburi-c05` **[corroborated·tradeoff·partial]** Counter-view to nightlife 9 with only 11 venues: independent guides flatly deny the area is a nightlife district - 'Pratunam remains active after dark, but it is not one of Bangkok's strongest nightlife districts... better for casual food, shopping, massage... than cocktail-bar hopping or clubbing' and 'not a neighborhood for serious bar culture'. The 9 most plausibly aggregates hotel-bar venues along New Phetchaburi Road (e.g. a Novotel rooftop bar) and the Palladium/Pratunam night-market belt at the Ratchaprarop x Phetchaburi corner (~1.2 km west) - a buffer effect rather than in-unit club density. _(scope: station_area — New Phetchaburi Rd / Pratunam edge)_
- `phetchaburi-c06` **[corroborated·neutral·entire_unit]** Crowd 4 (the least crowded core unit) has a plausible mechanism: the Makkasan block between the Asok business district and the railway lands is an office/warehouse/rail-corridor mix rather than a retail core - guides describe it as a connector between Asok and Makkasan-Ratchathewi, with the market crowds concentrated in Pratunam proper to the west. No pedestrian counts were found; this stays an inference. _(scope: station_area — Makkasan / New Phetchaburi)_
- `phetchaburi-c07` **[proposed·neutral·entire_unit]** Affordability vs stated figures (21,000/45,500, ratchathewi blend): 800 m-catchment medians from three portals cluster at 25,000-29,500 THB for all listings (1-BR 20,500-26,500; studios 17,500-19,500; 2-BR 32,000-47,300), with older Makkasan-Road stock such as Lumpini Suite Phetchaburi-Makkasan at ~15,250. The app's 21,000 fits the affordable older-stock end of the 1-BR band; 45,500 matches the upper 2-BR band. _(scope: station_area — MRT Phetchaburi / ARL Makkasan catchment)_
- `phetchaburi-c08` **[proposed·neutral·unknown]** Green 6 with a 0.5 ha park: no named public park of ~0.5-1 ha was found within 900 m of the stations in OSM - only unnamed garden ways (many building grounds) - so the 0.5 ha polygon's identity is unresolved. The canal adds linear water-space rather than parkland, and the nearest large green (Benjakitti Forest Park) lies ~2 km southeast. _(scope: station_area — Makkasan / Phetchaburi catchment)_
- `phetchaburi-c09` **[corroborated·neutral·entire_unit]** Walkability is mixed and documented: the covered elevated footpath links MRT Phetchaburi to ARL Makkasan, and the canal piers put a boat commute ~150-500 m away; but an agency guide warns that 'some stretches of pavement along Asok-Din Daeng are narrow and traffic is heavy' and 'some Phetchaburi sois have a single way in and out that backs up at peak hours'. No sidewalk measurements were found; no radius-to-time conversions are used. _(scope: station_area — New Phetchaburi / Asok-Din Daeng)_
- `phetchaburi-c10` **[corroborated·neutral·inside]** Daily-life anchors: a MetroMall inside the MRT station; the SUP Street Market node mapped ~430 m west; the canal piers for groceries-accessible runs toward Pratunam; and Bangkok Hospital on Soi Soonvijai 'a short ride further east' per a portal guide. No supermarket was tagged within 700 m of the stations in this OSM pass - a gap for the DE 8 rating that the surrounding Pratunam belt presumably fills. _(scope: station_area — Makkasan / New Phetchaburi)_
- `phetchaburi-c11` **[corroborated·neutral·entire_unit]** Naming tangle worth stating on the card: 'Makkasan' on Wikipedia is a disambiguation between the ARL station and an SRT railway station; the halt adjacent to the MRT station is called 'Asok' in both Wikipedia and OSM; and the unit's khwaeng is Makkasan in Ratchathewi district - three rail names for one 300 m block. _(scope: station_area — Makkasan / Asok halt / Phetchaburi)_
- `phetchaburi-c12` **[corroborated·neutral·partial]** Forward-looking changes: beyond the 2024 relocation housing, an agency guide flags the 'long-discussed plans for the Makkasan railway land, which could change views and traffic', and the three-airport HSR programme keeps the ARL corridor under construction - meaning the unit's eastern rail edge is the most likely place in this batch for structural change through 2030. _(scope: corridor — Makkasan railway lands / ARL corridor)_

## Reviewer notes from the researcher
- Researcher self-checks only; independent review still required (batch review/findings.md).
- 1 claim(s) carry relation_to_entity=unknown as an honest gap: phetchaburi-c08.
- 2 claim(s) carry explicit recheck_by flags for volatile facts.
- open issue: Identify the app's 0.5 ha park polygon (no named public park within 900 m in OSM) (phetchaburi-c08).
- open issue: Confirm which railway-corridor communities (if any) fall inside the unit and whether clearance works touch the unit's edge (phetchaburi-c04).
- open issue: Obtain a body-read rent median for the Makkasan catchment (all current medians are highlight-level) (phetchaburi-c07).
- open issue: Verify the MRT Phetchaburi station's opening year from a stronger source (extract omitted it; context implies the 2004 original line) (phetchaburi-c01).
- open issue: DooAsset's Makkasan page lists some 'nearest project' stock on the Asok side; if the app's Voronoi splits west of the walkway, several of those listings belong to other cells - polygon audit needed (phetchaburi-c02).
