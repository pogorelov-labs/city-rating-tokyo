# Tourist load for Bangkok: OSM hotel density + attraction gravity, khet and station-area counts (CRTKY-152)

Researched: **2026-10-13**, by the open-data research agent. Scope per the ask:
tourist-load signal for Bangkok — `tourism=hotel|guest_house|hostel|apartment`
counts by khet and by station-area 800 m circles, `tourism=attraction|museum`
counts, a badge threshold calibrated on the distribution (Tokyo mirror:
`research/notes/2026-10-13-tourists-crtky173.md`, badge ≥15/800 m), and a
verdict on how it should enter the product. All Overpass runs, local
classification and portal probes below were run by me in this session
(Appendix has the exact commands). Nothing here is an implementation
decision — the owner adopts the source and the format.

**TL;DR:** One Overpass dump per theme over the repo bbox gives the whole
picture from a single snapshot. **In-province totals: 2,113 accommodation
objects (hotel 1,246 / hostel 378 / guest_house 260 / apartment 229) and 301
attraction|museum objects** (dump bases: hotels 2026-07-28, attractions
2026-07-24). The khet gradient is extreme: **Phra Nakhon 380 hotels + 40
attractions** (Khaosan/Rattanakosin) vs **6 khets with zero hotels**. At
station level the 800 m counts run **Nana 197 → Asok 159 → … → 0** on 25 of
133 stations; median is 3, mean 18. The Tokyo badge threshold ≥15/800 m is
**too loose for Bangkok**: it would flag **38/133 stations (29 %)** because
Bangkok's tourist-hotel zone is one continuous 10-km Sukhumvit/Silom corridor
rather than Tokyo's bimodal pattern. Proposed replacement, calibrated on the
distribution: **H800 ≥ 50 (15/133 = 11 %, natural break 54→49 in the top
tail)**, optionally **OR A800 ≥ 8** to pull in Siam/Sanam Chai/National
Stadium/Mo Chit (Old Town + Chatuchak gravity) → **19/133 (14 %)**. The
threshold is robust to dropping the ambiguous `tourism=apartment` tag (same
15/133 at ≥50). **No open footfall data below province level exists** —
verified: MOTS/TAT publish province-level only (Bangkok = one province),
gdcatalog.go.th API search returns no khet-level arrivals dataset,
`economy.bangkok.go.th` answers 403 from this environment,
`data.bangkok.go.th` fails TLS, the TravelLink dashboard is a JS shell.
Verdict: **fact block + derived estimate-grade flag**, not a new numeric
rating key — details in §8.

---

## 1. What was actually verified (date, method, live output)

All runs 2026-10-13. Raw dumps kept outside the repo in `~/tmp_ov_tourists_crtky152/`
(`hotels_raw.json`, `attractions_kumi2.json`, `check_asok.json`,
`check_min-buri.json`); the only repo file created is this note.

**Two Overpass dumps** (`nwr["tourism"~…"](bbox); out center tags;`) over the
repo's Bangkok bbox 13.4907–13.9556 N / 100.3279–100.9383 E:

| dump | mirror | `timestamp_osm_base` | elements |
|---|---|---|---|
| hotels (`hotel\|guest_house\|hostel\|apartment`) | overpass.private.coffee | **2026-07-28T02:16:18Z** | 2,282 |
| attractions (`attraction\|museum`) | overpass.kumi.systems | **2026-07-24T11:04:51Z** | 479 |

