/**
 * Build complete station -> ward/city mapping for Suumo scraper.
 * Uses station coordinates to assign the correct Suumo area code.
 *
 * Output: scripts/station-area-codes.json
 */

import { readFileSync, writeFileSync } from 'fs';

const stations = JSON.parse(readFileSync(new URL('../app/src/data/stations.json', import.meta.url), 'utf-8'));

// Tokyo 23 Special Wards - approximate bounding boxes (lat, lng center + rough radius)
// Suumo codes: 131XX
const TOKYO_WARDS = {
  chiyoda:    { code: '13101', lat: 35.694, lng: 139.754, name: '千代田区' },
  chuo:       { code: '13102', lat: 35.671, lng: 139.772, name: '中央区' },
  minato:     { code: '13103', lat: 35.658, lng: 139.751, name: '港区' },
  shinjuku:   { code: '13104', lat: 35.694, lng: 139.703, name: '新宿区' },
  bunkyo:     { code: '13105', lat: 35.718, lng: 139.752, name: '文京区' },
  taito:      { code: '13106', lat: 35.713, lng: 139.780, name: '台東区' },
  sumida:     { code: '13107', lat: 35.711, lng: 139.802, name: '墨田区' },
  koto:       { code: '13108', lat: 35.672, lng: 139.817, name: '江東区' },
  shinagawa:  { code: '13109', lat: 35.609, lng: 139.730, name: '品川区' },
  meguro:     { code: '13110', lat: 35.634, lng: 139.698, name: '目黒区' },
  ota:        { code: '13111', lat: 35.561, lng: 139.716, name: '大田区' },
  setagaya:   { code: '13112', lat: 35.646, lng: 139.653, name: '世田谷区' },
  shibuya:    { code: '13113', lat: 35.664, lng: 139.698, name: '渋谷区' },
  nakano:     { code: '13114', lat: 35.708, lng: 139.664, name: '中野区' },
  suginami:   { code: '13115', lat: 35.699, lng: 139.637, name: '杉並区' },
  toshima:    { code: '13116', lat: 35.726, lng: 139.716, name: '豊島区' },
  kita:       { code: '13117', lat: 35.753, lng: 139.734, name: '北区' },
  arakawa:    { code: '13118', lat: 35.736, lng: 139.783, name: '荒川区' },
  itabashi:   { code: '13119', lat: 35.752, lng: 139.680, name: '板橋区' },
  nerima:     { code: '13120', lat: 35.736, lng: 139.652, name: '練馬区' },
  adachi:     { code: '13121', lat: 35.776, lng: 139.805, name: '足立区' },
  katsushika: { code: '13122', lat: 35.743, lng: 139.847, name: '葛飾区' },
  edogawa:    { code: '13123', lat: 35.707, lng: 139.868, name: '江戸川区' },
};

// Tokyo Tama-district cities (outside 23 wards)
const TAMA_CITIES = {
  hachioji:     { code: '13201', lat: 35.666, lng: 139.316, name: '八王子市' },
  tachikawa:    { code: '13202', lat: 35.714, lng: 139.413, name: '立川市' },
  musashino:    { code: '13203', lat: 35.717, lng: 139.566, name: '武蔵野市' }, // Kichijoji
  mitaka:       { code: '13204', lat: 35.684, lng: 139.560, name: '三鷹市' },
  ome:          { code: '13205', lat: 35.788, lng: 139.276, name: '青梅市' },
  fuchu:        { code: '13206', lat: 35.669, lng: 139.478, name: '府中市' },
  chofu:        { code: '13208', lat: 35.652, lng: 139.541, name: '調布市' },
  machida:      { code: '13209', lat: 35.549, lng: 139.446, name: '町田市' },
  koganei:      { code: '13210', lat: 35.700, lng: 139.503, name: '小金井市' },
  kodaira:      { code: '13211', lat: 35.729, lng: 139.477, name: '小平市' },
  hino:         { code: '13212', lat: 35.664, lng: 139.395, name: '日野市' },
  higashimurayama: { code: '13213', lat: 35.755, lng: 139.469, name: '東村山市' },
  kokubunji:    { code: '13214', lat: 35.710, lng: 139.462, name: '国分寺市' },
  kunitachi:    { code: '13215', lat: 35.684, lng: 139.442, name: '国立市' },
  fussa:        { code: '13218', lat: 35.739, lng: 139.328, name: '福生市' },
  komae:        { code: '13219', lat: 35.633, lng: 139.578, name: '狛江市' },
  higashiyamato: { code: '13220', lat: 35.746, lng: 139.427, name: '東大和市' },
  kiyose:       { code: '13221', lat: 35.786, lng: 139.527, name: '清瀬市' },
  higashikurume: { code: '13222', lat: 35.758, lng: 139.530, name: '東久留米市' },
  nishitokyo:   { code: '13229', lat: 35.726, lng: 139.539, name: '西東京市' }, // Tanashi, Hoya
  hamura:       { code: '13227', lat: 35.769, lng: 139.312, name: '羽村市' },
  akiruno:      { code: '13228', lat: 35.729, lng: 139.294, name: 'あきる野市' },
  tama:         { code: '13224', lat: 35.637, lng: 139.446, name: '多摩市' },
};

