# Saphan Khwai (st.saphan-khwai) — research brief

**Derived view** of `profiles/st.saphan-khwai.json` (authoritative bundle), batch `zcode-main (ZCode orchestrator + 6 light-pass subagents), 2026-11-07` era output. Status: **ready_for_review** — not independently approved. Drafted in English only; no translations manufactured.

- **Unit:** Station area (nearest-stop catchment, Voronoi ∩ 800 m disc). Aliases: —
- **Scope:** Nearest-stop catchment (Voronoi ∩ 800 m) around saphan-khwai [bts_sukhumvit]; districts: phaya-thai, chatuchak. Boundary claims are decided by the app polygons (coordinator checks apply).
- **App score context:** model 7.6 (display rounded), cohort rank 15 of 133, snapshot `bkk-d6499618507e7561`. Public popularity: **unmeasured** — No citywide popularity measure has been collected. Tier B selection used within-cohort rank; coverage recorded opportunistically per bundle.
- **Selection rationale:** Tier B (light pass): station-area rank 15/133, score 7.6.

## Card preview (proposed)
> One BTS stop south of the market and one north of Ari: a fast, viaduct-shaded stretch of Phahonyothin where 175 restaurants and 149 cafés pack the sois, 39 bars trade past 9 pm, and a one-bed at M Jatujak rents for 18,000 baht — with almost no green space and streets that close earlier than the neighbourhoods to the south.

## Guide lead (proposed)
Saphan Khwai is the working corridor between Ari's cafe rows and the Chatuchak market edge: BTS N7 over a wide, fast Phahonyothin Road, Pradiphat Road as the dense food spine, Or Tor Kor market at the unit's north-west corner, and 39 bars still pouring past 9 pm. Rents run below the app's Phaya Thai blend at station-adjacent buildings (12,000-23,000 baht studios and one-beds captured), while the two-bed blend of 36,500 matches district ranges. The frictions: 'almost no green space' by the neighbourhood guide's own account, a road you can only cross at spaced points, early closing by southern-Bangkok standards, and a safety score with no unit-specific evidence behind it.

## Strengths
- Density of everyday food and drink: 175 restaurants and 149 cafés in the neighbourhood dataset, a named food spine on Pradiphat Road, and premium daily shopping at Or Tor Kor at the unit's edge. *[`saphan-khwai-c05`]*
- Value rents with boardable rush-hour trains: station-adjacent one-beds captured at 12,000-23,000 baht, below the district blend, and morning trains you can actually board. *[`saphan-khwai-c07`, `saphan-khwai-c10`]*

## Trade-offs
- The road dominates: wide, fast, viaduct-noisy, crossable only at spaced points, with no centre — 'an intersection, not a square'. *[`saphan-khwai-c04`]*
- Green and late hours are thin: 'almost no green space' (Chatuchak Park 'a trip, not a stroll'), closing earlier than Ari, and no park centroid within 850 m in OSM. *[`saphan-khwai-c08`, `saphan-khwai-c09`]*

## Day / night
- Mornings start before 7 am around the markets; evenings wind down by Ari's standards — 163 of 445 timed places still open at 9 pm, 39 bars past 9 pm, and post-midnight movement by taxi or motorbike taxi once BTS stops. *[`saphan-khwai-c09`, `saphan-khwai-c06`]*

## Within-area variation
- The west side (Pradiphat band, market approaches) carries the density; the east side beyond the railway is the quiet residential pocket (Saliratthawiphak), and the south fringe toward Ari holds most of the 2 am bars. *[`saphan-khwai-c02`, `saphan-khwai-c06`, `saphan-khwai-c11`]*

## Conditional fit
- Fit for value-seeking renters and food-first residents who accept road noise and early closing; the hostels and craft-beer arrivals suit a young, mobile crowd. *[`saphan-khwai-c05`, `saphan-khwai-c07`, `saphan-khwai-c11`]*
- Poor fit for green-space daily users and late-night rail commuters — the park is a trip, not a stroll, and the BTS stops before the last bars do. *[`saphan-khwai-c08`, `saphan-khwai-c09`]*

