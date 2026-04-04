/**
 * Phase 3: Wikimedia Commons geo search for stations still missing images.
 * Uses the geosearch API to find geotagged photos near station coordinates.
 * No API key needed.
 *
 * Usage: node scripts/fetch-wiki-geo.mjs
 * Env: IMAGE_DIR=/data/images (default: /tmp/station-images-download)
 *       IMAGE_HOST=https://img.pogorelov.dev (default)
 *       MIN_IMAGES=3 (skip stations with >= this many images already)
 *
 * Input:  app/src/data/stations.json + existing metadata files
 * Output: {IMAGE_DIR}/wiki-geo/{slug}/{hash}.jpg
 *         /tmp/station-images-wiki-geo.json (metadata)
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { createHash } from 'crypto';
import { pipeline } from 'stream/promises';
import { createWriteStream } from 'fs';

const IMAGE_DIR = process.env.IMAGE_DIR || '/tmp/station-images-download';
const IMAGE_HOST = process.env.IMAGE_HOST || 'https://img.pogorelov.dev';
const MIN_IMAGES = parseInt(process.env.MIN_IMAGES || '0', 10); // 0 = search ALL stations
const DELAY_MS = 500; // Wikimedia rate limits, be respectful
const BACKOFF_MS = 5000;
const CHECKPOINT_EVERY = 50;
const TARGET_PER_STATION = 6;
const SEARCH_RADIUS = 1500; // meters — wider radius for better coverage

const UA = 'CityRatingTokyo/1.0 (https://github.com/ruspg/city-rating)';

const stationsPath = new URL('../app/src/data/stations.json', import.meta.url);
const outputMetaPath = '/tmp/station-images-wiki-geo.json';

const stations = JSON.parse(readFileSync(stationsPath, 'utf-8'));

// Load all existing image sources to count coverage
function loadExisting(filename) {
  const p = new URL(`../app/src/data/${filename}`, import.meta.url);
  return existsSync(p) ? JSON.parse(readFileSync(p, 'utf-8')) : {};
}

const existingWiki = loadExisting('station-images.json');
const existingFlickr = loadExisting('station-images-flickr.json');

// Also load Phase 1 & 2 outputs if available
function loadTmp(path) {
  return existsSync(path) ? JSON.parse(readFileSync(path, 'utf-8')) : {};
}

const wikiSelfhosted = loadTmp('/tmp/station-images-wiki-selfhosted.json');
const flickrSearch = loadTmp('/tmp/station-images-flickr-search.json');

// Load checkpoint
const metadata = existsSync(outputMetaPath)
  ? JSON.parse(readFileSync(outputMetaPath, 'utf-8'))
  : {};

function countImages(slug) {
  return (existingWiki[slug]?.length || 0) +
    (existingFlickr[slug]?.length || 0) +
    (wikiSelfhosted[slug]?.length || 0) +
    (flickrSearch[slug]?.length || 0) +
    (metadata[slug]?.length || 0);
}

// Find stations that still need images
const pendingStations = stations.filter(s => countImages(s.slug) < MIN_IMAGES);

console.log(`Total stations: ${stations.length}`);
console.log(`Stations with < ${MIN_IMAGES} images: ${pendingStations.length}`);
console.log(`Already in checkpoint: ${Object.keys(metadata).length}\n`);

// Skip stations already in checkpoint
const todoStations = pendingStations.filter(s => !metadata[s.slug]);
console.log(`Remaining to process: ${todoStations.length}\n`);

// Wikimedia geosearch: find geotagged files near coordinates
async function geoSearch(lat, lng) {
  const url = `https://commons.wikimedia.org/w/api.php?action=query` +
    `&list=geosearch&gscoord=${lat}|${lng}&gsradius=${SEARCH_RADIUS}` +
    `&gsnamespace=6&gslimit=50&format=json`;

  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (res.status === 429) {
    console.log(`    [429 rate limited, backing off ${BACKOFF_MS}ms]`);
    await new Promise(r => setTimeout(r, BACKOFF_MS));
    const retry = await fetch(url, { headers: { 'User-Agent': UA } });
    if (!retry.ok) return [];
    const data = await retry.json();
    return data.query?.geosearch || [];
  }
  if (!res.ok) return [];
  const data = await res.json();
  return data.query?.geosearch || [];
}

// Get image info (URL, dimensions, license) for a list of file titles
async function getImageInfo(titles) {
  if (titles.length === 0) return [];

  const url = `https://commons.wikimedia.org/w/api.php?action=query` +
    `&titles=${encodeURIComponent(titles.join('|'))}` +
    `&prop=imageinfo&iiprop=url|size|extmetadata|mime` +
    `&iiurlwidth=1280&format=json`;

  let res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (res.status === 429) {
    await new Promise(r => setTimeout(r, BACKOFF_MS));
    res = await fetch(url, { headers: { 'User-Agent': UA } });
  }
  if (!res.ok) return [];
  const data = await res.json();
  const pages = data.query?.pages || {};

  const results = [];
  for (const page of Object.values(pages)) {
    const info = page.imageinfo?.[0];
    if (!info) continue;

    // Filter: must be a photo (jpg/png), not SVG/GIF
    const mime = info.mime || '';
    if (!mime.startsWith('image/jpeg') && !mime.startsWith('image/png')) continue;

    // Filter: minimum width 640px
    if ((info.width || 0) < 640) continue;

    // Filter: skip obvious non-photos by filename
    const title = page.title || '';
    if (/logo|icon|map|diagram|symbol|route|sign|banner|flag|coat.of.arms|seal|emblem/i.test(title)) continue;

    const license = info.extmetadata?.LicenseShortName?.value || 'CC BY-SA';
    const artist = info.extmetadata?.Artist?.value?.replace(/<[^>]+>/g, '') || 'Wikimedia Commons';
    const description = info.extmetadata?.ImageDescription?.value?.replace(/<[^>]+>/g, '') || '';

    results.push({
      title,
      url: info.thumburl || info.url, // thumburl is 1280px version
      original_url: info.url,
      width: info.width,
      height: info.height,
      license,
      artist,
      description,
    });
  }

  return results;
}

function hashString(s) {
  return createHash('md5').update(s).digest('hex').slice(0, 12);
}

async function downloadImage(url, destPath) {
  try {
    const res = await fetch(url, { headers: { 'User-Agent': UA }, redirect: 'follow' });
    if (!res.ok) return false;
    await pipeline(res.body, createWriteStream(destPath));
    return true;
  } catch {
    return false;
  }
}

let processed = 0;
let totalDownloaded = 0;
let emptySearches = 0;

for (const station of todoStations) {
  const { slug, lat, lng, name_en } = station;
  const currentCount = countImages(slug);
  const need = TARGET_PER_STATION - currentCount;
  if (need <= 0) {
    processed++;
    continue;
  }

  // Step 1: Geo search
  const geoResults = await geoSearch(lat, lng);
  await new Promise(r => setTimeout(r, DELAY_MS));

  if (geoResults.length === 0) {
    emptySearches++;
    processed++;
    continue;
  }

  // Step 2: Get image info for found files
  const titles = geoResults.map(r => r.title).slice(0, 20);
  const imageInfos = await getImageInfo(titles);
  await new Promise(r => setTimeout(r, DELAY_MS));

  if (imageInfos.length === 0) {
    emptySearches++;
    processed++;
    continue;
  }

  // Step 3: Download top images
  const slugDir = `${IMAGE_DIR}/wiki-geo/${slug}`;
  mkdirSync(slugDir, { recursive: true });

  const stationImages = [];

  for (const info of imageInfos.slice(0, need)) {
    const hash = hashString(info.url);
    const destFile = `${slugDir}/${hash}.jpg`;
    const localPath = `wiki-geo/${slug}/${hash}.jpg`;

    let ok = true;
    if (!existsSync(destFile)) {
      ok = await downloadImage(info.url, destFile);
    }

    if (ok) {
      stationImages.push({
        url: `${IMAGE_HOST}/${localPath}`,
        alt: info.description?.slice(0, 100) || `${name_en} area`,
        attribution: info.artist,
        source: 'wikimedia',
        license: info.license,
        local_path: localPath,
        original_url: info.original_url,
      });
      totalDownloaded++;
    }

    await new Promise(r => setTimeout(r, 50));
  }

  if (stationImages.length > 0) {
    metadata[slug] = stationImages;
  }

  processed++;

  if (processed % 20 === 0) {
    console.log(`[${processed}/${todoStations.length}] ${slug}: ${stationImages.length} new images (total: ${totalDownloaded}, empty: ${emptySearches})`);
  }

  if (processed % CHECKPOINT_EVERY === 0) {
    writeFileSync(outputMetaPath, JSON.stringify(metadata, null, 2));
    console.log(`  [checkpoint: ${Object.keys(metadata).length} stations]`);
  }
}

// Final save
writeFileSync(outputMetaPath, JSON.stringify(metadata, null, 2));

console.log(`\n--- Phase 3 Complete ---`);
console.log(`Processed: ${processed} stations`);
console.log(`Downloaded: ${totalDownloaded} images`);
console.log(`Empty geo searches: ${emptySearches}`);
console.log(`Stations with new images: ${Object.keys(metadata).length}`);
console.log(`Total images: ${Object.values(metadata).reduce((s, v) => s + v.length, 0)}`);
console.log(`Images dir: ${IMAGE_DIR}/wiki-geo/`);
console.log(`Metadata: ${outputMetaPath}`);
