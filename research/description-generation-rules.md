# Description Generation Rules

## Voice & Style (from 252 existing RU descriptions)

**Tone:** Telegram-style. Punchy, comma-separated phrases. Local insider, not tourist guide. Opinionated but factual.

**Length per field:**
- atmosphere: 1-2 sentences (40-60 chars RU, ~30-50 EN)
- landmarks: 1-2 sentences (30-50 chars)
- food: 1-2 sentences (30-50 chars)
- nightlife: 1 sentence (20-40 chars)

**Examples of good voice (translated):**
- "Legendary 'drinking town' — izakaya culture at its peak, can drink from 9am."
- "Quiet suburb on the shore of Lake Teganuma."
- "Cheap izakaya, charcoal yakitori, sushi counters. Morning asa-nomi!"
- "Minimal." (for stations with truly nothing)

## Sub-fields

Keep current 4: `atmosphere`, `landmarks`, `food`, `nightlife`.

## Signal → Prose Rules

### atmosphere
Primary signal: **overall score profile** + **passenger_count** + **ward/prefecture** + **elevation/seismic** + **line count & types** + **last train time**

| Pattern | Prose direction |
|---------|----------------|
| high transport + high crowd (low quietness) | "Major hub, always busy" |
| high rent + high vibe | "Upscale residential, calm streets" |
| low rent + high food | "Budget-friendly with great eats" |
| high green + high quietness | "Peaceful green suburb" |
| high nightlife + low safety | "Lively but watch your belongings late at night" |
| elevation < 5m | Mention flood risk zone |
| seismic very_high | Mention soft ground / reclaimed land |
| line_count >= 5 | "Major junction with X lines" |
| daily_passengers > 100k | "One of the busiest stations" |
| daily_passengers < 5k | "Quiet local station" |
| last_train before 23:00 | "Trains stop early — plan your night" |
| last_train after 00:30 | "Good late-night connectivity" |
| Tram-only lines (Toden Arakawa) | "Tram-accessible shitamachi feel" |
| prefecture == 12/11/14 (outside Tokyo) | Mention commuter prefecture context |

### landmarks
Primary signal: **green_area_sqm** + **cultural_venue_count** + **pedestrian_street_count** + **ward location**

| Pattern | Prose direction |
|---------|----------------|
| green_area_sqm > 500k | Name the major park if known, or "large parks nearby" |
| cultural_venue_count > 10 | "Cultural hub with theaters/galleries" |
| pedestrian_street_count > 5 | "Walkable shopping streets" |
| near river (from ward name containing 川/河) | Mention riverbank walks |
| elevation > 100m | "Hill area with views" |

### food
Primary signal: **hotpepper total** + **osm food_count** + **izakaya_count** + **cafe_count** + **convenience_store_count**

| Pattern | Prose direction |
|---------|----------------|
| hp_total > 200, izakaya > 80 | "Izakaya paradise" |
| hp_total > 200, bar > 10 | "Dining + bar scene" |
| cafe_count > 15 | "Cafe culture" |
| hp_total < 20 | "Few dining options, mostly chains" |
| hp_total 20-80 | "Decent local selection" |
| convenience_store > 20 | Can mention as fallback if restaurants sparse |

### nightlife
Primary signal: **midnight_count** + **bar_count** + **karaoke_count** + **nightclub_count** + **hostel_count**

| Pattern | Prose direction |
|---------|----------------|
| midnight > 100 | "Thriving late-night scene" |
| midnight 30-100 | "Some options after dark" |
| midnight < 10 | "Quiet after 9pm" or "Minimal" |
| karaoke > 3 | Mention karaoke |
| nightclub > 0 | Mention clubs |
| hostel > 2 | "Backpacker-friendly" |
| bar > 20 | "Serious bar district" |

## What NOT to Say

1. **Don't restate numbers visible in ratings.** Don't say "Safety: 8/10" — the user already sees that.
2. **Don't be generic.** "Nice area with restaurants" = useless. Be specific about CHARACTER.
3. **Don't describe what you don't know.** If confidence is `estimate` for a category, don't describe it confidently.
4. **Don't over-praise.** Even top stations have weaknesses. Mention trade-offs.
5. **Don't mention data sources.** No "according to HotPepper" — that's meta, not description.
6. **Don't use "tourist guide" language.** No "must-visit" or "hidden gem" or "perfect for families".

## Confidence-Awareness

- If `confidence[category] == 'estimate'`: use hedging language ("likely", "probably", "appears to be")
- If `confidence[category] == 'strong'`: state directly
- If `confidence[category] == 'editorial'`: the AI-researched value differs from data — don't contradict it

## Interesting Contrasts (highlight these)

- High food + low safety → "Great eats, but watch your wallet at night"
- High transport + low quietness → "Connected everywhere, but never quiet"
- High rent + low vibe → "Expensive but bland"
- Low rent + high green → "Affordable with nature"
- High nightlife + high quietness → impossible, flag as data issue

## Language Strategy

**Generate in all 3 languages directly** (Option A from the plan).

Rationale:
- Russian voice matches the 252 existing descriptions
- Japanese descriptions should feel native, not translated (local audience)
- English is the default and most viewed
- 3× token cost is acceptable for 1493 stations (one-time batch)

## Generation Order

Composite score descending (default weights). Top-scored stations get the most views → generate and review first.

## Handling Existing 252 Descriptions

- **Preserve as-is** in Russian
- **Translate** existing 252 RU → EN and JA (faithful translation, not regeneration)
- **Generate new** for remaining 1241 stations using data-driven pipeline
- Mark provenance: `editorial` for translated, `generated` for new
