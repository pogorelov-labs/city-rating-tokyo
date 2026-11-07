# Siam (st.siam) — research brief

**Derived view** of `profiles/st.siam.json` (authoritative bundle), batch `zcode-main (ZCode orchestrator + 6 light-pass subagents), 2026-11-07` era output. Status: **ready_for_review** — not independently approved. Drafted in English only; no translations manufactured.

- **Unit:** Station area (nearest-stop catchment, Voronoi ∩ 800 m disc). Aliases: —
- **Scope:** Nearest-stop catchment (Voronoi ∩ 800 m) around siam [bts_sukhumvit/bts_silom]; districts: pathum-wan, ratchathewi. Boundary claims are decided by the app polygons (coordinator checks apply).
- **App score context:** model 7.56 (display rounded), cohort rank 17 of 133, snapshot `bkk-d6499618507e7561`. Public popularity: **unmeasured** — No citywide popularity measure has been collected. Tier B selection used within-cohort rank; coverage recorded opportunistically per bundle.
- **Selection rationale:** Tier B (light pass): station-area rank 17/133, score 7.56.

## Card preview (proposed)
> The two-line interchange at the heart of Bangkok's mall country: 676 food spots, a Chula-owned square of 4,200 shops, and a crowd score that bottoms out because ~400,000 people a day agree about the location.

## Guide lead (proposed)
Siam is where Bangkok's rail map and its retail map fold into each other: the only cross-platform interchange on the network sits under a district of four mega-malls and a university-owned square of small shops, street food and tutoring schools. The scores read like a glowing report card with one asterisk - everything is 9-10 except rent (1) and crowd (1), and the same footfall that fills the food courts is what empties the quiet.

## Strengths
- Transport and daily-essentials depth that few city units can match: a cross-platform interchange of both BTS lines wired by skybridge into Paragon, Center, Discovery, CentralWorld and MBK, with food from 40-stall food courts to evening street grills. *[`siam-c01`, `siam-c02`, `siam-c06`]*
- A non-mall half with its own economy: Siam Square's 4,200+ Chula-owned shops, tutoring cluster and wallet-friendly boutiques give the unit a small-shop layer the malls do not. *[`siam-c03`, `siam-c09`]*

## Trade-offs
- Crowd=1 is earned, not stylistic: ~400,000 daily through the square, weekend crushes, and incident history (2023 Paragon shooting, 2010 deaths by Wat Pathum) that shapes the safety score's ceiling. *[`siam-c08`, `siam-c10`]*
- Rent=1 with no relief valve inside the unit: the app's own 37,000/82,500 blend sits below brokerage asking averages (1BR 46,800; 2BR 99,600), so the true cost of living here is at least as steep as the score implies. *[`siam-c07`]*
- The green score rests on composite small polygons (Pathumwananurak, Park @ Siam, temple green) rather than a flagship park; the 6.0 ha figure cannot yet be tied to named ground. *[`siam-c05`]*

## Day / night
- Days run on mall hours (roughly 10:00-22:00) with a weekday commute spike through the interchange; evenings shift to food - street grills outside CentralWorld from ~17:00, square sois and food courts - while the crash arrives with the last trains; the square itself goes quietest on early Sunday mornings. *[`siam-c11`, `siam-c08`]*

## Within-area variation
- Three textures in one unit: the air-conditioned skywalk-and-mall layer, the Soi-level Siam Square grid (cheap food, tutoring, boutiques), and the monastery-green pocket of Wat Pathum Wanaram wedged between Paragon and CentralWorld - plus the unresolved Voronoi seam where CentralWorld could tip into the chit-lom unit. *[`siam-c02`, `siam-c03`, `siam-c04`]*

