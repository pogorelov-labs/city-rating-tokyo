# Health-conscious food nearby (Bangkok) — three-layer detection: tags → bilingual dictionary → LLM pass (CRTKY-149)

Researched: **2026-10-13**, by the open-data research agent. This run executed
**Layer 1 (Overpass tag counts, ticket query verbatim + variations)** and
**Layer 2 (Thai/English dictionary over POI names)** live; **Layer 3 (LLM
classification + hand-labeling ~100 POIs) is plan-only, not run here**, per the
ask. Everything below was fetched/run by me in this session against the live
Overpass API; commands and outputs are quoted. Nothing here is an
implementation decision — the owner adopts sources.

**TL;DR:** The ticket's Overpass query is live and returns real data —
**69 unique "dedicated" health POIs citywide** (of 6,587 named food POIs,
≈ 1.0 %), split `diet:vegan=only` 16 / `diet:vegetarian=only` 23, plus
`shop=health_food` 11, `cuisine~health|salad` 21, `shop=nutrition_supplements`
1. The **only-vs-yes split works**: vegan 16/113, vegetarian 23/149,
gluten_free 0/7 — a clean dedicated-vs-options signal on tags. The
**dictionary tier adds only ~43 POIs citywide** beyond tags (union 57), and its
biggest term `เจ` is a precision trap: 138 raw substring hits → **~6 true**
(≈ 5 %) — single-character Thai terms must be matched by compound rules
(`อาหารเจ`, `กินเจ`) or left to the LLM layer. The per-district contrast
confirms the ticket's fear in a stronger form than expected: **Watthana 646
food POIs / 8 dedicated / 28 options; Lat Phrao 76 / 0 / 1; Nong Chok
12 / 0 / 0** — outer districts are not under-labeled, they are barely present
in OSM at all, so the dictionary *cannot* correct mapping bias there. Verdict:
**promising** as a three-layer design, with Layer 3 (LLM over OSM **and
Overture**) mandatory; tags-only or tags+dictionary-only would blank most of
the city.

---

## 0. What was actually verified (method, date, live examples)

