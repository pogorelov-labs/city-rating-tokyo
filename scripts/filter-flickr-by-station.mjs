/**
 * Filter Kaggle Tokyo Geotagged Flickr photos by station proximity.
 * Matches photos within RADIUS_KM of each station, extracts Flickr photo IDs,
 * and generates download URLs.
 *
 * Usage: node scripts/filter-flickr-by-station.mjs
 * Input: /tmp/kaggle-tokyo/tokyo_clean.csv
 * Output: /tmp/station-flickr-matches.json
 */

import { readFileSync, writeFileSync } from 'fs';
import { createReadStream } from 'fs';
import { createInterface } from 'readline';

const RADIUS_KM = 0.5; // 500m radius around each station

const stations = JSON.parse(
  readFileSync(new URL('../app/src/data/stations.json', import.meta.url), 'utf-8')
);

function haversineKm(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Extract Flickr photo ID from URL like http://www.flickr.com/photos/USER/PHOTO_ID/
function extractPhotoId(url) {
  const m = url.match(/flickr\.com\/photos\/[^/]+\/(\d+)/);
  return m ? m[1] : null;
}

// Flickr static image URL from photo ID (medium 640px)
// Real URL requires API call, but we can try the common pattern
function flickrPageUrl(photoId) {
  return `https://www.flickr.com/photos/search/?photo_id=${photoId}`;
}

console.log(`Loading ${stations.length} stations...`);
console.log(`Radius: ${RADIUS_KM * 1000}m\n`);

// Build station lookup with slug -> {lat, lng, name}
const stationMap = new Map();
for (const s of stations) {
  stationMap.set(s.slug, { lat: s.lat, lng: s.lng, name_en: s.name_en, photos: [] });
}

// Read CSV line by line
const csvPath = '/tmp/kaggle-tokyo/tokyo_clean.csv';
const lines = readFileSync(csvPath, 'utf-8').split('\n');
const header = lines[0].split(',');

let totalMatches = 0;
let totalRows = 0;

for (let i = 1; i < lines.length; i++) {
  const line = lines[i].trim();
  if (!line) continue;
  totalRows++;

  // Parse: user_id,longitude,latitude,date_taken,photo/video_page_url,x,y
  const parts = line.split(',');
  const lng = parseFloat(parts[1]);
  const lat = parseFloat(parts[2]);
  const url = parts[4];

  if (isNaN(lat) || isNaN(lng) || !url) continue;

  const photoId = extractPhotoId(url);
  if (!photoId) continue;

  // Check against all stations
  for (const [slug, data] of stationMap) {
    const dist = haversineKm(lat, lng, data.lat, data.lng);
    if (dist <= RADIUS_KM) {
      data.photos.push({
        flickr_url: url,
        photo_id: photoId,
        lat,
        lng,
        distance_m: Math.round(dist * 1000),
      });
      totalMatches++;
    }
  }
}

console.log(`Processed ${totalRows} photos`);
console.log(`Total matches: ${totalMatches}\n`);

// Build result: slug -> photos[], sorted by distance
const result = {};
let stationsWithPhotos = 0;
const countDistribution = [];

for (const [slug, data] of stationMap) {
  if (data.photos.length > 0) {
    // Deduplicate by photo_id
    const seen = new Set();
    const unique = data.photos.filter(p => {
      if (seen.has(p.photo_id)) return false;
      seen.add(p.photo_id);
      return true;
    });

    // Sort by distance, take top 20
    unique.sort((a, b) => a.distance_m - b.distance_m);
    result[slug] = unique.slice(0, 20);
    stationsWithPhotos++;
    countDistribution.push({ slug, count: unique.length });
  }
}

countDistribution.sort((a, b) => b.count - a.count);
console.log(`Stations with photos: ${stationsWithPhotos} / ${stations.length}`);
console.log(`\nTop 20 stations by photo count:`);
for (const { slug, count } of countDistribution.slice(0, 20)) {
  console.log(`  ${slug}: ${count} photos`);
}
console.log(`\nBottom 10:`);
for (const { slug, count } of countDistribution.slice(-10)) {
  console.log(`  ${slug}: ${count} photos`);
}

writeFileSync('/tmp/station-flickr-matches.json', JSON.stringify(result, null, 2));
console.log(`\nWritten to /tmp/station-flickr-matches.json`);
