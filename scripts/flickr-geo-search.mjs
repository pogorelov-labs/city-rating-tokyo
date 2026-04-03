/**
 * Phase 2: Search Flickr by geo coordinates for all stations.
 * Uses Flickr API (free key, 3600 req/hr) to find CC-licensed photos
 * near each station, downloads them for self-hosting.
 *
 * Usage: FLICKR_API_KEY=xxx node scripts/flickr-geo-search.mjs
 * Env: FLICKR_API_KEY (required)
 *       IMAGE_DIR=/data/images (default: /tmp/station-images-download)
 *       IMAGE_HOST=https://img.pogorelov.dev (default)
 *
 * Input:  app/src/data/stations.json
 * Output: {IMAGE_DIR}/flickr-search/{slug}/{photo_id}.jpg
 *         /tmp/station-images-flickr-search.json (metadata)
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { pipeline } from 'stream/promises';
import { createWriteStream } from 'fs';

const FLICKR_API_KEY = process.env.FLICKR_API_KEY;
if (!FLICKR_API_KEY) {
  console.error('Error: FLICKR_API_KEY env var required');
  process.exit(1);
}

const IMAGE_DIR = process.env.IMAGE_DIR || '/tmp/station-images-download';
const IMAGE_HOST = process.env.IMAGE_HOST || 'https://img.pogorelov.dev';
const MAX_PER_STATION = 8;
const SEARCH_RADIUS_KM = 0.5;
const DELAY_MS = 150;
const CHECKPOINT_EVERY = 20;

const stationsPath = new URL('../app/src/data/stations.json', import.meta.url);
const outputMetaPath = '/tmp/station-images-flickr-search.json';

const stations = JSON.parse(readFileSync(stationsPath, 'utf-8'));

// Load existing flickr images to skip stations that already have enough
const existingFlickrPath = new URL('../app/src/data/station-images-flickr.json', import.meta.url);
const existingFlickr = existsSync(existingFlickrPath)
  ? JSON.parse(readFileSync(existingFlickrPath, 'utf-8'))
  : {};

// Load checkpoint
const metadata = existsSync(outputMetaPath)
  ? JSON.parse(readFileSync(outputMetaPath, 'utf-8'))
  : {};

// CC license IDs for Flickr API
// 1=CC BY-NC-SA, 2=CC BY-NC, 3=CC BY-NC-ND, 4=CC BY, 5=CC BY-SA, 6=CC BY-ND,
// 7=No known copyright, 9=CC0, 10=Public Domain
const LICENSE_IDS = '1,2,3,4,5,6,7,9,10';

const LICENSE_MAP = {
  '1': 'CC BY-NC-SA 2.0', '2': 'CC BY-NC 2.0', '3': 'CC BY-NC-ND 2.0',
  '4': 'CC BY 2.0', '5': 'CC BY-SA 2.0', '6': 'CC BY-ND 2.0',
  '7': 'No known copyright restrictions', '9': 'CC0 1.0', '10': 'Public Domain',
};

// Tags for content filtering (reused from enrich-flickr-metadata.mjs)
const BAD_TAGS = new Set([
  'portrait', 'selfie', 'self', 'me', 'face', 'people',
  'food', 'meal', 'dish', 'ramen', 'sushi',
  'drink', 'beer', 'cocktail', 'coffee',
  'cat', 'dog', 'pet', 'animal',
  'cosplay', 'anime', 'manga', 'figure', 'toy',
  'concert', 'event', 'party',
  'baby', 'child', 'kid', 'family',
  'wedding', 'ceremony',
  'macro', 'closeup',
  'indoor', 'interior', 'room', 'hotel',
]);

// Filter stations: skip those already fully covered
const pendingStations = stations.filter(s => {
  const existingCount = (existingFlickr[s.slug] || []).length + (metadata[s.slug] || []).length;
  return existingCount < MAX_PER_STATION;
});

console.log(`Total stations: ${stations.length}`);
console.log(`Already covered: ${stations.length - pendingStations.length}`);
console.log(`To search: ${pendingStations.length}\n`);

async function flickrSearch(lat, lng) {
  const url = `https://api.flickr.com/services/rest/?method=flickr.photos.search` +
    `&api_key=${FLICKR_API_KEY}` +
    `&lat=${lat}&lon=${lng}&radius=${SEARCH_RADIUS_KM}` +
    `&license=${LICENSE_IDS}` +
    `&content_type=1` +  // photos only
    `&media=photos` +
    `&extras=url_l,url_c,url_z,tags,owner_name,license,geo` +
    `&per_page=30` +
    `&sort=relevance` +
    `&format=json&nojsoncallback=1`;

  const res = await fetch(url);
  if (!res.ok) {
    if (res.status === 429) return '__RATE_LIMITED__';
    return null;
  }
  const data = await res.json();
  if (data.stat !== 'ok') return null;
  return data.photos?.photo || [];
}

function filterPhoto(photo) {
  const tags = (photo.tags || '').toLowerCase().split(/\s+/);
  const badCount = tags.filter(t => BAD_TAGS.has(t)).length;
  if (badCount >= 2) return false;
  // Must have a downloadable URL
  return !!(photo.url_l || photo.url_c || photo.url_z);
}

function getBestUrl(photo) {
  // Prefer url_l (1024px), then url_c (800px), then url_z (640px)
  return photo.url_l || photo.url_c || photo.url_z;
}

async function downloadImage(url, destPath) {
  try {
    const res = await fetch(url);
    if (!res.ok) return false;
    await pipeline(res.body, createWriteStream(destPath));
    return true;
  } catch {
    return false;
  }
}

let processed = 0;
let totalDownloaded = 0;
let totalSearched = 0;
let emptySearches = 0;
let rateLimited = false;

for (const station of pendingStations) {
  if (rateLimited) break;

  const { slug, lat, lng, name_en } = station;
  const existingCount = (existingFlickr[slug] || []).length + (metadata[slug] || []).length;
  const need = MAX_PER_STATION - existingCount;
  if (need <= 0) continue;

  totalSearched++;
  const photos = await flickrSearch(lat, lng);

  if (photos === '__RATE_LIMITED__') {
    console.log(`\n*** RATE LIMITED at station ${processed}. Saving progress and exiting. ***`);
    rateLimited = true;
    break;
  }

  if (!photos || photos.length === 0) {
    emptySearches++;
    processed++;
    await new Promise(r => setTimeout(r, DELAY_MS));
    continue;
  }

  const filtered = photos.filter(filterPhoto).slice(0, need);

  if (filtered.length === 0) {
    emptySearches++;
    processed++;
    await new Promise(r => setTimeout(r, DELAY_MS));
    continue;
  }

  const slugDir = `${IMAGE_DIR}/flickr-search/${slug}`;
  mkdirSync(slugDir, { recursive: true });

  const stationImages = metadata[slug] ? [...metadata[slug]] : [];
  const existingIds = new Set(stationImages.map(i => i.photo_id));

  for (const photo of filtered) {
    if (existingIds.has(photo.id)) continue;

    const imageUrl = getBestUrl(photo);
    const destFile = `${slugDir}/${photo.id}.jpg`;
    const localPath = `flickr-search/${slug}/${photo.id}.jpg`;

    let ok = true;
    if (!existsSync(destFile)) {
      ok = await downloadImage(imageUrl, destFile);
    }

    if (ok) {
      stationImages.push({
        photo_id: photo.id,
        url: `${IMAGE_HOST}/${localPath}`,
        alt: photo.title || `${name_en} area`,
        attribution: `Photo by ${photo.ownername} on Flickr`,
        photographer: photo.ownername,
        source: 'flickr',
        license: LICENSE_MAP[String(photo.license)] || 'CC',
        local_path: localPath,
        flickr_url: `https://www.flickr.com/photos/${photo.owner}/${photo.id}`,
        tags: photo.tags || '',
      });
      totalDownloaded++;
    }

    await new Promise(r => setTimeout(r, 50)); // Small delay between downloads
  }

  if (stationImages.length > 0) {
    metadata[slug] = stationImages;
  }

  processed++;

  if (processed % 20 === 0) {
    console.log(`[${processed}/${pendingStations.length}] ${slug}: ${stationImages.length} images (downloaded: ${totalDownloaded}, empty: ${emptySearches})`);
  }

  if (processed % CHECKPOINT_EVERY === 0) {
    writeFileSync(outputMetaPath, JSON.stringify(metadata, null, 2));
    console.log(`  [checkpoint: ${Object.keys(metadata).length} stations]`);
  }

  await new Promise(r => setTimeout(r, DELAY_MS));
}

// Final save
writeFileSync(outputMetaPath, JSON.stringify(metadata, null, 2));

console.log(`\n--- Phase 2 Complete ---`);
console.log(`Searched: ${totalSearched} stations`);
console.log(`Downloaded: ${totalDownloaded} images`);
console.log(`Empty searches (no photos nearby): ${emptySearches}`);
console.log(`Stations with new images: ${Object.keys(metadata).length}`);
console.log(`Total images: ${Object.values(metadata).reduce((s, v) => s + v.length, 0)}`);
console.log(`Images dir: ${IMAGE_DIR}/flickr-search/`);
console.log(`Metadata: ${outputMetaPath}`);
if (rateLimited) {
  console.log(`\n*** Was rate limited. Re-run to continue from checkpoint. ***`);
}
