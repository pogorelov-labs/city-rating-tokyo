# Bangkok institutions & landmarks — embassies, international hospitals/schools, coworking, attractions (CRTKY-145)

Researched: **2026-10-13**, by the open-data research agent. All fetches below
were run by me in this session; commands and outputs are quoted. Nothing here
is an implementation decision — the owner adopts sources.

**TL;DR:** Four of the five classes are genuinely open-data-mappable.
**Embassies are the strongest find**: OSM carries 81 embassy/consulate POIs
(all tagged `office=diplomatic`), Wikidata carries 58 embassy items with
`P159 → Bangkok` (not `P625` — that quirk cost one wrong SPARQL attempt), and
43 named embassies sit in both → **two-source rule satisfied**. The embassy
corridor is measurable, not anecdotal: `phloen-chit` station area (Wireless
Rd) has **19** embassy POIs, `lumphini` **11**, `asok` **8**, `chong-nonsi`
**7**; districts Pathum Wan **24**, Watthana **16**, Sathon **15**, Bang Rak
**11**. That character is **not** in any rating signal today — it surfaced
only through hand-written prose (pathum-wan atmosphere "embassy-lined
Wireless Road") — see §7. Museums/attractions are already counted inside the
vibe culture signal (`pois_culture` in `scripts/bangkok/fetch.py:125`), so the
new content is embassies + international schools/hospitals + coworking.
**Coworking must be rejected** (OSM has **5** POIs city-wide vs ~100–200
locations claimed by directories). **Recommendation: fact blocks on district
and station-area pages, not an 11th category** — §8.

---

## 1. What was checked and how (verification log)

| # | What | Command (abridged) | Result |
|---|------|--------------------|--------|
| 1 | Overpass POI fetch, ask's bbox `13.49,100.32,13.96,100.94` | `curl -d 'data=[out:json][bbox:…] (nwr["amenity"="embassy"]; nwr["office"="diplomatic"]; nwr["diplomatic"]; nwr["healthcare"="hospital"]; nwr["amenity"="hospital"]; nwr["amenity"="school"]; nwr["amenity"="coworking_space"]; nwr["tourism"="attraction"]; nwr["tourism"="museum"];); out center tags;' https://overpass-api.de/api/interpreter` | **exit 35 / SSL failure** on `overpass-api.de` and `overpass.kumi.systems` from this machine's curl; python `requests` POST with mirror rotation → **HTTP 200 from `overpass.kumi.systems`, 1743 elements**, cached at `/tmp/crtky145-institutions.json` (same endpoint set as `scripts/bangkok/fetch.py:47-51`) |
| 2 | Wikidata SPARQL, embassies | `GET query.wikidata.org/sparql?…?item wdt:P31/wdt:P279* wd:Q3917681 (embassy); wdt:P625…FILTER bbox` | 200, **1 row** — embassy items mostly lack `P625` (verified: `Q13021886` *Embassy of the United Kingdom, Bangkok* has `P31=Q3917681`, `P159=Q1861` Bangkok, **no P625**) |
| 3 | Wikidata SPARQL v2 | `?item wdt:P31 wd:Q3917681 . { ?item wdt:P159 ?hq . ?hq wdt:P131* wd:Q1861 } UNION { P625-in-bbox }` | 200, **66 rows / 58 unique items** → `/tmp/crtky145-wd-embassies.json` |
| 4 | Wikidata museums & attractions | `wikibase:around` service, `Point(100.63 13.725)`, radius 42 km, `P31/P279* wd:Q33506` (museum) / `wd:Q570116` (tourist attraction) | 200, museums **245 rows / 81 unique**; attractions **50 rows / 10 unique**. First museum attempt without `around` (plain bbox FILTER + `P279*` + label service) → **504 gateway timeout**; the `around` service is the way that works |
| 5 | District / station-area assignment | pure-python even-odd ray-casting PIP over `app/src/data/bangkok/geometry.json` (50) and `station-geometry.json` (133); sanity: **0/50 district centroids fell outside their own polygon**; spot-verified Shrewsbury → bang-kho-laem ✓, Shrewsbury City Campus → huai-khwang ✓, Bangkok Patana → bang-na ✓, Samitivej Sukhumvit → watthana (no station area — 884 m from Phrom Phong, outside the 800 m disc, consistent with overview honesty note 8) | `/tmp/crtky145-counts.json` |
| 6 | Overlaps & quality | name-normalised joins + co-location check (500 m) | see per-class sections |

**Bbox caveat.** The ask's bbox is slightly tighter than the repo's
`static_data.BBOX = (13.47, 100.30, 13.98, 100.96)` (`scripts/bangkok/static_data.py:195`).
In-bbox-but-outside-the-50-districts (Nonthaburi / Samut Prakan fringes):
272 schools, 160 attractions, 50 hospitals, 22 museums, 0 embassies/coworking.
**All district/area numbers below are inside the 50 khet only.**

**JMCP could not be identified.** Two targeted searches ("JMCP Bangkok English
speaking doctors directory hospitals expat", "JMCP Thailand medical clinic
expat") returned no directory by that name. I treated it as (probably) **JCI**
(Joint Commission International) and used the JCI-accreditation tier as the
"international hospital" proxy — flagged in §5.2.

## 2. Raw counts (Overpass, ask's bbox → inside the 50 districts)

| Class | Tag(s) | In bbox | In 50 districts | Named | Notes |
|---|---|---|---|---|---|
| Embassies | `office=diplomatic` (+`diplomatic=*`) | **81** | **81** | 80 | 71 `diplomatic=embassy`, 5 `diplomatic=consulate`, 4 unspecified, 1 unnamed; 47 carry a `wikidata` tag |
| Hospitals | `healthcare=hospital` / `amenity=hospital` | 226 | **176** | — | includes government hospitals (Rajavithi, Ramathibodi, Prasat Neurological…) **and mis-tagged private clinics** ("charisma", "HE Clinic for men", "WellMed clinic" in Watthana) |
| Schools | `amenity=school` | 948 | **673** | — | 113 carry a `wikidata` tag; only 2 have `isced:level` |
| — of which name-matched "International" | name contains "international" | 51 | **42** (+9 outside: ISB, Concordian, D-PREP ×2, Ruamrudee Ratchapruek, Thai-Sikh, Thai-Chinese, Norwich, MUIC demo school) | 51 | misses schools whose name lacks the word (Bangkok Patana, Bangkok Prep); "New International School of Thailand" (= NIST) is present |
| Coworking | `amenity=coworking_space` | **5** | **5** | 5 | ekkamai 2, phrom-phong 1, national-stadium 1, ha-yaek-lat-phrao 1 |
| Attractions | `tourism=attraction` | 335 | **175** | 164 | 11 unnamed (small nodes) |
| Museums | `tourism=museum` | 148 | **126** | 124 | ~1–3 co-located duplicates (Jim Thompson House exists as 3 elements under 2 name variants) → ≈ 123–124 unique |

## 3. Per-khet counts (all 50, sorted by embassies then total)

`emb` embassy · `hosp` hospital · `sch` school · `cow` coworking · `attr` attraction · `mus` museum

| District | emb | hosp | sch | cow | attr | mus |
|---|---|---|---|---|---|---|
| pathum-wan | 24 | 4 | 20 | 1 | 11 | 19 |
| watthana | 16 | 10 | 34 | 3 | 7 | 3 |
| sathon | 15 | 1 | 20 | 0 | 1 | 3 |
| bang-rak | 11 | 5 | 16 | 0 | 3 | 5 |
| khlong-toei | 6 | 7 | 20 | 0 | 5 | 4 |
| huai-khwang | 2 | 7 | 11 | 0 | 2 | 1 |
| din-daeng | 2 | 3 | 14 | 0 | 2 | 1 |
| wang-thonglang | 2 | 2 | 9 | 0 | 1 | 0 |
| ratchathewi | 1 | 14 | 16 | 0 | 7 | 7 |
| lat-phrao | 1 | 5 | 9 | 0 | 4 | 0 |
| lak-si | 1 | 3 | 11 | 0 | 1 | 0 |
| phra-nakhon | 0 | 1 | 16 | 0 | 25 | 18 |
| chatuchak | 0 | 7 | 21 | 1 | 14 | 10 |
| dusit | 0 | 2 | 27 | 0 | 2 | 8 |
| bangkok-noi | 0 | 5 | 18 | 0 | 4 | 9 |
| phasi-charoen | 0 | 4 | 23 | 0 | 4 | 2 |
| bang-khun-thian | 0 | 5 | 23 | 0 | 0 | 2 |
| thon-buri | 0 | 3 | 21 | 0 | 3 | 1 |
| samphanthawong | 0 | 2 | 8 | 0 | 13 | 4 |
| bang-khae | 0 | 4 | 21 | 0 | 2 | 0 |
| lat-krabang | 0 | 3 | 16 | 0 | 7 | 0 |
| phaya-thai | 0 | 12 | 8 | 0 | 2 | 3 |
| pom-prap-sattru-phai | 0 | 4 | 9 | 0 | 6 | 5 |
| bang-phlat | 0 | 2 | 17 | 0 | 3 | 2 |
| khlong-sam-wa | 0 | 1 | 13 | 0 | 10 | 0 |
| taling-chan | 0 | 0 | 21 | 0 | 2 | 0 |
| bang-na | 0 | 5 | 11 | 0 | 0 | 5 |
| bueng-kum | 0 | 5 | 15 | 0 | 0 | 1 |
| yan-nawa | 0 | 1 | 17 | 0 | 0 | 2 |
| bang-kapi | 0 | 4 | 11 | 0 | 4 | 1 |
| don-mueang | 0 | 2 | 11 | 0 | 5 | 1 |
| nong-khaem | 0 | 3 | 15 | 0 | 0 | 0 |
| suan-luang | 0 | 2 | 14 | 0 | 2 | 0 |
| bang-khen | 0 | 4 | 14 | 0 | 0 | 0 |
| prawet | 0 | 1 | 11 | 0 | 1 | 4 |
| khlong-san | 0 | 3 | 8 | 0 | 4 | 0 |
| thawi-watthana | 0 | 3 | 9 | 0 | 1 | 1 |
| sai-mai | 0 | 3 | 10 | 0 | 1 | 0 |
| min-buri | 0 | 2 | 7 | 0 | 3 | 1 |
| bang-bon | 0 | 1 | 8 | 0 | 3 | 1 |
| nong-chok | 0 | 1 | 10 | 0 | 1 | 0 |
| bang-sue | 0 | 3 | 9 | 0 | 0 | 0 |
| bang-kho-laem | 0 | 1 | 9 | 0 | 2 | 0 |
| khan-na-yao | 0 | 7 | 2 | 0 | 2 | 1 |
| saphan-sung | 0 | 1 | 9 | 0 | 1 | 0 |
| chom-thong | 0 | 3 | 7 | 0 | 1 | 0 |
| bangkok-yai | 0 | 0 | 9 | 0 | 2 | 0 |
| rat-burana | 0 | 4 | 6 | 0 | 0 | 0 |
| phra-khanong | 0 | 0 | 4 | 0 | 1 | 1 |
| thung-khru | 0 | 1 | 5 | 0 | 0 | 0 |

Museum spot-checks (names printed and eyeballed, §1 #6): phra-nakhon 18 —
Bangkok National Museum, Museum of Siam, Queen Sirikit Museum of Textiles,
Rattanakosin Exhibition Hall, Pipit Banglamphu… all real; chatuchak 10 — MOCA
Bangkok, Children's Discovery Museum, Thai Bank Museum…; pathum-wan 19 — Jim
Thompson House ×3 elements (= 1 museum), Madame Tussauds, Chulalongkorn
university museums.

## 4. Station-area counts

**Embassies — all 19 areas with ≥ 1** (the "embassy district" made numeric):

| Station area | Embassies |
|---|---|
| **phloen-chit** (BTS Phloen Chit — Wireless Rd) | **19** |
| lumphini (MRT Lumphini — Rama IV/Sathorn N) | 11 |
| asok | 8 |
| chong-nonsi (Sathorn) | 7 |
| phrom-phong | 3 |
| nana | 3 |
| saint-louis, sala-daeng, surasak, thailand-cultural-centre, charoen-nakhon, ratchadamri | 2 each |
| sam-yan, ratchathewi, phra-khanong, thong-lo, ekkamai, chit-lom, lak-si | 1 each |

Top areas, other classes (counts from the same PIP run):

- **Hospitals**: victory-monument 5, ram-inthra-kor-mor-9 5, sala-daeng 3,
  ramkhamhaeng 3, khlong-toei 3, phrom-phong 2, phloen-chit 2 …
- **Schools**: phrom-phong 11, phetchaburi 9, saphan-taksin 8, wat-mangkon 7,
  sanam-chai 7, itsaraphap 7 …
- **Coworking**: ekkamai 2, phrom-phong 1, national-stadium 1,
  ha-yaek-lat-phrao 1 (all 5 city-wide).
- **Attractions**: wat-mangkon 9, sanam-chai 8, sam-yot 5, khlong-san 5,
  mo-chit 4, kamphaeng-phet 4 …
- **Museums**: sam-yan 9, national-stadium 7, bang-khen 4, sanam-chai 4,
  siam 3, lumphini 3, thong-lo 3 …

108 of 133 station areas contain ≥ 1 institution of any class; 25 contain none
(outer arms of the network).

## 5. Per-class verdicts (two-source rule)

### 5.1 Embassies — **adopt, confidence strong**

- **OSM**: 81 POIs, all `office=diplomatic`; 80/81 named ("Embassy of
  Germany…", "Apostolic Nunciature", "Delegation of the European Union",
  "Consulate of the Republic of the Congo"). Coverage matches reality: the
  mission list of a capital with ~80 resident embassies.
- **Wikidata**: 58 unique embassy items in the bbox via `P31=Q3917681` +
  `P159→(P131*)Bangkok`. Only **1 of 58 carries P625** (Hungary, Q113940288).
- **Overlap**: 43 named items are in both (47 OSM POIs carry `wikidata` tags,
  43 of which are in the WD bbox set; 4 extra OSM wd-tags are items WD places
  elsewhere/misses; 15 WD items have no WD-tagged OSM POI — a few of those may
  still exist in OSM unlinked).
- **Caveat**: district assignment rests on OSM coordinates alone; Wikidata
  cannot geolocate embassies (P159-only model).
- **Licence**: OSM ODbL (already in the pipeline); Wikidata CC0
  (`research/bangkok/00-overview.md`, `scripts/bangkok/fetch.py:16-17`).

### 5.2 International hospitals — **adopt as a curated list** (manual, ~annual refresh); OSM raw count only with a noise caveat

- OSM `healthcare=hospital` (176 in-district) mixes tertiary international
  hospitals with government hospitals (Rajavithi, Ramathibodi, Priest
  Hospital…) and **private clinics mis-tagged as hospitals** (Watthana
  contains "charisma", "HE Clinic for men", "WellMed clinic").
- The international tier is a **short manual list**, not a countable tag. From
  JCI-flavoured directories: konkai.health lists **8** Bangkok hospitals
  (Bumrungrad, Vejthani, Bangkok Hospital main, Samitivej Sukhumvit, Praram 9,
  MedPark, Yanhee, Bangpakok 9) —
  https://konkai.health/hospitals; the official index is
  https://www.jointcommission.org/recognizing-excellence (searchable, no bulk
  export). Adding BNH (Sathorn; JCI history per search summaries, current
  status unverified) makes a plausible 9–11-name list.
- **Cross-check**: 10/11 of {that list + BNH + Saint Louis + Phyathai 3} were
  found in OSM with coordinates: Bumrungrad → watthana/phloen-chit,
  Samitivej Sukhumvit → watthana (no station area, 884 m from Phrom Phong),
  BNH → bang-rak/sala-daeng, Saint Louis → sathon/saint-louis, Bangkok
  Hospital → huai-khwang, Praram 9 → huai-khwang, MedPark →
  khlong-toei/khlong-toei, Vejthani → bang-kapi, Yanhee → bang-phlat/bang-o,
  Phyathai 3 → phasi-charoen/bang-phai, Bangpakok 8 → bang-bon. So the list
  geolocates cleanly against OSM — the "second source" here is the
  accreditation directory, which is **not open-licensed** → usage is citation,
  and the list must live in repo data (like `editorial.json`), not be
  re-scraped.
- "JMCP" from the ask remained unidentified (§1); JCI used instead.

### 5.3 International schools — **adopt with curation**; OSM alone is moderate

- OSM in-district: 673 schools; **42 name-matched "International"** (+9
  outside the 50 khet). All marquee names present: ISB (Nonthaburi), Harrow
  (Don Mueang), Shrewsbury riverside (bang-kho-laem) + City Campus (huai
  khwang), Ruamrudee, Berkeley, King's College, Wellington College,
  Concordian, Ekamai International, NIST (as "New International School of
  Thailand"), St. Andrews, Wells, Anglo Singapore…
- Second source: International Schools Database states **"104 international
  schools in Bangkok"** (https://www.international-schools-database.com/in/bangkok,
  fetched 2026-10-13 — commercial directory, includes campuses and
  Nonthaburi estates). ISAT's member directory (https://www.isat.or.th/search)
  is a JS app; WebFetch got navigation only, no count.
- Gap analysis: name-match undercounts because some big schools don't carry
  "International" in the name — Bangkok Patana (→ bang-na) and Bangkok Prep
  (→ watthana) are in OSM as `amenity=school` but would be missed. An
  international-school classifier needs name + operator/website heuristics or
  a curated overlay; expect ~60–80 in-district after curation vs OSM's 42.
- **Verdict**: OSM coordinates + a curated name overlay → moderate-to-strong;
  raw OSM name-match alone → moderate (undercount by ~40 %).

### 5.4 Coworking — **reject OSM as a signal**

- `amenity=coworking_space` yields **5** POIs in the whole bbox. Directories
  (Coworker.com, FlySpaces, CoworkingCafe) claim ~100–200 locations in
  Bangkok metro (search-summary evidence only — coworker.com itself returned
  **HTTP 403** to WebFetch, so I could not verify a directory count directly).
  Even at half that, OSM coverage is <10 %.
- Any coworking content would be a hand-maintained list of chains (WeWork,
  JustCo, The Hive, Common Ground, Glowfish…). Not worth it for a rating
  signal; at most a fact line "major coworking chains: Sukhumvit/Asok,
  Thong Lo, Sathorn, Rama IV".

### 5.5 Museums & attractions — museums **strong-ish** (OSM counts, WD verifies), attractions **moderate** (single open source)

- **Museums**: OSM 126 in-district (124 named; ≈123 unique after co-location
  dedupe) vs Wikidata 81 unique items (75 in-district). Name-normalised
  overlap is only **22** (Thai/English naming divergence), but the per-district
  *distribution* corroborates: WD's top districts are phra-nakhon 14 /
  pathum-wan 11 vs OSM's 18 / 19 — the same two cores. Substance of the
  two-source rule holds: counts from OSM, existence verified by WD.
- **Attractions**: OSM 175 in-district (164 named: Grand Palace area, Wat Arun
  viewpoint nodes, markets…). Wikidata's `tourist attraction` class (Q570116)
  has only **10 items** in the radius (zoos and parks: Safari World, Dream
  World, Sea Life, Dusit Zoo…) — not a usable source. Overture's
  `historic_site` category is excluded in the repo for mis-classification
  (`research/bangkok/00-overview.md` caveat; `build.py load_overture`). So
  attractions remain effectively **single-source** → moderate at best.
- Note: both classes are **already inside the vibe signal**
  (`pois_culture` fetches `tourism~^(museum|gallery|attraction)$`,
  `scripts/bangkok/fetch.py:125-131`); re-adding them as a separate category
  would double-count.

## 6. Is the "embassy district" (Wireless Rd) already surfaced?

**In prose and aliases yes; in data no.**

- `data/bangkok/editorial.json → districts.pathum-wan.aliases` contains
  **"Wireless Road"** (and Phloen Chit / Lumphini / Ploenchit).
- `data/bangkok/descriptions/pathum-wan.json` (EN atmosphere): *"…plus a big
  university campus and **embassy-lined Wireless Road**"*; `sathon.json`:
  *"South Sathorn towers, **embassies**, hotel lobbies…"*. Watthana's page
  mentions hospitals (Bumrungrad, Samitivej) but not embassies.
- **No data signal carries it**: `data/bangkok/signals.json` facts are
  food/nightlife/convenience/markets/essentials/sports/culture/temples/parks/piers
  — no embassy, school, hospital or institution field anywhere
  (`grep -ri "embass" scripts/bangkok/*.py data/bangkok/signals.json` → empty).
  Vibe (pathum-wan 9, watthana 9; station areas phloen-chit 9, lumphini 8) is
  driven by culture venues + cafés + temples — the embassy density happens to
  co-locate with those but is not measured.
- With §3/§4 numbers, the character becomes a **fact**: Phloen Chit station
  area has 19 embassy POIs — the densest in the city; Lumphini 11; Asok 8.

## 7. Composition proposal (owner decision)

1. **Not a new category.** Institutions are amenities users want to *know
   about*, not a quality axis to weight; embassies exist in ~11/50 districts,
   coworking is unmappable → an 11th category would be percentile noise. Also
   museums/attractions already live in vibe.
2. **Fact blocks** (recommended): extend `facts` in `signals.json` with
   `embassies`, `international_schools` (curated overlay), `museums`,
   `attractions` (+ optionally `international_hospitals` count) and render one
   "Institutions & landmarks" row on district and station-area pages, in the
   style of the existing facts. Cheap (one Overpass pass + one JSON field),
   honest (counts are counts), and the district pages get their "embassy
   district" line backed by data instead of prose.
3. **Boosts**: a small embassy/international-school term inside `vibe` raw
   would re-rank Phloen Chit/Lumphini/Asok/Sathorn slightly; do **not** put
   hospitals or coworking into vibe (health access is not "vibe").
   If boosts are added, keep vibe's two-source confidence rule intact
   (embassies are OSM-only per-district, WD verifies at city level).
4. **Manual lists** (hospital tier, coworking chains, school overlay) live in
   `data/bangkok/editorial.json`-style files with `updated:` stamps and
   citation URLs, same pattern as rent/safety.

## 8. Adopt / reject summary

| Source | Role | Verdict | Confidence if adopted |
|---|---|---|---|
| OSM `office=diplomatic` (Overpass) | embassy counts per khet / station area | **adopt** | strong (WD overlap 43 named) |
| Wikidata SPARQL `P31=Q3917681` + `P159*→Bangkok` | embassy cross-check, CC0 | **adopt** (city-level check) | — |
| OSM `healthcare=hospital` | hospital counts | **partial** (mis-tagged clinics) | moderate |
| JCI/konkai-style curated hospital list | international tier | **adopt as manual list** (not open-licensed; cite) | editorial + OSM-verified coords |
| OSM `amenity=school` + name/operator heuristic | international schools | **adopt with curation** | moderate (OSM undercounts ~40 % vs ISDB 104) |
| International Schools Database / ISAT | school cross-check | **reference only** (commercial / JS-only) | — |
| OSM `amenity=coworking_space` | coworking | **reject** (5 POIs city-wide) | — |
| OSM `tourism=museum` | museum counts | **adopt** | strong (WD distribution + 22-item name overlap corroborate) |
| OSM `tourism=attraction` | attraction counts | **adopt, flagged** | moderate (no second open source) |
| Wikidata Q570116 attractions | cross-check | **reject** (10 items) | — |

## 9. Open questions

1. Owner call: fact blocks (recommended) vs vibe boost vs status quo (prose
   only). If fact blocks: also at station-area level (Phloen Chit 19 is the
   single most telling number) or districts only?
2. Who owns the annual refresh of the curated international-hospital list
   (JCI status rotates on 3-year cycles; BNH's current status unverified)?
3. International-school classifier: accept a name+operator heuristic
   (imperfect) or maintain a curated school list like the hospital one?
4. WD embassy items lack P625 by design — accept OSM-only district assignment
   (strong elsewhere) or geocode WD items via addresses as a second pass?
5. JMCP remained unidentified; if the ticket author meant a specific
   directory, it needs a URL before it can be evaluated.
