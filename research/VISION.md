# Vision: Data-Driven Transparent Ratings

## Philosophy

Три слоя, снизу вверх:

```
┌─────────────────────────────────────────────┐
│  3. UI: Transparency & Trust                │  ← объясняем пользователю
│     Tooltips, confidence badges, data        │
│     sources, "why this score" explanations   │
├─────────────────────────────────────────────┤
│  2. Logic: Formulas over Data               │  ← нормализуем, взвешиваем
│     log-percentile, crime weights,           │
│     composite signals, minimal heuristics    │
├─────────────────────────────────────────────┤
│  1. Data: Real, Scraped, Verifiable         │  ← собираем побольше
│     HotPepper API, OSM Overpass, Keishicho  │
│     ArcGIS, MLIT, Nominatim, Suumo         │
└─────────────────────────────────────────────┘
```

**Принцип**: Rating настолько хорош, насколько хороши данные под ним. Если данных нет — честно показать пользователю, а не спрятать за красивой цифрой.

---

## Layer 1: Data — побольше и из первоисточников

### Текущее состояние данных

| Категория | Источники | Записей | Покрытие | Реальные данные? |
|-----------|----------|---------|----------|-----------------|
| food | HotPepper API + OSM Overpass | 1493 + 1398 | 100% | ✅ Да |
| nightlife | HP izakaya/bar/midnight + OSM bar/pub/karaoke | 1493 + building | 100% | ✅ Да |
| transport | line_count + MLIT passengers | 1493 + 1409 | 100% | ✅ Да |
| rent | Suumo scrape | 274 | 18% | ⚠️ Частично |
| safety | Keishicho ArcGIS (Tokyo), ward-level (others) | 615 + 91 ward | ~45% | ⚠️ Частично |
| green | OSM park count (area = 0 пока) | 1398 | 94% | ⚠️ Count без площади |
| gym | OSM fitness/sports/pool | 1398 | 94% | ✅ Да |
| vibe | OSM cultural venues (building) | building | 0%→100% | 🔄 Строится |
| crowd | MLIT + hardcoded | 1409 | 94% | ✅ Да |

### Критическая оценка готовности (2026-04)

- **«100%» / полное покрытие строк** в таблице выше = у **каждой** из 1493 станций есть значение в конвейере, **не** то, что все категории одинаково «измерены» (аренда: Suumo vs ward vs регрессия; безопасность: полигоны Токио vs ward вне Токио).
- **Confidence `strong`:** для **green** и **vibe** в снимках метаданных часто **0** при живом OSM — уровень отражает **правила compute**, а не «карта выглядит хорошо»; см. `research/00-overview.md`.
- ~~**Hub commute:** заглушка 30m~~ ✅ **CRTKY-81 done:** калиброванная модель (MAE 5.5 мин, 85% within 10 min), все 1493 уникальны.
- ~~**AI-станции без confidence**~~ ✅ **CRTKY-83 done:** per-category merge + `editorial` уровень, 252 AI-станции показывают dots.
- ✅ **CRTKY-64/65 done:** safety gap at rating 4 и gym gap at rating 2 исправлены (midpoint rank + jitter).

### Принцип "Data First"

Каждый рейтинг ДОЛЖЕН опираться на конкретные, проверяемые данные:

- **Не**: "Shinjuku food = 9 потому что мы так решили"
- **Да**: "Shinjuku food = 9 потому что в радиусе 800м: 794 ресторана в OSM + 2099 заведений на HotPepper, это top 0.3% из 1493 станций"

### Данные: сделано vs остаётся (актуализация 2026-04)

Раньше таблица ниже смешивала **уже закрытые** пункты с бэклогом; это давало завышенное ощущение долга по nightlife.

**Уже в конвейере (не держать как «нужно собрать»):**

| Что | Статус | Где |
|-----|--------|-----|
| HP `midnight_count` | ✅ | Phase A1 / `hotpepper` — см. [research/01-nightlife.md] |
| OSM karaoke + cultural + extended | ✅ | Phase A2 / `osm_extended` — см. [research/01-nightlife.md], [research/06-vibe.md] |
| Nominatim ward mapping (1493) | ✅ | Phase B3 / `station_wards` — см. [research/05-rent.md] |
| Station elevation (1493) | ✅ | Open-Elevation API → `station_elevation` — **CRTKY-85** |
| Seismic hazard (1493) | ✅ | J-SHIS Y2024 → `station_seismic` — **CRTKY-86** |
| Environment UI (info + filters) | ✅ | `NaturalEnvironment.tsx` + safety filters on map — commit `e165ff9` |