## Conditional fit
- Fit for people whose week runs on the malls and the interchange: students in the tutoring cluster, retail/office workers, car-free food-driven households who accept weekend crush as the price. *[`siam-c03`, `siam-c01`, `siam-c08`]*
- Poor fit for quiet-seeking residents or anyone renting against a budget: crowd=1, rent=1, and a unit where even the green is walk-through rather than a park you settle into. *[`siam-c08`, `siam-c07`, `siam-c05`]*

## Explicit unknowns
- 6.0 ha park figure unresolved against OSM polygons (siam-c05) - coordinator clip decides.
- CentralWorld (and possibly Pathumwananurak) straddles the siam/chit-lom Voronoi seam (siam-c02).
- Safety=7 and crowd=1 have no unit-level quantitative source in either direction for 2024-2026.
- Paragon BTS-connector reopening date after Oct 2023 not published in sources used.
- Rent figures compare an app district_blend to brokerage ASKING averages - bases differ (siam-c07).

## Question coverage
- **Q01 — answered**: Identity: CEN cross-platform interchange of both BTS lines inside the Siam-Ratchaprasong retail core; Siam Square (Chula-owned) is the non-mall half. CentralWorld membership between siam/chit-lom cells is the one open scope question.
- **Q02 — answered**: Everyday experience = dense retail, food at every price point, sustained crowds peaking weekends/evenings.
- **Q03 — answered**: Mechanisms: two-line interchange drives transport=10; mall + square density drives food/DE/vibe=10; the same density drives crowd=1.
- **Q04 — answered**: Counter-evidence: chain homogenization and cinema-site churn; incident history (2023 shooting, 2010 deaths) qualifies safety=7.
- **Q05 — answered**: Rhythm: weekday commute peaks, weekend shopper crush, evening food/shrine window, mall-hours frame 10:00-22:00.
- **Q06 — answered**: Walkability: continuous skywalk net (station-M floor; square to MBK/Paragon/Center/Discovery/CentralWorld). Straight-line distances only; no radius-to-time conversions performed.
- **Q07 — answered**: Daily life: Paragon/MBK food centers and supermarkets, square sois for cheap eats and tutoring; daily-needs depth is the mall system itself.
- **Q08 — answered**: Rent=1 justified by district data; app blend (37,000/82,500) is actually below FazWaz district asking averages (1BR 46,800; 2BR 99,600) - rent=1 is cohort-relative, not an absolute-ceiling claim.
- **Q09 — answered**: Green=9 with 6.0 ha cannot be tied to a named public park; best candidates are Pathumwananurak (BMA) + Park @ Siam (CU) + untagged temple green. Quiet pockets: Wat Pathum Wanaram grounds. Polygon clip needed.
- **Q10 — answered**: Fit: car-free shoppers, students/tutees, food-driven visitors; poor fit for crowd-averse or quiet-seeking residents.
- **Q11 — answered**: 2024-2026: Paragon shooting aftermath (2023), square churn, One Bangkok opened elsewhere (Lumphini khwaeng). No Siam-specific 2024-2026 public-works list found.
- **Q12 — answered**: Outside-the-score: Scala-site redevelopment direction, Siam Piwat/Central rivalry capex, footfall trend post-2023 - none scored, none found in this pass.

## Evidence base

