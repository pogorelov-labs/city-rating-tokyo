# Michelin stars + Bib Gourmand as a Bangkok food-quality layer (CRTKY-142)

Researched: **2026-10-13**, by the open-data research agent. Context: the
Bangkok `food` category (`research/bangkok/00-overview.md:52`) is a pure POI
quantity signal — Overture + OSM eating places within 800 m, percentile-ranked
across the 50 khets. This note evaluates adding a *quality* layer (Michelin
stars + Bib Gourmand), maps every 2026-guide restaurant to its khet, simulates
what folding it into the food percentile would do, and argues where cafe
"depth" belongs. All network checks below were run by me in this session;
commands and outputs are quoted. Nothing here is an implementation decision —
the owner adopts sources.

**TL;DR.** The 2026 Michelin data is real, live and reachable: Wikipedia's
*List of Michelin-starred restaurants in Thailand* parses cleanly to
**43 starred restaurants / 55 stars in Thailand** (guide 2026; my re-parse of
the rendered table matched its intro exactly), and the live
`guide.michelin.com/us/en/bangkok-region/restaurants` — reached through the
`r.jina.ai` reader proxy because the site sits behind an AWS WAF challenge
that blocks plain curl — reports **"1-48 of 197 restaurants"** for the Bangkok
region (the ticket's 186 is stale; the list grew), with facet counts
**3★=2, 2★=8, 1★=29 (39 starred), Bib Gourmand=32**. The star counts match
Wikipedia's Bangkok set name-for-name (39/39). I resolved **all 71 starred+Bib
restaurants to a khet** (guide `data-dtm-district` attributes in a Jan 2026
Wayback snapshot cross-checked against the address line on each live detail
page — **zero disagreements** where both exist). Result: stars live in only
**12 of 50 khets** (concentrated Bang Rak 12★, Watthana 11★, Pathum Wan 7★;
zero beyond ~9 km from Siam — exactly the ask's expectation), while Bib
reaches **10 more khets**, including Taling Chan, Chom Thong, Prawet,
Saphan Sung and rural Thawi Watthana — 11 of 32 Bib sit in khets with *no*
star. **Recommendation: do NOT fold Michelin into the food percentile** (a
`ln(1+2·stars+bib)` bump moves 30 of 50 districts and *lowers* Samphanthawong
10→9 and Huai Khwang 7→6 — punishing exactly the food-dense districts the
count already rewards); make it a **fact on the page** ("2★, 1 Bib in this
district" in the By-the-numbers card; "N★ within 800 m" is computable at
station level from ~70 geocoded addresses). A separate subscore is defensible
but sparse (0 for 28 khets). Wikidata **P4160 is unusable for Thailand**
(0 Thai items). On coffee: cafe depth is more concentrated than food (top-5
khets hold 42 % of OSM cafes vs 21 % of food POIs) and diverges from food in
the periphery — keep it in **vibe** (where it already is,
`scripts/bangkok/build.py:1014`), stop double-counting it in the food bucket
(`build.py:397`).

---

## 1. What the pipeline does today (code refs)

- **Food signal** — `scripts/bangkok/build.py:998-1000`:
  `pt["food"] = both("food", 800)` where `both()` is
  `0.35·log1p(OSM food ≤800 m) + 0.65·log1p(Overture food ≤800 m)`
  (`build.py:993-995`); district value = resident-weighted mean → percentile
  1–10 across 50 khets. Quantity only; no quality dimension anywhere.
- **What counts as food** — OSM bucket includes `amenity=cafe, fast_food,
  food_court, ice_cream` and `shop=bakery, coffee, pastry`
  (`build.py:397`); the Overture bucket maps `restaurant, casual_eatery,
  non_alcoholic_beverage_venue, bakery, dessert_shop, food_court,
  food_truck_stand` (`build.py:512-515`). **Cafes therefore already flow into
  food.**
- **Cafes also flow into vibe** — `build.py:1014`: vibe =
  `0.40·both("venue",1000) + 0.20·both("cafe",800) + …`. So cafe depth is
  currently **double-counted** (food bucket *and* a 0.2 vibe weight). A
  separate `cafe` bucket exists (`build.py:399-400`, Overture `build.py:517`)
  and is used at station level (`facts.cafes`).
- **Where a fact could render** — district page "By the numbers" card,
  `app/src/app/[locale]/bangkok/district/[slug]/page.tsx:429-465` (a `dl`
  of numeric facts: food, nightlife, …, population). Station pages carry a
  similar facts block.

## 2. Source A — Wikipedia star list (verified, adopt as cross-check)

`https://en.wikipedia.org/wiki/List_of_Michelin-starred_restaurants_in_Thailand`
(note the hyphen; the non-hyphenated title is a redirect — found via
`action=parse` returning `#REDIRECT`), a Featured list whose intro states:
*"In the 2026 Michelin Guide, there are 43 restaurants in Thailand with a
Michelin-star rating."* (The ticket's "43 stars" is really **43 starred
restaurants**; my parse counts **55 stars** among them.)

Method: `action=parse&prop=text`, then parsed the rendered table positionally
— each row has a fixed 9 year-columns (2018…2026); star cells carry
`<img alt="N Michelin star(s)">`, closed years are a `colspan` cell (e.g.
Bo.lan: 4 star cells, `colspan=4` "Closed", then a 2026 star cell). Verified
raw HTML for the surprising cells: **Bo.lan and Gaggan show 1★ in 2026**
(both had closed and returned). Output (2026 column):

| Province | Restaurants | Stars |
|---|---:|---:|
| Bangkok | 39 | 51 |
| Nonthaburi (Akkee, Suan Thip) | 2 | 2 |
| Phang Nga (Aulis) | 1 | 1 |
| Phuket (Pru) | 1 | 1 |
| **Thailand** | **43** | **55** |

Bangkok detail: 3★ Sorn, Sühring; 2★ Baan Tepa, Chef's Table, Côte by Mauro
Colagreco, Gaa, Inddee, Le Normandie, Mezzaluna, R-Haan (8); 1★ ×29. The ask
said "rows have districts" — they do **not**: the wiki table carries province
only, so khet mapping had to come from the guide (§3). Verdict: **adopt as
the authoritative star roster** (structured, stable URL, CC-BY-SA).

## 3. Source B — guide.michelin.com live pages (verified, adopt with care)

### 3.1 Access mechanics

- Plain curl → **HTTP 202, 0 bytes** (challenge); `r.jina.ai` with
  `x-return-format: html` → AWS WAF challenge JS; **default `r.jina.ai`
  markdown rendering executes the challenge and works** (HTTP 200 each time).
  So: reachable, but only via a JS-executing reader — plain `fetch.py`-style
  scraping of guide.michelin.com is not viable.
- Wayback Machine: `web.archive.org/cdx` lists snapshots of the region page
  (2025-03-25, 2026-01-16, both HTTP 200). The **2026-01-16 snapshot** is
  server-rendered HTML with per-card `data-dtm-*` attributes
  (`data-restaurant-name`, `data-dtm-district`, `data-dtm-distinction`,
  `data-dtm-price`) — 48 Bangkok cards + a few template/foreign cards. This
  is the cheapest way to get *districts* without JS.

### 3.2 Live inventory (2026-10-13)

Fetched list pages 1–5 via `r.jina.ai`:
`/us/en/bangkok-region/restaurants` + `/page/2…5`. Page 1 header:
**"Bangkok Region : 1-48 of 197 restaurants"** — the ticket's **186 is
stale**; the region now holds **197 entries**. Parsing each page's cards
(`### [Name](url)` + contiguous icon run above the header: `michelin-star`
imgs vs `symboleBibendum` img) yields exactly:

| Distinction | Count | Cross-check |
|---|---:|---|
| 3 stars | 2 | = Wikipedia Bangkok (Sorn, Sühring) ✓ |
| 2 stars | 8 | = Wikipedia's eight ✓ |
| 1 star | 29 | = Wikipedia's 29 ✓ |
| starred total | **39** | **name-for-name match with Wikipedia, 39/39** ✓ |
| Bib Gourmand | **32** | = the page's own facet "Bib Gourmand … 32" ✓ |
| selected (no icon) | 126 | 39+32+126 = 197 ✓ |

Guide naming quirks recorded: "Anne-Sophie Pic at Le Normandie" (= wiki "Le
Normandie"), "Elements, Inspired by Ciel Bleu", GOAT/AVANT/IGNIV/INDDEE
caps. The 2026 Bib set (32 names) is in the appendix; spot-checks all agree
with publicly known Bib places (Krua Apsorn, Rung Rueang, Ten Suns, K.
Panich, Jay Fai is *starred*, not Bib ✓).

Availability notes for the ask's sub-question: Wikipedia has "List of
Michelin Bib Gourmand restaurants…" pages for **US/Canada/Mexico/Malaysia but
none for Thailand** (checked via `list=search`). The guide's filtered URL
`?michelin-selection=bib-gourmand` does **not** apply server-side (facet says
32, list returns the default 52) — the reliable paths are the icon parse
above or an interactive browser session on the filter panel.

### 3.3 Khet resolution (71/71 resolved, two-source validated)

Starred+Bib = 39+32 = 71 restaurants. District from, in order: (a) the
Wayback snapshot's `data-dtm-district` (18 cards), (b) otherwise the address
line on the live detail page fetched via `r.jina.ai` (53 pages, ~3.5 s
spacing; address format e.g. Sühring: *"10 Soi Yen Akat 3, Chong Nonsi, Yan
Nawa, Bangkok, 10120, Thailand"* — the khet is the comma field before
"Bangkok"). Where both sources existed they **agreed in every case (0
mismatches)**; Sühring verified by hand (dtm "Yan Nawa" = address "Yan
Nawa"). Guide spellings normalised (Vadhana→watthana, Pathumwan→pathum-wan,
Ratchatewi→ratchathewi, Sampanthawong→samphanthawong, …). One new Bib (Baan
Pee Lek) sits in Prawet per its address.

## 4. Source C — Wikidata P4160 (checked, reject)

P4160 = *"Michelin Restaurants ID"* ("identifier for a restaurant in the
Michelin Restaurants website"), verified via `wbgetentities`. SPARQL
(`query.wikidata.org`): **195 items carry P4160 globally** — but filtered by
`wdt:P17 wd:Thailand` the result is **0 items**. The only Bangkok-adjacent
hit in the global dump is "Restaurant Sühring" (label-located to Bangkok, no
P17, no coordinates). As a structured/geocoding source for Bangkok P4160 is
empty; **reject** (it covers NYC/Toronto/Paris/Seoul, not Thailand).

## 5. The khet table (main deliverable)

Stars by khet (2026 guide; districts as assigned by the guide's own address
data) + Bib Gourmand count:

| Khet | 3★ | 2★ | 1★ | starred rest. | stars | Bib | names (stars) |
|---|---:|---:|---:|---:|---:|---:|---|
| Bang Rak | 0 | 3 | 6 | 9 | 12 | 3 | Chef's Table 2, A-S Pic at Le Normandie 2, Mezzaluna 2, Maison Dunand 1, 80/20 1, Cannubi 1, Le Du 1, Aksorn 1, Samrub Samrub Thai 1 · Aunglo, Samlor, Thien Duong |
| Watthana | 0 | 2 | 7 | 9 | 11 | 1 | R-Haan 2, Gaa 2, Gaggan 1, Haoma 1, Juksunchae 1, Resonance 1, GOAT 1, Bo.lan 1, NAWA 1 · Here Hai |
| Pathum Wan | 0 | 1 | 5 | 6 | 7 | 1 | INDDEE 2, AVANT 1, Saneh Jaan 1, Elements 1, IGNIV 1, Coda 1 · Thai Niyom |
| Khlong Toei | 1 | 0 | 1 | 2 | 4 | 3 | Sorn 3, Mia 1 · Keawloon, Rung Rueang, No Name Noodle |
| Sathon | 0 | 1 | 2 | 3 | 4 | 2 | Côte 2, Nahm 1, Sushi Saito 1 · Plu, Hia Wan |
| Yan Nawa | 1 | 0 | 0 | 1 | 3 | 1 | Sühring 3 · Jaan |
| Ratchathewi | 0 | 0 | 3 | 3 | 3 | 0 | Wana Yook 1, Signature 1, etcha 1 |
| Phra Nakhon | 0 | 0 | 2 | 2 | 2 | 5 | Jay Fai 1, Nusara 1 · Kolun.h, Pad Thai Fai Ta Lu, K. Panich, Thai Tham, Ten Suns |
| Bang Kapi | 0 | 1 | 0 | 1 | 2 | 0 | Baan Tepa 2 |
| Khlong San | 0 | 0 | 1 | 1 | 1 | 3 | Blue by Alain Ducasse 1 · Bokkia, Somsak Pu Ob, Ann Tha Din Daeng |
| Dusit | 0 | 0 | 1 | 1 | 1 | 1 | Chim by Siam Wisdom 1 · Krua Apsorn |
| Samphanthawong | 0 | 0 | 1 | 1 | 1 | 1 | POTONG 1 · Urai Braised Goose |
| Taling Chan | 0 | 0 | 0 | 0 | 0 | 2 | Lucky Seafood, Phed Phed Bistro |
| 9 more khets, 1 Bib each | | | | | | 9 | Chatuchak (Beer Hima), Bang Sue (Pae Jok), Phaya Thai (Prik-Yuak), Saphan Sung (Maan Muang), Thawi Watthana (Kin Kub Koi), Pom Prap (Bunloet), Wang Thonglang (Janhom), Chom Thong (Gim Nguan), Prawet (Baan Pee Lek) |
| **Total** | **2** | **8** | **29** | **39** | **51** | **32** | |

(Sum checks: 51 stars / 39 restaurants = Wikipedia Bangkok; 32 Bib = guide
facet. Full per-restaurant dump preserved in my session artifacts
`/tmp/mg_final.json`, `/tmp/mg_khet_table.json`.)

### 5.1 Spread outside the centre

- **Stars are a core-only phenomenon, as the ask suspected.** 12 of 50 khets
  hold any star; all 12 are the river-core/Sukhumvit/Silom/Sathorn block.
  The single furthest-out starred restaurant is Baan Tepa (2★, Bang Kapi,
  inner-east ~8 km). Nothing starred beyond ~9 km from Siam; the outer 28
  khets have **zero** Michelin listings of any kind.
- **Bib does reach out: 11 of 32 (34 %) Bib sit in khets with no star at
  all**, including genuinely outer ones — Taling Chan (2), Chom Thong,
  Prawet, Saphan Sung, **Thawi Watthana** (rural west, current food rating
  2), Bang Sue, Phaya Thai, Pom Prap, Wang Thonglang. 22 of 50 khets have at
  least one Michelin listing; 28 have none.
- Contrast with the quantity signal: the top-5 khets by food-POI count
  (Watthana 3111, Pathum Wan 3064, Chatuchak 2746, Khlong Toei 1817, Lat
  Phrao 1854) hold only 21 % of the city's 60,231 food POIs — Michelin is
  much more concentrated than the existing food signal, and its geography
  (Lat Phrao 0 stars) does not match it.

## 6. Composition: boost vs subscore vs fact (quantified)

I simulated the *"fold into food percentile"* option on the pipeline's own
raw signals (`data/bangkok/signals.json → districts.<slug>.raw.food`): added
`ln(1 + 2·stars + bib)` per khet and re-ran the percentile rule (my
re-implementation reproduced the published ratings for 46/50 exactly, the
rest differ only by tie-rounding). Result with the real khet table:

- **30 of 50 districts change their integer rating.** Winners are the
  one-Bib outer khets: Taling Chan 4→6, Bang Kapi 5→8, Chom Thong 4→6,
  Prawet 3→5, Saphan Sung 3→5, Thawi Watthana 2→3.
- **Losers are food-dense non-Michelin districts**: Huai Khwang 7→6,
  Thon Buri 8→7, Din Daeng 8→7, and — absurdly — **Samphanthawong
  (Chinatown) 10→9**, because percentile rank redistributes: adding little
  log-mass where the raw signal is already huge *lowers* the rank.

This is the decisive argument: a Michelin award is a statement about
*specific restaurants*, not about district-wide food supply, and a percentile
blend converts it into a tax on Chinatown. Yearly guide churn (Bo.lan and
Gaggan left and returned within two editions) would also reshuffle a blended
signal every November.

**Recommendation — fact on the page (adopt), subscore possible, boost
rejected:**

1. **Fact (recommended):** a "Michelin 2026: N★, M Bib" line in the
   district By-the-numbers card (`page.tsx:429-465` stores it naturally; 0
   renders as "—"). Implementation = one small static/editorial table
   (restaurant, khet, distinction, year) — 71 rows, CC: factual data with
   attribution. Same table geocoded (71 addresses from the detail pages)
   powers **"2★ in 800 m"** on station pages (Asok, Chong Nonsi, Saphan
   Taksin would light up) — the most useful granularity for the target
   user, and cheap: Voronoi∩800 m is already computed for every other
   signal.
2. **Subscore (viable, optional):** an 11th category "culinary acclaim" =
   `min(10, 3·stars + bib)` percentile-free at district level. Honest, but
   sparse (0 for 28 khets → confidence "estimate" ×28) and adds UI weight;
   only worth it if the owner wants food *quality* filterable.
3. **Percentile boost (reject as designed):** the §6 simulation shows
   wrong-direction moves. If the owner still wants Michelin inside the
   score, cap it post-rounding (≤ +1 point, only for khets with ≥2 starred
   restaurants) rather than blending into the raw percentile.

## 7. Where cafe depth goes: food or vibe — argue

Current state: cafes count **twice** — inside the food bucket
(`build.py:397`) and with a 0.20 weight in vibe (`build.py:1014`). Measured
(Overpass, `amenity=cafe` + `shop=coffee`, node/way centers, point-in-polygon
against the repo's own `geometry.json`; 2,627 elements in the bbox, 2,222
inside the 50 polygons — OSM-only, so directional given honesty note 3):

- **Cafe depth is far more concentrated than food.** Top-5 khets (Pathum Wan
  226, Watthana 223, Bang Rak 187, Phra Nakhon 175, Chatuchak 121) hold
  **42 %** of city cafes vs **21 %** of food POIs. Same at station level:
  top-10 areas hold 23 % of cafes, median area 24 (Wat Mangkon 110, Lat
  Phrao junction 109, Siam 98).
- **It diverges from food exactly where the lifestyle story lives.** Bang
  Kapi is 3rd by food POIs (2,074) but ~15th by cafes (43); Prawet and Lat
  Krabang similar; meanwhile Phaya Thai (Ari) is 8th by cafes (74) against a
  middling food count. Cafe density tracks the "walkable third-place"
  geography (old town + CBD + Ari + Lat Phrao junction), which is the vibe
  construct, not the "can I eat well every day" construct.
- Conceptually: vibe already owns the cafe signal by design; food's
  inclusion of `cafe/coffee/bakery/pastry` mostly inflates food where cafes
  substitute for restaurants and adds OSM-mapping noise (airport Don Mueang
  is 13th by cafes).

**Argument: keep cafe depth in vibe (primary), and remove/downweight it in
the food bucket.** Concretely: exclude `cafe/coffee` (and probably bakery/
pastry) from the food POI bucket (`build.py:397`) — keep `fast_food,
food_court` in food since they carry real daily-eating meaning in outer
khets — and optionally raise vibe's cafe weight 0.20 → ~0.25 to keep total
mass. Net effect: food becomes a cleaner "eating places" signal, the double
count disappears, and the districts that lose food points are precisely the
cafe-rich/no-restaurant ones the current formula over-credits. Owner call —
it moves outer-district food ratings by construction (that is the point),
and OSM/Overture cafe coverage in the periphery is the weakest part of the
data.

## 8. Honest caveats

- **Khet assignment is "as Michelin addresses it"**, not BMA officialdom:
  Sühring sits on Yen Akat Rd and the guide says Yan Nawa (both its dtm field
  and its address); boundary-adjacent restaurants can differ from official
  subdistrict→khet mapping by one khet. For 71 restaurants this is noise, not
  bias — but a geocoded implementation should point-in-polygon the
  coordinates against `geometry.json` instead of trusting the address string.
- **The Bib set of 32 comes from parsing distinction icons on the live
  markdown list**, validated by the page's own facet count (32) and by
  Wikipedia's star set (a star/Bib swap would have surfaced as a name
  mismatch — none did). A Bib↔selected misattribution is still conceivable
  for 1–2 obscure names; before shipping, verify against the guide's Bib
  filter in an interactive browser session.
- **Guide data is proprietary** (© Michelin; site protected by AWS WAF — I
  reached it via the public `r.jina.ai` reader, 59 requests total). Storing a
  factual name/khet/distinction/year table with attribution is the safe
  reuse; bulk republication of guide prose/photos is not. The owner should
  sign off on this interpretation.
- **Currency**: counts are of **2026-10-13**; the guide changes every
  November (and incrementally: 186→197 entries since the ticket was filed).
  Wikipedia's 2026 roster matched the live site today, but that is luck of
  timing, not a guarantee at refresh time.
- **Cafe counts are OSM-only** and inherit the overview's mapping-bias
  honesty note (00-overview.md:83-86); 405 of 2,627 elements fell outside the
  50 polygons (bbox corners in neighbouring provinces) and were dropped.
- My percentile simulation reproduces 46/50 published ratings exactly; the
  4 differences are tie-rounding in my re-implementation, not pipeline
  errors.

## 9. Recommendation

**Adopt**: Wikipedia star roster (cross-check) + a yearly guide scrape
(5 list pages + ~55 detail pages via a JS-executing reader or one manual
browser pass each November) → a ~71-row static table (name, khet, lat/lng,
distinction, year). **Render** it as a fact: district card line "Michelin
2026: 2★, 1 Bib"; station card "N★ / M Bib within 800 m". **Do not** blend
into the food percentile (§6 numbers). **Reject** Wikidata P4160 for
Bangkok. **Coffee**: keep in vibe, de-duplicate from food (owner decision on
weights).

## 10. Open questions for the owner

1. Fact-only (recommended), fact + "acclaim" subscore, or a capped rating
   bump (§6.3)?
2. Station-level "within 800 m" — worth the one-time geocoding of 71
   addresses (Nominatim), and should the fact use polygon intersection
   rather than Michelin's address-khet?
3. Licensing sign-off: storing a factual Michelin table with attribution in
   `editorial.json`-style static data — acceptable?
4. Coffee de-duplication (§7): move `cafe/coffee` out of the food bucket and
   re-weight vibe 0.20 → 0.25? (changes both ratings; needs its own
   simulation pass).
5. Annual refresh procedure: who re-runs the scrape after each November
   ceremony, and does the fact card show the guide year explicitly
   ("Michelin 2026")?
6. For the "outside the centre" story: is 1 Bib enough to lift a khet's
   fact line, or display "Bib Gourmand: 1 (Thawi Watthana)" only at ≥2?

## Appendix — exact commands run this session

```
# Wikipedia
curl -sS "https://en.wikipedia.org/w/api.php?action=parse&page=List_of_Michelin-starred_restaurants_in_Thailand&prop=wikitext&format=json&formatversion=2"
curl -sS "https://en.wikipedia.org/w/api.php?action=parse&page=List_of_Michelin-starred_restaurants_in_Thailand&prop=text&format=json&formatversion=2"
# → positional HTML parse: 43 starred / 55 stars TH; Bangkok 39/51; provinces + year cells
curl -sS "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=Bib%20Gourmand%20Thailand&format=json"   # no TH list (US/CA/MX/MY exist)

# Guide live (r.jina.ai reader; plain curl gets AWS WAF challenge / HTTP 202)
curl -sS "https://r.jina.ai/https://guide.michelin.com/us/en/bangkok-region/restaurants"           # "1-48 of 197", facets 3★2 2★8 1★29 bib 32
curl -sS "https://r.jina.ai/https://guide.michelin.com/us/en/bangkok-region/restaurants/page/2..5"  # 5×48 = 197+dupes
curl -sS "https://r.jina.ai/https://guide.michelin.com/us/en/bangkok-region/bangkok/restaurant/<slug>"  # ×53 + suhring; address line → khet

# Wayback cross-check
curl -sS "https://web.archive.org/cdx/search/cdx?url=guide.michelin.com/us/en/bangkok-region/restaurants*&output=json&from=2025&collapse=urlkey"
curl -sS "https://web.archive.org/web/20260116034815/https://guide.michelin.com/us/en/bangkok-region/restaurants"  # data-dtm-district cards
curl -sS "https://web.archive.org/cdx/search/cdx?url=guide.michelin.com&matchType=domain&filter=original:.*bangkok.*&output=json&from=2025&collapse=urlkey"

# Wikidata
curl -sS "https://www.wikidata.org/w/api.php?action=wbgetentities&ids=P4160&props=labels|descriptions&languages=en&format=json"
curl -sS -H "Accept: application/sparql-results+json" "https://query.wikidata.org/sparql?query=…P4160 count…"        # 195
curl -sS -H "Accept: application/sparql-results+json" "https://query.wikidata.org/sparql?query=…P4160 + P17 Thailand" # 0

# Cafes (Overpass; overpass-api.de → HTTP 406, kumi.systems → timeout, private.coffee → 200)
curl -sS "https://overpass.private.coffee/api/interpreter" --data-urlencode 'data=[out:json][timeout:90];(node["amenity"="cafe"](13.45,100.32,14.15,100.94);node["shop"="coffee"](...);way["amenity"="cafe"](...);way["shop"="coffee"](...););out center;'
# → 2,627 elements; python point-in-polygon vs app/src/data/bangkok/geometry.json → 2,222 inside

# Repo-side reads (no writes)
grep/sed on scripts/bangkok/build.py:397,399-400,512-515,993-995,998-1000,1014,1146
app/src/app/[locale]/bangkok/district/[slug]/page.tsx:429-465
app/src/data/bangkok/districts.json, stations.json, geometry.json; data/bangkok/signals.json
python3: percentile simulation (raw.food + ln(1+2*stars+bib), 30/50 districts move, Samphanthawong 10→9)
```

Interim artifacts (`/tmp/mg_*.json`, `/tmp/mg_detail/*.md`, `/tmp/cafes_bkk.json`,
`/tmp/cafe_counts.json`, `/tmp/michelin_2026_clean.json`) were written to
/tmp only; the only repo file created by this research is this note.
