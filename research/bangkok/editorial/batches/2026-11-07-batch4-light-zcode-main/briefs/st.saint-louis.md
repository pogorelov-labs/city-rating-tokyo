# Saint Louis (st.saint-louis) — research brief

**Derived view** of `profiles/st.saint-louis.json` (authoritative bundle), batch `zcode-main (ZCode orchestrator + 6 light-pass subagents), 2026-11-07` era output. Status: **ready_for_review** — not independently approved. Drafted in English only; no translations manufactured.

- **Unit:** Station area (nearest-stop catchment, Voronoi ∩ 800 m disc). Aliases: —
- **Scope:** Nearest-stop catchment (Voronoi ∩ 800 m) around saint-louis [bts_silom]; districts: sathon, bang-rak. Boundary claims are decided by the app polygons (coordinator checks apply).
- **App score context:** model 7.46 (display rounded), cohort rank 21 of 133, snapshot `bkk-d6499618507e7561`. Public popularity: **unmeasured** — No citywide popularity measure has been collected. Tier B selection used within-cohort rank; coverage recorded opportunistically per bundle.
- **Selection rationale:** Tier B (light pass): station-area rank 21/133, score 7.46.

## Card preview (proposed)
> Bangkok's first infill BTS station (2021) dropped into Sathorn's quietest pocket: a Catholic hospital, church and school cluster 200-340 m from the platform, a soi-3 street-food row - and zero mapped parkland.

## Guide lead (proposed)
Saint Louis is the anti-Chong Nonsi: the Silom line's infill station S4 (opened 8 February 2021) sits where North Sathorn becomes South Sathorn, straddling Bang Rak and Sathon, above a neighbourhood of church, hospital and school rather than towers. Saint Louis Hospital (1898, Thailand's first Catholic hospital) is ~200 m from the platform, the Soi Saint Louis 3 food row supplies B40-70 lunches, and the sois read tree-lined and calm. Two ratings strain against the evidence: nightlife 9 despite guides calling the pocket's scene quiet, and green 7 against a mapped 0.0 ha of park. Note the brief's anchor coordinate sits ~720 m from the real station node and needs re-checking.

## Strengths
- Hospital-and-church neighbourhood infrastructure at walking distance: Saint Louis Hospital ~200 m from the platform plus schools and a documented multi-faith cluster. *[`saint-louis-c03`, `saint-louis-c04`]*
- A genuine local food row (St. Louis Soi 3) with long-standing B40-70 vendors, distinct from tourist Silom. *[`saint-louis-c05`]*

## Trade-offs
- Nightlife 9 overstates the pocket: the sources describe a quiet, bar-scarce residential soi, with the nearest real bar clusters one or two stops away. *[`saint-louis-c06`]*
- No park inside the unit - Lumphini is ~1.4 km away across Rama IV - so green 7 rests entirely on buffer effects. *[`saint-louis-c07`]*

## Day / night
- Office-clock days (lunch carts, hospital shifts) give way to shophouse-step evenings; the soi goes quiet well before the Sathorn tower bars do. *[`saint-louis-c10`, `saint-louis-c06`]*

## Within-area variation
- The station frontage on Sathorn Road is office-block territory; one soi south toward Saint Louis Soi 2-3 the character flips to low-rise residential and food carts. *[`saint-louis-c01`, `saint-louis-c05`]*

## Conditional fit
- Strong fit: Sathorn/Silom office workers and hospital-adjacent households who want calm, walkable sois and BTS access without interchange crowds. *[`saint-louis-c09`, `saint-louis-c10`]*
- Poor fit: nightlife-first renters and park users - both 9s/7s in the scorecard trace to neighbouring units' amenities, not this pocket's. *[`saint-louis-c06`, `saint-louis-c07`]*

