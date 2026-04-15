#!/usr/bin/env python3
"""
Generate one self-contained prompt file per station → data/prompts/<slug>.md

Each file contains everything an LLM needs to produce the description:
- Voice/rules (system instructions)
- 3 few-shot examples (high/low/medium data density)
- Station data JSON
- Expected output contract

Usage:
    python3 scripts/build-prompts-dir.py          # all stations not yet done
    python3 scripts/build-prompts-dir.py --all    # regenerate for all 1493
    python3 scripts/build-prompts-dir.py --slug akabane   # single station

Note: since 2026-04-15 we regenerate descriptions for ALL 1493 stations,
including the ~252 AI-researched ones that previously had single-field
RU descriptions. New output is structured {en,ja,ru} × {atmosphere,landmarks,food,nightlife}.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESC_DIR = ROOT / "data" / "descriptions"
PROMPT_DIR = ROOT / "data" / "prompts"
PROMPT_DIR.mkdir(exist_ok=True, parents=True)


SYSTEM = """# Tokyo Station Description Generation

## Voice

Concise. Insider. Opinionated. **Telegram-style** — comma-separated phrases, not tourist brochure. Like you live there.

## Rules

1. **DON'T restate rating numbers** — the user already sees "Food: 9/10" on the page.
2. **DON'T be generic** — "nice area with restaurants" is useless. Be specific.
3. **DO mention trade-offs and contrasts** — "great food but gritty after dark"; "cheap rent but 40 min from center".
4. **DON'T describe what you don't know** — if data is mostly zeros/estimates, keep it short.
5. **DON'T over-praise** — even top stations have weaknesses.
6. **DO flag flood/seismic risk** — elevation <5m = flood risk, seismic very_high = soft ground.
7. **"Minimal." is a valid nightlife answer** if the station is dead after 9pm.
8. **DON'T mention data sources** — no "according to HotPepper".

## Length per field

- `atmosphere`: 1-2 sentences, 40-80 chars EN
- `landmarks`: 1-2 sentences, 40-80 chars EN
- `food`: 1-2 sentences, 40-80 chars EN
- `nightlife`: 1 sentence, 30-60 chars EN

Japanese is shorter (kanji density). Russian may be slightly longer than EN.

## Output contract

Return **only** this JSON object — no markdown, no explanation, no preamble:

```json
{
  "en": {"atmosphere": "...", "landmarks": "...", "food": "...", "nightlife": "..."},
  "ja": {"atmosphere": "...", "landmarks": "...", "food": "...", "nightlife": "..."},
  "ru": {"atmosphere": "...", "landmarks": "...", "food": "...", "nightlife": "..."}
}
```

## Few-shot examples

### Example 1 — Akihabara (data-rich, tourist hub)

Data: 5 lines, 249k daily passengers, 1077 HotPepper (527 izakaya, 51 bars, 44 cafes), 326 midnight spots, 48 cultural venues, 28 hostels, last train 00:47, elevation 11m, seismic high.

```json
{
  "en": {
    "atmosphere": "Otaku pilgrimage site, wall-to-wall arcades and maid cafes. Tourist-mobbed, especially weekends.",
    "landmarks": "Yodobashi Camera, UDX tower, Radio Kaikan. Electric Town pedestrian zone packed 24/7.",
    "food": "Izakaya dominates (527 spots). Ramen alleys, standing sushi, chain gyudon. Quality varies wildly.",
    "nightlife": "Karaoke sparse, clubs minimal. Izakayas run late. Midnight culture fades fast after 11pm."
  },
  "ja": {
    "atmosphere": "オタク聖地、アーケードとメイド喫茶の密集地帯。特に週末は観光客で身動き取れず。",
    "landmarks": "ヨドバシカメラ、UDXタワー、ラジオ会館。電気街歩行者天国は終日混雑。",
    "food": "居酒屋が圧倒的（527件）。ラーメン横丁、立ち寿司、チェーン牛丼。質はまちまち。",
    "nightlife": "カラオケ稀少、クラブほぼなし。居酒屋は遅くまで。夜中の文化は11時以降急速に萎縮。"
  },
  "ru": {
    "atmosphere": "Мекка отаку, стена-к-стене аркады и мейд-кафе. Туристический хаос, особо в выходные.",
    "landmarks": "Yodobashi Camera, башня UDX, Radio Kaikan. Пешеходная зона электротехники переполнена 24/7.",
    "food": "Изакая доминирует (527 мест). Лапша, стоячие суши, чейн гюдон. Качество прыгает.",
    "nightlife": "Караоке редко, клубы минимальны. Изакаи работают подольше. После 23:00 почти мертво."
  }
}
```

### Example 2 — Hatchobori (data-sparse, office district)

