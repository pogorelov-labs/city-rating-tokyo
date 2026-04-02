/**
 * Generate nearby places (POIs) for each station using Claude API.
 * Requires ANTHROPIC_API_KEY env var.
 *
 * Usage: ANTHROPIC_API_KEY=your_key node scripts/generate-places.mjs
 * Outputs: app/src/data/station-places.json
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';

const API_KEY = process.env.ANTHROPIC_API_KEY;
if (!API_KEY) {
  console.error('Error: Set ANTHROPIC_API_KEY env var');
  process.exit(1);
}

const stations = JSON.parse(readFileSync(new URL('../app/src/data/stations.json', import.meta.url), 'utf-8'));
const outputPath = new URL('../app/src/data/station-places.json', import.meta.url);

const existing = existsSync(outputPath)
  ? JSON.parse(readFileSync(outputPath, 'utf-8'))
  : {};

const CATEGORIES = ['gym', 'mall', 'park', 'landmark', 'cafe', 'restaurant', 'bar'];

async function generatePlaces(station) {
  const prompt = `For the area around ${station.name_en} (${station.name_jp}) station in Tokyo, Japan, list 6-10 notable real places that a resident would visit. Include a mix of categories.

Return ONLY a JSON array (no markdown, no explanation) with objects like:
[
  {"name": "Place Name", "category": "gym|mall|park|landmark|cafe|restaurant|bar"}
]

Categories: gym (fitness centers, sports facilities), mall (shopping centers, department stores), park (parks, gardens), landmark (famous spots, temples, observation decks), cafe, restaurant, bar (bars, izakaya).

Only include REAL places that currently exist. Be specific with names (include branch/location if needed). Focus on places within 10-15 min walk of the station.`;

  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 1024,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }

  const data = await res.json();
  const text = data.content[0].text.trim();

  // Parse JSON from response
  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) throw new Error('No JSON array found in response');

  const places = JSON.parse(jsonMatch[0]);

  // Convert to our format with Google Maps URLs
  return places
    .filter(p => CATEGORIES.includes(p.category))
    .map(p => ({
      name: p.name,
      category: p.category,
      google_maps_url: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.name + ' ' + station.name_en + ' Tokyo')}`,
    }));
}

// Process stations that don't have places yet
const toProcess = stations
  .filter(s => s.ratings !== null)
  .filter(s => !existing[s.slug])
  .sort((a, b) => b.line_count - a.line_count);

console.log(`Generating places for ${toProcess.length} stations...\n`);

const placesMap = { ...existing };
let processed = 0;
const BATCH_SIZE = 50; // Process 50 at a time

for (const station of toProcess.slice(0, BATCH_SIZE)) {
  console.log(`[${++processed}/${Math.min(toProcess.length, BATCH_SIZE)}] ${station.name_en}...`);

  try {
    const places = await generatePlaces(station);
    placesMap[station.slug] = places;
    console.log(`  Generated ${places.length} places`);
  } catch (e) {
    console.error(`  Error: ${e.message}`);
  }

  // Rate limiting
  await new Promise(r => setTimeout(r, 500));
}

console.log(`\nTotal stations with places: ${Object.keys(placesMap).length}`);
writeFileSync(outputPath, JSON.stringify(placesMap, null, 2), 'utf-8');
console.log('Written to app/src/data/station-places.json');
