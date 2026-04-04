/**
 * Phase 4: Merge all image sources into a single unified file.
 * Priority: Flickr (existing) > Flickr (API search) > Wikimedia (self-hosted) > Wiki geo
 *
 * Usage: node scripts/merge-all-images.mjs [--validate]
 * Env: IMAGE_HOST=https://img.pogorelov.dev (default)
 *
 * Input:  Multiple metadata JSON files from Phases 1-3 + existing data
 * Output: app/src/data/station-images-all.json
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';

const IMAGE_HOST = process.env.IMAGE_HOST || 'https://img.pogorelov.dev';
const VALIDATE_ONLY = process.argv.includes('--validate');
const MIN_IMAGES = 3;
const MAX_IMAGES = 8;

const stationsPath = new URL('../app/src/data/stations.json', import.meta.url);
const outputPath = new URL('../app/src/data/station-images-all.json', import.meta.url);

const stations = JSON.parse(readFileSync(stationsPath, 'utf-8'));

function loadJson(path) {
  if (typeof path === 'string') {
    return existsSync(path) ? JSON.parse(readFileSync(path, 'utf-8')) : {};
  }
  // URL object
  try {
    return JSON.parse(readFileSync(path, 'utf-8'));
  } catch {
    return {};
  }
}

// Load all sources (priority order: first = highest)
const sources = [
  { name: 'flickr-existing', data: loadJson(new URL('../app/src/data/station-images-flickr.json', import.meta.url)) },
  { name: 'wiki-selfhosted', data: loadJson('/tmp/station-images-wiki-selfhosted.json') },
  { name: 'wiki-geo', data: loadJson('/tmp/station-images-wiki-geo.json') },
];

console.log('Sources loaded:');
for (const s of sources) {
  const stationCount = Object.keys(s.data).length;
  const imageCount = Object.values(s.data).reduce((sum, imgs) => sum + imgs.length, 0);
  console.log(`  ${s.name}: ${stationCount} stations, ${imageCount} images`);
}
console.log();

// Merge
const merged = {};
const stats = {
  total: 0,
  withImages: 0,
  withMinImages: 0,
  noImages: 0,
  bySource: {},
  imageCounts: [],
};

for (const station of stations) {
  const { slug } = station;
  const allImages = [];
  const seenUrls = new Set();

  for (const source of sources) {
    const imgs = source.data[slug] || [];
    for (const img of imgs) {
      // Deduplicate by original_url or url
      const key = img.original_url || img.url;
      if (seenUrls.has(key)) continue;
      seenUrls.add(key);

      // Ensure all URLs are self-hosted
      const isSelfHosted = img.url?.startsWith(IMAGE_HOST);

      allImages.push({
        url: img.url,
        alt: img.alt || `${station.name_en} area`,
        attribution: img.attribution || 'Unknown',
        source: img.source || 'unknown',
        license: img.license || 'CC BY-SA',
        ...(img.local_path && { local_path: img.local_path }),
        ...(img.photographer && { photographer: img.photographer }),
        ...(img.flickr_url && { flickr_url: img.flickr_url }),
        _self_hosted: isSelfHosted,
      });
    }
  }

  // Trim to MAX_IMAGES
  const finalImages = allImages.slice(0, MAX_IMAGES).map(img => {
    const { _self_hosted, ...rest } = img;
    return rest;
  });

  if (finalImages.length > 0) {
    merged[slug] = finalImages;
    stats.withImages++;
    if (finalImages.length >= MIN_IMAGES) stats.withMinImages++;
  } else {
    stats.noImages++;
  }

  stats.total++;
  stats.imageCounts.push(finalImages.length);

  // Track source distribution
  for (const img of finalImages) {
    stats.bySource[img.source] = (stats.bySource[img.source] || 0) + 1;
  }
}

// Report
const totalImages = Object.values(merged).reduce((s, v) => s + v.length, 0);
const avgImages = (totalImages / stats.withImages).toFixed(1);

console.log(`--- Merge Report ---`);
console.log(`Total stations: ${stats.total}`);
console.log(`With images: ${stats.withImages} (${(stats.withImages / stats.total * 100).toFixed(1)}%)`);
console.log(`With >= ${MIN_IMAGES} images: ${stats.withMinImages} (${(stats.withMinImages / stats.total * 100).toFixed(1)}%)`);
console.log(`No images: ${stats.noImages}`);
console.log(`Total images: ${totalImages}`);
console.log(`Avg images per station (with images): ${avgImages}`);
console.log();
console.log(`By source:`);
for (const [source, count] of Object.entries(stats.bySource).sort((a, b) => b[1] - a[1])) {
  console.log(`  ${source}: ${count} (${(count / totalImages * 100).toFixed(1)}%)`);
}

// Check for non-self-hosted URLs
const externalUrls = [];
for (const [slug, imgs] of Object.entries(merged)) {
  for (const img of imgs) {
    if (!img.url?.startsWith(IMAGE_HOST)) {
      externalUrls.push({ slug, url: img.url });
    }
  }
}

if (externalUrls.length > 0) {
  console.log(`\n*** WARNING: ${externalUrls.length} images still use external URLs ***`);
  for (const e of externalUrls.slice(0, 5)) {
    console.log(`  ${e.slug}: ${e.url.slice(0, 80)}`);
  }
  if (externalUrls.length > 5) console.log(`  ... and ${externalUrls.length - 5} more`);
}

// Stations with no images
if (stats.noImages > 0) {
  const noImageSlugs = stations.filter(s => !merged[s.slug]).map(s => s.slug);
  console.log(`\n*** Stations with NO images (${noImageSlugs.length}): ***`);
  console.log(`  ${noImageSlugs.slice(0, 20).join(', ')}`);
  if (noImageSlugs.length > 20) console.log(`  ... and ${noImageSlugs.length - 20} more`);
}

// Distribution histogram
console.log(`\nImage count distribution:`);
const dist = {};
for (const c of stats.imageCounts) {
  dist[c] = (dist[c] || 0) + 1;
}
for (const [count, freq] of Object.entries(dist).sort((a, b) => Number(a[0]) - Number(b[0]))) {
  console.log(`  ${count} images: ${freq} stations`);
}

if (!VALIDATE_ONLY) {
  writeFileSync(outputPath, JSON.stringify(merged, null, 2));
  console.log(`\nSaved: ${outputPath}`);
}
