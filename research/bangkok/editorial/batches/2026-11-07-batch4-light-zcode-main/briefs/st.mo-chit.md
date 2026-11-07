# Mo Chit / Chatuchak Park (st.mo-chit) — research brief

**Derived view** of `profiles/st.mo-chit.json` (authoritative bundle), batch `zcode-main (ZCode orchestrator + 6 light-pass subagents), 2026-11-07` era output. Status: **ready_for_review** — not independently approved. Drafted in English only; no translations manufactured.

- **Unit:** Station area (nearest-stop catchment, Voronoi ∩ 800 m disc). Aliases: —
- **Scope:** Nearest-stop catchment (Voronoi ∩ 800 m) around mo-chit/chatuchak-park [bts_sukhumvit/mrt_blue]; districts: chatuchak. Boundary claims are decided by the app polygons (coordinator checks apply).
- **App score context:** model 7.56 (display rounded), cohort rank 16 of 133, snapshot `bkk-d6499618507e7561`. Public popularity: **unmeasured** — No citywide popularity measure has been collected. Tier B selection used within-cohort rank; coverage recorded opportunistically per bundle.
- **Selection rationale:** Tier B (light pass): station-area rank 16/133, score 7.56.

## Card preview (proposed)
> Two stations in one green pocket: BTS Mo Chit above Phahonyothin, MRT Chatuchak Park beneath the lake-side park, and the weekend market's 15,000 stalls next door — with district rents averaging mid-market and a 2025 redevelopment fight still reshaping the market's clock-tower end.

## Guide lead (proposed)
Mo Chit is the merged BTS N8 / MRT BL13 interchange on Chatuchak district's southern edge — one node, two systems, a street-level transfer, and the largest weekend market in the world (200,000+ weekend visitors, 35 acres) between them. The green 10 rests on the Chatuchak / Queen Sirikit / Rot Fai park run at the unit's edge (30.4 + ~22 + 60 ha in total, though the app maps only 62.8 ha inside the polygon), and rents track the district's mid-market blend of 16,000-33,000 baht. The frictions are real: an unpaid-area transfer, weekend crowds, a market half-way through a contested renovation, and no unit-specific safety evidence either way.

## Strengths
- A single merged interchange (BTS N8 + MRT BL13, ~70 m apart) with all four MRT exits wired to the BTS side, a park-and-ride lot, and bus bays off exits 3 and 4. *[`mo-chit-c01`, `mo-chit-c08`]*
- The Chatuchak / Queen Sirikit park block sits ~0.5-0.6 km from the station node, with 30.4 ha and ~22 ha components verified, plus the market's 200,000-strong weekend economy at the door. *[`mo-chit-c03`, `mo-chit-c04`, `mo-chit-c05`]*

## Trade-offs
- The interchange is outside the paid area and the market's weekend surge (200,000+ visitors) transforms the unit's streets twice a week; the 2025 clock-tower eviction of 529 stallholders signals more churn to come. *[`mo-chit-c02`, `mo-chit-c05`, `mo-chit-c06`]*
- Rent evidence is district-level only (studio USD 446 / 1BR USD 565 / 2BR USD 984, October 2026) and is dragged by Lat Phrao-corridor condominiums; no station-adjacent listing was captured to confirm the 16,000/33,000 blend at the doorstep. *[`mo-chit-c07`]*

## Day / night
- Days split between weekday park-and-commute calm and weekend market gridlock; after dark the unit is quiet by most accounts, with the market's Friday-night wholesale operation the main late activity (schedule snippet-corroborated only). *[`mo-chit-c10`]*

## Within-area variation
- The park-facing western edge (MRT exits 1-2, lake, botanical garden) and the market-facing northern blocks are different worlds from the Phahonyothin commuter strip at the BTS viaduct; Rot Fai Park's bulk lies beyond the catchment's northern reach. *[`mo-chit-c03`, `mo-chit-c04`]*

## Conditional fit
- Fit for weekend-market regulars, park exercisers and two-line commuters who accept a street-level, separate-ticket transfer. *[`mo-chit-c02`, `mo-chit-c03`, `mo-chit-c05`]*
- Poor fit for anyone needing quiet Saturdays, a single-ticket transfer, or guaranteed rent parity with station-adjacent buildings — the rent evidence is district-wide. *[`mo-chit-c05`, `mo-chit-c07`]*

