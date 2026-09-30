# Bangkok district descriptions — generation rules

Companion to `research/description-generation-rules.md` (Tokyo stations). Same
product, same voice; the unit is a **khet (district)** instead of a station
catchment, so descriptions characterise a whole district and name the
neighbourhoods inside it.

Output per district: `data/bangkok/descriptions/<slug>.json`

```json
{
  "en": { "atmosphere": "…", "landmarks": "…", "food": "…", "nightlife": "…" },
  "ja": { "atmosphere": "…", "landmarks": "…", "food": "…", "nightlife": "…" },
  "ru": { "atmosphere": "…", "landmarks": "…", "food": "…", "nightlife": "…" }
}
```

`scripts/bangkok/build.py` validates that all 12 strings exist and merges them
into `app/src/data/bangkok/districts.json`.

## Voice

Telegram-style, punchy, comma-separated phrases. A local insider talking to
someone choosing where to live — not a tourist guide. Opinionated but
factual; every district has trade-offs and they get named.

Length per field (EN): atmosphere 18–35 words · landmarks 12–30 · food 12–30 ·
nightlife 8–22. JA/RU roughly the same information density.

Good register (Tokyo examples, translated): "Canal-side cool Tokyo, design
offices, dates and cherry-blossom mobs. Beautiful, expensive, crowded." ·
"Minimal." (for truly nothing).

## What each field covers

- **atmosphere** — what living here feels like: character, who lives here,
  pace, the main trade-off. Name 1–3 neighbourhoods inside the district
  (Thong Lo, Ari, Talat Noi, Ramkhamhaeng…). Mention rail reality plainly
  (e.g. "no rail — buses, boats and motorbike taxis") when it defines daily life.
- **landmarks** — parks, temples, markets, rivers/canals, malls, campuses,
  walks. Only places you are certain are in (or on the edge of) this district.
- **food** — the eating culture: street food, markets, food courts, cafés,
  mall dining, famous strips. No invented restaurant names; well-known
  institutions only if you are sure of the location.
- **nightlife** — bars, live music, rooftop, clubs, night markets — or
  "Quiet after dark" when that is the truth.

## Hard rules

1. **Facts over flair.** Only mention places you are confident exist in this
   district today (2026). Bangkok changes fast: Dusit Zoo closed in 2018,
   Scala cinema was demolished, Chatuchak Weekend Market is in Chatuchak,
   Asiatique is in Bang Kho Laem, ICONSIAM in Khlong San, Suan Luang Rama IX
   in Prawet. When unsure, stay general.
2. **Don't restate the ratings** ("safety 7/10") and don't mention data
   sources (OSM, Overture) — that is meta, not description.
3. **At most one number per field**, rounded, and only from the brief
   ("~3k places to eat"). Numbers are optional.
4. **No tourist-brochure language**: no "hidden gem", "must-visit", "vibrant
   tapestry", "perfect for families", "something for everyone".
5. **Respect the data.** If the brief says transport is weak, don't call it
   well connected. Crowd = quietness (10 = very quiet). Rent is affordability
   (10 = cheapest). Rent and safety are editorial estimates: don't contradict
   them, don't dramatise safety.
6. **Hedge estimates.** Where a category's confidence is `estimate`, use
   "likely / mostly / seems".
7. **Write each language natively**, not as a translation:
   - JA: use the district's katakana name as given (e.g. ワッタナー区), common
     Japanese spellings for places (アソーク, トンロー, シーロム, サイアム,
     ヤワラート/チャイナタウン, チャオプラヤー川). です/ます not required —
     concise 体言止め is fine, like the Tokyo JA copy.
   - RU: natural Russian; Thai names in established Russian spelling where one
     exists (Сукхумвит, Силом, Сиам, Чао Прайя, Яоварат, Чатучак); brand and
     mall names stay in Latin (ICONSIAM, EmQuartier, Terminal 21).
8. Plain text only — no markdown, no emoji, no line breaks inside fields.