Data: 2 lines, no daily passengers, zero HotPepper, zero OSM food/nightlife, no crime data, Chuo-ku, last train 00:37.

```json
{
  "en": {
    "atmosphere": "Quiet office corridor near Tokyo Station. Daytime buzz, evening ghost town.",
    "landmarks": "Chuo-ku administrative hub. Riverfront walks along Sumida. Low-key.",
    "food": "Data limited — scrapers missed this area. Scattered lunch spots, minimal nightlife venues.",
    "nightlife": "Minimal. Office workers head elsewhere after 6pm."
  },
  "ja": {
    "atmosphere": "東京駅近い事務所街。昼は人通り多い、夜は静か。",
    "landmarks": "中央区役所エリア。隅田川沿いの散歩道。地味だが落ち着いた。",
    "food": "データ限定 — スクレイパーの網目粗い。昼食スポット散在、夜の店ほぼなし。",
    "nightlife": "ほぼ皆無。サラリーマンは別の場所へ。"
  },
  "ru": {
    "atmosphere": "Тихий офисный коридор у Токийского вокзала. День — толпа, вечер — пусто.",
    "landmarks": "Администрация Тюо-ку. Набережная Сумида. Скромно, но спокойно.",
    "food": "Данные неполные — скреперы пропустили район. Обеденные места разреженно, ночных заведений нет.",
    "nightlife": "Практически нет. Офисные работники разбегаются в 18:00."
  }
}
```

### Example 3 — Asuka-Yama (mid-tier, tram town, cherry blossoms)

Data: 1 line (Arakawa tram), Kita-ku, 52 restaurants, 21 izakaya, 395k sqm green (Asukayama Park), elevation 18m hill, 29 min avg transit.

```json
{
  "en": {
    "atmosphere": "Cherry blossom pilgrimage hub with granny-Tokyo charm. Steep hill, narrow lanes, zero high-rises.",
    "landmarks": "Asukayama Park, Oji Paper Museum, Shibusawa Memorial. Arakawa tram line nostalgia.",
    "food": "52 restaurants clustered near station; 21 izakayas, old-school joints. Quiet daytime, lively evenings.",
    "nightlife": "17 late-night spots, 1 karaoke. Neighborhood bars, not clubs. Drinks end early."
  },
  "ja": {
    "atmosphere": "飛鳥山公園が桜の名所。街全体が昔の東京。丘の上、坂道ばかり、新築なし。",
    "landmarks": "飛鳥山公園、紙の博物館、渋沢栄一記念館。荒川電車の情緒。",
    "food": "駅周辺に食堂52軒。居酒屋21軒、昭和の雰囲気。日中は静か、夜は賑やか。",
    "nightlife": "夜間営業17軒、カラオケ1軒。近所の飲み屋。酒は早仕舞い。"
  },
  "ru": {
    "atmosphere": "Холм Асукаяма — святилище сакуры. Окраина Токио, старые кварталы, крутые подъёмы.",
    "landmarks": "Парк Асукаяма, музей бумаги, мемориал Сибусавы. Трамвайная линия Аракава.",
    "food": "52 ресторана, 21 изакая, заведения дедушкиного поколения. Днём спит, вечером шумит.",
    "nightlife": "17 поздних баров, 1 караоке. Соседский уровень, не клубы. Ночи короткие."
  }
}
```
"""


def build_compact_context(s: dict) -> str:
    """Compact per-station context JSON."""
    r = s.get("ratings", {})
    hp = s.get("hotpepper", {})
    nl = s.get("nightlife_signals", {})
    green = s.get("green_signals", {})
    vibe = s.get("vibe_signals", {})
    crime = s.get("crime", {})
    env = s.get("environment", {})
    ward = s.get("ward", {})
    passengers = s.get("passengers", {})
    rent = s.get("rent", {})
    transit = s.get("transit_minutes", {})
    livability = s.get("livability", {})
    lines = s.get("lines", [])
    last_train = s.get("last_train", {})

    conf_str = r.get("confidence", "{}")
    try:
        conf = json.loads(conf_str) if isinstance(conf_str, str) else (conf_str or {})
    except Exception:
        conf = {}

    loc_parts = []
    if ward.get("prefecture_name"):
        loc_parts.append(ward["prefecture_name"])
    if ward.get("city_name"):
        loc_parts.append(ward["city_name"])
    if ward.get("ward_name") and ward["ward_name"] != ward.get("city_name"):
        loc_parts.append(ward["ward_name"])
    location_str = ", ".join(loc_parts) if loc_parts else "?"

    ctx = {
        "name": f"{s['name_en']} ({s['name_jp']})",
        "location": location_str,
        "line_count": s["line_count"],
    }
    if lines:
        ctx["lines"] = [l.get("name_en", l.get("id")) for l in lines[:6]]
    if passengers.get("daily_passengers"):
        ctx["daily_passengers"] = passengers["daily_passengers"]
    if last_train.get("weekday"):
        ctx["last_train_weekday"] = last_train["weekday"]

    rat = {}
    for k in ["food", "nightlife", "transport", "rent", "safety", "green", "gym_sports", "vibe", "crowd"]:
        v = r.get(k)
        c = conf.get(k, "?")
        if v is not None:
            rat[k] = f"{v}({c[:3]})"
    if rat:
        ctx["ratings"] = rat

    if hp.get("total_count", 0) > 0 or s.get("osm_food", {}).get("food_count", 0) > 0:
        ctx["food"] = {
            "hp": hp.get("total_count", 0),
            "izakaya": hp.get("izakaya_count", 0),
            "bars": hp.get("bar_count", 0),
            "cafes": hp.get("cafe_count", 0),
            "osm": s.get("osm_food", {}).get("food_count", 0),
        }

    if nl.get("midnight_count", 0) > 0 or nl.get("karaoke_count", 0) > 0 or nl.get("nightclub_count", 0) > 0:
        ctx["nightlife_data"] = {
            "midnight": nl.get("midnight_count", 0),
            "karaoke": nl.get("karaoke_count", 0),
            "clubs": nl.get("nightclub_count", 0),
            "hostels": nl.get("hostel_count", 0),
        }

    if green.get("green_count", 0) > 0:
        ctx["green"] = {"count": green["green_count"], "area_sqm": green.get("green_area_sqm", 0)}

    if vibe.get("cultural_venue_count", 0) > 0 or vibe.get("pedestrian_street_count", 0) > 0:
        ctx["vibe"] = {k: v for k, v in vibe.items() if v > 0}

    if crime:
        ctx["crime"] = {
            "total": crime.get("total_crimes"),
            "rate_per_10k": crime.get("crimes_per_10k"),
        }

    if env.get("elevation_m") is not None:
        ctx["environment"] = {
            "elevation_m": env.get("elevation_m"),
            "seismic": env.get("seismic_risk_tier"),
        }

    if rent.get("1k_1ldk"):
        ctx["rent_1k"] = rent["1k_1ldk"]
        ctx["rent_source"] = rent.get("source", "?")

    if transit:
        ctx["avg_transit_min"] = round(sum(transit.values()) / len(transit))

    if livability:
        ctx["essentials"] = {
            "market": livability.get("supermarket_count", 0),
            "pharm": livability.get("pharmacy_count", 0),
            "clinic": livability.get("clinic_count", 0),
        }

    return json.dumps(ctx, ensure_ascii=False, indent=2)


def build_prompt_md(station: dict) -> str:
    """Full self-contained markdown prompt for one station."""
    ctx = build_compact_context(station)
    return f"""{SYSTEM}