## Explicit unknowns
- Nightlife count basis: app 15 venues vs the neighbourhood dataset's 49 bars in a wider 1.2 km boundary — polygon decides (saphan-khwai-c06).
- The app's 0.7 ha mapped park has no identified OSM counterpart; green 6 may be generous (saphan-khwai-c08).
- Safety 8 has no unit-specific evidence in any read source (saphan-khwai-c11).
- App anchor 13.7914 vs OSM station node 13.79382 — reconcile as unit centroid vs node (saphan-khwai-c01).
- Primary station article is a flagged unsourced stub; ridership figure uncorroborated.

## Question coverage
- **Q01 — answered**: BTS N7 on Phahonyothin at the Saphan Khwai intersection, Phaya Thai/Chatuchak border; spelling split documented.
- **Q02 — answered**: Fast noisy artery + dense food spine; intersection without a square.
- **Q03 — answered**: High DE rides on 175 restaurants/149 cafés, Pradiphat food spine, local bar density and value rents.
- **Q04 — answered**: Counter-views: 'not the city's best nightlife' and 'almost no green space' cut against nightlife 8 and green 6 being taken at face value.
- **Q05 — answered**: Early markets, earlier closing than Ari/south; post-midnight life is taxi-dependent.
- **Q06 — answered**: 373/529 places within 800 m; crossing constraint; source-reported 10-12 min for 800 m (reported figure, not an agent conversion); no radius-to-time conversions by this agent.
- **Q07 — answered**: Parallel bus corridor, motorbike ranks, boardable rush-hour trains; services footprint explicitly not measurable per the neighbourhood dataset.
- **Q08 — answered**: Station-adjacent THB listings (12,000-23,000 for studios/1-beds) sit at or below the app's 18,000 blend; 36,500 two-bed blend matches the 25,000-40,000 range.
- **Q09 — answered**: Almost no green per the neighbourhood guide; no park centroid within 850 m in OSM; green 6 flagged as possibly generous; the 0.7 ha app parcel unidentified.
- **Q10 — answered**: Fit for value renters, food-first residents, hostel-traveller adjacency; poor fit for green-space seekers and late-night rail users.
- **Q11 — not_found**: No dated 2024-2026 openings/construction found in read sources; gentrification is a multi-year trend, not a dated event.
- **Q12 — answered**: Anchor/node mismatch; nightlife count basis differs (app 15 vs dataset 49-in-1.2 km); 0.7 ha park parcel unidentified; safety 8 unverified; station article is an unsourced stub.

## Evidence base