## Explicit unknowns
- Anchor mismatch: app anchor '@13.7273-ish' vs OSM station node 13.72082, 100.52669 - >=720 m apart; unit membership near the anchor is unreliable pending coordinator verification (saint-louis-c02).
- rating nightlife (9): no in-soi venue cluster found in any source; likely catchment-edge borrowing (saint-louis-c06).
- rating green (7): zero mapped park confirmed; mechanism inferred (saint-louis-c07).
- Rent comparison rests on 2019 listings plus 2026 highlight-level guides; no current portal median for this pocket (saint-louis-c08).
- 2024-2026 change evidence is thin - a gap, not a verified 'nothing happened'.

## Question coverage
- **Q01 — answered**: Single BTS infill station (S4, 2021-02-08) on the Sathorn corridor straddling Bang Rak/Sathon; NO station-anchor mismatch flag like this one elsewhere: the app anchor is >=720 m from the OSM node.
- **Q02 — answered**: Quiet soi-scale living around a hospital/church/school core, office-rhythm days, calm evenings and weekends.
- **Q03 — answered**: Values trace to concrete assets: a 2021 infill station, a hospital 180-260 m away, a documented soi-3 food row, and mid-band rents.
- **Q04 — answered**: Two counter-pairs: nightlife 9 vs 'not poppin'' pocket reality, and green 7 vs zero mapped parkland.
- **Q05 — answered**: Office-clock days, noon food carts, quiet evenings, calm weekend mornings.
- **Q06 — answered**: Walkable sois with heat/rain caveats; Sathorn Rd traffic notorious. No radius-to-time conversions used.
- **Q07 — answered**: Hospital at the door (~180-260 m), morning market on Soi Saint Louis 3, convenience stores along the sois (per 2026 guide, snippet-level).
- **Q08 — answered**: 25,500/55,000 plausible against 2019 listing brackets and 2026 guide bands; current portal medians for this exact pocket not obtained.
- **Q09 — answered**: Zero mapped park confirmed at the true station location; green 7 is a buffer/proximity effect, not in-unit parkland.
- **Q10 — answered**: Strong fit: Sathorn/Silom office workers wanting quiet sois and a hospital; poor fit: nightlife-seekers and park-users.
- **Q11 — answered**: Structuring change (station) is 2021; only incremental 2024-2026 findings (cafes, newer condos); Thai-language news search for this pocket not exhaustive.
- **Q12 — answered**: Biggest outside-the-score risk: the >=720 m anchor mismatch may relocate the whole unit; nightlife 9 and green 7 both look like buffer artifacts.

## Evidence base