Mirror health (recorded honestly, it cost retries): `overpass-api.de` was not
attempted first this session — `overpass.private.coffee` and
`overpass.kumi.systems` were used per the CRTKY-173 precedent; both
load-balance across backends with **different snapshot ages** (one kumi pull
returned base 2026-05-31, a later identical one 2026-07-24 — I re-pulled and
kept the fresher). `private.coffee` timed out 5× on the attractions query and
kumi timed out 12× consecutively on the small cross-check queries (§2);
every number in this note comes from a response that passed a JSON +
element-count validation loop. The stale-file trap from CRTKY-153 §1 (a
failed curl leaving the previous query's JSON in place) was explicitly
guarded against by validating each response before use.

**Local classification** (no further network): each dump element is placed by
its `center` (nodes: own lat/lng; ways/relations: Overpass-computed center),
then (a) assigned to a khet by point-in-polygon (pure-python ray casting,
even-odd over rings) against **`app/src/data/bangkok/geometry.json`** — the
same `admin_level=6` polygons the product draws — and (b) counted in an 800 m
haversine circle around station-area anchors from
**`app/src/data/bangkok/stations.json`** (133 areas). Note: the ask cited
`data/bangkok/stations.json`; that path does not exist — the actual file is
`app/src/data/bangkok/stations.json` (133 areas, `_meta.generated`
2026-09-30). 800 m matches the Tokyo note's convention and the repo's
walking-catchment usage.

**Cross-check of the local counting against Overpass's own `around`**
(direct `nwr[…](around:800,lat,lng); out count;`):

| station | local (dump, center-in-circle, base 07-28) | direct Overpass | base of direct run | delta |
|---|---:|---:|---|---|
| min-buri | 0 | **0** | 2026-07-24 | exact match |
| asok | 159 | **167** (87 nodes + 80 ways) | 2026-05-31 (older backend) | +8 (4.8 %) |

The asok delta is semantics, not churn: Overpass `around` counts ways whose
*geometry* intersects the circle, my pipeline counts element *centers* inside
it (large/splotchy ways poke in without their center); the direct run's base
was also 2 months older. Both readings are far above any candidate threshold,
so the badge is insensitive to the choice. The pipeline numbers below are the
center-in-circle convention, stated wherever cited.

**Coverage of the dumps:** 169/2,282 hotels (7.4 %) and 178/479 attractions
(37 %) fall **outside the 50-khet province boundary** — the repo bbox is
wider than Bangkok province and includes Nonthaburi, Samut Prakan and
Pathum Thani. Spot-checked unassigned names confirm this is correct, not a
polygon bug: Ancient Siam/Muang Boran (13.54, 100.63) and Phra Samut Chedi
(Samut Prakan), Nonthaburi Provincial Museum (13.84, 100.49), Bang Kachao
island venues (Phra Pradaeng), National Memorial (13.95, 100.62). All khet
and station counts below are in-province only: **2,113 hotels, 301
attractions**.

## 2. Khet-level counts (50 khets, H = accommodation, A = attraction+museum)

Sorted by hotels. Type mix shown as hotel/guest_house/hostel/apartment.

| khet | H | A | H type mix | khet | H | A |
|---|---:|---:|---|---|---:|---:|
| phra-nakhon | **380** | **40** | 144/112/119/5 | dusit | 16 | 10 |
| watthana | 217 | 9 | 167/13/24/13 | phra-khanong | 23 | 2 |
| khlong-toei | 190 | 8 | 148/20/16/6 | bangkok-noi | 12 | 12 |
| bang-rak | 186 | 9 | 120/8/34/24 | suan-luang | 21 | 2 |
| ratchathewi | 181 | 13 | 130/10/35/6 | wang-thonglang | 20 | 1 |
| pathum-wan | 115 | **32** | 86/8/13/8 | lak-si | 19 | 1 |
| sathon | 77 | 4 | 51/11/9/6 | prawet | 14 | 5 |
| samphanthawong | 55 | 19 | 22/18/14/1 | phasi-charoen | 13 | 6 |
| chatuchak | 41 | 24 | 28/4/5/4 | thon-buri | 11 | 4 |
| din-daeng | 56 | 3 | 41/6/6/3 | lat-phrao | 11 | 4 |
| huai-khwang | 54 | 4 | 35/6/5/8 | bang-kho-laem | 12 | 2 |
| lat-krabang | 49 | 7 | 40/1/6/2 | yan-nawa | 11 | 2 |
| phaya-thai | 47 | 5 | 19/6/9/13 | khlong-sam-wa | 1 | 10 |
| don-mueang | 43 | 6 | 23/2/17/1 | chom-thong | 9 | 1 |
| bang-kapi | 41 | 5 | 26/1/4/10 | min-buri | 5 | 4 |
| pom-prap-sattru-phai | 26 | 12 | 13/2/11/0 | bang-khun-thian | 7 | 2 |
| bang-khen | 33 | 0 | 4/1/1/27 | bangkok-yai | 6 | 2 |
| khlong-san | 28 | 4 | 16/3/2/7 | rat-burana | 7 | 0 |
| bang-phlat | 26 | 5 | 16/2/5/3 | bang-khae | 5 | 2 |
| bang-na | 23 | 5 | 13/2/2/6 | khan-na-yao | 2 | 3 |

Remaining bottom rows: taling-chan 2/2, saphan-sung 3/1, nong-chok 3/1,
bueng-kum 3/1, bang-bon 0/4, thung-khru 3/0, sai-mai 2/1, bang-sue 3/0,
thawi-watthana 0/2, nong-khaem 1/0.

Reading:

- **The tourist-bed city is 6 khets**: Phra Nakhon, Watthana, Khlong Toei,
  Bang Rak, Ratchathewi, Pathum Wan hold 1,269 of 2,113 hotels (60 %) on
  ~3 % of the province's land (51 of 1,566 km², measured from the
  `geometry.json` polygons this session). Phra Nakhon's mix (112 guest houses + 119 hostels)
  is the Khaosan/Rambuttri budget signature; Watthana/Khlong Toei/Bang Rak
  are hotel-heavy (167/148/120 hotels) — the Sukhumvit/Silom/Sathorn
  inventory.
