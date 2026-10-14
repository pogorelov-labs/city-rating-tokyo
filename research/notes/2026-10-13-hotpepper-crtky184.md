# De-risking the HotPepper mono-dependency (Tokyo) — second-source verdicts + resilience sketch (CRTKY-184)

Researched: **2026-10-13**, by the open-data research agent. Addresses the
documented **risk #8** (`CLAUDE.md:36`): *"HotPepper API is a **single-vendor**
dependency for food/nightlife signals; no automated fallback is
implemented."* Not an implementation decision — the owner adopts sources and
merge rules.

**TL;DR:** The primary is healthy today (live probe: HotPepper returns
`api_version 1.30`), but the blast radius is **four categories, not two** —
food (0.6 weight), nightlife (0.60 weight + the *only* nightlife cap input),
vibe (cafe 0.15) and crowd (unmanned-station proxy) all read the `hotpepper`
table (`compute-ratings.py:343-374,474,495-499`). An HP outage would not
break the build: it would silently re-stamp `data_date` to the run month over
5-month-old rows (the committed export has said `data_date: '2026-04'` for
all 1493 entries since April — **no alerting exists, and the staleness is
live in `app/src/data/demo-ratings.ts` today**). Of the ticket's five
candidates: **ぐるなび = dead** for self-serve (portal 404/403 history,
corporate-only), **楽天 = no venue API at all** (Recipe APIs are live but are
recipe *content*), **Yelp = alive but the free tier shrank 10–16×**
(5,000→500/day in 2023; Places Starter 300/day — unusable for 1,493-station
sweeps), **Tabelog = no public API** (re-confirmed), **Foursquare OS Places =
alive and actively maintained** (HF `foursquare/fsq-os-places`, Apache-2.0 +
attribution, monthly releases, last 2026-09-15) but HF-gated — the same
accept-terms decision as Bangkok **CRTKY-137**, one decision serves both
cities. The **practical second source is Overture Places**, already accepted
and coded in-repo for Bangkok (`scripts/bangkok/fetch.py:260-288`, release
`2026-09-23.1`, CDLA Permissive 2.0) — porting it to Tokyo costs no new
vendor relationship. OSM-only fallback is survivable but ugly: nightlife
caps **every** station below 8 (cap input is HP `midnight` alone) and food
`strong` goes 783 → 0. Resilience items (per-source vintage in `data_date`,
freshness canary, runbook) are pipeline-local and cheap — **they should land
regardless of source choice.**

---

## 0. What was actually verified (method, date, commands)

All external probes ran **2026-10-13** from this session. Live commands and
outputs (verbatim excerpts):

