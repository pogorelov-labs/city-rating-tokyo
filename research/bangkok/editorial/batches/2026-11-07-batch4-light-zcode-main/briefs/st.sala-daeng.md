# Sala Daeng / Si Lom (st.sala-daeng) — research brief

**Derived view** of `profiles/st.sala-daeng.json` (authoritative bundle), batch `zcode-main (ZCode orchestrator + 6 light-pass subagents), 2026-11-07` era output. Status: **ready_for_review** — not independently approved. Drafted in English only; no translations manufactured.

- **Unit:** Station area (nearest-stop catchment, Voronoi ∩ 800 m disc). Aliases: —
- **Scope:** Nearest-stop catchment (Voronoi ∩ 800 m) around sala-daeng/si-lom [bts_silom/mrt_blue]; districts: pathum-wan, bang-rak, sathon. Boundary claims are decided by the app polygons (coordinator checks apply).
- **App score context:** model 7.54 (display rounded), cohort rank 18 of 133, snapshot `bkk-d6499618507e7561`. Public popularity: **unmeasured** — No citywide popularity measure has been collected. Tier B selection used within-cohort rank; coverage recorded opportunistically per bundle.
- **Selection rationale:** Tier B (light pass): station-area rank 18/133, score 7.54.

## Card preview (proposed)
> The real interchange of the Silom CBD: BTS Sala Daeng and MRT Si Lom 330 m apart under one skywalk, Patpong at the station steps, the office-lunch alleys of Lalai Sap - and most of Lumphini Park's western edge inside the catchment.

## Guide lead (proposed)
Sala Daeng is the app's only merged BTS+MRT unit south of Siam, and the merge is physically real: a covered skywalk runs from BTS Sala Daeng (S2, 1999) over Rama IV to MRT Si Lom (BL26, 2004) and on to King Chulalongkorn Memorial Hospital. Food 10 and nightlife 10 have visible engines - the weekday Lalai Sap lunch alleys on Silom Soi 5 and Patpong's market-and-go-go strip 90-200 m from the platforms - and green 10 leans on Lumphini Park's west corner ~300-500 m east. The counterweights are the strip's documented tout-and-overcharge economy and a rent band (38,000/60,000) that sits above typical 1-BR guide medians.

## Strengths
- A true merged interchange: two metro lines 330 m apart under one skywalk, extended to a major hospital - the strongest everyday-transport geometry in this batch. *[`sala-daeng-c01`, `sala-daeng-c09`]*
- Food and nightlife are not abstractions here: the Lalai Sap office-lunch market and Patpong's night market sit within a few hundred metres of the platforms, on opposite halves of the day. *[`sala-daeng-c06`, `sala-daeng-c04`]*

## Trade-offs
- Nightlife 10 shares its address with Bangkok's most documented tourist-scam strip: unposted-price upstairs shows, inflated bills and touts are a real resident-adjacent externality, not just a tourist problem. *[`sala-daeng-c05`]*
- The stated rent (38,000/60,000) exceeds typical 1-BR guide medians (~22,000-28,000 near the BTS in early 2025); the figure is only defensible as station-adjacent or larger-unit stock. *[`sala-daeng-c11`]*

## Day / night
- The unit flips at roughly 18:00: office-lunch alleys close by mid-afternoon and Patpong's stalls and bars take the street until late; weekends quiet down across both halves. *[`sala-daeng-c12`, `sala-daeng-c06`]*

## Within-area variation
- The Silom frontage (Patpong, Thaniya, Lalai Sap) is loud and commercial, while the Rama IV/park side (Dusit Central Park, MRT Si Lom exits, hospital skywalk) reads calmer and greener. *[`sala-daeng-c04`, `sala-daeng-c08`, `sala-daeng-c09`]*

## Conditional fit
- Strong fit: office workers and frequent travellers who want car-free CBD living, a hospital skywalk, and street food at both ends of the day. *[`sala-daeng-c01`, `sala-daeng-c09`, `sala-daeng-c06`]*
- Poor fit: households wanting quiet evenings or family-oriented streets - the red-light frontage and its tout economy are unavoidable at the station steps. *[`sala-daeng-c05`, `sala-daeng-c12`]*