## Explicit unknowns
- App's 62.8 ha park figure vs the 112.8 ha sum of the three verified park components — polygon clipping decides which parts are in-unit (mo-chit-c03).
- App anchor 13.7999 sits ~300 m from the OSM BTS node 13.8026; coordinates should be reconciled by the coordinator (mo-chit-c01).
- Safety 7 and crowd 5 have no unit-specific source found in either direction (mo-chit-c11).
- Wednesday/Thursday plant days and Friday-night wholesale hours rest on search summaries, not a read body (mo-chit-c10).

## Question coverage
- **Q01 — answered**: BTS N8 (1999) above Phahonyothin + MRT BL13 (2004, formerly 'Mo Chit') under the park, ~70 m apart, Chatuchak district; merged unit is justified.
- **Q02 — answered**: Weekend-market gravity + park calm + one of the city's biggest transit interchanges; street-level, unpaid-area transfer.
- **Q03 — answered**: Values trace to the park complex (green), the market (food/shopping/rhythm) and mid-market district rents.
- **Q04 — answered**: Counter-evidence: vendor eviction conflict, review complaints, no support for safety/crowd scores found.
- **Q05 — answered**: Weekend surge vs weekday park/residential quiet; Friday-night extension snippet-level.
- **Q06 — answered**: Straight-line geometry only (70 m to MRT; parks 0.5-0.6 km); no radius-to-time conversions performed.
- **Q07 — answered**: Daily life anchored on the interchange plus bus stops at exits 3-4; regional bus gateway sits ~2 km away, outside the unit.
- **Q08 — answered**: HipFlat Oct-2026 district data consistent with the 16,000/33,000 Chatuchak blend; district-average caveat stated.
- **Q09 — answered**: Named in-polygon candidates: Chatuchak Park (MRT beneath it), Queen Sirikit Park centroid ~510 m; Rot Fai center ~1.1 km = partial. App's 62.8 ha is below the 112.8 ha component sum — polygon clips the complex.
- **Q10 — answered**: Best for market-goers, park users and budget-conscious commuters; worst for quiet weekends and for anyone wanting a single-ticket interchange.
- **Q11 — answered**: 2025 clock-tower eviction/redevelopment; possible regional-bus consolidation at Krung Thep Aphiwat under consideration.
- **Q12 — answered**: App anchor (13.7999) vs OSM station node (13.8026) mismatch; 62.8 ha vs 112.8 ha park sum; safety/crowd scores unverified; vendor-side sourcing thin.

## Evidence base