| Probe | Command (abbreviated) | Result |
|---|---|---|
| HotPepper primary liveness | `curl "https://webservice.recruit.co.jp/hotpepper/gourmet/v1/?key=INVALID&lat=35.68&lng=139.76&range=3&count=1&format=json"` | `HTTP 200`, `{"api_version":"1.30","error":[{"code":2000,"message":"APIキーが正しくありません"}]}` — service up, structured error |
| Gnavi API portal | `curl -A "Mozilla/5.0 …" https://api.gnavi.co.jp/api/` | `HTTP 403` CloudFront block ("Request blocked"), even with browser UA |
| Gnavi portal history | `curl "http://archive.org/wayback/available…"` + CDX `url=api.gnavi.co.jp/api*` | captures: **404 on 2023-05-18**, **403 on 2025-06-09 / 2025-09-25 / 2025-11-14** — the portal has not served public docs since at least 2023-05 |
| Rakuten Web Service catalog | `curl https://webservice.rakuten.co.jp/documentation` + text extraction | `HTTP 200`; catalog = **Ichiba / Books / Travel / Recipe / Kobo / GORA only — no restaurant/venue search API** |
| Rakuten Recipe CategoryList | `curl "https://app.rakuten.co.jp/services/api/Recipe/CategoryList/20170426?applicationId=INVALIDAPPID&format=json"` | `HTTP 400 {"error_description":"specify valid applicationId"}` — **alive** |
| Rakuten Recipe CategoryRanking | `…/Recipe/CategoryRanking/20170426?applicationId=INVALIDAPPID&categoryId=30` | `HTTP 400 {"error_description":"specify valid applicationId"}` — **alive** |
| Yelp Fusion v3 | `curl https://api.yelp.com/v3/businesses/search?latitude=35.6938&longitude=139.7036… -H "Authorization: Bearer INVALIDKEY"` | `HTTP 400 {"error":{"code":"VALIDATION_ERROR",…}}` — **endpoint alive**; real sample query **NOT RUN** (no `YELP_API_KEY` in this environment) |
| Yelp docs (old hosts) | `docs.yelp.com/docs/business-search-overview` → **410 Gone**; `www.yelp.com/developers/documentation/v3/business_search` → **404**; `docs.developers.yelp.com` → NXDOMAIN from this network | docs migrated |
| Yelp docs (current) | `curl https://docs.developer.yelp.com/llms.txt` (HTTP 200) + `…/docs/places-rate-limiting.md`, `…/docs/plans.md`, `…/changelog/fusion-daily-rate-limits-changed.md` | see §2.3 |
| Foursquare OS Places | `curl https://huggingface.co/api/datasets?search=foursquare` | `foursquare/fsq-os-places` — **gated: auto, lastModified 2026-09-15, 21,702 downloads**; `curl …/raw/main/README.md` → `HTTP 401 "Access to dataset … is restricted"` (gated, needs HF account + terms) |
| Foursquare access model | fetched Foursquare's post `medium.com/@foursquare/evolving-fsq-os-places-fa7a3f5197cd` (published **2025-10-08**) | see §2.4 |
| Tabelog public API | multiple web searches (JA+EN) | **no developer portal / public API found** — negative result |
| Overture license | `WebFetch https://docs.overturemaps.org/attribution/` | Places = **CDLA Permissive 2.0** (plus Apache-2.0 / CC0-1.0 per provider); other themes ODbL |
| OSM live counts | Overpass `out count`, bbox `35.5,139.2,36.0,139.9`, mirror `maps.mail.ru` (busy-aware retries; see the CRTKY-176 note §1 for the mirror playbook) | see §3.2 |

Not verified in this run (stated as such): **any authenticated sample query**
(no `YELP_API_KEY`, no HF token, no valid HP key in this environment);
NocoDB live reads (no `NOCODB_API_TOKEN` — the HP table's current
`scraped_at` spread is unknown); the HP key *registration* flow; the
"Rakuten RapidAPI marketplace shut (2021)" background (not re-verified; the
authoritative evidence used is the live Rakuten Web Service catalog);
Overture Tokyo per-station counts (needs one duckdb pass against
`s3://overturemaps-us-west-2`).

## 1. How much HotPepper actually matters today (code evidence)

`scripts/compute-ratings.py` reads the `hotpepper` table in **four** places
— risk #8's "two categories" understates it:

1. **food** — `raw = log1p(hp_total)*0.6 + log1p(osm_food)*0.4`
   (`compute-ratings.py:343-345`). Confidence: `strong` requires **both**
   hp>0 and osm>0; `moderate` requires **hp>0**; there is **no OSM-only
   branch** — hp=0 forces `estimate` with empty sources
   (`compute-ratings.py:347-355`).
2. **nightlife** — HP terms are `midnight*0.25 + izakaya*0.20 + bar*0.15`
   = **0.60 of the raw weight**; OSM terms are
   `night*0.15 + nightclub*10*0.10 + karaoke*5*0.08 + hostel*10*0.07`
   (`compute-ratings.py:365-372`). And the **absolute cap** uses only HP:
   `cap_raw["nightlife"] = midnight` (`compute-ratings.py:374`) against
   thresholds **8≥20 / 9≥100 / 10≥300**
   (`packages/schema/python/city_rating_schema/constants.py:105`).
3. **vibe** — `cafe_count` (HP) is 0.15 of the main path and part of the
   composite fallback (`compute-ratings.py:474,483`).