- **Attractions are a different geography**: Pathum Wan (32) and Phra Nakhon
  (40) dominate; Samphanthawong (19, Chinatown), Chatuchak (24, weekend
  market cluster), Dusit/Bangkok Noi/Pom Prap (10–12) are attraction-rich but
  hotel-poor. Hotel mass and attraction gravity are **complementary signals**,
  not the same one — this drives the threshold proposal in §5.
- **Caveat on `tourism=apartment`**: in Thai OSM it mixes serviced
  apartments with probable residential-condo mis-tags (bang-khen's 33 H are
  27 apartments — an ordinary residential district). §4.1 shows the proposed
  threshold does not move when apartments are excluded entirely.
- District-level facts in the pipeline already carry a culture count that
  includes attractions (`scripts/bangkok/build.py:1091` and `:1349` —
  `venue + attraction + temple`), but **accommodation is counted nowhere**
  today.

## 3. Station areas, 800 m — the 15-station sample (the ask)

Sample spans the ask's gradient: the three named stations (Siam, Asok,
Saphan Taksin) + core/inner anchors + semi-periphery + periphery. Counts are
center-in-circle against the two dumps (§1).

| station | khet of anchor | H800 | A800 |
|---|---|---:|---:|
| **nana** | khlong-toei | **197** | 3 |
| **asok** | khlong-toei | **159** | 4 |
| phloen-chit | pathum-wan | 128 | 3 |
| sala-daeng | bang-rak | 96 | 6 |
| **siam** | pathum-wan | 42 | **19** |
| victory-monument | ratchathewi | 39 | 6 |
| **saphan-taksin** | bang-rak | **31** | 3 |
| thong-lo | khlong-toei | 29 | 4 |
| on-nut | khlong-toei | 27 | 1 |
| ari | phaya-thai | 15 | 3 |
| phra-ram-9 | din-daeng | 11 | 1 |
| bang-chak | phra-khanong | 11 | 0 |
| lat-phrao | chatuchak | 5 | 0 |
| bearing | bang-na | 4 | 0 |
| **bang-khae / min-buri** (periphery) | bang-khae / min-buri | **0 / 0** | 0 / 0 |

The gradient is clean and monotone: core hotel wall (96–197) → inner
mixed (15–42) → semi-periphery (4–11) → periphery (0). The full 133-station
table was computed from the same dumps and is summarized below; per-station
values are reproducible from the note's method in ~seconds (no extra
network).

## 4. Full distribution (133 station areas) and the threshold question

Hotels in 800 m (H800): **median 3, mean 18, max 197** (Nana). Threshold
sweep, and what each would mean as a badge share:

