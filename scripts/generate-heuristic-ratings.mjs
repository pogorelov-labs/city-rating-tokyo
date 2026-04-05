/**
 * Generate heuristic-based ratings for stations without AI-researched data.
 * Uses line count, distance from center, and prefecture to estimate ratings.
 * Outputs TypeScript entries to append to demo-ratings.ts
 */

import { readFileSync, writeFileSync } from 'fs';

const stations = JSON.parse(readFileSync(new URL('../app/src/data/stations.json', import.meta.url), 'utf-8'));
const rentData = JSON.parse(readFileSync(new URL('../app/src/data/rent-averages.json', import.meta.url), 'utf-8'));

// Read existing demo-ratings to find already-rated slugs
const demoContent = readFileSync(new URL('../app/src/data/demo-ratings.ts', import.meta.url), 'utf-8');
const ratedSlugs = new Set();
for (const match of demoContent.matchAll(/^\s{2}'?([a-z][a-z0-9-]*)'?\s*:\s*\{/gm)) {
  const slug = match[1];
  if (!['ratings', 'transit_minutes', 'rent_avg', 'description'].includes(slug)) {
    ratedSlugs.add(slug);
  }
}

console.log(`Already rated: ${ratedSlugs.size}`);

// Center of Tokyo (approx Tokyo Station)
const CENTER = { lat: 35.6812, lng: 139.7671 };
// Major hubs for transit time estimation
const HUBS = {
  shibuya: { lat: 35.6580, lng: 139.7016 },
  shinjuku: { lat: 35.6897, lng: 139.7005 },
  tokyo: { lat: 35.6812, lng: 139.7671 },
  ikebukuro: { lat: 35.7295, lng: 139.7109 },
  shinagawa: { lat: 35.6284, lng: 139.7387 },
};

function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLon/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function clamp(v, min = 1, max = 10) {
  return Math.round(Math.max(min, Math.min(max, v)));
}

// Estimate transit minutes from distance (rough: ~2 min per km for train, but with wait/transfer)
function estimateTransitMinutes(lat, lng) {
  const result = {};
  for (const [hub, pos] of Object.entries(HUBS)) {
    const dist = haversineKm(lat, lng, pos.lat, pos.lng);
    // Rough estimate: 3 min/km for suburban, minimum 3 min
    result[hub] = Math.max(3, Math.round(dist * 3));
  }
  return result;
}

const newEntries = [];

for (const s of stations) {
  if (ratedSlugs.has(s.slug)) continue;

  const distFromCenter = haversineKm(s.lat, s.lng, CENTER.lat, CENTER.lng);
  const lines = s.line_count;
  const rent = rentData[s.slug];

  // Transport: based on line count
  const transport = clamp(lines >= 5 ? 9 : lines >= 3 ? 7 : lines >= 2 ? 6 : lines >= 1 ? 4 : 3);

  // Food: correlated with centrality and lines
  const food = clamp(
    distFromCenter < 5 ? 7 + Math.min(lines, 3) :
    distFromCenter < 10 ? 5 + Math.min(lines, 2) :
    distFromCenter < 20 ? 4 + Math.min(lines, 1) :
    3
  );

  // Nightlife: strongly correlated with centrality
  const nightlife = clamp(
    distFromCenter < 3 ? 6 + Math.min(lines, 3) :
    distFromCenter < 7 ? 4 + Math.min(lines, 2) :
    distFromCenter < 15 ? 3 + Math.min(lines, 1) :
    2
  );

  // Safety: inversely correlated with nightlife/centrality (suburban = safer)
  const safety = clamp(
    distFromCenter < 3 ? 6 :
    distFromCenter < 7 ? 7 :
    distFromCenter < 15 ? 8 :
    8
  );

  // Green: more green space in suburbs
  const green = clamp(
    distFromCenter < 3 ? 3 :
    distFromCenter < 7 ? 4 :
    distFromCenter < 15 ? 6 :
    7
  );

  // Rent affordability: continuous linear interpolation matching scoring.ts rentToAffordability()
  const RENT_FLOOR = 70000;
  const RENT_CEILING = 300000;
  let rentRating;
  const rentVal = rent?.['1k_1ldk'] ?? rent?.['2ldk'] ?? null;
  if (rentVal != null) {
    const t = Math.max(0, Math.min(1, (rentVal - RENT_FLOOR) / (RENT_CEILING - RENT_FLOOR)));
    rentRating = Math.round(10 - 9 * t);
  } else {
    rentRating = clamp(
      distFromCenter < 5 ? 3 :
      distFromCenter < 10 ? 5 :
      distFromCenter < 20 ? 7 :
      8
    );
  }

  // Gym/Sports: moderate everywhere, slightly better in suburbs
  const gym_sports = clamp(
    distFromCenter < 5 ? 5 :
    distFromCenter < 15 ? 5 :
    4
  );

  // Vibe: central stations have more character
  const vibe = clamp(
    distFromCenter < 3 ? 6 + Math.min(lines - 1, 2) :
    distFromCenter < 7 ? 5 + Math.min(lines - 1, 1) :
    distFromCenter < 15 ? 5 :
    4
  );

  // Crowd: suburban = less crowded
  const crowd = clamp(
    distFromCenter < 3 ? 3 :
    distFromCenter < 7 ? 5 :
    distFromCenter < 15 ? 7 :
    8
  );

  const transit_minutes = estimateTransitMinutes(s.lat, s.lng);

  // Estimate rent if no Suumo data
  const rentAvg = rent
    ? { '1k_1ldk': rent['1k_1ldk'], '2ldk': rent['2ldk'], source: 'suumo', updated: rent.updated }
    : {
        '1k_1ldk': clamp(
          distFromCenter < 5 ? 130000 :
          distFromCenter < 10 ? 95000 :
          distFromCenter < 20 ? 75000 :
          65000,
          50000, 200000
        ),
        '2ldk': null,
        source: 'estimate',
        updated: '2026-04',
      };

  newEntries.push({
    slug: s.slug,
    ratings: { food, nightlife, transport, rent: rentRating, safety, green, gym_sports, vibe, crowd },
    transit_minutes,
    rent_avg: rentAvg,
  });
}

console.log(`Generated ratings for ${newEntries.length} new stations`);

// Generate TypeScript code
const lines = [];
for (const e of newEntries) {
  const r = e.ratings;
  const t = e.transit_minutes;
  const ra = e.rent_avg;
  lines.push(`  '${e.slug}': {
    ratings: { food: ${r.food}, nightlife: ${r.nightlife}, transport: ${r.transport}, rent: ${r.rent}, safety: ${r.safety}, green: ${r.green}, gym_sports: ${r.gym_sports}, vibe: ${r.vibe}, crowd: ${r.crowd} },
    transit_minutes: { shibuya: ${t.shibuya}, shinjuku: ${t.shinjuku}, tokyo: ${t.tokyo}, ikebukuro: ${t.ikebukuro}, shinagawa: ${t.shinagawa} },
    rent_avg: { '1k_1ldk': ${ra['1k_1ldk']}, '2ldk': ${ra['2ldk']}, source: '${ra.source}', updated: '${ra.updated}' },
  },`);
}

// Insert before the closing }; of DEMO_RATINGS
const marker = '};';
const lastIdx = demoContent.lastIndexOf(marker);
const newContent = demoContent.slice(0, lastIdx) +
  `  // === Auto-generated heuristic ratings (${newEntries.length} stations) ===\n` +
  lines.join('\n') + '\n' +
  demoContent.slice(lastIdx);

writeFileSync(new URL('../app/src/data/demo-ratings.ts', import.meta.url), newContent, 'utf-8');
console.log('Updated demo-ratings.ts');