**Остаётся (бэклог / Plane):**

| Что | Зачем | Источник | Приоритет | Тикет / ссылка |
|-----|-------|----------|-----------|----------------|
| Green area (sqm) + geom | Честный strong для green | Overpass `out geom` | 🔴 high | **CRTKY-42**, [research/04-green.md] |
| LIFULL / расширение Suumo-зон | Больше station-level аренды | homes.co.jp, suumo.jp | 🟡 medium | **CRTKY-43**, [research/05-rent.md] |
| Kanagawa/Saitama/Chiba crime | Safety вне полигонов Токио | Prefectural police open data | 🟡 medium | **CRTKY-82**, [research/02-safety.md] |
| ~~Реальные `transit_minutes`~~ | ✅ Done — калиброванная модель | Geographic + line connectivity | ~~🔴 high~~ ✅ | **CRTKY-81** ✅ |
| MLIT S12 refresh + хвост crowd | Закрыть `crowd: estimate` где возможно | MLIT S12, см. [research/03-crowd.md] | 🟡 medium | **CRTKY-84** |
| OSM green extended tags | Доп. сигнал к площади | `landuse`, `natural` | 🟢 low | Внутри **CRTKY-42** / [research/04-green.md] |
| Daily essentials (10th category) | Supermarket, pharmacy, clinic и т.д. | Overpass → `osm_livability` (scraping) | 🔴 high | **CRTKY-87** |

### Phase 0 — открытые источники до коммерции (дисциплина бэклога)

Перед внедрением маршрутизации и платных API: зафиксировать **ODPT**, **GTFS-JP** / National Open Data Challenge, **MLIT 鉄道** там, где уместно; сравнить **лицензии** и допущения (будни, сезон, календарь). Коммерция (Navitime, Hyperdia и т.п.) — только после явно описанных пробелов. Чеклисты в **описаниях** Plane: **CRTKY-81**, **CRTKY-56**; пассажиры / S12 / хвост `crowd: estimate` — **CRTKY-84** + [research/03-crowd.md] (раздел 1); ODPT как пересечение с commute — подраздел 1b того же файла.

**Аренда:** **e-Stat** и муниципальная опендата — только **ward/prefecture** sanity и валидация рядов LIFULL/Suumo; **не** подмена station-level в UI или confidence (**CRTKY-43**, [research/05-rent.md]). Каноническая формулировка — описание задачи в Plane; эпик **CRTKY-80** дублирует карту детей.

---

## Layer 2: Logic — формулы поверх данных

### Принципы нормализации

1. **log-then-percentile** — для всех категорий с экстремально скошенным распределением (food, nightlife, crowd). Без log: медианная станция (24 ресторана) получает 5/10, а нужно 3-4.

2. **Inverted для "меньше = лучше"** — rent (дешевле = выше), safety (меньше преступлений = выше), crowd (тише = выше).

3. **Weighted crime score** — не все преступления одинаковы. Грабёж ×3, кража велосипеда ×0.3, мошенничество ×0.2. Подробности: [research/02-safety.md].

4. **Daytime population adjustment** — Chiyoda-ku имеет 68k жителей ночью и 820k днём. Без коррекции rate = 711/10k (самый "опасный" район), с коррекцией = 59/10k (нормально). Применяем для commercial wards.

5. **Множественные источники с весами** — food = 60% HotPepper + 40% OSM. Не один источник, а перекрёстная валидация. Корреляция HP↔OSM = 0.855.

### Формулы по категориям

См. [CLAUDE.md] — секция **Rating Formulas (v3, absolute caps + rent regression)** — полные формулы для всех 9 категорий.

### Где остаются эвристики (и это нормально)

| Место | Эвристика | Почему допустимо |
|-------|----------|-----------------|
| Transport | line_count как primary signal | Прямое измерение связности. Данные 100% точные. |
| Rent fallback | ward_average для 82% станций | Внутри-ward дисперсия ~10% CV, приемлемо |
| Crowd fallback | HP_total × 300 + line_count × 10000 | Только для 6% станций без MLIT данных |
| Vibe | Composite из cultural venues + cafes + ped streets | Vibe субъективен. Cultural venue density — лучший из доступных proxy (25:1 дифференциация) |

---

## Layer 3: UI — прозрачность и доверие

### Проблема сейчас

Текущий UI показывает число 1-10 и цветную полоску. Пользователь не знает:
- Откуда это число?
- Насколько ему доверять?
- Что за данные стоят за ним?
- Когда обновлялись?

Tooltip есть, но он описывает категорию ("Variety and quality of restaurants..."), а не данные ("794 restaurants in OSM + 2099 on HotPepper").