| H800 ≥ | stations flagged | share |
|---:|---:|---:|
| 15 (Tokyo badge) | 38 | **29 %** |
| 20 | 31 | 23 % |
| 25 | 26 | 20 % |
| 30 | 23 | 17 % |
| 50 | 15 | **11 %** |
| 80 | 9 | 7 % |

Top tail (H800): nana 197, asok 159, phloen-chit 128, ratchaprarop 121,
phaya-thai 117, ratchathewi 111, chong-nonsi 107, sala-daeng 96, phrom-phong
80, sam-yan 77, saint-louis 74, hua-lamphong 66, wat-mangkon 62, surasak 57,
sam-yot **54** ‖ chit-lom 49, national-stadium 47, siam 42, lumphini 40,
victory-monument 39 ‖ saphan-taksin 31, ratchadamri 30, thong-lo 29, …

### 4.1 Why Tokyo's ≥15 does not transfer, and the proposed threshold

The Tokyo badge (CRTKY-173 §3: Asakusa 62 / Ginza 46 vs Funabashi 9 /
Kichijoji 5, threshold ≥15) was calibrated on a **bimodal** pattern —
tourist-bed districts vs commuter towns with nothing between. Bangkok is
**continuous**: the Sukhumvit/Silom corridor is a 10-km hotel strip, so the
middle of the distribution (11–54) is densely populated and ≥15 lands in the
middle of it, flagging 29 % of the network — the badge stops meaning "high
tourist flow".

**Proposed threshold: H800 ≥ 50.** Rationale:

1. Natural break in the top tail: 54 (sam-yot) → 49 (chit-lom) is the gap
   that closes the coherent top-15 set — the Sukhumvit/Silom/Sathorn hotel
   wall plus Hua Lamphong, Chinatown (Wat Mangkon) and the Old Town edge
   (Sam Yot). Exactly the set a resident would name as "where the tourists
   stay".
2. Selectivity: 15/133 = 11 % — comparable to what the Tokyo badge was
   intended to be, vs 29 % at ≥15.
3. Robust to the `tourism=apartment` caveat: excluding apartments entirely
   leaves the same **15/133** at ≥50 (top-15 all stay ≥53).

**Optional second leg — attraction gravity: A800 ≥ 8** (9 stations: siam 19,
wat-mangkon 17, sam-yot 16, national-stadium 15, sanam-chai 13,
hua-lamphong 12, ratchathewi 11, sam-yan 11, mo-chit 9; A800 percentiles:
p50 = 0, p90 = 6, max = 19). Union with H800 ≥ 50 → **19/133 (14 %)**: adds
Siam (shopping/attractions node with 42 hotels — just under 50), Sanam Chai
and National Stadium (Grand Palace/Wat Pho/Jim Thompson district) and Mo
Chit (Chatuchak weekend market, ~200k visitors on market days). Semantically
this is the "tourist node" set, of which the hotel-heavy set is a subset. The
two legs are a scope decision for the owner: H-only = "where tourists sleep";
H OR A = "where tourists are".

## 5. Footfall open data — verified absence

The ask's premise ("открытых данных footfall для Бангкока нет, TAT —
городские цифры") is confirmed; probes run this session:

| channel | result |
|---|---|
| MOTS (Ministry of Tourism & Sports, mots.go.th) + TAT | publish **province-level** arrivals/receipts only (Bangkok = one province; e.g. ~28 M foreign arrivals to Thailand in 2025 per tat.or.th). No district/khet split found in any search index. |
| gdcatalog.go.th (national open-data API) | `package_search` for ท่องเที่ยว กรุงเทพ → HTTP 200, **8 datasets, none** is khet-level arrivals/footfall (Thai travel-behavior survey, amenities, domestic transport passengers…). |
| travellink.go.th (MOTS dashboard) | JS app; page body renders just "TRAVEL LINK" — content not readable with this tooling. **Untested, not claimed.** |
| economy.bangkok.go.th (BMA) | **HTTP 403** from this environment (also with a browser UA). Not verifiable here. |
| data.bangkok.go.th (BMA open data) | **TLS failure** (`SSL_ERROR_SYSCALL`) on every attempt. Not verifiable here. |

