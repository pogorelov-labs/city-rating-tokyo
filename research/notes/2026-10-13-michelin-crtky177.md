# Michelin Tokyo + Tabelog + kissaten depth as a Tokyo food-quality layer (CRTKY-177)

Researched: **2026-10-13**, by the open-data research agent. Context: the Tokyo
`food` category (`scripts/compute-ratings.py:342-355`) is a pure quantity
signal — `0.6·log1p(HotPepper total) + 0.4·log1p(OSM food ≤800 m)` —
percentile-ranked across the 1,493 stations (`log_percentile_normalize`,
`compute-ratings.py:539-540,566`); OSM "food" already includes
`amenity~restaurant|cafe|fast_food` (`scripts/scrapers/scrape-osm-pois.py:30-33`),
and HotPepper cafés carry a 0.15 weight in vibe (`compute-ratings.py:467-483`).
This note evaluates adding a *quality* layer (Michelin stars + Bib Gourmand),
rules on Tabelog as a scraping source, measures kissaten/coffee depth from OSM,
and prices the two composition options (fact on the station page vs boost).
Format and method mirror the Bangkok precedent
`research/bangkok/notes/2026-10-13-michelin-crtky142.md` — that note is the
template for the yearly scrape procedure proposed in §7. All network checks
below were run by me in this session; commands are quoted in the appendix.
Nothing here is an implementation decision — the owner adopts sources.

**TL;DR.** Michelin data for Tokyo is reachable and current: the live
`guide.michelin.com` Tokyo region (via the `r.jina.ai` reader, same as
Bangkok) reports **3★ = 11, 2★ = 26, 1★ = 119 (156 starred), Bib Gourmand =
111, "1-48 of 553 restaurants"** — and, unlike Bangkok, the Tokyo site honours
*path-style* distinction filters server-side
(`/restaurants/bib-gourmand` → "of 111 restaurants"), so the whole roster is
8 list fetches. Wikipedia's *List of Michelin-starred restaurants in Tokyo*
exists (rev 2026-07-01) but is **2★/3★-only by its own maintenance template**:
its 2026 column holds just **54 of the ~160** starred restaurants, mapped to
**8 of 23 wards** (Minato 25, Chūō 14 — 72 % in two wards), and **Wikipedia
has no Bib Gourmand list for Japan at all** (only US/CA/MX/MY/NZ exist). The
star/Bib spread is exactly what the ticket suspected: stars are core-only
(8 wards, all inside the Yamanote loop area), while a 22-restaurant Bib
sample resolves to **11 wards including Ōta, Setagaya (Yoga), Suginami
(Kōenji/Ogikubo), Toshima and Sumida** — Bib does reach out. **Tabelog:
reject.** `terms.tabelog.com` does not even resolve; the live terms at
`tabelog.com/en/help/rules` §9(1)[1] prohibit "**storing** … the information
provided by Tabelog by copying or any other means **without the Company's
prior consent**" — storage is what a pipeline does. Coffee: the ask's
`cuisine=coffee_shop + name~珈琲|コーヒー|焙煎` combo yields **2,291 + 1,367 →
1,006 strict / 2,652 union** elements in the bbox; catchment counts peak at
Shinjuku 100, Kanda 72, Ginza 67 — and the citywide median across 1,493
stations is **0** (852 stations have no matching venue at all). **Recommendation:
do NOT fold Michelin into the food percentile** (15+ of 23 wards have no
confirmed Michelin listing; a blend re-moves everyone while informing no one —
same wrong-direction arithmetic as the Bangkok simulation); render it as a
**fact**: ward line "Michelin 2026: N★, M Bib" and station line "N★ / M Bib
within 800 m". Price: one geocoding pass over **267 addresses** (156 starred +
111 Bib — the ticket's "~200" understates it), ≈ 4.5 min on Nominatim at
1 req/s, once per guide year.

---

## 1. What the Tokyo pipeline does today (code refs)

- **Food signal** — `scripts/compute-ratings.py:342-355`:
  `raw["food"][slug] = 0.6·log1p(hotpepper_total) + 0.4·log1p(osm_food_count)`;
  confidence "strong" when both sources present. Rating = station-level
  percentile (`log_percentile_normalize`, `compute-ratings.py:539-540`,
  applied at `:566`).
- **What counts as food** — `scripts/scrapers/scrape-osm-pois.py:30-33`:
  `node/way["amenity"~"restaurant|cafe|fast_food"]` within `food_r` (800 m).
  **Cafes — kissaten included — already flow into food.**