4. **crowd** — HP `total_count*300` is the fallback proxy for the 55
   unmanned stations MLIT never reports (`compute-ratings.py:495-499`,
   `CLAUDE.md:204`).

Food's cap, by contrast, is `hp_total + osm_food`
(`compute-ratings.py:346`, thresholds 100/400/1000 at
`constants.py:104`) — so OSM alone *keeps some* 8-tier headroom in hubs.

### 1.1 Current reliance, measured from the committed export

`app/src/data/demo-ratings.ts` (the last refresh output; all entries carry
`data_date: '2026-04'` — grep count `1493`) records per-station `sources`.
Counted with `grep -o … | sort | uniq -c` (2026-10-13):

| food sources | n | | nightlife sources | n |
|---|---|---|---|---|
| `['hotpepper','osm']` | **783** | | HP-dependent (any `hotpepper*`) | **732** |
| `['hotpepper']` | **78** | | `['osm']` (all-OSM survivors) | **36** |
| `[]` (hp=0 **and** osm=0) | 422 | | `[]` (no signal at all) | 479 |
| `['ai_research']` | 210 | | `['ai_research']` | 246 |

So today **861/1493 (57.7%)** of stations put HP in their food sources and
**732/1493 (49.0%)** in nightlife (≈ **67% / 59%** of computed-only
entries). The **422 `food: []`** stations are worth a flag of their own:
they already get rating ~1–2 from ties at raw=0 — that is an
outer-Tokyo *data* hole (both sources zero), not a merge bug.

### 1.2 One repo gap found on the way: the midnight scraper is not committed

`grep -rn midnight scripts/` shows `midnight_count` is **read** by
compute/datamart but **written by no committed script** — the only HP
scraper in the repo queries total/izakaya/bar/cafe only
(`scrapers/scrape-hotpepper.py:91-126`; the midnight pass was PR #29 per
`research/00-overview.md:46`). If the NocoDB column were ever lost, the
strongest nightlife signal (0.25 weight **and** the sole cap input) could
not be regenerated from the repo. This is a one-file fix and belongs with
the resilience work below.

## 2. Source-by-source verdicts (live 2026-10-13)

### 2.1 ぐるなび (Gnavi) — **reject: dead for self-serve**

- Live: `api.gnavi.co.jp/api/` → CloudFront **403** (browser UA included);
  cannot read the portal from this network.
- Wayback CDX: the portal returned **404 in the 2023-05-18 capture** and
  **403 (CloudFront block) in 2025-06/09/11 captures** — public docs have
  been gone ≥ 3 years.
- Web search (corporate.gnavi.co.jp FAQ, surfaced via search; page itself
  blocks crawling): the free ぐるなびWebサービス has **ended**; corporate
  access is by separate paid agreement.
- Verdict: no free tier, no registration path → **reject**. Do not revisit
  without a budget line.

### 2.2 楽天グルメ / 楽天レシピ — **reject as a food/nightlife source**

- Live: `webservice.rakuten.co.jp/documentation` (HTTP 200) lists **no**
  restaurant/venue-search API — catalog is Ichiba/Books/Travel/Recipe/
  Kobo/GORA. 楽天グルメ-the-API does not exist; there is no lat/lng venue
  search anywhere in the current catalog.
