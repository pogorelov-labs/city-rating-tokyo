/**
 * Batch image fetcher — saves after every station.
 * Uses Wikimedia Commons search only (faster than Wikipedia API).
 */

import { readFileSync, writeFileSync } from 'fs';
import { createHash } from 'crypto';

const stations = JSON.parse(readFileSync(new URL('../app/src/data/stations.json', import.meta.url), 'utf-8'));
const imagePath = new URL('../app/src/data/station-images.json', import.meta.url);
let imageMap = JSON.parse(readFileSync(imagePath, 'utf-8'));

const UA = 'CityRatingTokyo/1.0 (https://github.com/ruspg/city-rating-tokyo)';

async function searchCommons(query, limit = 4) {
  const results = [];
  try {
    const url = `https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(query)}&srnamespace=6&srlimit=${limit}&format=json`;
    const res = await fetch(url, { headers: { 'User-Agent': UA }, signal: AbortSignal.timeout(10000) });
    const data = await res.json();
    if (!data.query?.search) return results;
    for (const item of data.query.search) {
      const title = item.title;
      if (!/\.(jpg|jpeg|png)$/i.test(title)) continue;
      if (/logo|icon|map|diagram|symbol|route|sign|banner|flag|commons/i.test(title)) continue;
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
    // timeout or network error — skip
  }
  return results;
}

const toProcess = stations.filter(s => !imageMap[s.slug] || imageMap[s.slug].length === 0);
console.log(`${toProcess.length} stations need images`);

let done = 0;
let saved = 0;

for (const station of toProcess) {
  const images = [];
  const seen = new Set();

  // Single query with Japanese name — most effective
  const results = await searchCommons(`${station.name_jp} 駅`, 6);
  for (const img of results) {
    if (!seen.has(img.url)) {
      seen.add(img.url);
      img.alt = `${station.name_en} area`;
      images.push(img);
    }
  }

  if (images.length < 2) {
    // Fallback: search with English name
    const results2 = await searchCommons(`${station.name_en} station Japan`, 4);
    for (const img of results2) {
      if (!seen.has(img.url)) {
        seen.add(img.url);
        img.alt = `${station.name_en} area`;
        images.push(img);
      }
    }
  }

  if (images.length > 0) {
    imageMap[station.slug] = images;
    saved++;
  }

  done++;
  if (done % 50 === 0 || done === toProcess.length) {
    // Save periodically
    writeFileSync(imagePath, JSON.stringify(imageMap, null, 2), 'utf-8');
    console.log(`Progress: ${done}/${toProcess.length} processed, ${saved} with images`);
  }

  // Small delay to be polite
  await new Promise(r => setTimeout(r, 150));
}

// Final save
writeFileSync(imagePath, JSON.stringify(imageMap, null, 2), 'utf-8');
console.log(`\nDone! ${saved}/${toProcess.length} stations got images`);
console.log(`Total stations with images: ${Object.values(imageMap).filter(v => v.length > 0).length}`);
