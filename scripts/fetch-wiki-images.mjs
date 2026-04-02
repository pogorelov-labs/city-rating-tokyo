/**
 * Fetch station images from Wikidata SPARQL + Wikipedia REST API
 * Outputs: data/station-images.json
 */

import { readFileSync, writeFileSync } from 'fs';
import { createHash } from 'crypto';

const stations = JSON.parse(readFileSync(new URL('../app/src/data/stations.json', import.meta.url), 'utf-8'));

// Step 1: Wikidata SPARQL — get all Tokyo railway station images
const sparql = `
SELECT ?stationLabel ?image WHERE {
  ?station wdt:P31/wdt:P279* wd:Q55488 .
  ?station wdt:P17 wd:Q17 .
  ?station wdt:P18 ?image .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,ja" . }
}
LIMIT 2000
`;

console.log('Fetching Wikidata SPARQL...');
const sparqlUrl = `https://query.wikidata.org/sparql?format=json&query=${encodeURIComponent(sparql)}`;
const sparqlRes = await fetch(sparqlUrl, {
  headers: { 'User-Agent': 'CityRatingTokyo/1.0 (https://github.com/ruspg/city-rating-tokyo)' }
});
const sparqlData = await sparqlRes.json();

// Build lookup: station name -> image URLs
const wikiImages = {};
for (const binding of sparqlData.results.bindings) {
  const name = binding.stationLabel.value;
  const imageUrl = binding.image.value;
  if (!wikiImages[name]) wikiImages[name] = [];
  wikiImages[name].push(imageUrl);
}
console.log(`Wikidata: ${Object.keys(wikiImages).length} stations with images`);

// Convert Special:FilePath URL to direct Commons URL
function commonsUrl(filePathUrl) {
  // Input: http://commons.wikimedia.org/wiki/Special:FilePath/Filename.jpg
  // Output: https://upload.wikimedia.org/wikipedia/commons/a/ab/Filename.jpg
  const filename = decodeURIComponent(filePathUrl.split('/').pop());
  const md5 = createHash('md5').update(filename).digest('hex');
  const a = md5[0];
  const ab = md5.slice(0, 2);
  return `https://upload.wikimedia.org/wikipedia/commons/${a}/${ab}/${encodeURIComponent(filename)}`;
}

function commonsThumbUrl(filePathUrl, width = 640) {
  const filename = decodeURIComponent(filePathUrl.split('/').pop());
  const md5 = createHash('md5').update(filename).digest('hex');
  const a = md5[0];
  const ab = md5.slice(0, 2);
  const encoded = encodeURIComponent(filename);
  return `https://upload.wikimedia.org/wikipedia/commons/thumb/${a}/${ab}/${encoded}/${width}px-${encoded}`;
}

// Step 2: Try Wikipedia REST API for neighborhood pages (better images)
async function fetchWikipediaImage(pageName) {
  try {
    const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(pageName)}`;
    const res = await fetch(url, {
      headers: { 'User-Agent': 'CityRatingTokyo/1.0' }
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.originalimage?.source) {
      return {
        url: data.originalimage.source,
        thumb: data.thumbnail?.source || data.originalimage.source,
        title: data.title,
      };
    }
    return null;
  } catch {
    return null;
  }
}

// Step 3: For each station, find images
const imageMap = {};
let found = 0;
let missed = 0;

for (const station of stations.filter(s => s.ratings !== null || s.line_count >= 3)) {
  const slug = station.slug;
  const nameJp = station.name_jp;
  const nameEn = station.name_en;
  const images = [];

  // Try Wikidata matches
  const wikiKeys = [
    `${nameEn} Station`,
    `${nameEn}`,
    `${nameJp}駅`,
    `${nameJp}`,
  ];

  for (const key of wikiKeys) {
    if (wikiImages[key]) {
      for (const imgUrl of wikiImages[key].slice(0, 3)) {
        images.push({
          url: commonsUrl(imgUrl),
          alt: `${nameEn} station area`,
          attribution: 'Wikimedia Commons',
        });
      }
      break;
    }
  }

  // Try Wikipedia REST API for neighborhood image
  if (images.length < 3) {
    const wikiImg = await fetchWikipediaImage(nameEn);
    if (wikiImg && !images.some(i => i.url === wikiImg.url)) {
      images.push({
        url: wikiImg.thumb,
        alt: `${nameEn} - ${wikiImg.title}`,
        attribution: 'Wikipedia',
      });
    }

    // Also try with "Station" suffix
    if (images.length < 2) {
      const wikiImg2 = await fetchWikipediaImage(`${nameEn} Station`);
      if (wikiImg2 && !images.some(i => i.url === wikiImg2.url)) {
        images.push({
          url: wikiImg2.thumb,
          alt: `${nameEn} Station`,
          attribution: 'Wikipedia',
        });
      }
    }
  }

  if (images.length > 0) {
    imageMap[slug] = images.slice(0, 4); // Max 4 images per station
    found++;
  } else {
    missed++;
  }

  // Rate limiting
  await new Promise(r => setTimeout(r, 100));
}

console.log(`\nResults: ${found} stations with images, ${missed} without`);
console.log(`Total images: ${Object.values(imageMap).reduce((sum, imgs) => sum + imgs.length, 0)}`);

writeFileSync(
  new URL('../app/src/data/station-images.json', import.meta.url),
  JSON.stringify(imageMap, null, 2),
  'utf-8'
);

console.log('Written to app/src/data/station-images.json');
