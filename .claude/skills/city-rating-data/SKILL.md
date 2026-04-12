---
name: city-rating-data
description: Query and manage city-rating NocoDB data — feedback, POIs, ratings, crime stats, elevation, seismic, livability, passenger counts
---

# City Rating Data Skill

## When to use
Invoke when the user asks to: check feedback, query station data, update ratings, look at POI counts, analyze crime stats, review passenger data, or any data operation on the city-rating-db NocoDB base.

## MCP tools prefix
All tools: `mcp__NocoDB_Base_-_city-rating-db__*`

## Tables — discover at runtime

**Never hardcode table IDs.** Always call `getTablesList` first, then `getTableSchema` for the target table.

Known tables (IDs may change):

| Table | Key fields | Purpose |
|-------|-----------|---------|
| `feedback` | comment, station_slug, source, visitor_id, vote | User feedback from station pages + main page |
| `osm_pois` | slug, food_count, nightlife_count, green_count, gym_count, convenience_store_count | OpenStreetMap POI counts per station |
| `hotpepper` | (discover schema) | HotPepper restaurant data |
| `hostels` | (discover schema) | Hostel/accommodation data |
| `crime_stats` | (discover schema) | Crime statistics by area |
| `passenger_counts` | (discover schema) | Station passenger volume |
| `computed_ratings` | slug, food, nightlife, transport, rent, safety, green, gym_sports, vibe, crowd, source | Calculated ratings per station |
| `osm_extended` | slug, karaoke_count, nightclub_count, cultural_venue_count, pedestrian_street_count, hostel_count | Extended OSM tags |
| `station_wards` | slug, city_name, ward_name, prefecture | Nominatim reverse geocoding |
| `station_crime` | slug + ArcGIS crime fields | Keishicho neighborhood-level crime (Tokyo) |
| `station_elevation` | slug, elevation_m, lat, lng | Open-Elevation API (1493 stations, -2m to 741m) |
| `station_seismic` | slug, prob_i60_30yr, prob_i55_30yr, intensity_50yr_p10, meshcode | J-SHIS Y2024 seismic hazard |
| `osm_livability` | slug, supermarket_count, pharmacy_count, clinic_count, school_count, kindergarten_count, post_office_count, bank_count, laundry_count, dentist_count | Daily essentials (scraping) |

## Common operations

### Review recent feedback
```
1. getTablesList → find feedback table ID
2. queryRecords(tableId, {
     sort: [{ field: "Id", description: "desc" }],
     pageSize: 20
   })
```

### Feedback by source
```
queryRecords(tableId, { where: "(source,eq,station_page)" })
queryRecords(tableId, { where: "(source,eq,general)" })
```

### Station ratings lookup
```
queryRecords(computed_ratings_id, { where: "(slug,eq,shibuya)" })
```

### Compare stations
```
queryRecords(computed_ratings_id, {
  where: "(slug,in,shibuya,shinjuku,ikebukuro)",
  fields: ["slug", "food", "nightlife", "transport", "rent", "safety"]
})
```

### Aggregate across all stations
```
aggregate_single(computed_ratings_id, [
  { field: "food", type: "avg" },
  { field: "rent", type: "avg" },
  { field: "safety", type: "max" }
])
```

### Count feedback per station
```
aggregate_single(feedback_id, [
  { field: "station_slug", type: "count_filled" }
], { where: "(station_slug,eq,shibuya)" })
```

## Maintainer context (coverage vs quality)

NocoDB row counts and `computed_ratings` integers are **not** uniform “ground truth” per station. Before drawing product conclusions from aggregates:

1. Read repo **`CLAUDE.md`** → **Data readiness & coverage honesty**.
2. Read **`research/00-overview.md`** → **Critical readiness** + confidence snapshot.
3. **Plane:** epic **CRTKY-80** (children **81–84**) tracks commute stub removal, prefectural crime, AI confidence merge, MLIT/crowd tail.

## API integration

The feedback form writes to NocoDB via `/api/feedback` route in the Next.js app.

**Env vars** (set in Coolify, not in git):
- `NOCODB_API_URL` — `https://nocodb.pogorelov.dev`
- `NOCODB_API_TOKEN` — server-side only
- `NOCODB_TABLE_ID` — feedback table ID

**Security**: All inputs validated server-side with regex whitelists. NocoDB REST API uses parameterized queries (no SQL injection risk).

## Infrastructure

- NocoDB: `https://nocodb.pogorelov.dev` (Coolify service, always running)
- App: `https://city-rating.pogorelov.dev` (Next.js standalone on Coolify)
- Analytics: Umami at `https://analytics.pogorelov.dev` (separate NocoDB base for read-only access)