## Explicit unknowns
- rating green (10): 37.2 ha matches ~65% of Lumphini's 57.6 ha, and the park's SW corner is only ~281 m from MRT Si Lom, but the park-split is an app-polygon fact we could not verify; if the cell boundary runs west of the park, the rating's mechanism changes (sala-daeng-c07).
- rating rent (1-> figures): 38,000/60,000 is above typical 1-BR guide medians and below the luxury-skewed aggregator median; both comparison sets are snippet-level commercial sources (sala-daeng-c11).
- rating safety (7) / crowd (2): no unit-level statistics found; crowd-2 inference rests on the office-district drain pattern, not counts.
- Anchor longitude not provided; all distances computed from OSM/Wikipedia station nodes.
- Lalai Sap's exact extent differs between sources (Silom Soi 5 label vs travelfish GPS ~700 m WSW).

## Question coverage
- **Q01 — answered**: Merged BTS Sala Daeng (S2, 1999) + MRT Si Lom (BL26, 2004), ~330 m apart node-to-node, skywalk-connected; anchor latitude matches the BTS station coordinate exactly. Unit sits in Bang Rak (MRT straddles Bang Rak/Pathum Wan).
- **Q02 — answered**: Office-district everyday: noon lunch alleys, skywalk commutes, hospital and mall services at the door; after dark the strip turns to Patpong's market-and-bars economy.
- **Q03 — answered**: Transport/food/nightlife/green highs all have named mechanisms: two merged metro lines, 593-food-count density anchored by office demand and Lalai Sap, Patpong as the dataset's real nightlife heart, and a majority-ish share of Lumphini's 57.6 ha inside the catchment.
- **Q04 — answered**: Counter-view documented: Patpong's tout/scam economy (unposted-price shows, inflated bills, counterfeit goods, pickpocketing) - the same venues behind nightlife 10.
- **Q05 — answered**: Weekday: 06:00-15:30 market, noon peak; evening: Patpong from ~18:00, peak ~20:00, stalls down after ~22:00; weekends quiet.
- **Q06 — answered**: Walkability assets are structural: skywalk BTS-MRT-hospital, compact soi grid; guides advise walking over taxis at lunch. No sidewalk-width data found; no radius-to-time conversions used.
- **Q07 — answered**: Tops (Silom Complex, ~280 m), Foodland (~130 m), ~20 convenience stores within 700 m, Chulalongkorn Memorial Hospital on the skywalk (~410-516 m).
- **Q08 — answered**: 38,000/60,000 sits between the typical-guide 1-BR band (~22,000-35,000) and the luxury-skewed aggregator median (44,900). Plausible for station-adjacent stock; flagged as high versus guide medians.
- **Q09 — answered**: 37.2 ha most plausibly = western/southern Lumphini (281-512 m from MRT Si Lom node; ~65% of 57.6 ha), plus Dusit Central Park (2024) at ~128 m from the MRT node. Voronoi split through the park is app-decided - flagged partial.
- **Q10 — answered**: Strong fit: car-free CBD workers, food-driven households, nightlife-seekers tolerant of the strip's seaminess. Poor fit: quiet-seekers, families avoiding adult-entertainment frontage, weekend-liveliness seekers.
- **Q11 — answered**: Dusit Central Park opened 27 Sep 2024 in-unit; One Bangkok phased opening from Mar 2024 just outside the cell (Lumphini MRT side); Patpong Museum closed May 2023 (pre-window).
- **Q12 — answered**: Outside-the-score: green 10 depends on an unverified park split; rent figures rest on snippet-level portals; scam economy invisible to amenity counts; anchor longitude unknown.

## Evidence base