- The **Recipe** APIs are alive (both CategoryList and CategoryRanking
  answered `specify valid applicationId`) and are free with an App-ID
  registration + required Rakuten branding/credits ("necessary to display
  our branding…", guide page). But they return *recipe content ranked by
  category* — zero venue/POI semantics, cannot produce per-station venue
  counts.
- RapidAPI: the old "Rakuten RapidAPI" marketplace was shut years ago
  (background; not re-verified this session).
- Verdict: **reject** for this purpose. Recipe APIs could at most feed a
  *cooking-at-home* vibe signal someday — not a HotPepper replacement.

### 2.3 Yelp Fusion / Places — **reject for counts (quota), JP coverage unverified**

- Endpoint alive (`api.yelp.com/v3/businesses/search` → structured 400 on a
  malformed token). Old docs hosts are gone (410/404); the developer
  program now lives at `docs.developer.yelp.com` around a new **Yelp Places
  API** (OAuth/partner-flavored) + GraphQL + AI API.
- Quota collapse (verbatim from docs):
  - changelog *2023-05-16*: Fusion daily limit for new clients
    **5,000 → 500**;
  - `places-rate-limiting.md`: Starter Plan = **300 calls / 24 h**.
- Our need: 1,493 stations × ≥2 categories per sweep ≈ 3,000–6,000 calls →
  **6–20 days per full sweep** at new limits. The repo's own April
  assessment already flagged JP coverage as "limited / tourist-skewed"
  (`research/01-nightlife.md:146-157`); a real JP sample query was **not
  run** (no key in this environment).
- Verdict: **reject** as a count source. At most a micro-validation
  source for a handful of hub stations — not worth the integration.

### 2.4 Foursquare FSQ OS Places — **promising (wait: HF gating decision, shared with CRTKY-137)**

- Live: HF `foursquare/fsq-os-places` — **gated `auto`** (must be logged in
  and accept terms), **lastModified 2026-09-15** (monthly cadence alive),
  21,702 downloads; content endpoints 401 without an authenticated HF
  account (confirmed by `README.md` fetch).
- Foursquare's own post (2025-10-08, "Evolving FSQ OS Places"): **100M+
  places**, +1M places added since Nov 2024 launch, **monthly releases**,
  data "remains completely free with proper attribution under our **Apache
  2.0** license"; channels moved Oct 2025 to a Places portal (Iceberg
  catalog + token), Hugging Face, and a Snowflake listing.
- An ungated mirror exists (`do-me/foursquare_places_100M`, 2025-02-12 =
  the Nov-2024 snapshot, 100M rows) — usable for a *coverage dry run*, but
  stale and license-inherited from the same gated dataset.
- This is exactly the option parked in Bangkok
  (`research/bangkok/00-overview.md:127`, Plane **CRTKY-137**): accept
  terms once, and the dataset serves **both cities** as a third POI
  source / HP-decay cross-check. JP coverage inside the dataset is
  **unverified** (gated) — that check needs the owner's HF account.
- Verdict: **promising**; gate the adoption on (a) HF terms acceptance and
  (b) a Tokyo-bbox coverage sample vs HP counts. Not a drop-in HP
  replacement until outer-Tokyo density is proven.

### 2.5 Tabelog — **reject: no public API**

- Searches (JA + EN) surface no developer portal, no API docs, no
  self-serve access — consistent with the repo's April finding
  (`research/01-nightlife.md:133`: "No official API", hard anti-bot).
  Access is partnership-only with Kakaku.com.
- Verdict: **reject**. Scraping 1,493 stations behind CAPTCHAs is the
  exact risk profile risk #8 exists to avoid.

### 2.6 Adjacent option: Overture Places — **recommended second source (already accepted in-repo)**

- Bangkok already blends **Overture + OSM** for every POI signal
  (`scripts/bangkok/build.py:21`, loader at `build.py:491-502`), with a
  slim, proven fetch: duckdb over
  `s3://overturemaps-us-west-2/release/2026-09-23.1/theme=places/type=place/*`,
  bbox filter, `confidence >= 0.6`, `operating_status='open'`, keeping
  id/category/hierarchy/confidence/license/lat/lon
  (`scripts/bangkok/fetch.py:260-288`, constants at `fetch.py:57,60`).
- License (verified): Places = **CDLA Permissive 2.0** (+ Apache-2.0 /
  CC0-1.0 rows per provider) — permissive, attribution-style, suitable.
  The Bangkok fetch even records each row's `sources[].license`.
- For Tokyo this gives food/nightlife *bucket counts* (same shape as OSM
  counts) with **no new vendor contract, no key, no ToS negotiation**.
- Verdict: **adopt-candidate** — the concrete second source for
  food/nightlife, pending one merge experiment (§4).

## 3. OSM-only fallback: what actually degrades

