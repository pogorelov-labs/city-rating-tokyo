/**
 * Download Flickr images for stations using oEmbed API (no API key needed).
 * Filters to CC-licensed photos only.
 *
 * Usage: node scripts/download-flickr-images.mjs
 * Input: /tmp/station-flickr-matches.json
 * Output: /tmp/station-flickr-images/ (organized by slug)
 *         app/src/data/station-images-flickr.json (metadata)
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { pipeline } from 'stream/promises';
import { createWriteStream } from 'fs';

const matches = JSON.parse(readFileSync('/tmp/station-flickr-matches.json', 'utf-8'));
const outputDir = '/tmp/station-flickr-images';
const metadataPath = new URL('../app/src/data/station-images-flickr.json', import.meta.url);

// Load existing metadata to resume
const existing = existsSync(metadataPath)
  ? JSON.parse(readFileSync(metadataPath, 'utf-8'))
  : {};

const ALLOWED_LICENSES = [
  'CC BY 2.0', 'CC BY-SA 2.0', 'CC BY-ND 2.0',
  'CC BY 3.0', 'CC BY-SA 3.0',
  'CC BY 4.0', 'CC BY-SA 4.0',
  'CC0 1.0', 'Public Domain',
  'United States Government Work',
  'No known copyright restrictions',
];

// NC licenses - we'll include them since this is a free non-commercial project
const NC_LICENSES = [
  'CC BY-NC 2.0', 'CC BY-NC-SA 2.0', 'CC BY-NC-ND 2.0',
  'CC BY-NC 3.0', 'CC BY-NC-SA 3.0',
  'CC BY-NC 4.0', 'CC BY-NC-SA 4.0',
];

const ALL_ALLOWED = [...ALLOWED_LICENSES, ...NC_LICENSES];

const MAX_PER_STATION = 8;
const CONCURRENT = 5;
const DELAY_MS = 200; // Be nice to Flickr

async function getOembed(flickrUrl) {
  const url = `https://www.flickr.com/services/oembed/?url=${encodeURIComponent(flickrUrl)}&format=json`;
  const res = await fetch(url);
  if (!res.ok) return null;
  try {
    return await res.json();
  } catch {
    return null;
  }
}

async function downloadImage(imageUrl, destPath) {
  const res = await fetch(imageUrl);
  if (!res.ok) return false;
  await pipeline(res.body, createWriteStream(destPath));
  return true;
}

// Process stations that need photos
const slugs = Object.keys(matches).filter(slug => {
  const existingCount = (existing[slug] || []).length;
  return existingCount < MAX_PER_STATION;
});

console.log(`Processing ${slugs.length} stations (${Object.keys(matches).length} have matches)`);
console.log(`Downloading up to ${MAX_PER_STATION} photos per station\n`);

mkdirSync(outputDir, { recursive: true });

const metadata = { ...existing };
let totalDownloaded = 0;
let totalSkipped = 0;
let totalErrors = 0;
let stationsProcessed = 0;

for (const slug of slugs) {
  const photos = matches[slug];
  const alreadyHave = (existing[slug] || []).length;
  const need = MAX_PER_STATION - alreadyHave;
  if (need <= 0) continue;

  const slugDir = `${outputDir}/${slug}`;
  mkdirSync(slugDir, { recursive: true });

  const stationImages = existing[slug] ? [...existing[slug]] : [];
  const existingIds = new Set(stationImages.map(img => img.photo_id));

  console.log(`[${++stationsProcessed}/${slugs.length}] ${slug} (${photos.length} candidates, need ${need})...`);

  let downloaded = 0;
  for (const photo of photos) {
    if (downloaded >= need) break;
    if (existingIds.has(photo.photo_id)) continue;

    try {
      const oembed = await getOembed(photo.flickr_url);
      if (!oembed || !oembed.url) {
        totalSkipped++;
        continue;
      }

      // Check license
      const license = oembed.license || '';
      if (!ALL_ALLOWED.some(l => license.includes(l)) && license !== '') {
        totalSkipped++;
        continue;
      }

      // Get larger version (replace _b with _c for 800px, or keep _b for 1024px)
      const imageUrl = oembed.url;
      const ext = imageUrl.match(/\.(jpg|jpeg|png|webp)/i)?.[1] || 'jpg';
      const destFile = `${slugDir}/${photo.photo_id}.${ext}`;

      if (!existsSync(destFile)) {
        const ok = await downloadImage(imageUrl, destFile);
        if (!ok) {
          totalErrors++;
          continue;
        }
      }

      stationImages.push({
        photo_id: photo.photo_id,
        url: imageUrl, // Will be replaced with self-hosted URL later
        alt: oembed.title || `${slug} area photo`,
        attribution: `Photo by ${oembed.author_name} on Flickr`,
        photographer: oembed.author_name,
        photographer_url: oembed.author_url,
        license: oembed.license || 'Unknown',
        flickr_url: photo.flickr_url,
        source: 'flickr',
        local_path: `${slug}/${photo.photo_id}.${ext}`,
      });

      downloaded++;
      totalDownloaded++;
    } catch (e) {
      totalErrors++;
    }

    await new Promise(r => setTimeout(r, DELAY_MS));
  }

  if (stationImages.length > 0) {
    metadata[slug] = stationImages;
  }

  console.log(`  Downloaded: ${downloaded}, total for station: ${stationImages.length}`);

  // Save progress every 10 stations
  if (stationsProcessed % 10 === 0) {
    writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
    console.log(`  [checkpoint saved]`);
  }
}

// Final save
writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
console.log(`\n--- Done ---`);
console.log(`Downloaded: ${totalDownloaded}`);
console.log(`Skipped (license/missing): ${totalSkipped}`);
console.log(`Errors: ${totalErrors}`);
console.log(`Stations with images: ${Object.keys(metadata).length}`);
console.log(`Images saved to: ${outputDir}`);
console.log(`Metadata: ${metadataPath}`);
