# National Stadium (st.national-stadium) — research brief

**Derived view** of `profiles/st.national-stadium.json` (authoritative bundle), batch `zcode-main (ZCode orchestrator + 6 light-pass subagents), 2026-11-07` era output. Status: **ready_for_review** — not independently approved. Drafted in English only; no translations manufactured.

- **Unit:** Station area (nearest-stop catchment, Voronoi ∩ 800 m disc). Aliases: —
- **Scope:** Nearest-stop catchment (Voronoi ∩ 800 m) around national-stadium [bts_silom]; districts: pathum-wan, ratchathewi. Boundary claims are decided by the app polygons (coordinator checks apply).
- **App score context:** model 7.38 (display rounded), cohort rank 25 of 133, snapshot `bkk-d6499618507e7561`. Public popularity: **unmeasured** — No citywide popularity measure has been collected. Tier B selection used within-cohort rank; coverage recorded opportunistically per bundle.
- **Selection rationale:** Tier B (light pass): station-area rank 25/133, score 7.38.

## Card preview (proposed)
> The Silom line's western terminus in the shadow of a 19,793-seat national stadium: MBK's 2,000 stalls and food courts on one side, the Jim Thompson House teak compound on the other, and Centenary Park's green roof just past the catchment edge - with 66,000-person concert nights as the calendar's exclamation marks.