### 3.1 Mechanism (from code, §1)

| Category | Effect of losing all HP values | Severity |
|---|---|---|
| nightlife | raw loses 0.60/1.00 weight; **cap input `midnight`=0 for every station → no station can reach 8+** (`compute-ratings.py:374` + `constants.py:105`); confidence: only `osm`/`osm_karaoke` survive → most of the 732 HP-dependent stations drop to `estimate` | **severe** — the category silently flattens to ≤7 citywide |
| food | raw keeps only the `log1p(osm)*0.4` term; log-percentile normalization is *relative*, so ordering largely survives (HP↔OSM r = 0.855, `CLAUDE.md:170`); but **every one of the 861 HP-backed stations drops to `estimate`** (no OSM-only branch, `compute-ratings.py:347-355`); caps: sum falls, 9/10 tiers (≥400/≥1000) mostly unreachable outside a few mega-hubs; the 78 HP-only stations (osm=0) lose *all* signal | **moderate** — rankings survive, metadata collapses |
| vibe | cafe term (0.15) zeroed; primary signal is OSM cultural/pedestrian → confidence unchanged (`compute-ratings.py:478`) | **mild** |
| crowd | 55 unmanned stations lose the HP proxy (`compute-ratings.py:497`) — already `estimate` | **mild** |
| gym/transport/rent/safety/green/essentials | do not read HP | **none** |

Also structural: the scraper's skip-on-error semantics
(`scrape-hotpepper.py:40-46,170-175`) mean an outage **persists old rows
forever** while `compute-ratings.py:591` stamps a **fresh** `data_date`
(run month, not scrape vintage; the table's own `scraped_at` — set at
`scrape-hotpepper.py:182` — is never read). "Never silently mix" is
currently violated by design.

### 3.2 OSM base, verified live (bbox 35.5,139.2,36.0,139.9; mail.ru mirror)

| Selector (pipeline semantics) | Count | `timestamp_osm_base` |
|---|---|---|
| `amenity~restaurant\|cafe\|fast_food` (= `food_count` base, `scrape-osm-pois.py:26-33`) | **37,776** (35,547 n / 2,209 w / 20 r) | 2026-10-13T04:55:50Z |
| `amenity~bar\|pub\|nightclub` (= `nightlife_count` base, `scrape-osm-pois.py:35-40`) | **10,219** (9,721 n / 486 w / 12 r) | 2026-10-13T04:57:51Z |
| `amenity=karaoke` | **2** (the tag is effectively unused) | 2026-10-13 |
| `amenity=karaoke_box` | **378** (≈ the 382 documented in April, `research/01-nightlife.md:38,191`) | 2026-10-13 |
| food/night POIs carrying any `opening_hours` | **not completed** — mirror returned busy errors 3× | — |

Two consequences: (a) OSM food/nightlife density is real and stable
(37.8k / 10.2k POIs), so an OSM-only *ranking* mode is viable; (b) OSM has
**no midnight concept** — no `opening_hours` late-night parse exists in the
pipeline, and even the hours-coverage probe did not complete — so the
nightlife cap either needs a new raw input (e.g., `bar+pub+nightclub`
sum, re-thresholded) or an explicit "caps suspended" fallback mode.

## 4. Resilience sketch (implement regardless of source choice)

**Freeze the last-good snapshot — make vintage explicit, don't add
infrastructure.** The freeze already half-exists: the scraper never
overwrites failures (skip-on-error leaves the previous NocoDB row intact)
and every refresh commits `demo-ratings.ts` to git, so history is the
snapshot archive. What's missing is *honesty about vintage*:
`compute-ratings.py:591` stamps `data_date = run month`. The fix is to
derive `data_date` per category from the sources actually used (for
hotpepper: `MAX(scraped_at)` over the rows consumed; `scraped_at` already
exists at `scrape-hotpepper.py:182`), or at minimum to refuse to advance
`data_date` for a category whose upstream rows are older than a stated
threshold. On a confirmed HP outage, the documented fallback is a
**flagged degraded run**, not a silent one: recompute food/nightlife
OSM-only with `sources: ['osm_fallback']`, confidence capped at
`estimate`, nightlife caps suspended (midnight input gone), `data_date`
pinned to the last HP vintage — and only via an explicit CLI flag, never
as the default path.