| Source | Publisher (family) | Type | Published | Read |
| --- | --- | --- | --- | --- |
| [Siam BTS station](https://en.wikipedia.org/wiki/Siam_station) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Siam Square](https://en.wikipedia.org/wiki/Siam_Square) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Siam Paragon](https://en.wikipedia.org/wiki/Siam_Paragon) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [MBK Center](https://en.wikipedia.org/wiki/MBK_Center) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [CentralWorld](https://en.wikipedia.org/wiki/CentralWorld) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Wat Pathum Wanaram](https://en.wikipedia.org/wiki/Wat_Pathum_Wanaram) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [OpenStreetMap elements: stations, ferry terminals, piers, parks](https://overpass-api.de/api/interpreter) | OpenStreetMap contributors via Overpass API (OpenStreetMap) | other | — | yes |
| [Siam and Pratunam Bangkok (food/travel guide)](https://migrationology.com/siam-square-pratunam-bangkok) | Migrationology (Mark Wiens) (personal_blog) | other | — | yes |
| [Property for rent in Pathum Wan (FazWaz)](https://www.fazwaz.com/property-for-rent/thailand/bangkok/pathum-wan) | FazWaz (fazwaz) | other | — | yes |

## Claim index

- `siam-c01` **[corroborated·strength·entire_unit]** BTS Siam (code CEN) opened 5 December 1999 and is the network's cross-platform interchange where the Sukhumvit and Silom lines meet; it is one of only four BTS stations with island platforms and the only one on the Silom line. Wikipedia reports 6,160,924 passengers in 2021 and a claimed 40,000-50,000 daily. The station node (13.74562, 100.53422) matches the app's unit center exactly. _(scope: station_area — BTS Siam station, Rama I Road, Pathum Wan)_
- `siam-c02` **[proposed·neutral·partial]** The unit sits on top of the Siam-Ratchaprasong retail core: Siam Paragon (opened 9 Dec 2005, ~400,000 m2 retail, skybridge from the BTS M floor, on former Sa Pathum Palace royal parkland), Siam Center and Siam Discovery, MBK Center (7 Feb 1985; ~2,000 shops; at the Rama I x Phaya Thai corner), and CentralWorld (self-described ninth-largest shopping centre worldwide, 550,000 m2 of mall). CentralWorld is served by BOTH Siam and Chit Lom stations, so which malls fall inside this unit's polygon versus the chit-lom unit is a coordinator-level polygon decision; by straight-line distance all of the above are within the 800 m catchment. _(scope: district — Siam-Ratchaprasong retail core, Pathum Wan)_
- `siam-c03` **[proposed·strength·inside]** Siam Square itself is a Chulalongkorn University-owned grid of numbered sois first developed in 1962-63 (first building finished 1963), managed by Chula Property, with over 4,200 shops and an stated ~400,000 people passing through daily; tutoring schools have clustered there since 1991, making it one of the country's densest tutoring districts. It is connected by skywalk to MBK, Siam Paragon, Siam Center, Siam Discovery and CentralWorld. _(scope: station_area — Siam Square (between Phaya Thai Rd and Rama I Rd))_
- `siam-c04` **[proposed·neutral·inside]** Wat Pathum Wanaram, a third-class royal temple of the Thammayut order founded in 1857 by King Mongkut (Rama IV), sits between Siam Paragon and CentralWorld and across the street from Siam Square - a monastery block inside the retail core. During the 2010 crackdown it served as a safe zone for injured people, and on 19 May 2010 six people were killed by shots fired from outside the temple. _(scope: venue — Wat Pathum Wanaram, Rama I Road)_
- `siam-c05` **[proposed·neutral·partial]** Green inventory is small and composite: OSM shows only two park polygons plausibly inside the unit - 'Park @ Siam' (a Chulalongkorn University Property-managed pocket park, 308 m straight-line from the app center) and Pathumwananurak Park (BMA park in front of CentralWorld, 590 m; 695 m from Chit Lom station, so closer to Siam in nearest-stop terms). The app reports 6.0 ha of park in-unit; no single large public park accounts for that figure, and the de-facto green of the Wat Pathum Wanaram grounds is not tagged as a park in OSM. Composition of the 6.0 ha is unresolved. _(scope: station_area — Pathumwananurak Park + Park @ Siam (candidate polygons))_
- `siam-c06` **[proposed·strength·entire_unit]** The food count (app: 676 food, 98 cafes, 36 nightlife - the densest cluster in this batch) is qualitatively corroborated: Siam Paragon's ground-floor restaurants and large food center, MBK's 40-stall food court on the 6th floor, the awarded Som Tam Nua in Siam Square, and evening street food (grilled snakehead, som tam) outside CentralWorld from about 17:00. _(scope: district — Siam retail core)_
- `siam-c07` **[proposed·neutral·entire_unit]** The app's rent blend (37,000/82,500 THB, Pathum Wan district_blend as of 2026-09) sits below brokerage asking averages for the same district: FazWaz lists 3,242 Pathum Wan rentals with a median of 55,400/month, 1-bedroom average 46,800 (n=1,359) and 2-bedroom average 99,600 (n=1,114). _(scope: district — Pathum Wan district)_
- `siam-c08` **[corroborated·tradeoff·entire_unit]** Crowd=1 (worst cohort score) matches reported experience: Siam Square's own page claims ~400,000 people pass through daily; the food guide describes the area as crowded and bustling throughout and likens nearby Platinum Mall to 'an ant hill'; Thai-language review snippets describe a packed Siam on a Saturday evening. The crush concentrates on weekends, holidays and evenings. _(scope: district — Siam Square / Siam malls)_
- `siam-c09` **[proposed·tradeoff·inside]** Counter-view to the retail-monster image: the core is chain-mall dominated and its independent layer is under churn. The Siam cinema burned in the 2010 crackdown and was replaced by the Siam Square One development; the Scala cinema closed in mid-2020 and was demolished by Chulalongkorn University by 2021, its site reportedly still empty as of 2023; Lido became the Lido Connect venue after a 2018 closure. MBK, the area's budget anchor, drew half of its 100,000+ daily visitors from young Thais in 2009 - a mass-market base rather than a luxury one. _(scope: station_area — Siam Square cinemas and MBK)_
- `siam-c10` **[proposed·tradeoff·inside]** Safety=7 has concrete incident history in-unit: on 3 October 2023 a 14-year-old shooter opened fire on Siam Paragon's first floor, killing two people (a Burmese migrant worker and a Chinese tourist) and injuring five others; the mall and its BTS connector entrance were temporarily closed. The 2010 deaths by Wat Pathum Wanaram (six killed 19 May 2010) fall in the same unit. _(scope: venue — Siam Paragon; Wat Pathum Wanaram)_
- `siam-c11` **[corroborated·neutral·entire_unit]** Daily rhythm: malls run roughly 10:00-22:00; CentralWorld-side street food starts around 17:00; the interchange peaks on weekday commutes (Siam is the Sukhumvit/Silom transfer) and on weekend afternoons; food-guide observations put the Erawan/Trimurti shrine-visit window in the early evening across the Ratchaprasong side. Sunday-quiet mornings are the counter-rhythm in the square itself. _(scope: station_area — Siam interchange and malls)_
- `siam-c12` **[proposed·neutral·outside]** Recent changes: the 2023 Paragon shooting temporarily closed the mall's BTS connector (no reopening date published on the source); Siam Square's east side remains in redevelopment churn (Scala site empty as of 2023). One Bangkok's phased opening - first office tower 18 March 2024, public celebration 25 October 2024 - went to the khwaeng-Lumphini/Rama IV corner of Witthayu intersection, NOT into the Siam unit, consistent with the batch-3 placement. _(scope: citywide — Siam Paragon; Siam Square; One Bangkok (Witthayu/Rama IV corner))_

## Reviewer notes from the researcher
- Researcher self-checks only; independent review still required (batch review/findings.md).
- open issue: App park_ha=6.0 has no verified single-polygon source; Pathumwananurak + Park @ Siam + untagged Wat Pathum green is the best candidate set (siam-c05).
- open issue: CentralWorld is served by both Siam and Chit Lom; its polygon split between units is a coordinator decision (siam-c02).
- open issue: No 2024-2026 Siam-area infrastructure or mall-renovation list surfaced in this light pass; a targeted pass on Siam Piwat/Central announcements would close it.
- open issue: Bangkok Post, Reddit and TripAdvisor accesses failed (paywall/403); Thai-language evidence is snippet-level only for crowd perception.
