# Health-conscious food nearby (Tokyo) — three-layer detection: tags → Japanese dictionary → LLM pass (CRTKY-176)

Researched: **2026-10-13**, by the open-data research agent. This is the Tokyo
mirror of the Bangkok run **CRTKY-149**
(`research/bangkok/notes/2026-10-13-healthfood-crtky149.md`) and reuses its
format and validation protocol. Executed live: **Layer 1 (Overpass tag counts,
ticket query verbatim + per-selector breakdown + full `diet:*` dump)** and
**Layer 2 (Japanese/English dictionary over all named OSM food-POI names)**,
plus the **渋谷 / 世田谷 / 八王子 district contrast** with boundary polygons
validated against official areas. **Layer 3 (LLM pass, hand-labeling) is
plan-only, not run here.** Everything below was fetched/run in this session
against the live Overpass API; commands and outputs quoted. Not an
implementation decision — the owner adopts sources.

**TL;DR:** The ticket query is live on Tokyo and returns **110 dedicated
health POIs citywide** (of 35,869 named food POIs, ≈ 0.3 %) —
`diet:vegan=only` 55 / `diet:vegetarian=only` 17, `shop=health_food` 24,
`cuisine~health|salad` 22, `shop=nutrition_supplements` 2. The **only-vs-yes
split works even better than in Bangkok** (vegan 55/133, vegetarian 17/157,
gluten_free 0/33). The **cuisine~salad false-positive rate reproduces**
(8–9 of 22 ≈ 36–41 % vs BKK's 33 %; すき家 — a 351-branch beef-bowl chain —
carries `cuisine=…;salad` on one branch), and `shop=health_food` has a
Tokyo-specific FP profile: tofu shops and a Yakult *delivery center*. The
**Japanese dictionary tier adds only ~46 POIs (0.13 %)** — far thinner than
Bangkok's 0.87 % — because Tokyo's trendy health vocabulary
(プロテイン, 糖質制限, マクロビ, グルテンフリー, スムージー…) is **absent from
OSM names** (0 hits across the board); venues self-label in **Latin
"vegan" (13) 4× more often than ヴィーガン (3)**. Script FP traps replicate
เจ: `ケト` matched inside ケトル "kettle", `菜食` inside 蔡菜食堂 (surname
蔡), `豆腐` is a reject exactly like เต้าหู้. District contrast
**inverts the Bangkok lesson**: outer 八王子 is densely mapped (774 food POIs
vs Nong Chok's 12), yet has **1 tag-dedicated venue (a cuisine-salad FP) and
0 options** — the thin outer-district signal in Tokyo is *real absence*, not
mapping bias, so the dictionary cannot and need not correct it. Verdict:
**promising**; tags-only is already a usable *central-city* discriminator for
Tokyo, LLM+Overture is mainly an FP-fix and enrichment layer here, not a
recall lifeline.

---

## 0. What was actually verified (method, date, live examples)

All Overpass access ran today, **2026-10-13**, via `curl --data-urlencode
"data@…"`. The ticket union query was stamped
`"timestamp_osm_base": "2026-10-13T03:42:27Z"`; corpus dumps ~07:07–07:09Z.
Live fragment (verbatim ticket query, Tokyo bbox):

```json
{"type": "count", "id": 0, "tags": {"nodes": "107", "ways": "2",
 "relations": "1", "total": "110"}}
```

Local processing: Python 3.14 (homebrew) over saved JSON (`/tmp/crtky176/*.json`,
corpus 22.7 MB): JA substring + Latin `\b`-regex name matching; district
point-in-polygon (even-odd ray casting) over boundary relations stitched from
member ways, **ring areas cross-checked against Wikipedia official areas**
(§4 — an explicit step added after the Bangkok run's silent-empty-polygon
incident).

Not verified in this run (stated as such): Overture cross-check, the LLM pass,
hand-labeled precision/recall of any tier, per-dish nutrition data.

## 1. Access problems (mirror availability today) — pattern differs from the BKK run

| Endpoint | Result (2026-10-13) |
|---|---|
| `overpass-api.de` | **works but flaps**: TLS reset at ClientHello (`LibreSSL SSL_ERROR_SYSCALL`, curl 35) in bursts of ~2–8 tries; between bursts it answers. **Requires a `User-Agent` header — without it the server returns HTTP 406** (Apache "Not Acceptable"), which the BKK run never saw (it failed earlier, at TLS). Recovery needed 25–45 s sleeps, up to 4 min of patience |
| `maps.mail.ru/osm/tools/overpass` | **workhorse for dumps** (most data below), but: nginx 504 on ~1 try in 2; "server is too busy" dispatcher errors in waves; and **`area:…` filters silently return `total: 0`** (the BKK run's area bug, reconfirmed) |
| `overpass.osm.jp`, `overpass.kumi.systems`, `overpass.private.coffee` | HTTP 000 / silent, all day |
| **`overpass.osm.ch`** | responds instantly but **returns 0 elements for a Shibuya-center cafe query that has hundreds** — region-lagging, rejected (same verdict as the BKK run) |

Carry into `scripts/bangkok/fetch.py:47` (`OVERPASS_ENDPOINTS`, cited from the
BKK note): none of the three configured endpoints answered reliably today;
the working set is `overpass-api.de` (with User-Agent + 502-style retry) and
`maps.mail.ru` (busy-aware retry), and **area-id queries must be avoided on
mail.ru**. A 20-statement multi-`out count` query never completed on either
mirror; single-statement dumps with local counting were the reliable shape
(same lesson as BKK §1b).

## 2. Layer 1 — tag counts (bbox `35.5,139.2,36.0,139.9`)

### 2.1 The ticket's query, verbatim — and per-selector breakdown

Ticket query (run as-is, only the bbox swapped):

```
[out:json][timeout:90];
(
  nwr["shop"="health_food"](35.5,139.2,36.0,139.9);
  nwr["shop"="nutrition_supplements"](35.5,139.2,36.0,139.9);
  nwr["cuisine"~"health|salad"](35.5,139.2,36.0,139.9);
  nwr["diet:vegan"="only"](35.5,139.2,36.0,139.9);
  nwr["diet:vegetarian"="only"](35.5,139.2,36.0,139.9);
);
out count;
```

→ **total 110** (107 nodes + 2 ways + 1 relation). BKK equivalent was 69 on a
6,587-POI base; Tokyo's 110 on a 35,869 base is a *lower density* (0.31 %
vs 1.05 % of named food POIs).

| Selector | count |
|---|---|
| `shop=health_food` | 24 |
| `shop=nutrition_supplements` | 2 |
| `cuisine~"health\|salad\|vegan\|vegetarian"` (CRTKY-176 extension) | 22 elements — cuisine *values*: `salad` 21, `italian_pizza_pasta_salad` 1, `health_food` 1; **no `vegan`/`vegetarian` cuisine values exist in the bbox** |
| `diet:vegan=only` | 55 |
| `diet:vegetarian=only` | 17 |
| `diet:vegan=yes` | 133 |
| `diet:vegetarian=yes` | 157 |
| `diet:vegan=no` / `diet:vegetarian=no` | 32 / 59 |
| `diet:gluten_free=only` / `=yes` / `=limited` / `=no` | **0** / 33 / 1 / 8 |
| `diet:pescetarian=only` | 0 (`=yes` 5) |
| `diet:dairy_free=only` / `=yes` | 0 / 2 |
| `diet:halal=yes` / `=only` / `=no` | 40 / 7 / 47 |
| `diet:healthy=yes` | 1 (the tag exists, as in BKK) |
| `diet:organic=yes` | 7 |
| `organic=yes` (bbox-wide) | not fetched separately (server load); 1 named food POI carries 有機 in the name |

### 2.2 Full `diet:*` dump — 479 POIs carrying any `diet:*` key

Fetched with `nwr[~"^diet:"~"."](bbox); out tags center;` → 479 elements.
Composition: 265 restaurant, 66 fast_food, 63 cafe, 30 convenience,
11 supermarket, 7 bakery, 5 pastry, 5 pub, 4 ice_cream, 3 deli, 2 food_court,
2 health_food, 10 other. Tokyo's 479 vs BKK's 325 — denser tagging.

The signal slice (dedicated = `only`, options = `yes`):

| diet:* | only (dedicated) | yes (options) | no |
|---|---|---|---|
| vegan | **55** | 133 | 32 |
| vegetarian | **17** | 157 | 59 |
| gluten_free | 0 | 33 | 8 |

Tokyo is the mirror image of BKK on the dedicated split: **vegan-only 55 ≫
vegetarian-only 17** (BKK was vegan 16 < vegetarian 23) — Tokyo's dedicated
venues self-identify as vegan, consistent with the Latin-name finding in §3.

**Key-repurposing noise** (mappers inventing values; BKK had
`diet:omakase=yes`): `diet:ちゃんぽん=yes` (chanpon noodles!),
`diet:spicy=yes`, `diet:carnivore=yes`, `diet:omnivore=yes`,
`diet:natural_foods=yes`, `diet:alcohol_free=yes`, plus the meat-side family
`diet:meat=yes` 19, `diet:non-vegetarian=yes` 9, `diet:fish/seafood/chicken=
yes` 3/3/2, `diet:kosher=yes/no` 7/26. Any implementation reading `diet:*`
must whitelist keys.

**Tag-quality FP inside `=only`:** `KOMEDA is □` (Komeda's, a ~1,000-branch
coffee chain) carries `diet:vegan=only` on one branch; `ベィーガン居酒屋真さか`
has a typo'd name (ベィーガン) but is presumably genuinely vegan; several
`=only` cafes (Sky High, whyte, THE_B, coret, meu nota) are single-venue
claims that Layer 3 should spot-check. Chain auto-tag noise (BKK's Swensen's
problem) is rare here: すき家 has 351 corpus branches with exactly **one**
salad-cuisine tag; McDonald's (544), Mos Burger (247), Subway (57) have none.

### 2.3 Named examples, and the two Layer-1 FP profiles

Genuine dedicated venues (names from the dumps): **T's Tantan / T's たんたん**
(vegan tantan, Tokyo Eki), **FALAFEL BROTHERS** ×2, **Loving Hut**,
**HealthyTOKYO Cafe & Shop**, **Lima, vegan restaurant and store**,
**PLANT BASED**, **Vegan 8ablish**, **Universal Bakes and Cafe**,
**THE NUTS EXCHANGE**, **Bio café**, **Earth MILK** (plant_milk cuisine),
**Swell Bowls**, **Stork Vegan**, **Saladde-li MARGO (サラダデリ MARGO,
a relation!)**, **チョップドサラダデイズ** ×2, **クリスプ・サラダ・ワークス**,
**Aloha Salad Café**, **to your Farm**, **GONNA DAYS**, **Ome Farm Kitchen**
(cuisine `salad;vegetables;health_food` + `diet:*=yes`).

**FP profile 1 — `cuisine~salad` is on the menu, not the concept** (BKK's
finding, reproduced): of the 22 cuisine-matched POIs at least **8–9
(≈ 36–41 %)** are places where salad is a side: **すき家** (beef_bowl chain,
`cuisine=beef_bowl;breakfast;salad;curry;seafood`), **キャンティ・トレ**
(`italian_pizza_pasta_salad`), **コスギグリルマーケット**
(`grill;salad;rice;kimchi;seafood`), **うどんカフェ鈴屋**
(`noodle;salad;udon;…`), **アヤスカフェ小岩** (`chicken;curry;…;salad`),
**おたカフェ** ×2 (`dessert;salad;cake`), **Good morning café Waseda**
(`pizza;salad;burger;curry`), **東京Qeema** (`salad;thai`). Same rule as BKK:
require the matched cuisine value to be primary, or exclude POIs whose cuisine
contains a dominant cuisine (beef_bowl, noodle, pizza…).

**FP profile 2 — `shop=health_food` in Tokyo is a mixed bag** (new, BKK had no
analogue): of 24, genuine health-food shops are **自然食品の店 グルッペ,
Natural Mart, Bio-ral Shinjuku Marui, 有機の里, Beans, Nuts Tokyo, Zenb Store
& Sandwich, アクア, 飛鳥山テラス, ヤマギシファーム, 横山安五郎商店,
そうけん健康食品**; but the set also contains **tofu shops** (三代目茂蔵豆富
×2, 越後屋 豆腐店, 和泉屋豆腐店, 大豆工房 みや — traditional tofu retail is
*adjacent to* but not "health food"), **武州養蜂園** (honey), **あほや
にんにく堂** (garlic), **浅香精進食品製造** (a food *manufacturer*),
**LHG水素健康サロン** (a hydrogen-salon), and the only
`shop=nutrition_supplements` ×2 is/are **ヤクルト (Yakult) 赤羽センター — a
delivery center, not a shop**. A shop-tier filter needs brand/type exclusions
or Layer-3 review.

## 3. Layer 2 — Japanese/English dictionary over all named food POIs

Corpus: **35,869 named POIs** with `amenity=restaurant|cafe|fast_food`
(fetched as three exact-key dumps with `out tags center`; the regex-selector
form is what 504s on mail.ru — same as BKK): 22,734 restaurants (of 23,977
total amenity=restaurant — **1,243 = 5.2 % unnamed**), 5,891 cafes, 7,244
fast_food. Matched against `name` + `name:en` + `name:ja`, case-insensitive;
Latin terms with `\b` word boundaries; JA terms as substrings.

### 3.1 Core dictionary counts

Ticket's JA terms + measured v2 probes:

| Term | Meaning | Hits | Notes / samples |
|---|---|---|---|
| ヘルシー | healthy | **1** | ヘルシーカフェのら — near-dormant in Tokyo names |
| サラダ | salad | **8** | クリスプ・サラダ・ワークス ×2, チョップドサラダデイズ ×2, サラダキッチン, サラダニース; **FP: パスタ&サラダ ピエトロ** (Pietro chain, salad as side) |
| ヴィーガン | vegan | **3** | ヴィーガンビストロ じゃんがら, Vegan Ramen UZU Tokyo, ヴィーガン餃子 |
| ビーガン | vegan | **0** | ヴィーガン spelling dominates |
| 糖質制限 / 糖質オフ | low-carb | **0 / 0** | the entire low-carb vocabulary is absent |
| タンパク質 | protein | **0** | — |
| プロテイン | protein | **0** | — (protein-shop culture lives outside OSM names) |
| マクロビ(オティック) | macrobiotic | **0** | — |
| グルテンフリー / グルテン | gluten-free | **0 / 0** (JA) | but Latin `gluten` → 2, see below |
| 有機 | organic | **1** | 有機の陽 お弁当 (fast_food) |
| 発酵 | fermented | **4** | 発酵食専門カフェ 醸カフェ, OH!!! ～発酵、健康、食の魔法!!!～ ×2, 旬おばんざいと発酵酒肴 ただ今 (izakaya — partial FP) |
| ローカボ | low-carb abbr | **0** | — |
| 菜食 | vegetarian(ism) | **5 raw → 4 true** | 菜食健美, 旬菜食健 ひな野 ×2, 玄米菜食Dan; **FP: 蔡菜食堂** (surname 蔡) |
| 精進 | shōjin (Buddhist veg) | **1** | 精進蕎麦あさひ — clean; the BKK เจ compound-rule worry did not materialize (only 1 hit) |
| 玄米 | brown rice | **1** | 玄米菜食Dan (dup with 菜食) |
| 豆腐 | tofu | **10 — reject** | 麻婆豆腐専門 ×2, 東京純豆腐 (sundubu), 中山豆腐店, 豆腐うかい… — all tofu/mapo dishes, **exact analog of BKK's เต้าหู้ reject** |
| スムージー / デトックス / ファスティング / クリーン / 植物性 | smoothie / detox / fasting / clean / plant-based | **0 / 0 / 0 / 0 / 0** | all dormant |
| ケト | keto | **1 raw → 0 true** | **FP: コフィア エクスリビリス ケトル — matched inside ケトル "kettle"**; use ケトジェニック or compound rule |
| ベジ | veggie | **4 → ~2 true** | ベジキッチン, ベジハウス true; **FP: 肉野菜炒めベジ郎** (meat izakaya), ベジ酒場 borderline |
| 薬膳 | yakuzen (medicinal food) | **10** (v2 probe, not in ticket list) | 薬膳火鍋, 薬膳カレーじねんじょ, 薬膳食堂ちゃぶ膳, 薬膳スープカレー シャナイア… — a real, cleanly-matching JA health-food genre; **recommend adding as strong** |
| 豆乳 / ゴーヤ / 湯豆腐 | soy milk / gōya / yudōfu | 0 / 0 / 0 | dormant |

Latin probes (the BKK v2 list carried over):

| Term | Hits | Samples |
|---|---|---|
| **vegan** | **13** | Tokyo Vegan Ramen Center, 菜道, まるごとVeganダイニング浅草 / Marugoto Vegan Dining Asakusa (same venue, both scripts), Vegan 8ablish, Vegan Churros ~G'DAY~, Halal and Vegan Ramen Dattebayo!, Stork Vegan, ベィーガン居酒屋真さか (JA name has a typo ベィーガン, but its `name:en` "Vegan Izakaya Masaka" matched) |
| salad | 6 | Aloha Salad Café, High five salad ×2, クリスプサラダワークス, チョップドサラダデイズ, EAT GOOD PLACE |
| gluten | 2 | Rizlabo Gluten-free Pancakes, Gluten Free T's Kitchen |
| organic | 2 | オーガニックレストラン「広場」, 自然野菜レストラン 駒込 ナーリッシュ (name:en "Organic…") |
| natural | 3 | Natural kitchen yoomi, natural meal & cafe キナリヤ, Natural Cafe & Restaurant TA — *weak* (natural-branding ≠ health) |
| healthy | 1 | LinNa HEALTHY LIFESTYLE |
| vegetarian / veggie | 1 / 1 | Vegetarian Beast; ベジハウス |
| fit | 1 | Echika fit — borderline (lifestyle brand, not health food) |
| health, protein, keto, clean, macro(s), low-carb, meal prep, calorie | 0 each | all dormant |

**Union of the dictionary: 61 unique POIs** = JA 38 + Latin 30 − 7 overlap
(0.17 % of 35,869; BKK was 57 = 0.87 %). **15 of the 61 also carry
Layer-1 dedicated tags → the dictionary's marginal contribution over Layer 1
is ≈ 46 POIs citywide (0.13 %)**. Bangkok's dictionary added relatively 5×
more (43/6,587 = 0.65 %).

### 3.2 The two Layer-2 laws for Japanese (mirrors of the เจ problem)

1. **Katakana morae are not tokens.** `ケト` matched ケトル ("kettle") —
   one-off here, but structurally identical to raw `เจ` (5 % precision in
   BKK). Rule: multi-mora loanwords only as full words (グルテンフリー,
   ケトジェニック) or with explicit compound lists.
2. **Kanji homophones and dish names poison short kanji strings.** `菜食` →
   蔡菜食堂; `豆腐` → mapo/tofu restaurants (reject, 10/10 FP in the true
   sense). Kanji terms need domain validation per term before adoption.

And the headline lexical finding: **Tokyo health venues label themselves in
Latin.** `vegan` (13) ≫ `ヴィーガン` (3) + `ビーガン` (0); `salad` (6) ≈
`サラダ` (8); `gluten` (2) > グルテン (0). An implementation that matches only
JA script would miss most of the signal; the dictionary must be bilingual by
construction (the BKK run found the same for Thai names with Latin brand
parts).

## 4. Per-district contrast (Layer-3 context; 渋谷 vs 世田谷 vs 八王子)

Method (BKK protocol, one fix): boundary relations `admin_level=7` from OSM —
渋谷区 `1759477`, 世田谷区 `1759474`, 八王子市 `5301639` — fetched `out geom`;
member ways stitched into rings by endpoint-adjacency walk (the naive
"extend-until-closed" chain from the BKK note produced a broken Setagaya ring
of 1,586 km²; the adjacency walk closed 1 ring per district: 1,045 / 1,972 /
4,506 points, no repeated vertices). **Ring areas were validated against
official figures:** computed 15.2 / 58.2 / 186.9 km² vs Wikipedia 渋谷区
**15.11 km²**, 世田谷区 **58.05 km²**, 八王子市 **186.38 km²** — all within
0.6 %. (Two "sanity failures" en route were my own bad landmark coordinates,
not data errors: real OSM POIs named 幡ヶ谷/笹塚/初台 and 26 八王子-named
POIs all fall inside the rings.) Landmark spot checks: Shibuya Station,
区役所, 原宿, 恵比寿 inside; Nakano/Shinjuku/Kokubunji/Sagamihara outside.
`nwr(area:…)` server-side filtering could not be used: mail.ru returns 0
(§1), api.de flapped — hence local PIP, as in BKK. The 32/61 `subarea`
sub-relations of 渋谷/世田谷 were fetched and are **not needed**: the main
rings already match official areas, so the sub-relations are alternate/duplicate
boundary parts.

| District | area (km²) | food POIs (named) | tag-dedicated | tag-options | dict hits (marginal) | health shops |
|---|---|---|---|---|---|---|
| **渋谷区** (central, 15.2 km²) | 15.2 | **1,636** | **12** | **21** | 6 (3) | 0 |
| **世田谷区** (residential, 58.2 km²) | 58.2 | **1,309** | **5** | **20** | 3 (2) | 0 |
| **八王子市** (outer-west suburb, 186.9 km²) | 186.9 | **774** | **1** | **0** | 2 (2) | 0 |

Dedicated per 1,000 food POIs: **渋谷 7.3 → 世田谷 3.8 → 八王子 1.3** — a
clean 5.6× center-to-suburb gradient.

渋谷's 12 dedicated: Lima, Bio café, ヴィーガンビストロ じゃんがら,
ベィーガン居酒屋真さか, Hemp Cafe Tokyo, PLANT BASED, Sky High, whyte,
Earth MILK, to your Farm, THE NUTS EXCHANGE, なぎ食堂. 世田谷's 5: 薬膳食堂
ちゃぶ膳, 明天好好, Universal Bakes and Cafe, Cafe Anthrop,
チョップドサラダデイズ. 八王子's sole "dedicated" is うどんカフェ鈴屋 — a
cuisine-salad **false positive**; its 2 marginal dictionary hits are 豆腐うかい
(tofu kaiseki — dubious) and LinNa HEALTHY LIFESTYLE (genuine).

**This inverts the Bangkok reading.** In BKK the outer district was
*unmapped* (Nong Chok: 12 food POIs — nothing to read). In Tokyo the suburb is
well mapped (774 POIs in 八王子 vs BKK Lat Phrao's 76) and the health signal
genuinely *thins*: 1 dedicated (itself an FP), 0 options, dictionary hits of
dubious relevance. For Tokyo, the near-zero outer-district score is a
**faithful signal of absence**, not mapping bias — the dictionary cannot
"correct" it because there is nothing mislabeled to recover, and Overture's
role shifts from recall-lifeline (BKK) to FP-quality and chain completeness.

## 5. Layer 3 — plan only (not run)

1. **LLM pass** over every food POI's `name + cuisine + brand + description`
   (OSM) plus Overture Places for the same bbox, labeling
   `dedicated / options / not-health` + confidence — as in CRTKY-149.
2. **Hand validation ~100 POIs**, drawn 渋谷 / 世田谷 / 八王子; unlike BKK,
   all three legs can be drawn from OSM itself (八王子 has 774 candidates).
   Priority FP checks for hand-labeling: `cuisine~salad` set (36–41 % FP
   expected), `shop=health_food` (tofu/honey/garlic/Yakult FPs),
   single-branch chain `=only` tags (KOMEDA is □), the `=only` long tail of
   cafes (Sky High, whyte, THE_B, coret, meu nota).
3. Precision/recall per tier; adopt thresholds only if dictionary precision
   holds and the dedicated/options split survives hand-labeling.
4. KBJU reality check (kept honest, same as BKK): name/tag hits are
   venue-type evidence, not nutrition data.

## 6. Verdict per layer, and the cross-city framework

| Layer | Verdict | Basis (this run) |
|---|---|---|
| 1 — OSM tags | **adopt, with FP filters** | live, 110 dedicated / ~216 options citywide; require primary `cuisine=health_food\|salad` or dominant-cuisine exclusion (§2.3); keep only-vs-yes semantics; whitelist `diet:*` keys |
| 2 — dictionary | **adopt only as a cheap booster** | +46 marginal (0.13 %); bilingual by construction (Latin carries the vegan signal in Tokyo); ケト/菜食/豆腐 need compound-or-reject rules; add 薬膳; expect near-zero yield outside central wards |
| 3 — LLM + Overture | **adopt for FP-quality & enrichment, not recall** | in Tokyo the tags+dictionary already separate 渋谷 (7.3 dedicated/1000) from 八王子 (≈0) *correctly*; LLM mainly kills cuisine-salad and tofu-class FPs and resolves single-branch chain tags |

**Cross-city framework (both CRTKY-149 and CRTKY-176), one design:**

- Layer 1 identical selector set + only-vs-yes semantics; per-city FP rules
  (BKK: ส้มตำ-style dominant-cuisine exclusion; Tokyo: beef_bowl/noodle/
  italian_pasta families) — the salad-side-FP rate is 33–41 % in both cities,
  the single most reproducible Layer-1 finding.
- Layer 2 per-city dictionaries sharing structure (script-specific
  substring/`\b`/compound rules + bilingual Latin terms) and the shared
  rejects (tofu family in both cities); city-specific strong terms
  (เจ-compounds / อาหารสุขภาพ; ヴィーガン, 薬膳, 菜食).
- Layer 3 weighted differently: **BKK needs it for recall** (outer districts
  unmapped), **Tokyo needs it for precision** (suburbs mapped, absence real).
- Mirror plumbing is shared and currently broken: `OVERPASS_ENDPOINTS`
  (`scripts/bangkok/fetch.py:47`) needs `overpass-api.de`+User-Agent and
  mail.ru, busy/504-aware retries, and must not use `area:` filters.

Overall: **promising** — the same three-layer design ports to Tokyo with
better-than-BKK Layer-1 signal quality (only-vs-yes split is cleaner, tagging
is denser) and a smaller Layer-2 marginal yield.

## 7. Draft dictionary (reusable; Bangkok mirror CRTKY-149)

| # | Term | Script | Meaning | Tier | Match rule | TYO hits (this run) | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | ヘルシー | ja | healthy | strong | substring | 1 | keep (near-dormant) |
| 2 | サラダ | ja | salad | **weak (options)** | substring | 8 (1 chain FP) | keep |
| 3 | ヴィーガン / ビーガン | ja | vegan | strong | substring | 3 / 0 | keep |
| 4 | 糖質制限 / 糖質オフ / ローカボ | ja | low-carb | strong | substring | 0 | keep (dormant) |
| 5 | タンパク質 / プロテイン | ja | protein | strong | substring | 0 | keep (dormant) |
| 6 | マクロビ(オティック) | ja | macrobiotic | strong | substring (マクロビ) | 0 | keep (dormant) |
| 7 | グルテンフリー / グルテン | ja | gluten-free | strong | substring | 0 / 0 | keep |
| 8 | ケト / ケトジェニック | ja | keto | strong | **compound only** — ケトジェニック or token ケト | 1 raw = ケトル FP | keep with rule; never bare ケト |
| 9 | 有機 / オーガニック | ja | organic | strong | substring | 1 / (Latin 2) | keep |
| 10 | 発酵 | ja | fermented | weak | substring | 4 (1 izakaya partial) | keep, tier=weak |
| 11 | 菜食 | ja | vegetarian | strong | **compound**: 菜食 but not 蔡菜食 | 5→4 | keep |
| 12 | 精進(料理) | ja | Buddhist veg | strong | compound 精進料理/精進蕎麦 | 1 | keep |
| 13 | ベジ(タリアン/カフェ) | ja | veggie | strong/options | substring + FP list | 4→~2 | keep |
| 14 | 薬膳 | ja | yakuzen | **strong (new)** | substring | 10, all genuine | **add** |
| 15 | 豆腐 | ja | tofu | — | — | 10, all tofu dishes | **reject** (same as เต้าหู้) |
| 16 | vegan / vegetarian / veggie | en | vegan | strong/options | `\b` regex | 13 / 1 / 1 | keep — **dominant signal in Tokyo** |
| 17 | salad | en | salad | weak (options) | `\bsalad\b` | 6 | keep, tier=options |
| 18 | healthy / health | en | healthy | strong | `\bhealthy\b`, `\bhealth\b` | 1 / 0 | keep |
| 19 | gluten / organic | en | gluten-free / organic | strong | `\b` regex | 2 / 2 | keep |
| 20 | natural | en | natural | — | `\bnatural\b` | 3, ambiguous branding | keep at weak tier only |
| 21 | fit | en | fit | strong | `\bfit\b` | 1 borderline (brand) | keep, needs review |
| 22 | protein / keto / clean / macro / low-carb / meal prep / calorie / smoothie / detox / fasting / plant-based / スムージー / デトックス / ファスティング / クリーン / 植物性 / 玄米 / 豆乳 | en/ja | misc | strong | `\b` / substring | 0–1 each | keep (dormant); 玄米 only as compound (玄米菜食) |

Bangkok-adaptation note (reverse of BKK §7): tier semantics transfer; Latin
block is shared; the JA block replaces Thai there. The เจ lesson now has two
confirmed instances — Thai เจ (raw-substring trap) and JA ケト/菜食
(mora/homophone traps) — plus one confirmed shared reject (tofu). Any
single-CJK/Thai short string must ship with a compound rule or a measured
precision check.

## 8. Sources & license

- Overpass mirrors (queried 2026-10-13, POST `data=`):
  `https://maps.mail.ru/osm/tools/overpass/api/interpreter` (dumps),
  `https://overpass-api.de/api/interpreter` (counts; needs User-Agent),
  availability per §1; `overpass.osm.ch` rejected (region lag).
- Data license: OSM **ODbL** (stated in every Overpass response: "The data
  included in this document is from www.openstreetmap.org… ODbL").
- Granularity/fields: OSM node/way/relation POIs, tags `name`, `name:en`,
  `name:ja`, `amenity`, `shop`, `cuisine`, `diet:*`, `organic`, `brand`;
  district polygons OSM relations `admin_level=7` (+ `subarea` sub-relations,
  unused). Official areas for validation: Wikipedia 渋谷区 15.11 km²,
  世田谷区 58.05 km², 八王子市 186.38 km² (en.wikipedia, fetched 2026-10-13).
- Working data: `/tmp/crtky176/` (raw dumps, corpus, hit lists).
- Pipeline helpers referenced: `scripts/bangkok/fetch.py:47`
  (OVERPASS_ENDPOINTS — needs updating per §1), `fetch.py:64-87`
  (rotation/backoff).
- Tickets: Plane CRTKY-176 (this run), CRTKY-149 (Bangkok precedent and
  dictionary/validation design).

## 9. Open questions for the owner

1. Overture cross-check for Tokyo (categories/names for the same bbox) —
   still unrun; given §4 it should be scoped to FP-quality/chain-completeness
   rather than outer-district recall.
2. Hand-validation sample design: with 八王子's 774 POIs the "outer leg" can
   come from OSM (unlike BKK); confirm the 25/50/25 split 渋谷/世田谷/八王子.
3. `shop=health_food` tier: keep tofu/honey/garlic/Yakult-delivery FPs out
   via what — brand list, `organic=*`/`viando`-style secondary tags, or Layer
   3? (Tokyo-specific; BKK's 11 shops were clean by comparison.)
4. Chain `=only` tags (KOMEDA is □ single branch; BKK's Swensen's
   chain-wide `=yes`): filter `brand`-tagged POIs out of both tiers, or keep
   per-branch truth?
5. `cuisine~salad` FP rule: primary-cuisine-position requirement vs
   dominant-cuisine exclusion list vs Layer-3-only — the 33–41 % FP rate
   makes raw adoption the worst option in both cities.
6. Mirror policy (both cities): add mail.ru + User-Agent for
   `overpass-api.de`, retry waves of 25–45 s, forbid `area:` filters on
   mail.ru, drop `overpass.osm.ch`.

*Companion notes from the same day: research/notes/2026-10-13-{air-pollen-
crtky172, flood-crtky171, noise-crtky175, roads-homeless-crtky174,
tourists-crtky173}.md; Bangkok precedent:
research/bangkok/notes/2026-10-13-healthfood-crtky149.md.*
