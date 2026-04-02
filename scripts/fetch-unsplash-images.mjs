/**
 * Fetch station area photos from Unsplash API.
 * Requires UNSPLASH_ACCESS_KEY env var.
 * Free tier: 50 requests/hour.
 *
 * Usage: UNSPLASH_ACCESS_KEY=your_key node scripts/fetch-unsplash-images.mjs
 * Outputs: app/src/data/station-images-unsplash.json
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';

const UNSPLASH_KEY = process.env.UNSPLASH_ACCESS_KEY;
if (!UNSPLASH_KEY) {
  console.error('Error: Set UNSPLASH_ACCESS_KEY env var');
  process.exit(1);
}

const stations = JSON.parse(readFileSync(new URL('../app/src/data/stations.json', import.meta.url), 'utf-8'));
const outputPath = new URL('../app/src/data/station-images-unsplash.json', import.meta.url);

// Load existing to avoid re-fetching
const existing = existsSync(outputPath)
  ? JSON.parse(readFileSync(outputPath, 'utf-8'))
  : {};

const IMAGES_PER_STATION = 3;
const RATE_LIMIT_DELAY = 3600; // ms between requests (50/hour = 72s, but we batch)

async function searchUnsplash(query, perPage = 3) {
  const url = `https://api.unsplash.com/search/photos?query=${encodeURIComponent(query)}&per_page=${perPage}&orientation=landscape`;
  const res = await fetch(url, {
    headers: { Authorization: `Client-ID ${UNSPLASH_KEY}` },
  });

  if (res.status === 403) {
    console.error('Rate limited. Try again later.');
    process.exit(1);
  }

  const remaining = res.headers.get('x-ratelimit-remaining');
  console.log(`  Rate limit remaining: ${remaining}`);

  if (!res.ok) {
    console.error(`Unsplash error ${res.status}: ${await res.text()}`);
    return [];
  }

  const data = await res.json();
  return data.results.map((photo) => ({
    url: photo.urls.regular, // 1080px wide
    alt: photo.description || photo.alt_description || query,
    attribution: `Photo by ${photo.user.name} on Unsplash`,
    photographer: photo.user.name,
    photographer_url: photo.user.links.html,
    source: 'unsplash',
    unsplash_link: photo.links.html, // Required by Unsplash guidelines
  }));
}

// Process top stations first (ones with higher line counts / more popular)
const toProcess = stations
  .filter(s => !existing[s.slug] || existing[s.slug].length < IMAGES_PER_STATION)
  .sort((a, b) => b.line_count - a.line_count);

console.log(`Fetching Unsplash images for ${toProcess.length} stations...`);
console.log('(50 requests/hour limit — will process in batches)\n');

const imageMap = { ...existing };
let processed = 0;
const BATCH_SIZE = 40; // Stay under 50/hour limit

for (const station of toProcess.slice(0, BATCH_SIZE)) {
  const slug = station.slug;
  console.log(`[${++processed}/${Math.min(toProcess.length, BATCH_SIZE)}] ${station.name_en}...`);

  const results = await searchUnsplash(`${station.name_en} Tokyo neighborhood`, IMAGES_PER_STATION);

  if (results.length > 0) {
    imageMap[slug] = results;
    console.log(`  Found ${results.length} images`);
  } else {
    // Fallback: broader search
    const fallback = await searchUnsplash(`${station.name_en} Japan`, 2);
    if (fallback.length > 0) {
      imageMap[slug] = fallback;
      console.log(`  Fallback: ${fallback.length} images`);
    } else {
      console.log(`  No images found`);
    }
    await new Promise(r => setTimeout(r, RATE_LIMIT_DELAY));
  }

  await new Promise(r => setTimeout(r, RATE_LIMIT_DELAY));
}

console.log(`\nSaved images for ${Object.keys(imageMap).length} stations`);
writeFileSync(outputPath, JSON.stringify(imageMap, null, 2), 'utf-8');
console.log('Written to app/src/data/station-images-unsplash.json');
