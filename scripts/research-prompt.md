# AI Research Prompt Template for Station Neighborhoods

## System Prompt

You are a knowledgeable Tokyo neighborhood researcher and writer. You will research a specific station area in Greater Tokyo and produce a structured JSON output with neighborhood ratings and descriptions.

Your output must be factual, based on real knowledge of Tokyo neighborhoods. Write descriptions in Russian (живой, дружелюбный стиль). Ratings must be integers 1-10.

## User Prompt Template

```
Исследуй район вокруг станции {STATION_NAME} ({STATION_NAME_JP}) в радиусе 10-15 минут пешком.

Линии: {LINES}

Верни JSON в следующем формате (без markdown, только чистый JSON):

{
  "slug": "{SLUG}",
  "ratings": {
    "food": <1-10, разнообразие и качество еды, ресторанов>,
    "nightlife": <1-10, бары, изакаи, ночная жизнь>,
    "transport": <1-10, количество линий, частота, удобство пересадок>,
    "rent": <1-10, доступность аренды — 10=дёшево ¥70-80k, 1=дорого ¥170k+>,
    "safety": <1-10, безопасность района>,
    "green": <1-10, парки, зелёные зоны, прогулки>,
    "gym_sports": <1-10, наличие спортзалов, фитнес-клубов, спортивных площадок>,
    "vibe": <1-10, общая атмосфера, "душевность", интересность района>,
    "crowd": <1-10, 10=тихо и спокойно, 1=очень многолюдно>
  },
  "transit_minutes": {
    "shibuya": <минуты на поезде>,
    "shinjuku": <минуты на поезде>,
    "tokyo": <минуты на поезде>,
    "ikebukuro": <минуты на поезде>,
    "shinagawa": <минуты на поезде>
  },
  "rent_estimate": {
    "1k_1ldk_min": <примерный минимум аренды 1K-1LDK 40-50кв.м в йенах>,
    "1k_1ldk_avg": <примерная средняя аренда>,
    "2ldk_avg": <примерная средняя 2LDK>
  },
  "description": {
    "atmosphere": "<2-3 предложения на русском: общая атмосфера района>",
    "landmarks": "<2-4 предложения: ключевые достопримечательности, храмы, парки, рынки в 15 мин пешком>",
    "food": "<2-4 предложения: где покушать, уличная еда, фуд-корты, киссатэн, интересные кофейни>",
    "nightlife": "<2-3 предложения: бары, изакаи, ночная жизнь, где провести вечер>"
  },
  "highlights": ["<3-5 ключевых фишек района коротко>"],
  "nearby_gyms": ["<названия 1-3 крупных спортзалов рядом, если знаешь>"],
  "nearby_parks": ["<названия парков в 15 мин пешком>"]
}

Важно:
- transit_minutes — реальное время на поезде (не пешком), включая пересадки
- rent — инвертированный: дешевле = выше рейтинг
- crowd — инвертированный: тише = выше рейтинг
- Пиши описания живо и дружелюбно, как будто рассказываешь другу
- Будь точен в оценках — не завышай рейтинги
```

## Batch Execution

For batch processing, iterate over stations from `data/stations.json`:

```python
import json
from anthropic import Anthropic

client = Anthropic()

with open('data/stations.json') as f:
    stations = json.load(f)

for station in stations:
    if os.path.exists(f'data/ratings/{station["slug"]}.json'):
        continue  # skip already processed

    prompt = TEMPLATE.format(
        STATION_NAME=station['name_en'],
        STATION_NAME_JP=station['name_jp'],
        SLUG=station['slug'],
        LINES=', '.join(station['lines']),
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    result = json.loads(response.content[0].text)

    with open(f'data/ratings/{station["slug"]}.json', 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
```

## Manual Research Mode (in Claude Code session)

For interactive research, ask Claude directly:

```
Исследуй район вокруг станции Nakano (中野).
Линии: JR Chuo, Tokyo Metro Tozai.
[paste full prompt template above]
```

Review output, adjust ratings if needed, save to `data/ratings/nakano.json`.

## Quality Checklist

After AI generates data, verify:
- [ ] Transit times are reasonable (compare with Google Maps)
- [ ] Rent estimates align with Suumo ranges
- [ ] Ratings feel calibrated (Shinjuku food=9, not 10; Roppongi nightlife=10)
- [ ] Descriptions mention real places, not hallucinated ones
- [ ] No rating is exactly 5 for everything (avoid lazy middle-ground)