| Source | Publisher (family) | Type | Published | Read |
| --- | --- | --- | --- | --- |
| [Query: stations, parks, worship around 13.7285,100.5370; BTS nodes; Lumphini bbox; supe…](https://overpass-api.de/api/interpreter) | OpenStreetMap via Overpass API (OpenStreetMap via Overpass API) | other | — | yes |
| [Sala Daeng station](https://en.wikipedia.org/wiki/Sala_Daeng_BTS_station) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Si Lom station](https://en.wikipedia.org/wiki/Si_Lom_MRT_station) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Lumphini Park](https://en.wikipedia.org/wiki/Lumphini_Park) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Patpong](https://en.wikipedia.org/wiki/Patpong) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [One Bangkok](https://en.wikipedia.org/wiki/One_Bangkok) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Dusit Thani Bangkok](https://en.wikipedia.org/wiki/Dusit_Thani_Bangkok) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Soi Lalai Sap Market Guide: Silom Lunch Food, Office Crowds and Timing](https://www.thefinestthai.com/2026/06/03/soi-lalai-sap-silom-lunch-market-street-food-guide/) | The Finest Thai (lifestyle_blog) | editorial_guide | 2026-06-03 | partial |
| [Lalai Sap Market in Silom](https://www.hotels.com/go/thailand/lalai-sap-market-bangkok) | Hotels.com GO (ota_content) | editorial_guide | — | partial |
| [Patpong Night Market Bangkok, Silom - What to Expect](https://www.nomadotravel.app/en/attractions/patpong-night-market) | Nomado Travel (lifestyle_blog) | editorial_guide | 2026-03-20 | partial |
| [Patpong Bangkok](https://bangkokup.com/patpong-bangkok) | Bangkok Up (lifestyle_blog) | editorial_guide | 2026-06-05 | partial |
| [1 Bedroom Condos for Rent near Sala Daeng BTS (Sala Daeng BTS Rental Market Prices)](https://www.property-hua-hin.com/1-bedroom-condo-for-rent/thailand/bangkok/bang-rak/si-lom/near-sala-daeng-bts) | Property Hua Hin (aggregator) (real_estate_portal) | other | — | partial |
| [Silom Food Street Rent - Bangkok Living Guide](https://www.superagent.co/en/blog/renting-near-silom-food-street-bangkoks-lunch-district-living-guide) | Superagent (real_estate_content) | other | 2026-05-03 | partial |
| [Saladaeng One: Silom Luxury Condo Reviewed for Renters](https://www.superagent.co/en/blog/saladaeng-one-silom-luxury-condo-reviewed-for-renters) | Superagent (real_estate_content) | other | 2026-04-28 | partial |
| [Horrifying Experience at Patpong Night Market (r/ThailandTourism)](https://www.reddit.com/r/ThailandTourism/comments/1n9bw1d/horrifying_experience_at_patpong_night_market) | Reddit (forum_ugc) | other | — | partial |

## Claim index

- `sala-daeng-c01` **[corroborated·strength·entire_unit]** The unit is the Sala Daeng interchange: BTS Sala Daeng (S2, Silom Line, opened 5 December 1999, Bang Rak district, coordinates 13.72851 N 100.53413 E) plus MRT Si Lom (BL26, Blue Line, opened 3 July 2004), whose station sits under Rama IV Road at Sala Daeng Intersection where Si Lom Road begins. The two are connected by a covered elevated skywalk that also reaches King Chulalongkorn Memorial Hospital; OSM node-to-node distance is ~330 m, consistent with a <=450 m merge. _(scope: station_area — Sala Daeng / Si Lom (Bang Rak))_
- `sala-daeng-c02` **[corroborated·neutral·entire_unit]** The app anchor latitude (~13.7285) matches the OSM/Wikipedia BTS Sala Daeng coordinate (13.72851) almost exactly, so unlike other batch-4 units there is no station-anchor mismatch here; the anchor longitude was not provided in the brief. _(scope: station_area — BTS Sala Daeng)_
- `sala-daeng-c03` **[proposed·neutral·inside]** Sala Daeng Intersection is the junction of Ratchadamri, Rama IV and Si Lom roads, on land that was formerly the 'Thung Sala Daeng' field donated by King Rama VI; it is served by both MRT Si Lom and BTS Sala Daeng, and surrounds include Dusit Central Park (the old Dusit Thani site), King Chulalongkorn Memorial Hospital and Silom Edge. _(scope: station_area — Sala Daeng Intersection)_
- `sala-daeng-c04` **[corroborated·neutral·inside]** Patpong - two parallel private sois between Silom and Surawong Roads with a tourist night market since the early 1990s and an internationally known red-light strip (plus Soi Thaniya and Silom Soi 4/Jaruwan) - sits at the doorstep of BTS Sala Daeng: Wikipedia's Patpong coordinates compute to ~90 m from the BTS station node, and the article names both stations as walking-distance access. _(scope: venue — Patpong 1-2 / Soi Thaniya)_
- `sala-daeng-c05` **[corroborated·tradeoff·inside]** Counter-view to nightlife 10: multiple 2025-2026 guides describe Patpong's signature tourist-scam pattern - touts ushering visitors to unposted-price upstairs 'ping-pong shows' that end in exorbitant, intimidatingly enforced bills - plus inflated market prices, counterfeit goods and pickpocket warnings; the area is described as adult-oriented and uncomfortable for families. _(scope: venue — Patpong)_
- `sala-daeng-c06` **[conflicted·strength·inside]** The unit's daytime food engine is the Soi Lalai Sap market (Silom Soi 5 alleys near Bangkok Bank HQ, running since about 1983): a weekday-only office-worker market open roughly 06:00-15:30/16:00, with a noon crush described as thousands of workers from Silom/Sathorn offices; guides name BTS Sala Daeng and MRT Si Lom as its rail anchors. One guide (travelfish) GPS-places the alley network further west toward the Silom/Narathiwas end, so the market's exact extent is fuzzier than the 'Silom Soi 5' label suggests. _(scope: venue — Soi Lalai Sap (Silom Soi 5))_
- `sala-daeng-c07` **[corroborated·strength·partial]** Green 10 rests on Lumphini Park: 360 rai / 57.6 ha bounded by Ratchadamri (west), Rama IV (south) and Witthayu (east). The park's southwest corner at Ratchadamri x Rama IV computes to ~281 m from the MRT Si Lom node and ~428 m from the BTS node, and the park centroid ~512 m from the MRT node - all inside an 800 m catchment. The app's 37.2 ha equals ~65% of the park, consistent with a nearest-station Voronoi split that leaves the park's western/southern portion in this cell; but the split line is app-decided, so membership is partial. _(scope: station_area — Lumphini Park (west portion))_
- `sala-daeng-c08` **[corroborated·strength·inside]** A 2024-2026 green change sits inside the unit: Dusit Thani Bangkok reopened 27 September 2024 as part of the Dusit Central Park complex on the southeast corner of Sala Daeng Intersection (the old hotel site), and OSM maps a 'Dusit Central Park' way ~128 m from the MRT Si Lom node / ~399 m from the BTS node. _(scope: building — Dusit Central Park)_
- `sala-daeng-c09` **[corroborated·strength·inside]** Daily-life infrastructure is dense and close: the skywalk links both stations to King Chulalongkorn Memorial Hospital (computed ~410 m from the MRT node, ~516 m from the BTS node), and OSM maps a Tops supermarket at Silom Complex (~280 m from the BTS node), Foodland Silom (~130 m) and roughly twenty 7-Eleven/FamilyMart nodes within 700 m. _(scope: station_area — Sala Daeng / Silom)_
- `sala-daeng-c10` **[corroborated·neutral·outside]** One Bangkok (16.7 ha, five office towers plus 8 ha of green, opening from 18 March 2024 at the Witthayu intersection, tunnel-linked to MRT Lumphini) is the belt's flagship 2024 opening but lies ~1.1 km east of the MRT Si Lom node across the park - outside this unit; it belongs to the MRT Lumphini cell. _(scope: district — One Bangkok / Witthayu intersection)_
- `sala-daeng-c11` **[corroborated·neutral·entire_unit]** Affordability vs stated figures (38,000/60,000, station_override 2026-10-07): market evidence spans a wide band. An aggregator's Sala Daeng BTS stats show median monthly rent ~44,900 THB (1-BR avg 39,100, 2-BR 66,300, 489 listings) but its listing mix is luxury-heavy (Dusit Parkside at 150,000-190,000), while guide-based figures put typical 1-BR asking rents within ~500 m of the BTS at ~22,000-28,000 THB (early 2025) and the CBD band at 28,000-50,000. The app's 38,000 sits between the typical-guide band and the luxury-skewed median; 60,000 matches upper 2-BR/luxury stock. _(scope: station_area — Sala Daeng / Si Lom)_
- `sala-daeng-c12` **[corroborated·neutral·entire_unit]** Rhythm and crowd: the unit runs on Silom's office clock - a noon lunch crush in the Lalai Sap alleys, then Patpong's market ramping from ~18:00 to a ~20:00 peak with stalls packing down after ~22:00 while bars continue later; weekends are markedly quieter (Lalai Sap closed Sat-Sun). This drain pattern is consistent with the app's crowd 2. _(scope: station_area — Silom / Sala Daeng)_

## Reviewer notes from the researcher
- Researcher self-checks only; independent review still required (batch review/findings.md).
- 2 claim(s) carry explicit recheck_by flags for volatile facts.
- open issue: Coordinator to audit the app polygon for the Lumphini Park split: 37.2 ha in-unit implies the boundary runs through the park between the Sala Daeng cell and ratchadamri/lumphini cells (sala-daeng-c07).
- open issue: Whether Dusit Central Park's green is publicly accessible (and how much is park vs hotel podium) is unverified (sala-daeng-c08).
- open issue: Rent claims rest on exa-highlight-only portal sources; Dot Property's rendered stats were unreachable via curl (client-side rendering) - a body-read rent source would firm up Q08.
- open issue: TripAdvisor/Reddit complaint threads returned 403 and were not read; scam-claim evidence is guide-level plus flagged snippets (sala-daeng-c05).