## Guide lead (proposed)
National Stadium is Siam's practical back door: same skywalk network, same food density in the app's top tier, but rents that start where the student khwaeng begins (app blend 36,500/82,000, the batch's lowest). The trade is precision - the stadium gives the unit its name and its event nights, and the park its green score leans on sits mostly beyond the 800-meter line.

## Strengths
- Skybridge-connected everyday logistics: MBK (Tops supermarket, 40-stall food court, Don Don Donki) plus BACC and Siam Discovery on one covered spine from the W1 platform. *[`national-stadium-c01`, `national-stadium-c05`]*
- A real sports-and-culture anchor pair: a 19,793-seat national stadium with a packed 2024-2026 concert calendar, and the Jim Thompson House museum one block away. *[`national-stadium-c02`, `national-stadium-c04`, `national-stadium-c06`]*

## Trade-offs
- The green=9 figure outruns the geometry: Centenary Park's centroid is 955 m out, so only its northern tip likely sits inside; the verified close-in green is two small parks - the 4.3 ha claim needs the polygon to survive. *[`national-stadium-c07`, `national-stadium-c08`]*
- gym_sports=9 blends two different things: a scheduled-event stadium (not a drop-in gym) and the app's fitness-venue count - the score is defensible but the mechanism should be separated. *[`national-stadium-c03`]*
- Event-night crush: bookings for 50,000-person shows in 2026 mean the unit's crowd experience can flip overnight without any change to its score. *[`national-stadium-c04`]*

## Day / night
- Daytime runs on campus and MBK errands - food courts, phone stalls, faculty buildings; evenings lean on the Siam seam's food strip; concert nights (Dec 2024, Mar and May 2026 bookings) flood Rama I with tens of thousands, while non-event nights keep the hostel-and-student layer as the main late activity. *[`national-stadium-c04`, `national-stadium-c11`]*

## Within-area variation
- The Rama I retail spine (MBK, Discovery, skybridge) is loud and continuous; north across the canal-side blocks toward Phetchaburi it thins to the Charoenpol pier lanes; east past Phaya Thai Road the campus gardens (Chamchuri 10) and pocket parks take over - three units of texture inside one scorecard. *[`national-stadium-c01`, `national-stadium-c09`, `national-stadium-c08`]*

## Conditional fit
- Fit for students, event-goers and budget-leaning renters who want Siam's food reach at the batch's lowest rent blend and can live with concert-night crowds. *[`national-stadium-c10`, `national-stadium-c11`, `national-stadium-c04`]*
- Poor fit for quiet-seekers during event season and for anyone whose 'green' expectation is a large park inside the catchment - the flagship park sits mostly beyond the line. *[`national-stadium-c04`, `national-stadium-c07`]*

## Explicit unknowns
- park_ha=4.3 vs Centenary Park partial-membership geometry unresolved; park size sources conflict (11 acres vs 30 rai) (national-stadium-c07).
- gym_sports method (venue count vs stadium access) not exposed (national-stadium-c03).
- No 2024-2026 station-area infrastructure change found - explicit gap (national-stadium-c12).
- Pier assignment (Charoenpol in-cell, Hua Chang out) is the researcher's straight-line Voronoi check (national-stadium-c09).
- 2026 concert attendances are source-listed estimates, not realized counts.

## Question coverage
- **Q01 — answered**: Identity: W1 branch terminus serving the National Stadium complex, MBK and the Jim Thompson House; app center equals the true station site.
- **Q02 — answered**: Everyday experience: campus-adjacent shopping and food at MBK, student texture, event-night surges at the stadium.
- **Q03 — answered**: Mechanisms: transport=10 from the skybridge-linked W1; vibe=10 from the Siam seam; gym_sports=9 from the stadium-faculty mix (flagged).
- **Q04 — answered**: Counter-evidence: no quiet refuge from the Siam crush inside the retail blocks; event nights import the crush instead.
- **Q05 — answered**: Rhythm: weekday student/commuter base, weekend Siam spillover, concert nights (incl. three 2026 bookings).
- **Q06 — answered**: Walkability: skybridge spine to MBK/Discovery/BACC/Square; straight-line distances only, no radius-to-time conversions.
- **Q07 — answered**: Daily life: MBK's Tops supermarket and food courts, street-level faculties, canal pier for the old town, cheaper rents than the neighbors.
- **Q08 — answered**: 36,500/82,000 is the batch's lowest blend; Wang Mai listing floor (12,900) supports the student-adjacent reading; still district-level, asking-basis.
- **Q09 — answered**: Green=9 with 4.3 ha: Centenary Park is partial at best (centroid 955 m); the verified close-in green is two small parks; 4.3 ha needs the polygon.
- **Q10 — answered**: Fit: students, MU-style event-goers, budget-leaning renters comfortable with weekend crush; poor fit for quiet-seekers on concert weekends.
- **Q11 — answered**: 2024-2026: event calendar verified; station-area infrastructure changes not found (gap).
- **Q12 — answered**: Outside-the-score: gym-vs-venue method split, park-clip geometry, Scala-site redevelopment direction - flagged, unscored.

## Evidence base

| Source | Publisher (family) | Type | Published | Read |
| --- | --- | --- | --- | --- |
| [National Stadium BTS station](https://en.wikipedia.org/wiki/National_Stadium_BTS_station) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Suphachalasai Stadium](https://en.wikipedia.org/wiki/Suphachalasai_Stadium) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [MBK Center](https://en.wikipedia.org/wiki/MBK_Center) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [Jim Thompson House](https://en.wikipedia.org/wiki/Jim_Thompson_House) | Wikipedia (English) (Wikipedia) | other | — | yes |
| [OpenStreetMap elements: stations, ferry terminals, piers, parks](https://overpass-api.de/api/interpreter) | OpenStreetMap contributors via Overpass API (OpenStreetMap) | other | — | yes |
| [Chulalongkorn University Centenary Park (LILA award page)](https://landezine-award.com/chulalongkorn-university-centenary-park/) | Landezine International Landscape Award (landezine) | other | — | yes |
| [Siam and Pratunam Bangkok (food/travel guide)](https://migrationology.com/siam-square-pratunam-bangkok) | Migrationology (Mark Wiens) (personal_blog) | other | — | yes |
| [Property for rent in Pathum Wan (FazWaz)](https://www.fazwaz.com/property-for-rent/thailand/bangkok/pathum-wan) | FazWaz (fazwaz) | other | — | yes |
| [Siam Square](https://en.wikipedia.org/wiki/Siam_Square) | Wikipedia (English) (Wikipedia) | other | — | yes |

## Claim index

- `national-stadium-c01` **[corroborated·strength·entire_unit]** BTS National Stadium (code W1) opened 5 December 1999 as the terminus of the Silom line's western branch, at 13.7465139 N, 100.5291083 E - identical to the app's unit center - on Rama I Road west of the Pathum Wan junction. The station's skybridge links directly to the National Stadium complex, MBK Center, Siam Discovery, the Bangkok Art and Culture Centre and Siam Square; the Jim Thompson House sits opposite in Soi Kasemsan 2, and Chulalongkorn University's sports-science and psychology faculties front the street level. _(scope: station_area — BTS National Stadium station, Rama I Road)_
- `national-stadium-c02` **[proposed·neutral·inside]** The station's namesake, Suphachalasai Stadium in the National Stadium complex (Wang Mai, Pathum Wan), was built 1937 and opened 1938, named after Luang Suphachalasai, the 'father of Thai sport'; it seats 19,793 (35,000 concert configuration), hosted the 1966/1970/1978 Asian Games as main stadium, and is owned by Chulalongkorn University with the Department of Physical Education as operator. _(scope: venue — Suphachalasai Stadium, National Stadium complex)_
- `national-stadium-c03` **[proposed·neutral·inside]** The gym_sports=9 score has a dual mechanism this unit should be honest about: the verified sports anchor is a 19,793-seat public stadium plus a university sports-science faculty, while the app's gym layer counts fitness venues - the two are different amenities, and the app's method does not separate them. The stadium is not a drop-in gym; its track-and-field and match use is scheduled. _(scope: venue — National Stadium complex)_
- `national-stadium-c04` **[proposed·neutral·inside]** Event rhythm is the unit's swing factor: the stadium's concert calendar runs large - Blackpink drew 66,211 across two nights (7-8 January 2023), Stray Kids 20,600 on 14 December 2024, and three more stadium-scale shows are booked into 2026 (Three Man Down 7-8 March, 50,000; Seventeen 14-15 March; Treasure 16 May). On event nights the campus-quiet unit absorbs tens of thousands; between events it reverts to student and commuter texture. _(scope: venue — Suphachalasai Stadium)_
- `national-stadium-c05` **[corroborated·strength·inside]** MBK Center anchors the unit's west edge: opened 7 February 1985, ~2,000 shops across 8 floors at the Rama I x Phaya Thai corner, historically youth-led (half of 100,000+ daily visitors were young Thais in 2009), with Don Don Donki, a Tops supermarket and a 40-stall food court on the 6th floor feeding everyday errands. _(scope: venue — MBK Center)_
- `national-stadium-c06` **[proposed·strength·inside]** The Jim Thompson House museum - six relocated teak houses, most 19th-century and moved from Ayutthaya, assembled by the American who founded the Thai Silk Company in 1948 and vanished in Malaysia in 1967 - was built in 1959 at 6 Soi Kasemsan 2, one block from this station, and runs guided tours. _(scope: venue — Jim Thompson House, Soi Kasemsan 2)_
- `national-stadium-c07` **[conflicted·neutral·partial]** Chulalongkorn University Centenary Park - opened August 2017, designed by LANDPROCESS (Kotchakorn Voraakhom) with N7A, about 11 acres (~4.45 ha; a project PDF says 30 rai/~4.8 ha - the figures differ), with a 1.3 km bike-priority CU Promenade, Thailand's largest green roof (5,200 m2) and million-gallon-scale rain retention - is the green=9 candidate: its OSM centroid sits 955 m from the app center, so most of the park likely falls OUTSIDE the 800 m catchment with only its northern part inside (partial). The app's 4.3 ha in-unit figure implies nearly the whole park, which the centroid geometry does not support. _(scope: venue — Chulalongkorn University Centenary Park, Phaya Thai Road frontage)_
- `national-stadium-c08` **[proposed·strength·inside]** Two smaller named greens sit closer in: Suan Chaloem Loa (BMA pocket park on Phaya Thai Road, hours 05:30-19:00, no alcohol/pets/smoking per OSM) at 491 m, and Chamchuri 10 Garden (CU campus garden) at 460 m - together with the Centenary Park tip they form the unit's real green layer, none of it large. _(scope: station_area — Suan Chaloem Loa; Chamchuri 10 Garden)_
- `national-stadium-c09` **[proposed·strength·inside]** The lone pier checks out against OSM geometry: Saphan Hua Chang's ferry terminal is 356 m from the app center but only ~303 m from Ratchathewi station, so nearest-stop logic assigns it to the ratchathewi cell - leaving Saphan Charoenpol (634 m, on the Khlong Saen Saep's Golden Mount line) as this unit's single canal-boat pier, matching the app's piers=1. _(scope: station_area — Saphan Charoenpol pier (Khlong Saen Saep))_
- `national-stadium-c10` **[proposed·neutral·entire_unit]** The rent blend (36,500/82,000 THB, district_blend as of 2026-09) is the lowest of the four Pathum Wan units in this batch, plausibly because the unit's khwaeng-level stock spans student-adjacent and older blocks: FazWaz shows Wang Mai listings from 12,900 to 434,000/month (129 listings) against a district 1-bed average of 46,800. _(scope: district — Wang Mai khwaeng / Pathum Wan district)_
- `national-stadium-c11` **[corroborated·neutral·entire_unit]** Counter-view to the 'quieter Siam' reading: the unit lacks a mall-owned food engine of Siam's scale (app 511 food vs 676) but is stitched into the same crush by the skybridge - the guide treats Siam as 'the most well known shopping district in all of Bangkok' with MBK 'an entire city of its own', and a hostel sits directly below this station, keeping the 24-hour youth-traveler layer present. Weekend spillover from Siam Square reaches MBK's doors; the quiet is between events and north of Rama I, not in the retail blocks. _(scope: station_area — MBK / Siam Square seam)_
- `national-stadium-c12` **[proposed·neutral·inside]** Recent changes 2024-2026: the stadium calendar (Stray Kids Dec 2024; three stadium shows Mar-May 2026) is the main verified change driver; next door, Siam Square's east side continued its churn (Scala demolished by 2021, site reportedly empty as of 2023). No 2024-2026 infrastructure change at the station itself surfaced in this pass - an explicit gap. _(scope: station_area — Suphachalasai Stadium; Siam Square edge; station)_

## Reviewer notes from the researcher
- Researcher self-checks only; independent review still required (batch review/findings.md).
- 1 claim(s) carry explicit recheck_by flags for volatile facts.
- open issue: Park-clip geometry: app park_ha=4.3 implies nearly all of Centenary Park (~4.45-4.8 ha) in-unit, but the OSM centroid sits 955 m out - coordinator polygon check decides between 'partial tip' and 'app uses a different park dataset' (national-stadium-c07).
- open issue: gym_sports=9 should separate scheduled-venue access (stadium) from fitness-venue counts (national-stadium-c03).
- open issue: No station-area 2024-2026 public-works source found; a BMA-targeted pass could close it.
- open issue: Reddit/TripAdvisor 403 and Bangkok Post paywall blocked perception-side corroboration.
