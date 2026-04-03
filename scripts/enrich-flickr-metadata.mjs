/**
 * Enrich Flickr photo metadata by scraping each photo's page.
 * Extracts: tags, description, GPS, location, all image sizes.
 * Then filters out portraits/food/irrelevant content by tags.
 *
 * Usage: node scripts/enrich-flickr-metadata.mjs
 * Input: app/src/data/station-images-flickr.json
 * Output: app/src/data/station-images-flickr.json (enriched)
 *         /tmp/flickr-enrichment-report.json (stats)
 */

import { readFileSync, writeFileSync } from 'fs';

const metadataPath = new URL('../app/src/data/station-images-flickr.json', import.meta.url);
const data = JSON.parse(readFileSync(metadataPath, 'utf-8'));

const DELAY_MS = 250;

// Tags that indicate good urban/landscape content
const GOOD_TAGS = new Set([
  'architecture', 'building', 'buildings', 'street', 'streets',
  'city', 'cityscape', 'urban', 'town', 'downtown',
  'park', 'garden', 'temple', 'shrine', 'church', 'castle',
  'bridge', 'tower', 'station', 'train', 'railway', 'subway',
  'tokyo', 'japan', 'nihon', 'nippon',
  'shinjuku', 'shibuya', 'ginza', 'akihabara', 'asakusa', 'ueno',
  'roppongi', 'ikebukuro', 'harajuku', 'shinagawa', 'meguro',
  'landscape', 'skyline', 'panorama', 'night', 'nightscape',
  'neon', 'lights', 'sign', 'shop', 'store', 'market',
  'river', 'canal', 'waterfront', 'bay',
  'road', 'alley', 'lane', 'crossing', 'intersection',
  'neighborhood', 'neighbourhood', 'district', 'area',
  '東京', '新宿', '渋谷', '銀座', '秋葉原', '浅草',
  '建物', '街', '公園', '神社', '寺', '駅',
]);

// Tags that indicate unwanted content
const BAD_TAGS = new Set([
  'portrait', 'selfie', 'self', 'me', 'face', 'people',
  'food', 'meal', 'dish', 'ramen', 'sushi', 'restaurant',
  'drink', 'beer', 'cocktail', 'coffee',
  'cat', 'dog', 'pet', 'animal',
  'cosplay', 'anime', 'manga', 'figure', 'toy',
  'concert', 'event', 'party',
  'baby', 'child', 'kid', 'family',
  'wedding', 'ceremony',
  'macro', 'closeup', 'close-up',
  'indoor', 'interior', 'room', 'hotel',
]);

async function scrapeFlickrPage(flickrUrl) {
  try {
    const res = await fetch(flickrUrl, {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; research bot)' },
    });
    if (!res.ok) return null;
    const html = await res.text();

    const m = html.match(/modelExport:\s*({.+?})\s*,\s*auth/s);
    if (!m) return null;

    const exported = JSON.parse(m[1]);
    const main = exported.main;
    const photoModel = main['photo-models']?.[0]?.data;
    if (!photoModel) return null;

    // Extract tags
    const tags = [];
    // Tags can be in the photo model or in separate tag-models
    // Try to find them in the HTML as well
    const tagMatch = html.match(/"tags":\[([^\]]*)\]/);
    if (tagMatch) {
      try {
        const tagArray = JSON.parse(`[${tagMatch[1]}]`);
        tags.push(...tagArray.filter(t => typeof t === 'string'));
      } catch {}
    }
    // Also extract from tag links in HTML
    const tagLinkPattern = /\/photos\/tags\/([^/"]+)/g;
    let tagLinkMatch;
    while ((tagLinkMatch = tagLinkPattern.exec(html)) !== null) {
      const tag = decodeURIComponent(tagLinkMatch[1]).toLowerCase();
      if (tag && !tags.includes(tag)) tags.push(tag);
    }

    // Extract geo
    const geoModel = main['photo-geo-models']?.[0]?.data;
    const geo = geoModel?.hasGeo ? { lat: geoModel.latitude, lng: geoModel.longitude } : null;

    // Extract location
    const locModel = main['photo-location-models']?.[0]?.data;
    let neighbourhood = null;
    let locality = null;
    let county = null;
    if (locModel?.levels?.data) {
      const levels = locModel.levels.data;
      neighbourhood = levels.neighbourhood?.data?.name;
      locality = levels.locality?.data?.name;
      county = levels.county?.data?.name;
    }

    // Extract best image size
    const sizes = photoModel.sizes?.data;
    let bestUrl = null;
    let bestWidth = 0;
    if (sizes) {
      for (const [key, sizeData] of Object.entries(sizes)) {
        const s = sizeData?.data;
        if (s?.width > bestWidth && s?.url) {
          bestWidth = s.width;
          bestUrl = s.url.startsWith('//') ? 'https:' + s.url : s.url;
        }
      }
    }

    return {
      title: photoModel.title || null,
      description: photoModel.description || null,
      tags,
      geo,
      location: { neighbourhood, locality, county },
      bestImageUrl: bestUrl,
      bestImageWidth: bestWidth,
    };
  } catch (e) {
    return null;
  }
}