So OSM density is not just the cheapest signal — below province level it is
the **only** open, uniformly available one. TAT/MOTS city figures remain
usable as editorial prose only ("Bangkok received X M visitors in Y"),
needing attribution and a date.

## 6. Licenses

- OSM/Overpass: **ODbL** (stated in every response header); same terms the
  repo already runs under. Counts derived from OSM need no per-number
  attribution but the standard OSM credit applies (see existing `/methodology`).
- TAT/MOTS: government works, reusable with attribution under Thai practice;
  moot for this feature since only province-level exists (§5). Any city-level
  sentence in descriptions should carry "TAT, <year>".
- Pipeline's own `stations.json`/`geometry.json`: repo data, no external
  constraint.

## 7. How this relates to the existing pipeline

- Bangkok `crowd` = `0.5·log(district density) + 0.5·log1p(Overture places
  per km²)` inverted (`scripts/bangkok/build.py:1094-1096`), confidence
  `moderate` (`build.py:1356`) — a **density/quietness** measure, not
  tourism: On Nut rates "livelier" than Nana despite 197-vs-27 hotels. A
  tourist-load layer is genuinely absent.
- Station areas already emit a `facts` card (`build.py:1330-1343`: food,
  cafes, nightlife, culture, temples, park_ha, piers…) — an accommodation
  count slots in as one more key with provenance `osm` and a snapshot date.
- The 133-station distribution (§4) means any per-station tourist display
  normalizes cleanly on existing percentile machinery; nothing new to build
  numerically.

## 8. Verdict — метка vs факт-блок vs prose (the ask's three options)

| option | assessment |
|---|---|
| **Факт-блок (рекомендуется, основа)** | Add `hotels` (H800) and `attractions` (A800) to the existing station `facts` card — a count is a *fact* (OSM, dated snapshot), fits the card's existing style (numbers with source), zero new rating machinery. Khet-level numbers feed district descriptions. |
| **Метка/флаг «высокий турпоток» (estimate-grade, поверх факт-блока)** | Justified by the distribution (§4.1): threshold H800 ≥ 50 (или H800 ≥ 50 OR A800 ≥ 8 для «туристических узлов»). The *count* is a fact; the *label* is an inference from density, not measured flow — mark it estimate-grade, same honesty rule as the Tokyo mirror note. Do **not** introduce a new numeric rating key: it would double-count with `crowd`/`nightlife` (all three reward the same central corridor) and re-open normalization for one axis. |
| **Только prose (отклоняется)** | The ordinal separation (197/159 vs 0 on a third of stations) is far too clean to leave implicit, and the repo's description rules prefer facts over flair. Prose alone also gives the family-filter-style consumers nothing deterministic. |

For Tokyo (CRTKY-173) the mirror recommendation was badge + facts; Bangkok's
native fact-card support makes the same stack *cheaper* here — the badge can
simply be a display rule over the two facts keys.

## 9. Adopt / reject per source

| source | verdict | why |
|---|---|---|
| Overpass dumps (private.coffee 2026-07-28 hotels / kumi 2026-07-24 attractions) | **adopt** | one snapshot per theme covers all 133 stations + 50 khets; cross-checked against `around` (§1); ODbL |
| Threshold H800 ≥ 50 (± OR A800 ≥ 8) | **adopt as proposal** | calibrated on the actual 133-station distribution, robust to the apartment caveat; owner fixes the final number |
| `tourism=apartment` as tourist inventory | **adopt with caveat** | mixes serviced apartments with condo mis-tags; threshold proven insensitive, but don't surface per-type splits from it |
| TAT/MOTS data | **reject as signal, keep as prose source** | province-level only (§5); no khet/station granularity exists openly |
| BMA portals (economy.bangkok.go.th, data.bangkok.go.th) | **unverifiable this session** | 403 / TLS failure; re-probe before relying on them |

## 10. Open questions for the owner

1. Badge semantics: hotel-centric (H800 ≥ 50, 15/133) or tourist-node union
   (H800 ≥ 50 OR A800 ≥ 8, 19/133)? §4.1 recommends either, with the union
   matching "high tourist flow" wording better.