- **Cafe in vibe** — `compute-ratings.py:470-475`: vibe adds
  `0.15·log1p(hotpepper_cafe_count)` (HotPepper `cafe_count`,
  `scripts/scrapers/scrape-hotpepper.py:125`). Note the sources differ: vibe's
  cafe count is HotPepper's, food's cafe share is OSM's — no OSM cafe
  double-count *within* one source, but the kissaten layer exists in neither
  bucket as a *quality/depth* signal.
- **Where a fact could render** — station page description block
  "Food & cafes" (`app/src/app/[locale]/station/[slug]/page.tsx:485-490`); the
  same page template takes numeric facts the way Bangkok's district card does
  (`page.tsx:429-465` precedent in crtky142).

## 2. Source A — Wikipedia Tokyo star list (verified, partial — adopt as cross-check only)

`https://en.wikipedia.org/wiki/List_of_Michelin-starred_restaurants_in_Tokyo`
(the hyphenated title; the un-hyphenated variant is **missing** — verified via
`action=query`), last revision **2026-07-01**. The intro states: *"As of the
2026 Michelin Guide, there are 160 restaurants in the Greater Tokyo Area with
a Michelin star rating."* Availability findings for the ask:

- The page carries three tables (2008–2010, 2011–2020, 2021–2026), each
  `Name / Cuisine / Location ("Tokyo – Ward") / year-columns`, star cells as
  `{{Michelin stars table cell|stars=N}}` with `colspan` cells for
  "closed" spans — parsed positionally (colspan-aware).
- **But the page has a standing maintenance template**:
  `{{Missing information|List|one-star ratings|date=February 2026}}`. Its
  2026 column therefore holds only **54 starred restaurants** (12×3★,
  26×2★, 16×1★ legacy rows) against the guide's ~160 — the ~106 missing are
  one-stars.
- **Bib Gourmand: not on Wikipedia for Japan at all.** `list=search
  intitle:"Bib Gourmand"` returns lists for the United States, Canada,
  Mexico, Malaysia, New Zealand — **no Tokyo/Japan page** (same search that
  in crtky142 confirmed the Thailand gap).
- Cross-check against the live guide (§3): wiki 2026 2★ set matches the
  live 26 **name-for-name** (only "Ginza Koju"/"Ginza Kojyu" spelling
  differs); 3★ matches 11-of-11 live names plus **Sézanne** (§3.2). So the
  wiki roster is accurate for what it covers — it just doesn't cover 1★
  or Bib.

Ward table from the wiki 2026 column (54 starred restaurants / 104 stars):

| Ward (23区) | 3★ | 2★ | 1★ | starred rest. | stars |
|---|---:|---:|---:|---:|---:|
| Minato | 6 | 10 | 9 | 25 | 47 |
| Chūō | 2 | 8 | 4 | 14 | 26 |
| Shibuya | 0 | 3 | 1 | 4 | 7 |
| Chiyoda | 1 | 2 | 0 | 3 | 7 |
| Meguro | 1 | 1 | 1 | 3 | 6 |
| Shinjuku | 1 | 1 | 0 | 2 | 5 |
| Taito | 0 | 1 | 1 | 2 | 3 |
| Shinagawa | 1 | 0 | 0 | 1 | 3 |
| **Total (8 of 23 wards)** | **12** | **26** | **16** | **54** | **104** |

3★ roster (wiki 2026): Minato — Kadowaki, Kanda, L'Effervescence, Myojaku,
Ryugin, Sazenka; Chūō — Harutaka, L'Osier; Meguro — Joël Robuchon Tokyo;
Shinjuku — Kagurazaka Ishikawa; Shinagawa — Quintessence; Chiyoda — Sézanne.

Verdict: **adopt as the yearly cross-check roster** (structured, stable URL,
CC BY-SA), **not** as the primary source — it structurally cannot supply
1★ or Bib.

## 3. Source B — guide.michelin.com live pages (verified, adopt as primary)

### 3.1 Access mechanics

Same as Bangkok (crtky142 §3.1): plain `curl` hits the AWS WAF; the default
`r.jina.ai` markdown reader executes the challenge and works (every fetch
HTTP 200 this session). New Tokyo-specific finding: **path-style distinction
filters are server-rendered**, unlike Bangkok's query-param filter:

- `…/us/en/tokyo-region/restaurants` → "Tokyo : 1-48 of 553 restaurants"
- `…/restaurants/bib-gourmand` (+ `/page/2`, `/page/3`) → "of 111 restaurants - Bib Gourmand"
- `…/restaurants/3-stars-michelin` → "of 11 restaurants - 3 Stars"
- `…/restaurants/2-stars-michelin` → "of 26 restaurants"
- `…/restaurants/1-star-michelin` (+ `/page/2`, `/page/3`) → "of 119 restaurants - 1 Star"

The whole 2026 inventory is therefore **8 list fetches**; cards parse as
`### [Name](…/restaurant/slug)` headings with the icon run above
(`michelin-star_8519.svg` per star, `symboleBibendum` for Bib) — the Bangkok
parser, bounded to the `# Tokyo :` section so "related content" links from
other guides' regions (Texas, …) don't leak in.

### 3.2 Live inventory (2026-10-13)

| Distinction | Count | Cross-check |
|---|---:|---|
| 3 stars | 11 | wiki 12 incl. Sézanne — see below |
| 2 stars | 26 | = wiki's 26, name-for-name ✓ |
| 1 star | 119 | wiki has only 16 legacy 1★ rows |
| starred total | **156** | wiki intro says 160 (Greater Tokyo) |
| Bib Gourmand | **111** | = the page's own facet ✓ (my card parse got 110 — one card lost to a section cut; ±1) |
| selected (no icon) | 286 | 156+111+286 = 553 ✓ |

**The Sézanne discrepancy** (the only 3★ name that differs): Sézanne
(Four Seasons Marunouchi, wiki 2026 3★ per the Time Out ceremony article,
which reports the November 2025 reveal) is **absent from every live
tokyo-region list today**, and its expected detail URL returns "Restaurant
not found" — while web sources from March 2026 show the restaurant open.
So today the guide site shows 11×3★/156 starred where the ceremony roster
says 12×3★/~160. Take-away for the implementation: **neither source is a
single point of truth** — scrape both, reconcile, and stamp the guide year
on the fact card.

### 3.3 Ward resolution (two validated methods)

- **Wayback `data-dtm-district`** — snapshot
  `web.archive.org/web/20250317130533/…/tokyo-region/restaurants` is
  server-rendered HTML with per-card `data-dtm-district` in "XX-ku" form
  (50 cards: Minato-ku 18, Chuo-ku 6, Shinjuku-ku 6, Meguro-ku 4, Bunkyo-ku 2,
  Shinagawa-ku 2, Shibuya-ku 1, …). Confirms the crtky142 method works for
  Tokyo, but only page 1 is archived.
- **Detail-page address line** — each detail page (via `r.jina.ai`, ~3 s
  spacing) carries e.g. `3-25-7 Sumida, Sumida-ku, Tokyo, 131-0031, Japan`;
  the `<ward>-ku` field is a one-regex extraction (verified on 22 Bib pages:
  20 auto + 1 manual = **21/22 resolved**, 1 fetch failed).

### 3.4 Bib spread outside the centre (21 resolved Bib sample, every 5th entry)

| Ward | Bib in sample | | Ward | Bib in sample |
|---|---:|---|---|---:|
| Shibuya-ku | 4 | | Meguro-ku | 1 |
| Toshima-ku | 3 | | Sumida-ku | 1 |
| Minato-ku | 3 | | Ōta-ku | 1 |
| Chūō-ku | 2 | | Bunkyō-ku | 1 |
| Setagaya-ku | 2 | | Shinjuku-ku | 1 |
| Suginami-ku | 2 | | **11 wards / 21 Bib** | |

Examples of out-of-core Bib: Tonkatsu Enraku (Ōta, Ikegami), LANBRoA
(Setagaya, Yoga), Sennomago (Suginami, Nishi-Ogikubo), Tensuke (Suginami,
Kōenji), Shutei Tanaka (Sumida). **Conclusion: the ask's expectation holds —
stars only in 8 central wards (wiki-complete for 2★/3★), while Bib spreads to
≥14 of 23 wards** (8 star wards ∪ 6 new wards from a 21-item sample; the full
111-item mapping will add more). This mirrors Bangkok: Bib is the
"outside the centre" signal.

## 4. Source C — Tabelog (checked, **reject**)

Tabelog (kakaku.com) is the natural Japanese food-*quality* source (5-point
community scale), so this verdict matters: **the pipeline must not scrape it.**

- The ask's URL **`terms.tabelog.com` does not exist**: `curl` fails with
  "Could not resolve host" (DNS NXDOMAIN, checked 2026-10-13). The live
  canonical terms are at `https://tabelog.com/en/help/rules` (HTTP 200,
  fetched this session; linked from `s.tabelog.com` as "Terms of Use").
