/**
 * Expanded Wikimedia image fetcher — targets 5-6 images per station.
 * Adds Wikimedia Commons search API to supplement Wikidata SPARQL + Wikipedia REST.
 * Outputs: data/station-images.json (merges with existing)
 */

import { readFileSync, writeFileSync } from 'fs';
import { createHash } from 'crypto';

const stations = JSON.parse(readFileSync(new URL('../app/src/data/stations.json', import.meta.url), 'utf-8'));
const existing = JSON.parse(readFileSync(new URL('../app/src/data/station-images.json', import.meta.url), 'utf-8'));

const UA = 'CityRatingTokyo/1.0 (https://github.com/ruspg/city-rating-tokyo)';
const TARGET_IMAGES = 6;

function commonsUrl(filePathUrl) {
  const filename = decodeURIComponent(filePathUrl.split('/').pop());
  const md5 = createHash('md5').update(filename).digest('hex');
  return `https://upload.wikimedia.org/wikipedia/commons/${md5[0]}/${md5.slice(0, 2)}/${encodeURIComponent(filename)}`;
}

// Search Wikimedia Commons for photos of a location
async function searchCommons(query, limit = 6) {
  const results = [];
  try {
    const url = `https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(query)}&srnamespace=6&srlimit=${limit}&format=json`;
    const res = await fetch(url, { headers: { 'User-Agent': UA } });
    const data = await res.json();

    if (!data.query?.search) return results;

    for (const item of data.query.search) {
      const title = item.title; // "File:Something.jpg"
      if (!/\.(jpg|jpeg|png)$/i.test(title)) continue;
      // Skip logos, icons, maps, diagrams
      if (/logo|icon|map|diagram|symbol|route|sign|banner/i.test(title)) continue;

      const filename = title.replace('File:', '');
      const md5 = createHash('md5').update(filename).digest('hex');
      const thumbUrl = `https://upload.wikimedia.org/wikipedia/commons/thumb/${md5[0]}/${md5.slice(0, 2)}/${encodeURIComponent(filename)}/640px-${encodeURIComponent(filename)}`;

      results.push({
        url: thumbUrl,
        alt: filename.replace(/\.(jpg|jpeg|png)$/i, '').replace(/_/g, ' '),
        attribution: 'Wikimedia Commons',
      });
    }
  } catch (e) {
    console.error(`Commons search failed for "${query}": ${e.message}`);
  }
  return results;
}

// Fetch images from Wikipedia article
async function fetchWikipediaImages(pageName) {
  const images = [];
  try {
    // Get page images via query API (returns multiple)
    const url = `https://en.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(pageName)}&prop=images&imlimit=10&format=json`;
    const res = await fetch(url, { headers: { 'User-Agent': UA } });
    const data = await res.json();

    const pages = data.query?.pages;
    if (!pages) return images;

    for (const page of Object.values(pages)) {
      if (!page.images) continue;
      for (const img of page.images) {
        const title = img.title;
        if (!/\.(jpg|jpeg|png)$/i.test(title)) continue;
        if (/logo|icon|map|symbol|flag|commons-logo|wiki/i.test(title)) continue;

        const filename = title.replace('File:', '');
        const md5 = createHash('md5').update(filename).digest('hex');
        const thumbUrl = `https://upload.wikimedia.org/wikipedia/commons/thumb/${md5[0]}/${md5.slice(0, 2)}/${encodeURIComponent(filename)}/640px-${encodeURIComponent(filename)}`;

        images.push({
          url: thumbUrl,
          alt: filename.replace(/\.(jpg|jpeg|png)$/i, '').replace(/_/g, ' '),
          attribution: 'Wikipedia',
        });
      }
    }
  } catch (e) {
    console.error(`Wikipedia images failed for "${pageName}": ${e.message}`);
  }
  return images;
}

const imageMap = { ...existing };
let improved = 0;

const stationsToProcess = stations.filter(s => {
  const current = existing[s.slug] || [];
  return current.length < TARGET_IMAGES;
});

console.log(`Processing ${stationsToProcess.length} stations needing more images...`);

for (const station of stationsToProcess) {
  const slug = station.slug;
  const currentImages = imageMap[slug] || [];
  const currentUrls = new Set(currentImages.map(i => i.url));
  const needed = TARGET_IMAGES - currentImages.length;

  if (needed <= 0) continue;

  const newImages = [];

  // Search Commons with various queries
  const queries = [
    `${station.name_jp} ${station.name_en}`,
    `${station.name_en} Tokyo`,
    `${station.name_en} station`,
  ];

  for (const q of queries) {
    if (newImages.length >= needed) break;
    const results = await searchCommons(q, needed + 2);
    for (const img of results) {
      if (newImages.length >= needed) break;
      if (!currentUrls.has(img.url) && !newImages.some(i => i.url === img.url)) {
        img.alt = `${station.name_en} area`;
        newImages.push(img);
      }
    }
    await new Promise(r => setTimeout(r, 200));
  }

  // Try Wikipedia article images
  if (newImages.length < needed) {
    const wikiImgs = await fetchWikipediaImages(`${station.name_en}, Tokyo`);
    for (const img of wikiImgs) {
      if (newImages.length >= needed) break;
      if (!currentUrls.has(img.url) && !newImages.some(i => i.url === img.url)) {
        img.alt = `${station.name_en} area`;
        newImages.push(img);
      }
    }
    await new Promise(r => setTimeout(r, 200));
  }

  if (newImages.length > 0) {
    imageMap[slug] = [...currentImages, ...newImages];
    improved++;
    console.log(`  ${slug}: ${currentImages.length} → ${imageMap[slug].length} images (+${newImages.length})`);
  }
}

console.log(`\nImproved ${improved} stations`);
console.log(`Total images: ${Object.values(imageMap).reduce((sum, imgs) => sum + imgs.length, 0)}`);

writeFileSync(
  new URL('../app/src/data/station-images.json', import.meta.url),
  JSON.stringify(imageMap, null, 2),
  'utf-8'
);

console.log('Written to app/src/data/station-images.json');