// Kanagawa cities
const KANAGAWA_CITIES = {
  yokohama_nishi:   { code: '14101', lat: 35.466, lng: 139.622, name: '横浜市西区' },
  yokohama_naka:    { code: '14104', lat: 35.444, lng: 139.643, name: '横浜市中区' },
  yokohama_kanagawa:{ code: '14102', lat: 35.480, lng: 139.632, name: '横浜市神奈川区' },
  yokohama_tsurumi: { code: '14101', lat: 35.505, lng: 139.674, name: '横浜市鶴見区' },
  yokohama_kohoku:  { code: '14109', lat: 35.531, lng: 139.633, name: '横浜市港北区' },
  yokohama_totsuka: { code: '14110', lat: 35.399, lng: 139.535, name: '横浜市戸塚区' },
  yokohama_kanazawa:{ code: '14108', lat: 35.342, lng: 139.623, name: '横浜市金沢区' },
  kawasaki_kawasaki: { code: '14131', lat: 35.530, lng: 139.703, name: '川崎市川崎区' },
  kawasaki_nakahara: { code: '14133', lat: 35.572, lng: 139.660, name: '川崎市中原区' },
  kawasaki_takatsu:  { code: '14134', lat: 35.601, lng: 139.615, name: '川崎市高津区' },
  fujisawa:     { code: '14205', lat: 35.341, lng: 139.487, name: '藤沢市' },
  kamakura:     { code: '14204', lat: 35.319, lng: 139.546, name: '鎌倉市' },
  sagamihara:   { code: '14150', lat: 35.571, lng: 139.373, name: '相模原市' },
};

// Saitama cities
const SAITAMA_CITIES = {
  saitama_omiya:  { code: '11103', lat: 35.906, lng: 139.631, name: 'さいたま市大宮区' },
  saitama_urawa:  { code: '11107', lat: 35.858, lng: 139.657, name: 'さいたま市浦和区' },
  kawagoe:        { code: '11201', lat: 35.925, lng: 139.486, name: '川越市' },
  kawaguchi:      { code: '11203', lat: 35.808, lng: 139.724, name: '川口市' },
  tokorozawa:     { code: '11208', lat: 35.799, lng: 139.469, name: '所沢市' },
  warabi:         { code: '11223', lat: 35.826, lng: 139.679, name: '蕨市' },
  wako:           { code: '11229', lat: 35.781, lng: 139.606, name: '和光市' },
};

// Chiba cities
const CHIBA_CITIES = {
  chiba:          { code: '12101', lat: 35.607, lng: 140.106, name: '千葉市' },
  funabashi:      { code: '12204', lat: 35.695, lng: 139.983, name: '船橋市' },
  matsudo:        { code: '12207', lat: 35.788, lng: 139.903, name: '松戸市' },
  kashiwa:        { code: '12217', lat: 35.868, lng: 139.971, name: '柏市' },
  ichikawa:       { code: '12203', lat: 35.732, lng: 139.931, name: '市川市' },
  narita:         { code: '12211', lat: 35.776, lng: 140.318, name: '成田市' },
  kamagaya:       { code: '12224', lat: 35.777, lng: 140.001, name: '鎌ケ谷市' },
  abiko:          { code: '12222', lat: 35.864, lng: 140.028, name: '我孫子市' },
  nagareyama:     { code: '12220', lat: 35.856, lng: 139.903, name: '流山市' },
  urayasu:        { code: '12227', lat: 35.654, lng: 139.902, name: '浦安市' },
};

// Distance function (simple euclidean on lat/lng — good enough for ward assignment)
function dist(lat1, lng1, lat2, lng2) {
  return Math.sqrt((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2);
}

// Find nearest area for a station
function findNearestArea(lat, lng, pref) {
  let allAreas = {};

  if (pref === '13') {
    allAreas = { ...TOKYO_WARDS, ...TAMA_CITIES };
  } else if (pref === '14') {
    allAreas = KANAGAWA_CITIES;
  } else if (pref === '11') {
    allAreas = SAITAMA_CITIES;
  } else if (pref === '12') {
    allAreas = CHIBA_CITIES;
  }

  let bestKey = null;
  let bestDist = Infinity;

  for (const [key, area] of Object.entries(allAreas)) {
    const d = dist(lat, lng, area.lat, area.lng);
    if (d < bestDist) {
      bestDist = d;
      bestKey = key;
    }
  }

  return bestKey ? { areaKey: bestKey, ...allAreas[bestKey] } : null;
}

// Build mapping
const stationAreaMap = {};
const areaCounts = {};

for (const station of stations) {
  const area = findNearestArea(station.lat, station.lng, station.prefecture);
  if (area) {
    stationAreaMap[station.slug] = {
      area_key: area.areaKey,
      area_code: area.code,
      area_name: area.name,
    };
    areaCounts[area.areaKey] = (areaCounts[area.areaKey] || 0) + 1;
  }
}

console.log(`Mapped ${Object.keys(stationAreaMap).length} / ${stations.length} stations`);
console.log(`\nAreas used: ${Object.keys(areaCounts).length}`);

// Show distribution
const sorted = Object.entries(areaCounts).sort((a, b) => b[1] - a[1]);
console.log('\nTop areas:');
sorted.slice(0, 15).forEach(([k, v]) => console.log(`  ${k}: ${v} stations`));

// Unique codes we need to scrape
const uniqueCodes = new Set(Object.values(stationAreaMap).map(v => v.area_code));
console.log(`\nUnique Suumo area codes to scrape: ${uniqueCodes.size}`);

// Save
writeFileSync(
  new URL('./station-area-codes.json', import.meta.url),
  JSON.stringify({ stationAreaMap, areaCounts }, null, 2),
  'utf-8'
);

console.log('\nSaved to scripts/station-area-codes.json');