- **§9 Prohibited Acts, clause [1]** (verbatim from the fetched EN terms):
  > "[1] Reproducing, duplicating, sending, transferring, distributing,
  > reselling, **or storing for the purpose of such use, the information
  > provided by Tabelog by copying or any other means without the Company's
  > prior consent**, except as specifically permitted by law, these Terms of
  > Use or the guidelines;"

  A pipeline's static data file is "storing … by any other means without
  prior consent" — squarely prohibited, with no crawler-specific carve-out.
- Supporting clauses: the IP section ("The Customer must not reproduce, edit,
  modify, publish, reprint, publicly transmit, distribute, sell, translate,
  adapt, publicly display or otherwise utilize or use Tabelog or its content
  in any manner, unless authorized…") and §2 [2] (reviews are non-licensed to
  third parties). `robots.txt` (fetched) disallows only a few paths for
  `User-agent: *` — permissive robots do **not** license storage; the terms
  govern.
- Consequence for the product: no Tabelog score per restaurant/station, now
  or annually. The quality layer must come from Michelin (§3) + OSM
  kissaten depth (§5) + optional editorial.

## 5. Kissaten / specialty coffee — Overpass counts (verified, adopt as an OSM layer)

Queries on the Tokyo bbox `35.5,139.2,36.0,139.9` (mirror status: 
overpass-api.de → SSL error, kumi.systems → 504, **private.coffee → 504 on
first try, 200 on retry** — the Bangkok note's mirror behaviour reproduces;
retry with backoff):

- **A** `cuisine=coffee_shop` (node+way, `out center tags`): **2,291**
  (2,223 nodes, 68 ways).
- **B** `amenity=cafe`/`shop=coffee` with `name~"珈琲|コーヒー|焙煎"`: **1,367**
  (1,286 cafe, 81 shop=coffee).