**Alerting on `data_date` and source mix — two cheap canaries in
`refresh-ratings.sh`.** (1) *Freshness*: a small script reads the exported
JSON (or NocoDB `computed_ratings`) and fails — exit 1, so `set -e` in
`refresh-ratings.sh:20` aborts before commit — when any category's
`data_date` is older than ~90 days or when HP-dependent `sources`
(`hotpepper`/`hotpepper_midnight`) drop by more than a few percent
between runs; today's committed export would already have fired this
alarm in May (`data_date: '2026-04'` × 1493 while the site kept serving).
(2) *Liveness*: a monthly CI step that hits the HP endpoint with a real
key and one Shinjuku query, asserting `results_available > 0` — a
non-429 "invalid key" answer is the key-loss signature (observed live:
`code 2000`), 429 is quota, 5xx is transient; map each to the runbook.

**Runbook (one CLAUDE.md subsection).** Symptom → action: *(a) code 2000
invalid key* → key lost/revoked: re-register (self-serve,
`webservice.recruit.co.jp/register/`, per the scraper docstring) and
re-run `scrape-hotpepper.py` incrementally — skip-on-error resumes the
~unscraped stations; *(b) persistent 429* → lower `--delay`, split sweeps
by prefecture with `--limit`; *(c) 5xx/timeout waves* → retry next day,
the incremental design makes this free; *(d) service gone for good* →
execute the flagged OSM-fallback run (above) + adopt the second source
(Overture port per §2.6; Foursquare if CRTKY-137 lands), then update
`CLAUDE.md:36` and this note. Also in the same PR: **commit the missing
midnight scraper** (§1.2) — today the nightlife cap input cannot be
regenerated from the repo at all.

## 5. Verdict table

| Source | Live status (2026-10-13) | License / ToS | JP venue coverage | Verdict |
|---|---|---|---|---|
| HotPepper (current primary) | up, `api_version 1.30`; free self-serve key (registration flow not re-verified) | Recruit web-service terms (existing compliance) | 100% of 1493 stations (NocoDB) | **keep** + add resilience (§4) |
| ぐるなび API | portal 403 live; 404 since 2023-05 (Wayback); free service ended, corporate-only | corporate contract | n/a | **reject** |
| 楽天グルメ/レシピ | Recipe APIs alive (App-ID, free, branding required); **no venue API** in catalog | per-API terms | recipes only, no venues | **reject** |
| Yelp Fusion/Places | endpoint alive; docs migrated; free tier now 500/day (Fusion, since 2023-05) / 300/day (Places Starter) | Yelp API terms, attribution/display rules | JP weak (repo assessment); sample **not run** (no key) | **reject** for counts |
| Foursquare FSQ OS Places | HF `fsq-os-places`, gated, **monthly, last 2026-09-15**, Apache-2.0 + attribution | Apache-2.0 w/ attribution (post 2025-10-08) | unverified (gated) | **promising — wait** for HF terms + coverage test (shared with CRTKY-137) |
| Tabelog | no public API (search absence, ×2 epochs) | partnership only | deepest JP data, unreachable | **reject** |
| Overture Places (adjacent) | proven in-repo for Bangkok (`fetch.py:260-288`, release 2026-09-23.1) | **CDLA Permissive 2.0** (+Apache/CC0 rows) | good for POI buckets; Tokyo counts unverified | **adopt-candidate** — the practical second source |

## 6. Recommendations

**Implement now (no new vendor, pipeline-local):**
1. Per-source `data_date` (derive from `scraped_at`, never the run date)
   + freshness/source-mix canary in `refresh-ratings.sh` + monthly HP
   liveness check.
2. Flagged OSM-fallback compute mode (explicit `osm_fallback` sources,
   `estimate` confidence, nightlife caps suspended) + the runbook in
   CLAUDE.md; update risk #8 to point here.