| Source | Publisher (family) | Type | Published | Read |
| --- | --- | --- | --- | --- |
| [Queries: BTS stations within 3 km of 13.7273,100.5430; Saint Louis-named objects around…](https://overpass-api.de/api/interpreter) | OpenStreetMap via Overpass API (OpenStreetMap via Overpass API) | other | — | yes |
| [สถานีเซนต์หลุยส์ (Saint Louis station)](https://th.wikipedia.org/wiki/สถานีเซนต์หลุยส์) | Wikipedia (Thai) (Wikimedia) | other | — | yes |
| [Saint Louis Hospital (Bangkok)](https://en.wikipedia.org/wiki/Saint_Louis_Hospital) | Wikipedia (English) (Wikimedia) | other | — | yes |
| [Should you live in Sathorn's Soi St. Louis?](https://www.bkmagazine.com/city-living/should-you-live-sathorns-soi-st-louis/) | BK Magazine (expat_lifestyle_press) | editorial_guide | 2019-02-15 | yes |
| [Saint Louis BTS Condo Rentals in Quiet Sathorn](https://www.superagent.co/en/blog/saint-louis-bts-station-quiet-sathorn-pocket-rental-guide) | Superagent (real_estate_content) | other | 2026-04-22 | partial |
| [Living in Sathorn, Bangkok: Practical Neighborhood Guide](https://planwellabroad.com/articles/living-in-sathorn-bangkok) | Plan Well Abroad (expat_lifestyle_press) | editorial_guide | — | partial |
| [Living in Sathorn: Embassy Row, Quiet Sois and High-End Towers](https://www.thailandstarterkit.com/moving/living-in-sathorn/) | Thailand Starter Kit (expat_lifestyle_press) | editorial_guide | 2026-10-26 | partial |
| [Sathorn Area Guide 2026](https://roavara.com/sathorn-area-guide/) | Roavara (real_estate_content) | editorial_guide | 2026-08-18 | partial |
| [BTS Saint Louis, Saint Louis neighborhood](https://connex.in.th/en/content/bts-saint-louis) | Connex Property (real_estate_content) | editorial_guide | — | partial |

## Claim index

- `saint-louis-c01` **[corroborated·neutral·entire_unit]** BTS Saint Louis (S4, Silom Line) opened 8 February 2021 as Thailand's first infill station built on an already-operating line, elevated over Khlong Sathron where North Sathorn meets South Sathorn Road at the mouth of Soi Sathorn 11 (Saint Louis 3), in front of AIA Tower Sathorn; its footprint straddles khwaeng Silom (Bang Rak district) and khwaeng Yan Nawa (Sathon district). The ~900M THB build was co-funded by the BTS Grow infrastructure fund and the AIA group, which gained a direct connection into AIA Tower. It was renamed from the planned 'Suksawit' to match the Saint Louis neighbourhood and soi. _(scope: station_area — BTS Saint Louis (Sathorn Rd / Soi Sathorn 11))_
- `saint-louis-c02` **[proposed·tradeoff·entire_unit]** Major anchor mismatch: the brief's app anchor '@13.7273-ish' sits at least ~720 m north of the real station node (13.72082, 100.52669) - beyond the 300-700 m batch-4 pattern - so any unit-membership statement tied to the anchor latitude is unreliable. All distances in this file are computed from the OSM station node; the coordinator should re-check the app's anchor/polygon before trusting edge memberships. _(scope: station_area — BTS Saint Louis)_
- `saint-louis-c03` **[corroborated·strength·inside]** Saint Louis Hospital - founded 1898 by Bishop Vey beside the Saint Louis Church, Thailand's first Catholic hospital, in Sathon District - anchors the pocket and computes to ~180-260 m from the station node (OSM node 4402346390 / way 347919475), i.e. inside the station's catchment. The batch-2 note that the hospital is outside Bang Rak khet is a district-boundary fact (Sathon side), not an exclusion from this station unit. _(scope: building — Saint Louis Hospital)_
- `saint-louis-c04` **[corroborated·neutral·inside]** The ย่านเซนต์หลุยส์ identity is church-and-school anchored: Saint Louis Catholic Church at 23 South Sathorn Rd (OSM church ~336 m from the station), Saint Louis Suksa School and the Saint Louis Marie building nearby, plus a documented multi-faith mix (Jawa Mosque, historic Witsanu Hindu temple). _(scope: corridor — Saint Louis sois (South Sathorn))_
- `saint-louis-c05` **[corroborated·strength·inside]** The pocket's food reputation is a single-soi street-food row: St. Louis Soi 3 carries long-standing vendors - Khao Ka Moo Jorsor 100 (braised pork rice B50-70), Boon Eak braised duck, Khao Mok Gai Od Ton biryani (B40), Hea Ngou noodles, Lot Chong Singapore Pichit - plus a cluster of cafes (All Good in the Hood, Make Me Bread, Super Seoul Cafe) documented in 2019 and echoed by later guides. _(scope: venue — St. Louis Soi 3 / Sathorn Soi 11)_
- `saint-louis-c06` **[corroborated·tradeoff·entire_unit]** Counter-view to nightlife 9: every source describing the pocket itself calls it quiet - BK Magazine: 'might not be home to the most poppin' nightlife scene'; later guides: 'quieter and more residential', few bars, Sathorn 10-12 bars 'a quick ride away'. The 9 most plausibly borrows from the Sathorn/Silom edges of the catchment rather than the Saint Louis sois; no in-soi bar cluster was found. _(scope: corridor — Saint Louis sois)_
- `saint-louis-c07` **[corroborated·tradeoff·entire_unit]** Green 7 with a mapped 0.0 ha park is a pure buffer effect: no named public park exists within ~1.3 km of the true station node (OSM query within 1300 m returned none; Lumphini Park's SW corner computes to ~1.38 km NE, the Chaloem Phrakiat 80 Phansa park ~1.7 km S), matching the app's zero. A relocation guide states plainly that Sathorn has 'very little parkland... Lumphini Park is across Rama 4, not inside Sathorn'. The 7 therefore cannot reflect in-unit parkland - likely proximity green/street trees or a catchment-edge effect near the anchor. _(scope: station_area — Saint Louis pocket)_
- `saint-louis-c08` **[corroborated·neutral·entire_unit]** Affordability vs stated figures (25,500/55,000, Bang Rak blend): 2019 BK listings bracket the soi - The Room Sathorn-St. Louis B17,000-200,000 across 376 units, Mini House Apartment B33,000-35,000, Sky Villas Sathorn B40,000-250,000; a 2026 rental guide adds basic furnished 1-BRs in smaller buildings at B9,000-13,000 and notes the market is smaller than Chong Nonsi/Surasak. 25,500 is a plausible mid-band 1-BR; 55,000 implies a larger or newer tower unit. _(scope: corridor — Saint Louis / Sathorn)_
- `saint-louis-c09` **[corroborated·strength·entire_unit]** Transport 8's mechanism is a single-line infill station, not an interchange: S4 sits 610 m from Chong Nonsi and 570 m from Surasak (Thai Wikipedia; OSM node-to-node ~594 m to Surasak), one stop from either, on the elevated Sathorn corridor serving the office belt. _(scope: station_area — BTS Silom Line (Sathorn corridor))_
- `saint-louis-c10` **[corroborated·neutral·entire_unit]** Rhythm runs on the Sathorn office clock with a calmer weekend: lunch carts on Saint Louis Soi 3 and Sathorn Soi 11 fill with office workers around noon, streets are 'active on weekdays and noticeably calmer on weekend mornings', evenings are quiet, and hospital traffic around Saint Louis Hospital varies through the day. _(scope: corridor — Saint Louis / Sathorn)_
- `saint-louis-c11` **[corroborated·neutral·inside]** 2024-2026 changes specific to this pocket are thin: the structuring event (station opening) was Feb 2021, outside the window. What surfaces for 2024-2026 is increment - 'a few coffee cafes that have popped up along the soi in the past two years' (2026 rental guide) and newer mid-rise stock such as Centric Sathorn-St. Louis mapped on the soi - with no major infrastructure or land-use change found in this pass. _(scope: corridor — Saint Louis sois)_
- `saint-louis-c12` **[corroborated·neutral·entire_unit]** Walkability is soi-scale and conditional: guides describe tree-lined, low-traffic residential lanes where elderly residents sit outside shophouses, but flag that 'the exact street matters' - properties a block off Sathorn can end in uncomfortable walks in heat or rain - and Sathorn Road itself is 'notorious' at rush hour. _(scope: corridor — Saint Louis sois / Sathorn Rd)_

## Reviewer notes from the researcher
- Researcher self-checks only; independent review still required (batch review/findings.md).
- 3 claim(s) carry explicit recheck_by flags for volatile facts.
- open issue: Coordinator must reconcile the app anchor for st.saint-louis with the OSM station node (13.72082, 100.52669) and re-run polygon-dependent facts (hospital/park memberships) (saint-louis-c02).
- open issue: No current rent medians for the Saint Louis pocket from a raw-body portal source; BK's listings are 2019 vintage (saint-louis-c08).
- open issue: Thai-language coverage of ย่านเซนต์หลุยส์ beyond the station article was not searched in this pass - possible missing local sources.