| Source | Publisher (family) | Type | Published | Read |
| --- | --- | --- | --- | --- |
| [Mo Chit BTS station](https://en.wikipedia.org/wiki/Mo_Chit_BTS_station) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [สถานีสวนจตุจักร (MRT Chatuchak Park)](https://th.wikipedia.org/wiki/สถานีสวนจตุจักร) | Wikipedia (Thai) (Wikipedia) | other | — | yes |
| [Chatuchak Park](https://en.wikipedia.org/wiki/Chatuchak_Park) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Wachirabenchat Park (Rot Fai Park)](https://en.wikipedia.org/wiki/Wachirabenchathat_Park) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Queen Sirikit Park](https://en.wikipedia.org/wiki/Queen_Sirikit_Park) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Chatuchak Market official-ish info site](https://www.chatuchakmarket.org) | chatuchakmarket.org (chatuchakmarket.org) | tourism_publisher | — | yes |
| [Condos for rent in Chatuchak, Bangkok — HipFlat](https://www.hipflat.com/condo-for-rent/bangkok/chatuchak) | HipFlat (HipFlat) | commercial_property | — | yes |
| [Time's up: Stallholders at Chatuchak weekend market told to leave](https://thethaiger.com/news/bangkok/times-up-stallholders-at-chatuchak-weekend-market-told-to-leave) | The Thaiger (Thaiger) | news | 2025-02-19 | yes |
| [Hundreds of vendors at Chatuchak market given deadline to move](https://www.bangkokpost.com/thailand/general/2964115/hundreds-of-vendors-at-chatuchak-market-given-deadline-to-move) | Bangkok Post (Bangkok Post) | news | 2025-02-19 | yes |
| [Mo Chit 2 bus terminal (Bangkok Bus Terminal, Chatuchak)](https://en.wikipedia.org/wiki/Mo_Chit_2_bus_terminal) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [OpenStreetMap Overpass query: rail stations + parks/gardens within 800-850 m of Mo Chit…](https://overpass-api.de/api/interpreter) | OpenStreetMap (Overpass API) (OpenStreetMap) | other | — | yes |

## Claim index

- `mo-chit-c01` **[proposed·neutral·inside]** The unit's two rail stops: BTS Mo Chit (N8), elevated above Phahonyothin Road between Soi Phahon Yothin 18 and 20 in Chatuchak district, opened 5 December 1999 on the Sukhumvit Line, with 5,166,915 passengers in 2021 (13.8025833 N, 100.5538333 E); and MRT Chatuchak Park (BL13), underground beneath the southern part of Chatuchak Park on the west side of Phahonyothin Road, opened 3 July 2004 under its former name 'Mo Chit', with 6,865,636 passengers in 2021. The BTS stop was the Sukhumvit Line's northern terminus until Ha Yaek Lat Phrao opened on 9 August 2019. _(scope: station_area — Mo Chit / Chatuchak Park)_
- `mo-chit-c02` **[corroborated·neutral·entire_unit]** The two stops are one interchange area: OpenStreetMap tags the BTS Mo Chit node (13.80260, 100.55379) and the MRT Chatuchak Park node (13.80296, 100.55328) roughly 70 m apart in straight line (agent-computed), and the English Wikipedia article states the BTS station sits directly above the MRT station with the interchange made at street level outside the paid area. A search-engine summary claiming Chatuchak Park is 'BL12' was tool inference and is contradicted by the body reads: BEM's own site and English Wikipedia give BL12 to Kamphaeng Phet, Thai Wikipedia and OSM give BL13 to Chatuchak Park. _(scope: station_area — Mo Chit / Chatuchak Park interchange)_
- `mo-chit-c03` **[proposed·strength·partial]** The green complex this unit borders consists of three adjoining parks: Chatuchak Park, 0.304 sq km (30.4 ha, ~190 rai), opened 1975 on former State Railway land with a long artificial lake and the MRT line running beneath it; Queen Sirikit Park, 0.22 sq km (~22 ha / 140 rai), a botanical garden established 1992 and formally opened December 1996 with over 2,000 plant species; and Wachirabenchat (Rot Fai) Park, 375 rai (60.0 ha), created 2002 from a State Railway golf course with a roughly 3 km walking/cycling loop. The parks are separated from one another by Kamphaeng Phet 3 Road. _(scope: station_area — Chatuchak / Queen Sirikit / Wachirabenchat parks)_
- `mo-chit-c04` **[proposed·strength·partial]** Agent-computed straight-line distances from the BTS Mo Chit node place the green complex close at hand: Queen Sirikit Park's centroid about 510 m and Chatuchak Park's centroid about 640 m away, both well inside an 800 m catchment, while Wachirabenchat Park's centroid is about 1.1 km to the north (its polygon edge comes nearer; the Overpass radius search still caught the way). The park block therefore reads as genuinely in- or directly adjoining this unit, with Rot Fai the farthest component. _(scope: station_area — Chatuchak park complex)_
- `mo-chit-c05` **[conflicted·strength·partial]** Chatuchak Weekend Market, which occupies the blocks north-west of the stations, is described by its visitor site as the largest weekend market in the world: about 35 acres, divided into 26-27 sections, with a paragraph claiming more than 15,000 stalls (the same page's intro says 8,000+ — the site contradicts itself) and more than 200,000 people visiting each weekend. The market office's 2025 figures put permanent stall fees at 1,800 baht/month (green stalls 1,400; plant stalls 900) on land owned by the State Railway of Thailand, for which the BMA pays 169 million baht a year. _(scope: venue — Chatuchak Weekend Market)_
- `mo-chit-c06` **[corroborated·tradeoff·partial]** The market is being reorganised: in February 2025 City Hall told 529 stallholders around the clock tower to move out by 30 April 2025 so the zone could be redeveloped as a new tourist-drawing landmark, saying the vending area's walkways had narrowed from 19 m to 9 m. Only about 15 vendors accepted offered alternative stalls (fee waived), 122 were in rent arrears facing contract cancellation, and vendors had petitioned the Prime Minister and the Bangkok governor over the market office's management. _(scope: venue — Chatuchak Weekend Market clock-tower zone)_
- `mo-chit-c07` **[proposed·strength·partial]** Rents around the unit sit at mid-market for inner-north Bangkok: HipFlat's Chatuchak district averages (October 2026, 4,537 rental listings) are USD 446 for studios, USD 565 for 1-bedrooms and USD 984 for 2-bedrooms, with THB-denominated listings on the page running 16,000-25,000 baht for studios and small 1-beds (e.g. The Saint Residences 16,000; Life Ladprao 21,000-25,000). This is consistent with the app's 16,000/33,000 Chatuchak blend, though the district average is pulled down/north by Lat Phrao-corridor condominiums and no captured listing sat at Mo Chit station itself. _(scope: district — Chatuchak district)_
- `mo-chit-c08` **[proposed·strength·inside]** Day-to-day interchange mechanics: all four exits of MRT Chatuchak Park connect to BTS Mo Chit via the ground level/B1 underpass network (the line runs beneath the park and the BTS sits above Phahonyothin Road), the station has a large park-and-ride lot, and Exit 3 faces the bus stops toward Kamphaeng Phet Road and the Chatuchak bus terminal while Exit 4 faces buses toward Saphan Khwai and the Department of Land Transport. _(scope: station_area — Chatuchak Park MRT / BTS Mo Chit)_
- `mo-chit-c09` **[conflicted·neutral·outside]** The long-distance bus gateway associated with 'Mo Chit' is not in this catchment: Mo Chit 2 (officially Bangkok Bus Terminal, Chatuchak) sits at 999 Kamphaeng Phet 2 Road behind Queen Sirikit Park, roughly 2 km from the BTS/MRT stations per the terminal's article, serving northern and northeastern provinces. In 2025 the Transport Ministry was reported to be weighing consolidation of Bangkok's three long-distance terminals at Krung Thep Aphiwat Central Terminal, which would remove this regional-bus role from the area if it proceeds. _(scope: other — Mo Chit 2 bus terminal)_
- `mo-chit-c10` **[corroborated·mixed·entire_unit]** The unit's rhythm is market-driven: on Saturdays and Sundays the market draws 200,000+ visitors into the blocks between the two stations, while the park complex and residential streets carry the weekdays; Wednesday-Thursday plant-section days and a Friday-night wholesale/night operation extend the surge beyond the pure weekend (the weekday/night schedule appears in secondary guides and should be re-verified against the market office). The station pair's own baseline (5.2M + 6.9M riders in 2021) marks it as one of northern Bangkok's biggest daily nodes. _(scope: station_area — Mo Chit / Chatuchak)_
- `mo-chit-c11` **[corroborated·tradeoff·partial]** Counter-view and gaps: the market's own visitor-review aggregate surfaces complaints worth carrying into copy — limited halal options, variable vendor friendliness, and a maze layout needing comfortable shoes and water — and the 2025 eviction/redevelopment is an open wound with the vendor community. Nothing read supports or refutes a safety-7 for this specific unit (no crime or incident data found), and 'crowd 5' has no unit-specific measurement behind it in any read source; both stay as app values with research finding neither corroboration nor contradiction. _(scope: venue — Chatuchak Weekend Market / Mo Chit unit)_

## Reviewer notes from the researcher
- Researcher self-checks only; independent review still required (batch review/findings.md).
- 6 claim(s) carry explicit recheck_by flags for volatile facts.
- open issue: Park-area mismatch: app says 62.8 ha in-unit; verified components total ~112.8 ha (30.4 + 22 + 60). Needs the app polygon to name exactly which park parts are inside (mo-chit-c03/c04).
- open issue: Chatuchak Park MRT's station code: body reads (Thai Wikipedia, OSM, BEM line map) give BL13; a search-engine summary claimed BL12. App station_ids must be checked against BL13 (mo-chit-c02).
- open issue: Vendor-side account of the 2025 market eviction exists mainly as a social post; a readable news piece with vendor quotes would strengthen mo-chit-c06.
- open issue: No accessible resident-report sources (Reddit/TripAdvisor 403 per brief) — lived-experience claims lean on editorial guides and review aggregates.