All Overpass access ran today, **2026-10-13**, via `curl --data-urlencode
"data=…"` POST. Queries were run against the live DB — the mirror stamped
`"osm3s": {"timestamp_osm_base": "2026-10-13T00:24:59Z"}`. Live example
(verbatim output fragment, ticket's union query):

```json
{"type": "count", "id": 0, "tags": {"nodes": "61", "ways": "8", "relations": "0", "total": "69"}}
```

Local processing: Python 3.14 over saved JSON (`/tmp/crtky149/*.json`):
dictionary regex/substring matching, and point-in-polygon (pure-Python
even-odd ray casting) over district boundaries fetched with `out geom`.

Not verified in this run (stated as such): Overture cross-check, the LLM pass,
hand-labeled precision/recall of any tier, and per-dish KBJU data (the ticket
already records: no open per-dish macro dataset for Bangkok exists).

## 1. Access problems (mirror availability today) — differs from the past run

Direct Overpass egress from this machine was **blocked today**, in contrast to
the past run's confirmation:

| Endpoint | Result (2026-10-13) |
|---|---|
| `overpass-api.de` | TCP connects, TLS reset at ClientHello (`LibreSSL SSL_connect: SSL_ERROR_SYSCALL`, curl exit 35; plain HTTP 80 → 000 too) |
| `overpass.kumi.systems` | HTTP 000 (connection failed) |
| `overpass.private.coffee` | HTTP 000 / 504 |
| `overpass.osm.jp` | HTTP 000 |
| **`maps.mail.ru/osm/tools/overpass`** | **works** (all data below) |
| `overpass.osm.ch` | responds but returned **0 elements** for a bbox query that has 11 matches — unreliable, not used |

Two mirror quirks to carry into any implementation on top of
`scripts/bangkok/fetch.py:47` (`OVERPASS_ENDPOINTS` — today none of its three
entries worked; `maps.mail.ru` must be added): (a) the nginx front of mail.ru
504s intermittently (1 retry out of ~2 needed on most queries); (b) two query
shapes reliably 504'd there — `nwr["amenity"~"^(restaurant\|cafe\|fast_food)$"]`
in a union, and `rel(bbox)`-style admin scans — while the same content via a
union of exact-key selectors succeeded. The pipeline's rotation helper
(`fetch.py:64-87`) needs the mail.ru endpoint plus 504-aware retries.

## 2. Layer 1 — tag counts (bbox `13.4907,100.3279,13.9556,100.9383` = grid bounds)

### 2.1 The ticket's query, verbatim — and per-selector breakdown

Ticket query (run as-is):

```
[out:json][timeout:60];
(
  nwr["shop"="health_food"](13.4907,100.3279,13.9556,100.9383);
  nwr["shop"="nutrition_supplements"](13.4907,100.3279,13.9556,100.9383);
  nwr["cuisine"~"health|salad"](13.4907,100.3279,13.9556,100.9383);
  nwr["diet:vegan"="only"](13.4907,100.3279,13.9556,100.9383);
  nwr["diet:vegetarian"="only"](13.4907,100.3279,13.9556,100.9383);
);
out count;
```

→ **total 69** (61 nodes + 8 ways). Cross-check: my independent union of the
same selector set + `diet:gluten_free=only` (0) over the centered dump also
gives **69** — consistent.

| Selector | count |
|---|---|
| `shop=health_food` | 11 (10 nodes + 1 way) |
| `shop=nutrition_supplements` | 1 |
| `cuisine~"health\|salad"` | 21 (= health 2 + salad 19) |
| `diet:vegan=only` | 16 |
| `diet:vegetarian=only` | 23 |
| `diet:vegan=yes` | 113 |
| `diet:vegetarian=yes` | 149 |
| `diet:gluten_free=only` / `=yes` | 0 / 7 |
| `diet:pescetarian=only` | 0 |
| `organic=yes` (bbox-wide) | 21 (3 on named food POIs) |
| **union (ticket query)** | **69** |

### 2.2 Full `diet:*` only-vs-yes breakdown (dump of all 325 POIs carrying any `diet:*` tag)

Fetched with `nwr[~"^diet:"~"."](bbox); out tags;` → 325 elements. Composition
of that set: 268 restaurant, 25 cafe, 14 fast_food, 9 supermarket, 3
convenience, 1 pub, 1 bar, 1 other. Notable values beyond the diet family:
`diet:healthy=yes` **9** (the tag exists!), `diet:organic=yes` 4,
`diet:plant-based=yes` 1, `diet:raw=yes` 1, plus noise like
`diet:omakase=yes`/`diet:noodle=yes` (mappers repurposing the key).

The signal-relevant slice (dedicated = `only`, options = `yes`):

| diet:* | only (dedicated) | yes (options) | no |
|---|---|---|---|
| vegan | 16 | 113 | 5 |
| vegetarian | 23 | 149 | 9 |
| gluten_free | 0 | 7 | — |
| halal | n/a | 42 | 22 |

Citywide tag unions over the centered dump (6,654 elements = 6,587 named food
POIs + 67 tag-only POIs): **dedicated union 69** (shop=health_food /
nutrition_supplements ∪ cuisine~health\|salad ∪ diet:*=only), **options union
184** (diet:*=yes not already dedicated).

### 2.3 Named examples (health_food + nutrition_supplements + cuisine~health\|salad, 33 elements)

Genuinely dedicated venues: **house of salad** (cuisine=health food),
**Broccoli Revolution**, **Nourish Cafe** (healthy;international),
**Garden Salad** (salad;thai), **Jones' Salad** / **Jone's Salad**,
**Take a Bowl (FYI Center)**, **KRAFT** (cuisine=salad), **Avocado Farm By
Mom**, shops: **Lemon Farm organic & natural foods**, **Dinosao**, **Baimiang**,
**Ginger Farm Kitchen**, **Makai Açaí**, **Kate Home Farm**, **กิน ณ ดี**;
supplements: **Neoca** (the only `nutrition_supplements` in the bbox); **3
unnamed** `health_food` POIs (nameless — a data-quality footnote for any
dictionary tier, which can only read names).

**False-positive finding for `cuisine~salad`:** the tag is on the *menu*, not
the concept — of 21 cuisine-tagged POIs at least 7 are steak/pizza/italian
places that merely serve a salad: **Tabor Steak Hut, Pizza Papa Joe, Tutto
Matto, Black Pepper Steak, Va Presto (The Up), T-REX'S Gastrobar, Seven Sisters
Home Cafe**. ≈ 33 % FP rate if `cuisine~salad` is read as "dedicated health
venue". Any implementation should require `cuisine=health_food`/`salad` as a
primary cuisine or apply an exclusion list.

## 3. Layer 2 — Thai/English dictionary over all named food POIs

Corpus: **6,587 named POIs** with `amenity=restaurant|cafe|fast_food` in the
bbox (fetched via union of exact-key selectors + `out tags`, 2.0 MB — the
regex-selector form of the same query 504s on the mail.ru nginx). Matched
against `name` + `name:en`, case-insensitive; Latin terms with `\b` word
boundaries (macro → macros? too); Thai terms as substrings (Thai script has no
inter-word spaces in practice).

### 3.1 Core dictionary counts (the ask's 16 terms)

| Term | Script | Meaning | Hits | Notes / sample names |
|---|---|---|---|---|
| คลีน | Thai | clean | **2** | คลีนดีลีน (fast_food); ตามสั่ง ไก่คลีนคล่อง |
| คีโต | Thai | keto | **0** | — |
| ฟิต | Thai | fit | **0** | — (gym exclusion is structurally handled: corpus is food-only) |
| อาหารสุขภาพ | Thai | health food | **0** | — |
| มังสวิรัติ | Thai | vegetarian | **4** | Origi มังสวิรัติ; มังสวิรัติ; ณพนันต์ มังสวิรัติ [Nopnam Vegan]; ร้านหัวใจมังสวิรัติ |
| เจ | Thai | je (Buddhist vegan) | **138 raw → ~6 true** | see §3.2 — do NOT match raw |
| ไขมันต่ำ | Thai | low fat | **0** | — |
| โปรตีน | Thai | protein | **0** | — |
| fit | Latin | fit | **0** | — |
| healthy | Latin | healthy | **4** | The Rice And Healthy Food; Healthy Pan; Home made healthy; Green Season Healthy |
| salad | Latin | salad | **9** | house of salad; Salad Pla; Garden Salad; SALAD FACTORY ×2; Jones' Salad ×2 (TH+EN names); Milk Toast Coffee Salad (FP-ish); Salad Factory (dup) |
| protein | Latin | protein | **0** | — |
| clean | Latin | clean | **1** | Kin Clean |
| keto | Latin | keto | **1** | OiC Keto Cafe By Cherry |
| macro(s) | Latin | macro | **0** | — |
| meal prep | Latin | meal prep | **0** | — |

**Union of the dictionary: 57 unique POIs** (0.87 % of 6,587). Only **14 of 57**
also carry `diet:*` tags → the dictionary's marginal contribution over Layer 1
is ≈ **43 POIs citywide**. Ticket-suggested extra Latin terms (measured):
vegan 21, health 7, veggie 4, greens 2, organic 2, low-carb 0, calorie 0.

Dictionary-v2 transliteration probes (measured): **สลัด** (salad in Thai
script) 2 — catches โจนส์สลัด that the Latin term misses; **สุขภาพ** (health,
unprefixed) 2 — catches เจ สุขภาพ, น้ำผลไม้…เพื่อสุขภาพ; **วีแกน** (vegan) 0;
**คลีนฟู้ด / อาหารคลีน / กินเจ** 0; **เต้าหู้** (tofu) 5 — **reject**: all are
tofu-pudding/soy-milk dessert stalls (น้ำเต้าหู้…), not health venues.

### 3.2 The เจ problem — the single most important Layer-2 finding

Raw substring `เจ` matches **138** of 6,587 names. True `เจ` (Buddhist vegan)
venues in the sample: **~6** (`อาหารเจ บ้านถั่วเหลือง`, `ปัณสุข อาหารเจ`,
`โยตาอาหารเจ`, `สินาทอาหารเจ Sinart Vegan`, `เจ สุขภาพ`; borderline:
`เจ เจ ชาบู` = "JJ chabu", a *false* hit). The rest are
(`precision ≈ 5 %`): เจียง = Chiang/*Jiang* (หมูทอดเจียงฮาย, ครัวเจียงใหม่,
เจียง ลูกชิ้นปลา), เจ้ = granny (เจ้นิด, เจ๊หนู, เจ๊ไข่, เจ๊ไฝ, เจ๊เปี๊ยก),
เจดีย์ = stupa (สามแยกเจดีย์), เจียว = fried (ข้าวไข่เจียว), เจ้าเก่า =
"famous old shop" (มากมาย), เจริญ = Charoen road/name, เจ็ง = Jeng (เจ็ง
นู้ดเดิ้ล), and the long compounds สุกี้เจหรูยี่ [Ruyi *Vegetarian* — actually
a true hit my first refined rule discarded]. **Rule for any implementation:**
match `อาหารเจ` / `กินเจ` compounds or space-delimited standalone `เจ`, never
the bare grapheme — and accept that a small residue needs the LLM layer.

## 4. Per-district contrast (Layer-3 context; dedicated vs options)

Method: district polygons from OSM `admin_level=6` relations (Watthana =
`2938036` "Vadhana District", Lat Phrao = `2938034`, Nong Chok = `3147501`),
fetched `out geom`, boundary member-ways **stitched into rings** (they come as
unclosed segments — closing each segment independently silently yields a
near-empty polygon, first attempt proved it), even-odd point-in-polygon over
POI centers of the global dump. The mirror's `area(...)` queries returned
empty, hence local PIP.

| District | food POIs (named) | tag-dedicated | tag-options | dictionary hits (food) |
|---|---|---|---|---|
| **Watthana** (Sukhumvit/Thong Lo, central) | **646** | **8** | **28** | 1 |
| **Lat Phrao** (mid) | **76** | **0** | **1** | 0 |
| **Nong Chok** (outer, rural-east) | **12** | **0** | **0** | 0 |

Watthana's 8 tag-dedicated: house of salad, Broccoli Revolution, Dinosao,
The Vegan Table (`diet:vegan=only`), Mercy Republic (`only`×2), REAL GROCERS,
+ 2 of the `cuisine~salad` false positives (Pizza Papa Joe, Croissant Factory)
→ **6 true dedicated**. Watthana's options include chain-wide auto-tags
(Swensen's, CoCoICHIBANYA, BAR B Q Plaza — `diet:vegetarian=yes` on every
branch); decide whether chain auto-tags count as "options". Lat Phrao's sole
option: Kind Cafe.

Reading: the central/mid/outer gradient is driven by **food-POI stock**
(646 → 76 → 12, a 54× spread) before any health classification — the ticket's
hope that "the dictionary tier partially corrects mapping bias by reading Thai
names in outer districts" is **not supported**: where OSM has 12 eateries,
there is nothing for a dictionary or an LLM to read. The outer-district signal
must come from **Overture** (~300 k places in the bbox per
`scripts/bangkok/fetch.py` docstring), not from OSM names.

## 5. Layer 3 — plan only (not run)

1. **LLM pass** over every food POI's `name + cuisine + brand + description`
   (OSM) **plus the Overture Places category/names** for the same bbox,
   labeling `dedicated / options / not-health` + confidence. Prompt shape per
   the ticket; batch like the district-description parallel agents.
2. **Hand validation ~100 POIs** across Watthana / Lat Phrao / Nong Chok.
   Amendment required: Nong Chok has 12 OSM food POIs total, so the outer leg
   of the sample must be drawn from the Overture candidate pool, or the
   "outer districts not systematically blank" test is vacuous.
3. Precision/recall per tier against the labels; adopt thresholds only if
   dictionary and LLM precision hold *and* outer coverage is non-zero.
4. KBJU reality check (kept honest): keyword hits are *venue-type* evidence,
   not nutrition data; per-dish macros remain page facts for named chains only.

## 6. Verdict per layer (for the owner)

| Layer | Verdict | Basis (this run) |
|---|---|---|
| 1 — OSM tags | **adopt, with FP filter** | live, 69 dedicated / 184 options citywide; require primary `cuisine=health_food\|salad` or exclusion list (§2.3); keep only-vs-yes semantics |
| 2 — dictionary | **adopt only as a cheap booster** | +43 marginal citywide; mandatory เจ compound rules; สลัด/สุขภาพ additions worth having; 0 hits in mid/outer — cannot be the main path |
| 3 — LLM + Overture | **mandatory, main path** | tags+dictionary blank Lat Phrao and Nong Chok; only a pass over Overture (plus OSM) can fill outer districts; hand-label before adopting |

Overall: **promising** — the base source (OSM/Overpass) is live and the
detection design is feasible, but as a district-level "healthy food nearby"
signal the two metadata layers alone are too thin (≈ 113 dedicated candidates
citywide, concentrated in the center) — Layer 3 decides.

## 7. Draft dictionary (reusable; Tokyo mirror CRTKY-176)

| # | Term | Script/lang | Meaning | Tier | Match rule | BKK hits (this run) | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | คลีน | th | clean food | strong (dedicated) | substring | 2 | keep |
| 2 | คีโต | th | keto | strong | substring | 0 | keep (dormant) |
| 3 | ฟิต | th | fit | strong | substring | 0 | keep (dormant) |
| 4 | อาหารสุขภาพ | th | health food | strong | substring | 0 | keep |
| 5 | มังสวิรัติ | th | vegetarian | strong | substring | 4 | keep |
| 6 | เจ | th | je/Buddhist vegan | strong | **compound only**: `อาหารเจ`, `กินเจ`, standalone token | 6/138 raw | keep with rule; never raw |
| 7 | ไขมันต่ำ | th | low fat | strong | substring | 0 | keep (dormant) |
| 8 | โปรตีน | th | protein | strong | substring | 0 | keep (dormant) |
| 9 | fit | en | fit | strong | `\bfit\b` | 0 | keep |
| 10 | healthy / health | en | healthy | strong | `\bhealthy\b` / `\bhealth\b` | 4 / 7 | keep |
| 11 | salad / สลัด | en/th | salad | **weak (options)** | `\bsalad\b` / substring | 9 / 2 | keep, tier = options |
| 12 | protein | en | protein | strong | `\bprotein\b` | 0 | keep |
| 13 | clean | en | clean | strong | `\bclean\b` | 1 | keep |
| 14 | keto | en | keto | strong | `\bketo\b` | 1 | keep |
| 15 | macro(s) | en | macros | strong | `\bmacros?\b` | 0 | keep |
| 16 | meal prep | en | meal prep | strong | phrase | 0 | keep |
| 17 | vegan / veggie | en | vegan | strong/options | `\bvegan\b` etc. | 21 / 4 | keep |
| 18 | วีแกน | th | vegan | strong | substring | 0 | keep (dormant) |
| 19 | สุขภาพ | th | health (unprefixed) | weak | substring | 2 | keep |
| 20 | เต้าหู้ | th | tofu | — | — | 5, all tofu-drink stalls | **reject** |

Tokyo adaptation note: tier semantics transfer; Latin terms carry over
as-is; the Thai block is BKK-only, replaced there by JA (ヴィーガン, ローカボ,
グルテンフリー, プロテイン, サラダ, クリーンイーティング…). The `เจ` lesson
generalizes: single-CJK-morose graphemes (e.g. 精進 in JA) need compound
rules, never raw substring.

## 8. Sources & license

- Overpass mirrors (queried 2026-10-13, POST `data=`):
  `https://maps.mail.ru/osm/tools/overpass/api/interpreter` (all data),
  `https://overpass-api.de/api/interpreter`, `overpass.kumi.systems`,
  `overpass.private.coffee`, `overpass.osm.jp`, `overpass.osm.ch`
  (availability per §1).
- Data license: OSM **ODbL** (stated in every Overpass response:
  "The data included in this document is from www.openstreetmap.org… ODbL").
- Granularity/fields: OSM node/way POIs, tags `name`, `name:en`, `amenity`,
  `shop`, `cuisine`, `diet:*`, `organic`; district polygons OSM relations
  `admin_level=6`.
- Pipeline helpers referenced: `scripts/bangkok/fetch.py:47` (mirror list —
  needs maps.mail.ru added), `fetch.py:64-87` (rotation/backoff), bbox =
  `BBOX` in `scripts/bangkok/static_data.py` (matches the ticket bbox).
- Ticket: Plane CRTKY-149 (source of the query, dictionary, and district
  validation design).

## 9. Open questions for the owner

1. Overture cross-check (categories/names for the same bbox) — the main path
   for outer districts; not in this run. Which Overture category list counts
   as health-food (their taxonomy has distinct salad/vegan/juice categories)?
2. Hand-validation sample: Nong Chok has 12 OSM food POIs — draw the outer leg
   from Overture candidates instead, or drop the outer leg?
3. Chain auto-tags (`diet:vegetarian=yes` on every Swensen's / CoCoICHIBANYA
   branch): count as "options", or filter `brand`-tagged POIs out of options?
4. `shop=health_food` (11, incl. 3 unnamed) and `nutrition_supplements` (1):
   part of "dedicated food nearby", or a separate sports-nutrition signal?
5. Mirror policy: add `maps.mail.ru` to `OVERPASS_ENDPOINTS` and make 504
   retries the default? Today none of the three configured mirrors answered.

*Companion notes from the same day: 2026-10-13-{air-crtky146,
flood-crtky139, noise-crtky151, population-crtky140, safety-crtky150}.md.*