- **A∩B (the ask's strict combo)**: **1,006**. **A∪B**: **2,652**.

Interpretation caveat (verified, important): the name regex is a
*kissaten/Japanese-name* filter, not a coffee-depth filter — it excludes
Starbucks/Blue Bottle-style roman names but **includes Doutor chains**
(ドトールコーヒーショップ contains コーヒー). Calibration against plain
`amenity=cafe` within 800 m (separate `out count` queries): Kiyosumi-shirakawa
19 total cafes vs 5 in my union; Nakameguro 41 vs 13; Kōenji 45 vs 9 — i.e.
the regex layer misses ~70–80 % of cafes at specialty-coffee stations. Use it
as the **kissaten signal**, not as "coffee depth" overall.

### 5.1 Catchment counts, 16 sample stations (800 m circles)

| Station | union A∪B | strict A∩rx | | Station | union | strict |
|---|---:|---:|---|---|---:|---:|
| Shinjuku | 100 | 25 | | Ueno | 41 | 15 |
| Kanda | 72 | 27 | | Asakusa | 29 | 11 |
| Ginza | 67 | 26 | | Ebisu | 20 | 6 |
| Shibuya | 66 | 19 | | Sugamo | 10 | 5 |
| Shimbashi | 64 | 18 | | Nakameguro | 13 | 2 |
| Jimbōchō | 53 | 19 | | Kōenji | 9 | 2 |
| Ikebukuro | 60 | 17 | | Kichijōji | 34 | 8 |
| | | | | Nishi-Ogikubo | 4 | 1 |
| | | | | Kiyosumi-shirakawa | 5 | 1 |

### 5.2 Citywide distribution (all 1,493 stations, 800 m, union set)

- Top-12: Shinjuku 100, Awajichō 95, Shinjuku-Nishiguchi 95,
  Shinjuku-Sanchōme 87, Seibu-Shinjuku 75, Kanda 72, Mitsukoshimae 72,
  Suehirochō 71, Iwamotochō 70, Higashi-Ginza 69, Akihabara 68,
  Uchisaiwaichō 68.
- **Median 0, mean 4.3, 852 of 1,493 stations have zero** matching venues.
  Kissaten density is a CBD/Yamanote-core phenomenon — far more
  concentrated than the food signal itself (crtky142 found the same for
  Bangkok cafes: concentration ≫ food POI spread).

Verdict: **adopt** the kissaten layer as OSM data (ODbL, no ToS issue,
already inside the existing Overpass pass); it is a "depth/character" fact
(kissaten-count or per-1000-POI share), not a food-percentile ingredient —
same placement argument as Bangkok's café question (crtky142 §7), with the
extra Tokyo nuance that chains pollute the strict combo.

## 6. Composition: fact on the page vs boost

**Fact (recommended).** Two granularities, same static annual table
(name, ward, lat/lng, distinction, guide year — ~267 rows):

- *Ward/district line*: "Michelin 2026: 2★, 3 Bib" — **needs no geocoding**;
  the ward comes free from the guide's address line (§3.3), with a
  point-in-polygon check against ward polygons as validation.
- *Station line*: "N★ / M Bib within 800 m" — the useful one for the target
  user (Ginza, Shimbashi, Hibiya, Kagurazaka-area and Meguro stations light
  up; 852 outer stations show nothing). Requires coordinates.

**Geocoding volume (the ask's estimate request):** the roster is **267
addresses** (156 starred + 111 Bib), not ~200 — the ticket's figure covers
roughly the starred set alone. One-off per guide year:
267 Nominatim requests at 1 req/s ≈ **4.5 minutes** (within Nominatim's
usage policy at this scale); detail-page addresses are the input (already
fetched during the scrape — the markdown carries no embedded coordinates, so
Nominatim is required). Subsequent years only re-geocode new/changed entries
(guide turnover ~10–15 %/yr).

**Annual scrape volume (same procedure as crtky142 §9):** 8 list fetches
(§3.1) + up to 267 detail fetches at ~3 s spacing ≈ 15 min + the Nominatim
pass ≈ 5 min. Wikipedia's roster cross-checks 2★/3★ names for free (§2).
Everything lands in a static file reviewed once a year — one person-hour
scale, like Bangkok.

**Boost (reject).** The Bangkok simulation (crtky142 §6) showed a
`ln(1+2·stars+bib)` percentile blend *lowers* food-dense non-Michelin
districts (Chinatown 10→9) because percentile rank redistributes. Tokyo is
more extreme: **≥15 of 23 wards have no confirmed Michelin listing at all**
(only 8 star wards + Bib-sample wards are known positives), and the signal
lives in 2 wards (72 % of wiki stars). A station-level blend over 1,493
stations would move most stations while adding information for maybe a few
dozen central catchments, and the November churn (Myojaku's 2→3★
promotion; Sézanne appearing/disappearing between roster and live site)
would reshuffle it every year. If the owner still wants Michelin inside the
score, the Bangkok fallback applies: post-rounding cap (≤ +1, only stations
with ≥1 starred restaurant in 800 m), never a raw-percentile blend.

## 7. Recommendation

1. **Adopt** the Michelin layer as a *fact*: static annual table
   (name, ward, lat/lng, distinction, year; 267 rows) from the 8-fetch live
   scrape + address-line wards + one Nominatim pass; render ward line
   "Michelin 2026: N★, M Bib" and station line "N★ / M Bib within 800 m"
   (station page template `page.tsx:485-490` area). Wiki roster = cross-check.
   © Michelin is proprietary — factual table with attribution, owner
   sign-off required (same interpretation as crtky142 §8).
2. **Reject** Tabelog outright (terms quote in §4) — no scraping, no storage,
   no exceptions without a licence from kakaku.com.
3. **Adopt** the OSM kissaten layer (§5) as a coffee-depth/kissaten fact,
   not a food input; if "coffee depth" is wanted, use plain `amenity=cafe`
   counts and keep the 珈琲-regex subset as the kissaten character signal.
4. **Reject** folding Michelin into the food percentile (§6).

## 8. Honest caveats

- **Wikipedia Tokyo list is incomplete by design** (no 1★, no Bib); all
  current-year Bib/1★ numbers above come from the live guide site and are
  point-in-time 2026-10-13.
- **Guide-site noise**: Sézanne missing from the live lists while present in
  the ceremony roster and wiki; wiki intro 160 vs live facet 156; my Bib card
  parse 110 vs facet 111. Reconciliation at refresh time is mandatory.
- **Bib ward spread is a 21/22 sample** (every 5th entry), not the full 111;
  ward totals will grow with full mapping. The 1★ ward table is likewise
  partial (wiki's 16 legacy 1★ only) — full 1★ ward mapping comes free with
  the implementation scrape (156 detail pages).
- **Wayback dtm-district snapshot is the 2025-03 guide** (50 cards); used as
  method validation, not as current data.
- **OSM kissaten counts inherit mapping bias** (`research/00-overview.md:83-86`
  honesty note): outer-ward cafe coverage is the weakest; the 852 zero-stations
  include genuinely cafe-less suburbs but also under-mapped ones.
- The strict combo double-counts Doutor-type chains into "kissaten" — any
  character index must filter chains by name list.

## 9. Open questions for the owner

1. Fact-only (recommended) or fact + capped post-rounding bump for starred
   stations?
2. Licensing sign-off: static 267-row Michelin factual table with
   attribution (© Michelin) — acceptable, as in Bangkok?
3. Station fact thresholds: show "N★ / M Bib within 800 m" at any N≥1, or
   hide at 0 (852 stations will show nothing)?
4. Kissaten layer: which metric — raw count, count share of food POIs, or a
   named-list curated kissaten set to exclude Doutor/Starbucks?
5. Annual refresh owner: who re-runs the 8-fetch scrape + Nominatim pass
   after each November ceremony, and does the card stamp "Michelin 2026"?
6. Should the Bib full-ward mapping (111 detail fetches) be done once now to
   replace the 21-sample spread table in §3.4?

## Appendix — exact commands run this session

```
# Repo reads (no writes)
sed -n 30,70p / 100,130p scripts/scrapers/scrape-osm-pois.py      # food bucket = amenity~restaurant|cafe|fast_food
grep -n food / scripts/compute-ratings.py                          # :342-355 blend, :467-483 vibe cafe 0.15, :539-566 percentile
grep -n food scripts/scrapers/scrape-hotpepper.py                  # cafe_count source
python3: 16 sample stations from data/stations.json (1,493 rows, lat/lng)

# Wikipedia
curl -sS "…/w/api.php?action=query&titles=List of Michelin starred restaurants in Tokyo&prop=revisions"   # missing:True
curl -sS "…/w/api.php?action=query&titles=List of Michelin-starred restaurants in Tokyo|…&prop=revisions" # exists, rev 2026-07-01
curl -sS "…/w/api.php?action=parse&page=List of Michelin-starred restaurants in Tokyo&prop=wikitext"      # 105,957 chars → colspan-aware parse
curl -sS "…/w/api.php?action=query&list=search&srsearch=intitle:%22Bib Gourmand%22"                        # US/CA/MX/MY/NZ only, no Japan

# Live guide (r.jina.ai reader; plain curl = WAF)
curl -sS "https://r.jina.ai/https://guide.michelin.com/us/en/tokyo-region/restaurants"                     # 553, facets 3★11 2★26 1★119 bib111
curl -sS "…/r.jina.ai/…/tokyo-region/restaurants/bib-gourmand{,/page/2,/page/3}"                           # 111
curl -sS "…/r.jina.ai/…/tokyo-region/restaurants/{3-stars-michelin,2-stars-michelin,1-star-michelin,/page/2,/page/3}"  # 11/26/119
curl -sS "…/r.jina.ai/…/tokyo-region/tokyo/restaurant/sezanne"                                             # "Restaurant not found"
curl -sS "…/r.jina.ai/…/tokyo-region/tokyo/restaurant/<slug>" ×22                                          # Bib ward sample, address line regex
curl -sSL "https://web.archive.org/web/20250317130533/…/tokyo-region/restaurants"                          # data-dtm-district cards (2025-03)
curl -sSL "https://web.archive.org/web/20251024032647/…/timeout.com/…/michelin-guide-tokyo-…-092925"       # 2026 ceremony (Myojaku 3★)

# Tabelog
curl -sSL "https://tabelog.com/en/help/rules"          # HTTP 200; §9[1] storage prohibition quoted in §4
curl -sS "https://terms.tabelog.com/"                  # DNS NXDOMAIN
curl -sS "https://tabelog.com/robots.txt"              # generic-crawler paths mostly allowed; ToS governs

# Overpass (private.coffee; 504 → retry 200; overpass-api.de SSL err; kumi 504)
[out:json][timeout:180];(node["cuisine"="coffee_shop"](35.5,139.2,36.0,139.9);way[…];);out center tags;   # 2,291
[out:json][timeout:180];(node/way["amenity"="cafe"]["name"~"珈琲|コーヒー|焙煎"](bbox);node/way["shop"="coffee"][…](bbox););out center tags;  # 1,367
[out:json][timeout:60]; 3× (node/way["amenity"="cafe"](around:800,lat,lng););out count;                   # 19/41/45 calibration
# local python: strict 1,006 / union 2,652; per-catchment tables §5.1-5.2 (equirect 800 m)
```

Interim artifacts (`/tmp/mtl_*`, `/tmp/tk_*`) live in /tmp only; the only
repo file created by this research is this note.