---

## THIS STATION

**Slug:** `{station['slug']}`
**Name:** {station['name_en']} ({station['name_jp']})
**Composite score:** {station.get('composite_score', '?')}

### Data

```json
{ctx}
```

### Output

Write the JSON object (and **only** the JSON object) to:

```
data/descriptions/{station['slug']}.json
```

Use the same shape as the examples above: `{{en: {{...}}, ja: {{...}}, ru: {{...}}}}`.

Do not add markdown fences in the output file — write raw JSON.
"""


def main():
    single_slug = None
    regenerate_all = "--all" in sys.argv
    if "--slug" in sys.argv:
        i = sys.argv.index("--slug")
        if i + 1 < len(sys.argv):
            single_slug = sys.argv[i + 1]

    with open(ROOT / "data" / "station-datamart.json") as f:
        dm = json.load(f)

    stations = dm["stations"]
    order = dm["generation_order"]

    written = 0
    skipped_already_done = 0
    skipped_already_prompt = 0

    for slug in order:
        if single_slug and slug != single_slug:
            continue

        station = stations[slug]

        # Skip if already done (output file exists)
        if (DESC_DIR / f"{slug}.json").exists():
            skipped_already_done += 1
            continue

        # Skip if prompt already exists and not --all
        prompt_path = PROMPT_DIR / f"{slug}.md"
        if prompt_path.exists() and not regenerate_all:
            skipped_already_prompt += 1
            continue

        prompt_path.write_text(build_prompt_md(station), encoding="utf-8")
        written += 1

    print(f"✓ Wrote {written} prompt files to {PROMPT_DIR}")
    print(f"  Skipped: {skipped_already_done} already generated, {skipped_already_prompt} already prompted")
    if single_slug:
        print(f"  Single slug mode: {single_slug}")


if __name__ == "__main__":
    main()