| Source | Publisher (family) | Type | Published | Read |
| --- | --- | --- | --- | --- |
| [Saphan Khwai BTS station](https://en.wikipedia.org/wiki/Saphan_Khwai_BTS_station) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Getting to and around Saphan Kwai](https://saphankwai.com/guides/getting-around/) | SaphanKwai.com (SaphanKwai.com) | editorial_guide | — | yes |
| [Living in Saphan Kwai](https://saphankwai.com/guides/moving-to-saphan-kwai/) | SaphanKwai.com (SaphanKwai.com) | editorial_guide | — | yes |
| [Late-night bars and pubs near BTS Saphan Khwai](https://saphankwai.com/bars/late-night) | SaphanKwai.com (SaphanKwai.com) | editorial_guide | — | yes |
| [Saphan Khwai, Bangkok: A Quick Guide](https://travelhappy.info/saphan-khwai-bangkok-a-quick-guide) | Travel Happy (Travel Happy) | editorial_guide | — | yes |
| [Condos for rent in Phaya Thai, Bangkok — HipFlat](https://www.hipflat.co.th/en/condo-for-rent/bangkok/phaya-thai) | HipFlat (HipFlat) | commercial_property | — | yes |
| [Phaya Thai Neighborhood Guide 2026](https://www.superagent.co/en/blog/phaya-thai-bangkok-complete-2026-expat-neighborhood-guide) | Superagent (Superagent) | expat_publication | 2026-05-04 | yes |
| [Or Tor Kor Market guide](https://saphankwai.com/guides/or-tor-kor-market/) | SaphanKwai.com (SaphanKwai.com) | editorial_guide | — | yes |
| [OpenStreetMap Overpass query: rail stations + parks/gardens within 800-850 m of Saphan …](https://overpass-api.de/api/interpreter) | OpenStreetMap (Overpass API) (OpenStreetMap) | other | — | yes |

## Claim index

- `saphan-khwai-c01` **[corroborated·neutral·inside]** BTS Saphan Khwai (N7) is an elevated Sukhumvit Line station opened 5 December 1999 on Phahonyothin Road at the Saphan Khwai intersection in Phaya Thai district (13.7938 N, 100.54973 E per the article; OSM node 13.79382, 100.54971), between Ari and Mo Chit, with 1,427,958 passengers in 2021. The station fronts Saphan Khwai market and Paolo Memorial Hospital, with a Big C supercenter and the Thai Philatelic Museum at the Sam Sen Nai post office to the south. The encyclopedic article carrying these facts is a flagged unsourced stub. _(scope: station_area — Saphan Khwai)_
- `saphan-khwai-c02` **[proposed·neutral·entire_unit]** Naming and scope: the BTS signage spells 'Saphan Khwai' while the neighbourhood commonly writes 'Saphan Kwai' — the same place; the neighbourhood is described as sitting on the Phaya Thai / Chatuchak border, defined by Phahonyothin Road, with a west side (dense Pradiphat Road band and market approaches) and a thinner residential east side beyond the railway. _(scope: station_area — Saphan Kwai)_
- `saphan-khwai-c03` **[proposed·mixed·entire_unit]** Walkability is real but directional: of 529 places in the neighbourhood dataset, 373 fall within 800 m straight-line of the station (the site treats that band as the walkable core, which it equates to roughly a 10-12 minute walk) and 60 within 400 m; but Phahonyothin Road's spaced crossings mean a place 150 m away across the road can take longer to reach than one 400 m on the same side — the site's rule is 'check which side of Phahonyothin you want before you set off'. All distances are straight-line; the site warns real walks are always longer. _(scope: station_area — Saphan Kwai)_
- `saphan-khwai-c04` **[proposed·tradeoff·entire_unit]** The corridor's defining downside is the road itself: a wide, fast, multi-lane artery whose BTS viaduct shades most of it and makes it noisy, with no centre — the site calls the station 'an intersection, not a square'. A major north-south bus corridor parallels the BTS ('much cheaper and much slower'), and motorbike-taxi ranks at soi mouths cover the awkward middle distance. _(scope: corridor — Phahonyothin Road at Saphan Khwai)_
- `saphan-khwai-c05` **[corroborated·strength·partial]** Food is the unit's engine: the neighbourhood dataset holds 175 restaurants and 149 coffee shops/cafés among its 529 places; Pradiphat Road west of the station is called 'the food spine — the densest run of small kitchens in the neighbourhood'; and the Aqua pedestrian courtyard between Phahonyothin Sois 14-16 clusters restaurants and cafés (Filete, Smiley Shrimp, Yakizen, Ansel & Elliott per the travel guide). At the unit's north-west edge sits Or Tor Kor market — described as Thailand's best-known fresh market, daily, covered, partly air-conditioned, premium-priced rather than cheap. _(scope: station_area — Saphan Kwai / Pradiphat / Or Tor Kor)_
- `saphan-khwai-c06` **[corroborated·mixed·partial]** Nightlife is denser than the 'gritty' label suggests but stays local-scale: 49 bars/pubs sit inside the 1.2 km dataset boundary, 39 of them open past 9 pm as of 2 August 2026 — closest AV Izakaya 128 m from the station (closes 1 am), Old Dirty in the south fringe 604 m away closing 2 am, with several 2 am venues (Honest Mistake Bar, Glur.bar, MOMO BAR). The travel guide's counter-view: it is 'not the city's best for nightlife', with gastropubs (Old Dirty live music, Brewix) plus a low-price, Thai-oriented go-go strip on Sutthisan Winitchai Road — a bar-hopping neighbourhood rather than a party district. _(scope: station_area — Saphan Kwai nightlife)_
- `saphan-khwai-c07` **[corroborated·strength·partial]** Rents match the unit's value positioning: HipFlat's Phaya Thai district averages (2,253 condo listings, October data) run USD 474 studio / USD 652 one-bedroom / USD 1,037 two-bedroom, while THB-denominated listings near this station go lower — M Jatujak (Soi Phahonyothin 18, ~400 m to BTS Saphan Khwai) at 18,000-19,000 baht for 29-33 sqm one-beds, Vela De Residence 12,000 baht (24 sqm), Rhythm Phahol-Ari 18,000-23,000 baht. A May 2026 expat guide puts studio/one-bed starts at 12,000-18,000 baht and newer-pool-gym one-beds at 15,000-22,000, two-beds 25,000-40,000. The app's 18,000/36,500 Phaya Thai blend sits inside these ranges. _(scope: district — Phaya Thai district)_
- `saphan-khwai-c08` **[corroborated·tradeoff·entire_unit]** Green is the unit's weakest card and the app's green 6 looks generous against the evidence: the neighbourhood guide states there is 'almost no green space; Chatuchak Park is a trip, not a stroll', and the Overpass search found no leisure=park centroid within 850 m of the station node — only condominium gardens and two small dog parks toward the Kamphaeng Phet side. The app maps just 0.7 ha of park inside the unit. _(scope: station_area — Saphan Kwai green space)_
- `saphan-khwai-c09` **[proposed·mixed·entire_unit]** Daily rhythm runs early and closes earlier than areas to the south: 51 of 445 places with published hours open before 7 am (concentrated around the markets), 163 still trade at 9 pm, 374 open Sundays, and the guide notes the neighbourhood 'closes earlier than Ari and southern areas'; BTS stops before midnight, so the 81 places open at 11 pm are reached by taxi or motorbike taxi, not rail. _(scope: station_area — Saphan Kwai)_
- `saphan-khwai-c10` **[corroborated·neutral·entire_unit]** Crowding is moderate by north-Bangkok standards and the transport experience is livable at peak: the guide says you can board trains in the morning rush here 'unlike further south', and the station's 2021 ridership (1.43 million) is roughly a quarter of Mo Chit's (5.17 million) a stop north — consistent with a busy local corridor rather than a hub crush. No source quantifies street-level crowding for this unit specifically. _(scope: station_area — Saphan Khwai / Mo Chit corridor)_
- `saphan-khwai-c11` **[corroborated·mixed·entire_unit]** Gentrification is the observed 2020s trend and the honest gaps are safety and recent change: the travel guide describes a neighbourhood 'gentrifying quickly' but still 'gritty, industrial', with craft-beer bars arriving among old shophouses and a hostel cluster (Everyday Sunday, Adventure Hostel by the BTS, KENCOZY, Buff), and the neighbourhood guide's verdict is to live in a soi off western Pradiphat Road with the quietest pocket east of the railway on Saliratthawiphak. No read source addresses crime or safety for this unit (app safety 8 is unverified), and no 2024-2026 construction or opening was found in read sources — the strongest dated signal is the guide dataset's August 2026 snapshot. _(scope: station_area — Saphan Kwai)_

## Reviewer notes from the researcher
- Researcher self-checks only; independent review still required (batch review/findings.md).
- 6 claim(s) carry explicit recheck_by flags for volatile facts.
- open issue: Reconcile app's 15 nightlife venues with SaphanKwai.com's 49-bar (1.2 km) dataset once polygons are applied (saphan-khwai-c06).
- open issue: Identify the 0.7 ha mapped park parcel; OSM shows no named public park within 850 m of the station node (saphan-khwai-c08).
- open issue: Safety 8 unverified — needs either local-crime data or an explicit 'perception, not documented' label.
- open issue: No resident-report sources accessible (Reddit/TripAdvisor 403 per brief); lived-experience claims rest on two editorial guides with different voices.
- open issue: Station article is an unsourced stub — ridership and surroundings would benefit from a BTS official page cross-check.
