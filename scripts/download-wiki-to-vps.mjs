/**
 * Phase 1: Download existing Wikimedia images and prepare for self-hosting.
 * Reads station-images.json (external wikimedia URLs), downloads each image,
 * resizes to 1280px max width, outputs new metadata with self-hosted URLs.
 *
 * Usage: node scripts/download-wiki-to-vps.mjs
 * Env: IMAGE_DIR=/data/images (default: /tmp/station-images-download)
 *       IMAGE_HOST=https://img.pogorelov.dev (default)
 *
 * Input:  app/src/data/station-images.json
 * Output: {IMAGE_DIR}/wiki/{slug}/{hash}.jpg
 *         /tmp/station-images-wiki-selfhosted.json (metadata)
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { createHash } from 'crypto';
import { pipeline } from 'stream/promises';
import { createWriteStream } from 'fs';

const IMAGE_DIR = process.env.IMAGE_DIR || '/tmp/station-images-download';
const IMAGE_HOST = process.env.IMAGE_HOST || 'https://img.pogorelov.dev';
const CHECKPOINT_EVERY = 50;
const DELAY_MS = 1000; // Wikimedia rate limits aggressively, be respectful
const BACKOFF_MS = 10000; // Wait on 429

const wikiImagesPath = new URL('../app/src/data/station-images.json', import.meta.url);
const outputMetaPath = '/tmp/station-images-wiki-selfhosted.json';

const wikiImages = JSON.parse(readFileSync(wikiImagesPath, 'utf-8'));

// Load checkpoint if exists
const metadata = existsSync(outputMetaPath)
  ? JSON.parse(readFileSync(outputMetaPath, 'utf-8'))
  : {};

const allSlugs = Object.keys(wikiImages);
const pendingSlugs = allSlugs.filter(slug => !metadata[slug]);

console.log(`Total stations with wiki images: ${allSlugs.length}`);
console.log(`Already processed: ${allSlugs.length - pendingSlugs.length}`);
console.log(`Remaining: ${pendingSlugs.length}\n`);

function hashFilename(url) {
  return createHash('md5').update(url).digest('hex').slice(0, 12);
}

// Try to get a larger version of the Wikimedia thumb URL
function getLargerUrls(thumbUrl) {
  // Returns array of URLs to try, from best to worst
  const urls = [];
  const thumbMatch = thumbUrl.match(/\/thumb\/(.+?)\/\d+px-/);
  if (thumbMatch) {
    const basePath = thumbMatch[1];
    const filename = basePath.split('/').pop();
    // Try 1280px first, then 800px, then original thumb
    urls.push(thumbUrl.replace(/\/\d+px-[^/]+$/, `/1280px-${filename}`));
    urls.push(thumbUrl.replace(/\/\d+px-[^/]+$/, `/800px-${filename}`));
  }
  urls.push(thumbUrl); // Always include original as fallback
  return urls;
}

async function downloadImage(url, destPath) {
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': 'CityRatingTokyo/1.0 (https://github.com/ruspg/city-rating; contact@pogorelov.dev)' },
      redirect: 'follow',
    });
    if (res.status === 429) {
      console.log(`    [429 rate limited, backing off ${BACKOFF_MS}ms]`);
      await new Promise(r => setTimeout(r, BACKOFF_MS));
      // Retry once
      const retry = await fetch(url, {
        headers: { 'User-Agent': 'CityRatingTokyo/1.0 (https://github.com/ruspg/city-rating; contact@pogorelov.dev)' },
        redirect: 'follow',
      });
      if (!retry.ok) return false;
      await pipeline(retry.body, createWriteStream(destPath));
      return true;
    }
    if (!res.ok) return false;
    await pipeline(res.body, createWriteStream(destPath));
    return true;
  } catch {
    return false;
  }
}

let processed = 0;
let downloaded = 0;
let errors = 0;

for (const slug of pendingSlugs) {
  const images = wikiImages[slug];
  if (!images || images.length === 0) continue;

  const slugDir = `${IMAGE_DIR}/wiki/${slug}`;
  mkdirSync(slugDir, { recursive: true });

  const stationImages = [];

  for (const img of images) {
    const hash = hashFilename(img.url);
    const destFile = `${slugDir}/${hash}.jpg`;
    const localPath = `wiki/${slug}/${hash}.jpg`;

    if (existsSync(destFile)) {
      // Already downloaded, just add metadata
      stationImages.push({
        url: `${IMAGE_HOST}/${localPath}`,
        alt: img.alt || `${slug} area`,
        attribution: img.attribution || 'Wikimedia Commons',
        source: 'wikimedia',
        license: 'CC BY-SA',
        local_path: localPath,
        original_url: img.url,
      });
      continue;
    }

    // Skip HEAD check — just try downloading directly to reduce request count
    const urlsToTry = getLargerUrls(img.url);
    let ok = false;
    for (const tryUrl of urlsToTry) {
      ok = await downloadImage(tryUrl, destFile);
      if (ok) break;
      await new Promise(r => setTimeout(r, DELAY_MS));
    }

    if (ok) {
      stationImages.push({
        url: `${IMAGE_HOST}/${localPath}`,
        alt: img.alt || `${slug} area`,
        attribution: img.attribution || 'Wikimedia Commons',
        source: 'wikimedia',
        license: 'CC BY-SA',
        local_path: localPath,
        original_url: img.url,
      });
      downloaded++;
    } else {
      errors++;
    }

    await new Promise(r => setTimeout(r, DELAY_MS));
  }

  if (stationImages.length > 0) {
    metadata[slug] = stationImages;
  }

  processed++;

  if (processed % 10 === 0) {
    console.log(`[${processed}/${pendingSlugs.length}] ${slug}: ${stationImages.length} images (total downloaded: ${downloaded}, errors: ${errors})`);
  }

  if (processed % CHECKPOINT_EVERY === 0) {
    writeFileSync(outputMetaPath, JSON.stringify(metadata, null, 2));
    console.log(`  [checkpoint saved: ${Object.keys(metadata).length} stations]`);
  }
}

// Final save
writeFileSync(outputMetaPath, JSON.stringify(metadata, null, 2));

console.log(`\n--- Phase 1 Complete ---`);
console.log(`Processed: ${processed} stations`);
console.log(`Downloaded: ${downloaded} images`);
console.log(`Errors: ${errors}`);
console.log(`Stations with images: ${Object.keys(metadata).length}`);
console.log(`Total images: ${Object.values(metadata).reduce((s, v) => s + v.length, 0)}`);
console.log(`Images dir: ${IMAGE_DIR}/wiki/`);
console.log(`Metadata: ${outputMetaPath}`);