function classifyPhoto(tags) {
  const lowerTags = tags.map(t => t.toLowerCase());
  let goodScore = 0;
  let badScore = 0;

  for (const tag of lowerTags) {
    if (GOOD_TAGS.has(tag)) goodScore++;
    if (BAD_TAGS.has(tag)) badScore++;
  }

  if (badScore >= 2) return 'bad';
  if (badScore > 0 && goodScore === 0) return 'bad';
  return 'good'; // Default to good if no bad tags
}

// Process all photos
const allPhotos = [];
for (const [slug, photos] of Object.entries(data)) {
  for (const photo of photos) {
    allPhotos.push({ slug, photo });
  }
}

console.log(`Enriching metadata for ${allPhotos.length} photos across ${Object.keys(data).length} stations...\n`);

let processed = 0;
let enriched = 0;
let filtered = 0;
let errors = 0;

const report = { enriched: [], filtered: [], errors: [] };

for (const { slug, photo } of allPhotos) {
  processed++;
  if (processed % 50 === 0) {
    console.log(`[${processed}/${allPhotos.length}] enriched=${enriched} filtered=${filtered} errors=${errors}`);
  }

  const meta = await scrapeFlickrPage(photo.flickr_url);
  if (!meta) {
    errors++;
    report.errors.push({ slug, photo_id: photo.photo_id, url: photo.flickr_url });
    await new Promise(r => setTimeout(r, DELAY_MS));
    continue;
  }

  // Enrich photo metadata
  photo.tags = meta.tags;
  photo.description_text = meta.description || photo.alt;
  if (meta.geo) photo.geo = meta.geo;
  if (meta.location.county) photo.location = meta.location;
  if (meta.bestImageUrl && meta.bestImageWidth > 1024) {
    photo.original_url = meta.bestImageUrl;
    photo.original_width = meta.bestImageWidth;
  }

  // Classify
  const classification = classifyPhoto(meta.tags);
  photo._classification = classification;

  if (classification === 'bad') {
    filtered++;
    report.filtered.push({ slug, photo_id: photo.photo_id, tags: meta.tags, title: meta.title });
  } else {
    enriched++;
  }

  await new Promise(r => setTimeout(r, DELAY_MS));
}

// Remove filtered photos from data
let removedCount = 0;
for (const [slug, photos] of Object.entries(data)) {
  const before = photos.length;
  data[slug] = photos.filter(p => p._classification !== 'bad');
  // Clean up internal field
  for (const p of data[slug]) delete p._classification;
  removedCount += before - data[slug].length;
  if (data[slug].length === 0) delete data[slug];
}

// Save enriched data
writeFileSync(metadataPath, JSON.stringify(data, null, 2));

// Save report
report.summary = {
  total_processed: processed,
  enriched,
  filtered_out: filtered,
  errors,
  removed_from_dataset: removedCount,
  stations_remaining: Object.keys(data).length,
  photos_remaining: Object.values(data).reduce((s, p) => s + p.length, 0),
};
writeFileSync('/tmp/flickr-enrichment-report.json', JSON.stringify(report, null, 2));

console.log(`\n--- Done ---`);
console.log(`Processed: ${processed}`);
console.log(`Enriched with tags/geo: ${enriched}`);
console.log(`Filtered out (portraits/food/etc): ${filtered}`);
console.log(`Errors: ${errors}`);
console.log(`Photos remaining: ${report.summary.photos_remaining}`);
console.log(`Stations remaining: ${report.summary.stations_remaining}`);
