# Tokyo Neighborhood Explorer

Interactive map-based tool that helps expats and foreign residents find the perfect neighborhood in Greater Tokyo. Explore **274 train stations** rated across 9 dimensions — from food and nightlife to safety and commute times.

**Live:** [city-rating.pogorelov.dev](https://city-rating.pogorelov.dev)

## What It Does

- **Interactive map** — color-coded markers (red to green) show how each station scores based on your priorities
- **Adjustable weights** — drag sliders to emphasize what matters to you (cheap rent? great food? short commute?)
- **Smart filters** — filter by budget, max commute time, or minimum score
- **Station profiles** — dedicated page for each station with radar chart, rent data, transit times, and neighborhood description
- **Real rent data** — scraped from Suumo for accuracy, shown in JPY for 1K/1LDK and 2LDK apartments

## Rating Categories

| Category | Default Weight | Description |
|----------|---------------|-------------|
| Transport | 20% | Train access, line count, commute to major hubs |
| Affordability | 20% | Rent levels (lower = better score) |
| Food & Dining | 15% | Restaurant variety and quality |
| Nightlife | 10% | Bars, izakayas, late-night options |
| Safety | 10% | Crime rates, street lighting, general feel |
| Parks & Green | 10% | Green spaces and nature access |
| Gym & Sports | 5% | Fitness facilities availability |
| Vibe | 5% | Neighborhood character and atmosphere |
| Low Crowds | 5% | Quietness (less crowded = better) |

## Tech Stack

- **Next.js 16** (App Router, SSG) + **React 19** + **TypeScript**
- **Leaflet** + react-leaflet for mapping
- **Recharts** for radar chart visualization
- **Zustand** for state management
- **Tailwind CSS 4** for styling
- **next-sitemap** for SEO

## Project Structure

```
app/                          # Next.js application
  src/
    app/
      page.tsx                # Home — map + filter panel
      station/[slug]/page.tsx # Station detail page (SSG)
    components/
      Map.tsx                 # Leaflet map with 274 markers
      FilterPanel.tsx         # Weight sliders, filters, top-15 ranking
      RadarChart.tsx          # 9-axis radar chart
      MobileDrawer.tsx        # Mobile filter UI
    lib/
      scoring.ts              # Weighted score calculation
      store.ts                # Zustand state (weights, filters, selection)
      data.ts                 # Data loading & merging
    data/
      demo-ratings.ts         # AI-researched ratings for 50+ stations
data/
  stations.json               # 274 stations (coords, lines, prefecture)
  rent/rent-averages.json     # Suumo-scraped rent data
```

## Getting Started

```bash
cd app
npm install
npm run dev
```

Open [localhost:3000](http://localhost:3000).

## Deployment

Dockerized multi-stage build with standalone Next.js output. See `app/Dockerfile`.

```bash
cd app
docker build -t city-rating .
docker run -p 3000:3000 city-rating
```

Currently deployed on Coolify VPS with Traefik reverse proxy and Let's Encrypt TLS.

## Data Sources

- **Station coordinates:** [piuccio/open-data-jp-railway-stations](https://github.com/piuccio/open-data-jp-railway-stations)
- **Rent data:** Suumo.jp (custom scraper)
- **Ratings & descriptions:** AI-researched via Claude, human-reviewed
- **Transit times:** Estimated based on Tokyo rail network

## Status

Early beta. ~50 stations fully researched with ratings, descriptions, and verified rent data. 274 stations mapped with coordinates and line information.

## License

MIT