3. Commit the missing midnight scraper (§1.2).

**Adopt next (one experiment):** port the Bangkok Overture fetch to Tokyo
(`--only overture_places`, Tokyo bbox), then measure per-station
HP-total vs Overture-food/nightlife within 800 m — if the correlation is
near OSM's r=0.855, wire Overture as the `second` source with the
two-source `strong` rule (mirroring `scripts/bangkok/build.py:21`
semantics; shared package per CRTKY-166 pattern cited in the ticket).

**Wait:** Foursquare FSQ OS Places — one HF terms acceptance unlocks both
cities (CRTKY-137); run the Tokyo coverage sample after that decision.

**Reject:** Gnavi (dead self-serve), Rakuten (no venue API), Tabelog (no
API), Yelp as a count source (quota 300–500/day ≪ sweep need; thin JP).

## 7. Sources & license

- Repo (read this session): `CLAUDE.md:36,107-111,204`; `SPEC.md:292-299`;
  `scripts/compute-ratings.py:342-381,467-499,591`;
  `packages/schema/python/city_rating_schema/constants.py:104-105`;
  `scripts/scrapers/scrape-hotpepper.py:27-46,91-126,144,170-182`;
  `scripts/scrapers/scrape-osm-pois.py:26-61`;
  `scripts/refresh-ratings.sh:20,103-107`; `scripts/export-ratings.py:281,320,489`;
  `app/src/data/demo-ratings.ts` (grep distribution, `data_date` ×1493);
  `scripts/bangkok/fetch.py:57,60,260-288`, `scripts/bangkok/build.py:21,491-502`;
  `research/01-nightlife.md:130-157,191`; `research/00-overview.md:29,46`;
  `research/bangkok/00-overview.md:127`.
- Live web (2026-10-13): recruit.co.jp HP endpoint probe; Wayback CDX for
  `api.gnavi.co.jp`; webservice.rakuten.co.jp catalog + `app.rakuten.co.jp`
  Recipe probes; `docs.developer.yelp.com` (`llms.txt`, `docs/plans.md`,
  `docs/places-rate-limiting.md`,
  `changelog/fusion-daily-rate-limits-changed.md`); HF datasets API
  (`foursquare/fsq-os-places`) + gated README probe; Foursquare Medium
  "Evolving FSQ OS Places" (2025-10-08); `docs.overturemaps.org/attribution/`.
- OSM data via Overpass (mail.ru mirror), **ODbL** (stated in every
  response); bbox counts in §3.2.
- Tickets: Plane CRTKY-184 (this), CRTKY-137 (Foursquare-for-Bangkok
  precedent), CRTKY-166 (shared two-source confidence package, cited by
  the ticket).

## 8. Open questions for the owner

1. HP free-tier terms/registration in 2026 — endpoint is live, but the
   key-registration flow and any usage cap were not re-verified (needs a
   browser session); worth one check before the runbook leans on
   "self-serve re-registration".
2. FSQ OS Places Tokyo coverage + category fidelity — requires the HF
   account/terms decision (same decision as CRTKY-137); the ungated
   Nov-2024 mirror can de-risk this early if license-clean use is OK.
3. Overture Tokyo merge experiment — is the HP↔Overture per-station
   correlation accepted as the adoption bar (and at what threshold),
   mirroring the Bangkok two-source `strong` rule?
4. OSM-only confidence semantics: today hp=0 → `estimate`/empty sources
   even when OSM is rich (`compute-ratings.py:347-355`). Intentional, or
   should an OSM-only branch exist for the degraded mode?
5. Staleness threshold for the `data_date` alarm: 60 / 90 / 120 days?
   (HP data is refreshed opportunistically, not on a schedule — the
   threshold defines the SLA.)
6. The 422 stations with `food: []` (both sources zero) — accept as
   outer-Tokyo reality, or is an outer-bbox OSM re-scrape (the osm_pois
   table covers 94% of stations) worth a ticket?