2. Should the badge be bilingual copy aligned with Tokyo's CRTKY-173
   wording (「高い観光来訪」/«высокий турпоток»/"high tourist flow") so the
   two cities mirror?
3. Fact-card placement: add `hotels`/`attractions` keys to `a["facts"]` in
   `build.py` (one-line additions + source/date), or keep counts display-only?
4. Snapshot policy: re-pull the two dumps on each build (cheap, ~2 requests)
   vs pin a dated extract? (Counts move a few % per quarter in the corridor —
   asok-style churn — which does not flip any threshold.)
5. Cross-check convention to pin in code: center-in-circle (this note) vs
   Overpass `around` intersection (+4.8 % at the top end); pick one for both
   cities.
6. Re-probe BMA portals (403/TLS here) if any district-level footfall is ever
   wanted — from a different network if possible.

## Appendix — exact commands run this session (2026-10-13)

```
# dumps (validation loop on every response)
curl -sS "https://overpass.private.coffee/api/interpreter" --data-urlencode \
  "data=[out:json][timeout:180];nwr[\"tourism\"~\"^(hotel|guest_house|hostel|apartment)\"](13.4907,100.3279,13.9556,100.9383);out center tags;"
  # -> hotels_raw.json, base 2026-07-28T02:16:18Z, 2282 elements
curl -sS "https://overpass.kumi.systems/api/interpreter" --data-urlencode \
  "data=[out:json][timeout:180];nwr[\"tourism\"~\"^(attraction|museum)\"](13.4907,100.3279,13.9556,100.9383);out center tags;"
  # -> attractions_kumi2.json, base 2026-07-24T11:04:51Z, 479 elements
#   (private.coffee attractions: 5 timeouts; one earlier kumi pull gave the
#    2026-05-31 backend — re-pulled until the fresher base answered)

# local: ray-casting khet classification vs app/src/data/bangkok/geometry.json,
# haversine 800m vs app/src/data/bangkok/stations.json (python3, scripts kept
# in ~/tmp_ov_tourists_crtky152/: classify.py, dist.py, diag.py)

# cross-check (kumi timed out 12x consecutively; alternating retries):
curl -sS "https://overpass.kumi.systems/api/interpreter" --data-urlencode \
  "data=[out:json][timeout:90];nwr[\"tourism\"~\"^(hotel|guest_house|hostel|apartment)\"](around:800,13.80841,100.73269);out count;"
  # -> min-buri total 0 (base 2026-07-24) — matches local 0
curl -sS "https://overpass.kumi.systems/api/interpreter" --data-urlencode \
  "data=[out:json][timeout:90];nwr[\"tourism\"~\"^(hotel|guest_house|hostel|apartment)\"](around:800,13.73704,100.56036);out count;"
  # -> asok total 167 (base 2026-05-31) vs local 159 (semantics delta, §1)

# open-data probes
curl -sS "https://gdcatalog.go.th/api/3/action/package_search?q=ท่องเที่ยว กรุงเทพ&rows=10"
  # 200, 8 datasets, none khet-level arrivals
curl -sS -A "Mozilla/5.0" "https://economy.bangkok.go.th"        # 403
curl -sS "https://data.bangkok.go.th/api/3/action/package_search?q=ท่องเที่ยว"
  # SSL_ERROR_SYSCALL (exit 35) — not verifiable from this environment
WebFetch travellink.go.th   # JS shell, "TRAVEL LINK" only — untested, not claimed
WebSearch TAT/MOTS granularity  # province-level confirmed via search index
```

Sources: Overpass mirrors `overpass.private.coffee` (base 2026-07-28) and
`overpass.kumi.systems` (base 2026-07-24, one 2026-05-31 backend noted);
repo data `app/src/data/bangkok/stations.json`, `app/src/data/bangkok/geometry.json`,
`scripts/bangkok/build.py`; precedent notes
`research/notes/2026-10-13-tourists-crtky173.md`,
`research/bangkok/notes/2026-10-13-redlight-crtky153.md`; portals as listed
in §5 and the Appendix. All fetched/read 2026-10-13.