**Сделано (2026-04, CRTKY-76 / PR #51):** на странице станции радар Overview рисует полупрозрачный полигон **медиан Токио** по осям (`CITY_MEDIANS` в `scoring.ts`) под полигоном самой станции — та же идея «отклонение от типичного», что и цветные бары рейтингов, без дублирования сырых счётчиков в UI.

### Предлагаемые улучшения

#### 3.1 Confidence Badge на каждом рейтинге

Рядом с категорией или значением — маленькая **точка** (не светофор): цвета из `CONFIDENCE_DOT_COLORS` в коде — 苔色 `#6A8059`, 山吹 `#C9A227`, 鈍色 `#828A8C` (см. `CLAUDE.md`, Color System). В UI подписи: **Measured / Partial / Estimate**.

```
Food & Dining  ●  ████████░░  8   ↑
Nightlife      ●  ██████░░░░  6   ↑
```

Три уровня (ключи в данных: `strong` / `moderate` / `estimate`):
- **Measured** — 2+ согласованных источника по конвейеру (типично food, transport, gym у computed-станций)
- **Partial** — один источник или агрегированный fallback (ward-level rent/safety и т.п.)
- **Estimate** — модель/регрессия/прокси без прямого наблюдения (часть vibe/crowd/rent)

Станции только с AI-описанием без блока `confidence` в данных — бейджи не показываются (ожидаемо до отдельной задачи на метаданные).

**Зафиксированный пробел (продукт/данные):** подставлять для таких станций в UI уровень `estimate` по умолчанию **не стоит** — в конвейере `estimate` = модель/прокси без прямого наблюдения, а не «оценка по тексту эксперта»; см. таблицу уровней выше и `CLAUDE.md` (NocoDB metadata → `ConfidenceBadge`). Нормальное решение — явные метаданные при экспорте: мердж computed `confidence` там, где категория не перекрыта AI, отдельный уровень вроде editorial/researched, или согласованная политика маппинга + обновление `export-ratings.py` / типов.

#### 3.2 Data Tooltip — "Почему этот score?"

При наведении на рейтинг или клике на "?" — не абстрактное описание, а конкретные данные:

**Пример для food=8 (Nakano):**
```
Food & Dining: 8/10
━━━━━━━━━━━━━━━━━━━━━━
📊 Based on real data:
   • 287 restaurants on HotPepper (top 15%)
   • 143 food places in OpenStreetMap
   • Percentile: better than 82% of stations

📅 Data: April 2026
📁 Sources: HotPepper Gourmet API, OpenStreetMap
```

**Пример для safety=7 (Suginami station):**
```
Safety: 7/10
━━━━━━━━━━━━━━━━━━━━━━
📊 Based on police data:
   • Neighborhood: 杉並区阿佐谷南三丁目
   • 75 crimes/year (weighted: 12 serious)
   • Crime rate: 15.0 per 10k residents
   • Safer than 74% of stations

📅 Data: 2024 (Keishicho annual report)
📁 Source: Tokyo Metropolitan Police ArcGIS
🟢 Neighborhood-level data (high confidence)
```

**Пример для safety=5 (suburban Kanagawa, ward-level only):**
```
Safety: 5/10
━━━━━━━━━━━━━━━━━━━━━━
📊 Based on ward-level data:
   • Ward: 横浜市中区
   • Ward crime rate: 205.7 per 10k
   • Average for 80% of stations

⚠️ Ward-level only — actual neighborhood may differ
📅 Data: 2024
📁 Source: Kanagawa Prefectural Police
🟡 Ward-level data (moderate confidence)
```

#### 3.3 Station Page — "How are ratings calculated?" section

Отдельный раздел под рейтингами — раскрывающийся блок:

```
▸ How are ratings calculated?

  All ratings are computed from real data: restaurant databases,
  crime statistics, transit authorities, and OpenStreetMap.

  We collect data from 6+ sources, normalize using statistical
  percentiles across all 1,493 stations in Greater Tokyo, and
  combine multiple signals per category.

  Stations with hand-researched descriptions (like this one)
  have human-verified ratings. Others are purely data-driven.

  [See methodology →]
```

#### 3.4 Methodology Page (новая страница)

`/methodology` — объясняет весь подход:

- Data sources с ссылками (HotPepper, OSM, MLIT, Keishicho)
- Формулы (упрощённо, без кода)
- Confidence levels
- Update frequency
- Known limitations
- Changelog

#### 3.5 "This station is AI-researched" badge

Для 272 станций с description — badge "Researched" или "Verified":
```
🔍 This station has been individually researched with detailed
   neighborhood descriptions and verified ratings.
```

Для остальных — "Data-driven":
```
📊 Ratings computed from public data sources.
   No individual review.
```

#### 3.6 Data freshness indicator

На странице станции — мелким текстом:
```
Data updated: April 2026 · Sources: 6 · Confidence: high
```

#### 3.7 Radar Chart enhancement

Сейчас radar chart одноцветный (синий). Можно:
- Сделать оси разного цвета по confidence (strong = solid, estimate = dashed)
- Или добавить second ring с "city average" для сравнения

---

## Roadmap: от данных к UI

### Sprint 1: Data completion [частично закрыт]
**Задачи (Phase A-C из плана):**
1. ~~HP midnight scrape~~ ✅ done (см. A1 / `hotpepper`)
2. ~~OSM extended (karaoke, cultural, hostel)~~ ✅ done (A2 / `osm_extended`)
3. ~~ArcGIS crime data~~ ✅ done (615 Tokyo stations)
4. ~~MLIT passengers~~ ✅ done (1409 records) — **ongoing:** свежий FY + хвост `crowd: estimate` → **CRTKY-84**
5. ~~Nominatim ward mapping~~ ✅ done (1493 / `station_wards`)
6. OSM green area re-scrape — **CRTKY-42**
7. LIFULL HOME'S rent scrape — **CRTKY-43**
8. Kanagawa/Saitama/Chiba crime CSV — **CRTKY-82**

### Sprint 2: Compute pipeline rewrite [Phase D]
**Задачи:**
1. ✅ Rewrite compute-ratings.py с log-percentile + новыми формулами (CRTKY-45, v2)
2. ✅ Include per-station metadata: sources used, data freshness, confidence level (CRTKY-46)
3. ✅ Export to demo-ratings.ts (CRTKY-46)
4. ✅ Spot-check + distribution validation
5. ✅ **Formula v3** — absolute caps + log-linear rent regression (CRTKY-63)

**Formula v3 outcome:** "top 10" was meaningless under pure log-percentile (top 5.6% auto-rounded to 10). Added `ABSOLUTE_CAPS` gating the 8/9/10 tiers by raw value (e.g. transport=10 requires ≥5 train lines). Also replaced the broken `distance_estimate` rent fallback (507 fake ¥50k stations) with a log-linear regression fitted on 273 real Suumo points. Top-10 counts dropped from ~83 per category to 15–64 (5 for rent).

**Known follow-ups:**
- CRTKY-64 — fix lumpy safety distribution (0 stations at rating 4 due to tri-modal fallback)
- CRTKY-65 — fix gym distribution (0 stations at rating 2 due to log(0) zero-clustering)

### Sprint 3: UI transparency [Phase E+]
**Задачи по категориям:**
1. ✅ Confidence badge component (CRTKY-47, merged)
2. Data-source tooltip (replace current generic tooltips) — CRTKY-48
3. "How ratings work" expandable section on station page — CRTKY-49
4. /methodology page — CRTKY-50
5. AI-researched vs data-driven badge — CRTKY-52
6. Data freshness indicator — CRTKY-51
7. Radar chart confidence overlay (optional)

Prerequisite (done):
- ✅ CRTKY-46 — per-station confidence metadata pipeline (compute → NocoDB columns → demo-ratings.ts → Station objects)

---

## Plane Issues (City Rating Tokyo — CRTKY)

Sprint 2 (compute pipeline) — **done**:
- ✅ `CRTKY-45` Compute-ratings.py v2 rewrite (log-percentile + research formulas)
- ✅ `CRTKY-46` Per-station confidence metadata (compute → NocoDB columns → demo-ratings.ts)
- ✅ `CRTKY-63` Formula v3 — absolute caps + rent log-linear regression
- ✅ `CRTKY-64` Fix lumpy safety distribution (midpoint rank + distance jitter)
- ✅ `CRTKY-65` Fix gym distribution (tie-breaking jitter for gym=0)

Sprint 3 (UI transparency):
- ✅ `CRTKY-47` Confidence badges (🟢🟡⚪) next to each rating
- ✅ `CRTKY-48` Data-source tooltips (sources + data_date in category hover)
- `CRTKY-49` "How ratings work" expandable section on station page
- `CRTKY-50` /methodology page with data sources + formulas
- `CRTKY-51` Data freshness indicator (uses `data_date` from metadata)
- `CRTKY-52` AI-researched vs data-driven station badge

Sprint 1 (data completion) issues were tracked separately and scrapers are all running. See `research/00-overview.md` for data source status.

**Plane — эпик и новые тикеты (2026-04):** `CRTKY-80` umbrella; дочерние **`CRTKY-81`** реальные `transit_minutes`, **`CRTKY-82`** криминал префектур, **`CRTKY-83`** мердж pipeline `confidence` для AI-only slugs, **`CRTKY-84`** обновление MLIT S12 / закрытие хвоста пассажиров (crowd). У **CRTKY-48–52, 55–56, 42–43, 64–65, 69** — комментарии *Spec packet*. **Док-синхронизация готовности:** `CLAUDE.md` §Data readiness, этот файл §Критическая оценка, `README.md`, `00-overview.md` (2026-04-07).

---

## Roadmap: транспорт, хабы, аренда, «последний поезд»

Направления **рядом с рейтингами**, но не сведённые к одной формуле CRTKY. Ниже — статус в продукте, зазоры в данных и оценка сложности.

### Commute to major hubs (минуты)

| Аспект | Статус | ~% готовности | Сложность довести |
|--------|--------|---------------|-------------------|
| UI: полоса **Hubs** (`HubStrip`), 5 хабов, ссылка в Google Maps | ✅ на странице станции, если есть `transit_minutes` | UI **100%** | — |
| Фильтр **max commute** на карте (по минимуму из хабов) | ✅ в `scoring.ts` | **100%** | — |
| Качество данных | ✅ калибровано | **~80%** | **M** (upgrade to GTFS) |

✅ **CRTKY-81 (done, PR #56):** Географическая модель (Haversine + line connectivity), калибрована grid search по 252 AI ground truth. MAE 5.5 мин, 85% within 10 min. Spot-checked vs Google Maps. Output: `data/transit-times.json`, потребляется `export-ratings.py`. **Upgrade path:** TokyoGTFS + RAPTOR для timetable-based routing.

### Last train (終電)

| Аспект | Статус | ~% | Сложность |
|--------|--------|-----|-----------|
| UI на странице станции | Заглушка «coming soon» / «—» | **0%** | — |
| Данные | Нет в NocoDB и в `demo-ratings.ts` | **0%** | **L** |

Зависит от расписаний по линиям/дням недели (GTFS-JP, ODPT, ручная курировка для 1493 станций не масштабируется). Минимальный MVP: одна «типичная пятница» + ветка последнего поезда по **главной линии** станции; полноценно — мультилинейные пересадки и выходы. **~3–5** задач (исследование прав, ETL, модель «какую линию показываем», UI, дисклеймер).

### Rent: больше данных и точность

| Трек | Статус | ~% | Сложность |
|------|--------|-----|-----------|
| Suumo station-level / area codes (`rent-averages.json`) | 274 станции, 67 кодов зон | **~18%** станций с «жёстким» Suumo | **M** на расширение карт зон |
| Ward / Nominatim fallback + регрессия в формуле | ✅ в compute v3 | **100%** для формулы | — |
| Расширение покрытия | См. `research/05-rent.md`: 1A–1D (Nominatim→коды, больше Suumo-зон, поиск по `ek`, LIFULL по станции) | **0–40%** по отдельным подпунктам | **M–L** каждый |

Сводно по **аренде как продукту**: формула и метаданные confidence **готовы**; **сырьё** для «все станции с честной ¥/мес» — главный долг. Ориентир **~5–7** инициатив из `05-rent.md`, общая готовность **~35–45%** если считать «есть осмысленный score для всех», и **~20%** если цель — «все с реальным scraped rent».

### Прочее (соседние темы)

| Тема | Заметка |
|------|---------|
| **Walking / last mile** | Нет в скоупе; усиливает rent/transport narrative |
| **Airport access** (Haneda/Narita) | Тот же класс задач, что хабы — отдельная матрица |
| **Сезонность аренды** | Suumo snapshot; повторные скрейпы → `data_date` / тренды |

---

### Сводка по этому блоку

| Направление | Крупных задач (оценка) | ~готовность | Остаток |
|-------------|-------------------------|-------------|---------|
| Hubs UI + фильтр | 2 | **~95%** | Методология tooltip |
| Hubs **реальные минуты** | 4 | **~80%** ✅ CRTKY-81 | Upgrade: GTFS+RAPTOR |
| Last train | 3–5 | **~0%** | Расписания + UI |
| Rent expansion | 5–7 | **~20–45%** по цели | Скрейп + маппинг + этика нагрузки |

Этот блок **ортогонален** Sprint 1–3 (рейтинги из POI/crime/passengers): его можно вести параллельными эпиками в Plane без блокировки CRTKY-48/50.
