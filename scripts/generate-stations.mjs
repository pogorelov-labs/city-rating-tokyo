/**
 * Generate filtered stations.json for Tokyo Neighborhood Explorer
 * Source: piuccio/open-data-jp-railway-stations
 * Enriched with romaji names and line names
 *
 * HISTORICAL — bootstrapped stations.json in 2026-04. Do not re-run: it would
 * overwrite everything edited in place since (CRTKY-113 slugs, CRTKY-107
 * name_ru, CRTKY-134 name_en, whose misreadings came from this source's romaji).
 */

import { readFileSync, writeFileSync } from 'fs';

const raw = JSON.parse(readFileSync(new URL('../data/raw-stations.json', import.meta.url), 'utf-8'));

// Greater Tokyo prefectures
const TARGET_PREFS = new Set(['13', '14', '11', '12']);

// Manual romaji mapping for stations that lack it
const ROMAJI_MAP = {
  '新宿': 'Shinjuku', '東京': 'Tokyo', '横浜': 'Yokohama', '渋谷': 'Shibuya',
  '千葉': 'Chiba', '大宮': 'Omiya', '池袋': 'Ikebukuro', '上野': 'Ueno',
  '新橋': 'Shimbashi', '北千住': 'Kita-Senju', '品川': 'Shinagawa',
  '大船': 'Ofuna', '成田': 'Narita', '日暮里': 'Nippori',
  '武蔵小杉': 'Musashi-Kosugi', '京成高砂': 'Keisei-Takasago',
  '八王子': 'Hachioji', '吉祥寺': 'Kichijoji', '四ツ谷': 'Yotsuya',
  '国分寺': 'Kokubunji', '代々木上原': 'Yoyogi-Uehara', '中目黒': 'Nakameguro',
  '中野': 'Nakano', '代々木': 'Yoyogi', '目黒': 'Meguro', '飯田橋': 'Iidabashi',
  '秋葉原': 'Akihabara', '恵比寿': 'Ebisu', '有楽町': 'Yurakucho',
  '田町': 'Tamachi', '浜松町': 'Hamamatsucho', '神田': 'Kanda',
  '御茶ノ水': 'Ochanomizu', '水道橋': 'Suidobashi', '九段下': 'Kudanshita',
  '大手町': 'Otemachi', '永田町': 'Nagatacho', '霞ヶ関': 'Kasumigaseki',
  '銀座': 'Ginza', '表参道': 'Omotesando', '六本木': 'Roppongi',
  '麻布十番': 'Azabu-Juban', '広尾': 'Hiroo', '赤坂': 'Akasaka',
  '溜池山王': 'Tameike-Sanno', '虎ノ門': 'Toranomon',
  '日本橋': 'Nihonbashi', '三越前': 'Mitsukoshimae', '人形町': 'Ningyocho',
  '茅場町': 'Kayabacho', '門前仲町': 'Monzen-Nakacho',
  '清澄白河': 'Kiyosumi-Shirakawa', '両国': 'Ryogoku',
  '錦糸町': 'Kinshicho', '押上': 'Oshiage', '浅草': 'Asakusa',
  '蔵前': 'Kuramae', '御徒町': 'Okachimachi', '鶯谷': 'Uguisudani',
  '西日暮里': 'Nishi-Nippori', '田端': 'Tabata', '駒込': 'Komagome',
  '巣鴨': 'Sugamo', '大塚': 'Otsuka', '目白': 'Mejiro',
  '高田馬場': 'Takadanobaba', '新大久保': 'Shin-Okubo',
  '原宿': 'Harajuku', '五反田': 'Gotanda', '大崎': 'Osaki',
  '西大井': 'Nishi-Oi', '大井町': 'Oimachi', '青山一丁目': 'Aoyama-Itchome',
  '赤坂見附': 'Akasaka-Mitsuke', '神保町': 'Jimbocho',
  '後楽園': 'Korakuen', '春日': 'Kasuga', '東池袋': 'Higashi-Ikebukuro',
  '護国寺': 'Gokokuji', '王子': 'Oji', '赤羽': 'Akabane',
  '十条': 'Jujo', '板橋': 'Itabashi',
  '練馬': 'Nerima', '光が丘': 'Hikarigaoka', '石神井公園': 'Shakujii-Koen',
  '小竹向原': 'Kotake-Mukaihara', '和光市': 'Wakoshi',
  '志木': 'Shiki', '朝霞台': 'Asakadai', '川越': 'Kawagoe',
  '所沢': 'Tokorozawa', '浦和': 'Urawa', '川口': 'Kawaguchi',
  '船橋': 'Funabashi', '柏': 'Kashiwa', '松戸': 'Matsudo',
  '市川': 'Ichikawa', '本八幡': 'Motoyawata', '西船橋': 'Nishi-Funabashi',
  '津田沼': 'Tsudanuma', '舞浜': 'Maihama',
  '川崎': 'Kawasaki', '藤沢': 'Fujisawa', '茅ヶ崎': 'Chigasaki',
  '平塚': 'Hiratsuka', '鎌倉': 'Kamakura', '逗子': 'Zushi',
  '溝の口': 'Mizonokuchi', '登戸': 'Noborito', '町田': 'Machida',
  '立川': 'Tachikawa', '三鷹': 'Mitaka', '荻窪': 'Ogikubo',
  '阿佐ヶ谷': 'Asagaya', '高円寺': 'Koenji',
  '下北沢': 'Shimokitazawa', '三軒茶屋': 'Sangenjaya',
  '二子玉川': 'Futako-Tamagawa', '自由が丘': 'Jiyugaoka',
  '田園調布': 'Denenchofu', '蒲田': 'Kamata', '大森': 'Omori',
  '北品川': 'Kita-Shinagawa', '天王洲アイル': 'Tennozu Isle',
  'お台場海浜公園': 'Odaiba-Kaihinkoen', '豊洲': 'Toyosu',
  '月島': 'Tsukishima', '築地': 'Tsukiji', '新富町': 'Shintomicho',
  '勝どき': 'Kachidoki', '汐留': 'Shiodome',
  '東新宿': 'Higashi-Shinjuku', '西新宿五丁目': 'Nishi-Shinjuku-Gochome',
  '中野坂上': 'Nakano-Sakaue', '新中野': 'Shin-Nakano',
  '方南町': 'Honancho', '笹塚': 'Sasazuka', '明大前': 'Meidaimae',
  '下高井戸': 'Shimotakaido', '桜上水': 'Sakurajosui',
  '千歳烏山': 'Chitose-Karasuyama', '調布': 'Chofu',
  '仙川': 'Sengawa', '府中': 'Fuchu', '聖蹟桜ヶ丘': 'Seiseki-Sakuragaoka',
  '多摩センター': 'Tama-Center', '橋本': 'Hashimoto',
  '中目黒': 'Nakameguro', '祐天寺': 'Yutenji', '学芸大学': 'Gakugei-Daigaku',
  '都立大学': 'Toritsu-Daigaku', '武蔵小山': 'Musashi-Koyama',
  '戸越銀座': 'Togoshi-Ginza', '旗の台': 'Hatanodai',
  '馬込': 'Magome', '西馬込': 'Nishi-Magome',
  '浅草橋': 'Asakusabashi', '両国': 'Ryogoku',
  '亀戸': 'Kameido', '新小岩': 'Shin-Koiwa', '小岩': 'Koiwa',
  '葛西': 'Kasai', '西葛西': 'Nishi-Kasai', '東陽町': 'Toyocho',
  '木場': 'Kiba', '南砂町': 'Minami-Sunamachi',
  '西新井': 'Nishiarai', '竹ノ塚': 'Takenotsuka',
  '綾瀬': 'Ayase', '亀有': 'Kameari', '金町': 'Kanamachi',
  '北綾瀬': 'Kita-Ayase', '町屋': 'Machiya',
  '三ノ輪': 'Minowa', '入谷': 'Iriya', '稲荷町': 'Inaricho',
  '新御茶ノ水': 'Shin-Ochanomizu', '小川町': 'Ogawamachi',
  '淡路町': 'Awajicho', '岩本町': 'Iwamotocho',
  '馬喰町': 'Bakurocho', '馬喰横山': 'Bakuro-Yokoyama',
  '東日本橋': 'Higashi-Nihonbashi', '浜町': 'Hamacho',
  '森下': 'Morishita', '菊川': 'Kikukawa', '住吉': 'Sumiyoshi',
  '半蔵門': 'Hanzomon', '市ヶ谷': 'Ichigaya',
  '曙橋': 'Akebonobashi', '牛込神楽坂': 'Ushigome-Kagurazaka',
  '江戸川橋': 'Edogawabashi', '茗荷谷': 'Myogadani',
  '新大塚': 'Shin-Otsuka', '千駄木': 'Sendagi', '根津': 'Nezu',
  '湯島': 'Yushima', '仲御徒町': 'Nakaokachimachi',
  '末広町': 'Suehirocho', '上野広小路': 'Ueno-Hirokoji',
  '京橋': 'Kyobashi', '宝町': 'Takaracho',
  '新宿三丁目': 'Shinjuku-Sanchome', '新宿御苑前': 'Shinjuku-Gyoenmae',
  '四谷三丁目': 'Yotsuya-Sanchome', '麹町': 'Kojimachi',
  '桜田門': 'Sakuradamon', '国会議事堂前': 'Kokkai-Gijidomae',
  '乃木坂': 'Nogizaka', '赤坂': 'Akasaka',
  '外苑前': 'Gaiemmae', '明治神宮前': 'Meiji-Jingumae', '明治神宮前〈原宿〉': 'Harajuku',
  '阿佐ケ谷': 'Asagaya',
  '北参道': 'Kita-Sando', '西早稲田': 'Nishi-Waseda',
  '雑司が谷': 'Zoshigaya', '要町': 'Kanamecho',
  '千川': 'Senkawa', '氷川台': 'Hikawadai',
  '平和台': 'Heiwadai', '地下鉄赤塚': 'Chikatetsu-Akatsuka',
  '地下鉄成増': 'Chikatetsu-Narimasu',
  '白金台': 'Shirokanedai', '白金高輪': 'Shirokane-Takanawa',
  '麻布十番': 'Azabu-Juban', '六本木一丁目': 'Roppongi-Itchome',
  '駒込': 'Komagome', '本駒込': 'Hon-Komagome',
  '東大前': 'Todaimae', '西ヶ原': 'Nishigahara',
  '王子神谷': 'Oji-Kamiya', '志茂': 'Shimo',
  '赤羽岩淵': 'Akabane-Iwabuchi',
  '都庁前': 'Tochomae', '西新宿': 'Nishi-Shinjuku',
  '中井': 'Nakai', '落合南長崎': 'Ochiai-Minami-Nagasaki',
  '新江古田': 'Shin-Egota', '練馬春日町': 'Nerima-Kasugacho',
  '豊島園': 'Toshimaen', '新桜台': 'Shin-Sakuradai',
  '本郷三丁目': 'Hongo-Sanchome', '上野御徒町': 'Ueno-Okachimachi',
  '新御徒町': 'Shin-Okachimachi', '蔵前': 'Kuramae',
  '両国': 'Ryogoku', '森下': 'Morishita',
  '清澄白河': 'Kiyosumi-Shirakawa', '門前仲町': 'Monzen-Nakacho',
  '月島': 'Tsukishima', '勝どき': 'Kachidoki',
  '築地市場': 'Tsukiji-Shijo', '汐留': 'Shiodome',
  '大門': 'Daimon', '赤羽橋': 'Akabanebashi',
  '麻布十番': 'Azabu-Juban', '六本木': 'Roppongi',
  '青山一丁目': 'Aoyama-Itchome', '国立競技場': 'Kokuritsu-Kyogijo',
  '代々木': 'Yoyogi', '新宿': 'Shinjuku',
  '都庁前': 'Tochomae', '落合南長崎': 'Ochiai-Minami-Nagasaki',
  '中野坂上': 'Nakano-Sakaue', '東中野': 'Higashi-Nakano',
  '中野': 'Nakano', '新中野': 'Shin-Nakano',
  '東高円寺': 'Higashi-Koenji', '新高円寺': 'Shin-Koenji',
  '南阿佐ヶ谷': 'Minami-Asagaya',
  '高井戸': 'Takaido', '富士見ヶ丘': 'Fujimigaoka',
  '久我山': 'Kugayama', '三鷹台': 'Mitakadai',
  '井の頭公園': 'Inokashira-Koen',
  '世田谷代田': 'Setagaya-Daita', '梅ヶ丘': 'Umegaoka',
  '豪徳寺': 'Gotokuji', '経堂': 'Kyodo',
  '千歳船橋': 'Chitose-Funabashi', '祖師ヶ谷大蔵': 'Soshigaya-Okura',
  '成城学園前': 'Seijo-Gakuenmae', '喜多見': 'Kitami',
  '狛江': 'Komae', '和泉多摩川': 'Izumi-Tamagawa',
  '向ヶ丘遊園': 'Mukogaoka-Yuen', '生田': 'Ikuta',
  '読売ランド前': 'Yomiuriland-Mae', '百合ヶ丘': 'Yurigaoka',
  '新百合ヶ丘': 'Shin-Yurigaoka',
  '中央林間': 'Chuo-Rinkan', '南町田グランベリーパーク': 'Minami-Machida-Grandberry-Park',
  'つきみ野': 'Tsukimino', 'すずかけ台': 'Suzukakedai',
  '南大沢': 'Minami-Osawa', '京王堀之内': 'Keio-Horinouchi',
  '高幡不動': 'Takahata-Fudo', '分倍河原': 'Bubaigawara',
  '北府中': 'Kita-Fuchu', '武蔵境': 'Musashi-Sakai',
  '東小金井': 'Higashi-Koganei', '武蔵小金井': 'Musashi-Koganei',
  '西国分寺': 'Nishi-Kokubunji',
  '国立': 'Kunitachi', '日野': 'Hino', '豊田': 'Toyota',
  '西八王子': 'Nishi-Hachioji', '高尾': 'Takao',
  '拝島': 'Haijima', '福生': 'Fussa', '羽村': 'Hamura', '青梅': 'Ome',
  '田無': 'Tanashi', '花小金井': 'Hana-Koganei',
  '小平': 'Kodaira', '久米川': 'Kumegawa',
  '東村山': 'Higashi-Murayama', '秋津': 'Akitsu',
  '清瀬': 'Kiyose', 'ひばりヶ丘': 'Hibarigaoka',
  '保谷': 'Hoya', '大泉学園': 'Oizumi-Gakuen',
  '笹目': 'Sasame', '北朝霞': 'Kita-Asaka',
  '新座': 'Niiza', '東所沢': 'Higashi-Tokorozawa',
  '秋津': 'Akitsu', '新秋津': 'Shin-Akitsu',
  '北浦和': 'Kita-Urawa', '南浦和': 'Minami-Urawa',
  '武蔵浦和': 'Musashi-Urawa', '中浦和': 'Naka-Urawa',
  '西浦和': 'Nishi-Urawa', '東浦和': 'Higashi-Urawa',
  '蕨': 'Warabi', '西川口': 'Nishi-Kawaguchi',
  '戸田': 'Toda', '戸田公園': 'Toda-Koen',
  '北戸田': 'Kita-Toda',
  '草加': 'Soka', '越谷': 'Koshigaya', 'せんげん台': 'Sengendai',
  '春日部': 'Kasukabe', '久喜': 'Kuki',
  '越谷レイクタウン': 'Koshigaya-Laketown',
  '南越谷': 'Minami-Koshigaya', '新越谷': 'Shin-Koshigaya',
  '東川口': 'Higashi-Kawaguchi',
  '綾瀬': 'Ayase', '北綾瀬': 'Kita-Ayase',
  '新松戸': 'Shin-Matsudo', '南流山': 'Minami-Nagareyama',
  '流山おおたかの森': 'Nagareyama-Otakanomori',
  '新鎌ヶ谷': 'Shin-Kamagaya', '鎌ヶ谷': 'Kamagaya',
  '東松戸': 'Higashi-Matsudo', '新八柱': 'Shin-Yahashira',
  '北小金': 'Kita-Kogane', '南柏': 'Minami-Kashiwa',
  '北柏': 'Kita-Kashiwa', '我孫子': 'Abiko',
  '取手': 'Toride', '天王台': 'Tennodai',
  '幕張': 'Makuhari', '海浜幕張': 'Kaihin-Makuhari',
  '稲毛': 'Inage', '検見川浜': 'Kemigawa-Hama',
  '蘇我': 'Soga', '鎌取': 'Kamatori',
  '新浦安': 'Shin-Urayasu', '浦安': 'Urayasu',
  '行徳': 'Gyotoku', '妙典': 'Myoden',
  '新鶴見': 'Shin-Tsurumi', '鶴見': 'Tsurumi',
  '新子安': 'Shin-Koyasu', '東神奈川': 'Higashi-Kanagawa',
  '菊名': 'Kikuna', '新横浜': 'Shin-Yokohama',
  '綱島': 'Tsunashima', '日吉': 'Hiyoshi',
  '元住吉': 'Motosumiyoshi', '武蔵新城': 'Musashi-Shinjo',
  '武蔵溝ノ口': 'Musashi-Mizonokuchi', '二俣川': 'Futamatagawa',
  '上大岡': 'Kami-Ooka', '金沢文庫': 'Kanazawa-Bunko',
  '金沢八景': 'Kanazawa-Hakkei', '逗子・葉山': 'Zushi-Hayama',
  '戸塚': 'Totsuka', '本郷台': 'Hongodai',
  '港南台': 'Konandai', '洋光台': 'Yokodai',
  '桜木町': 'Sakuragicho', '関内': 'Kannai',
  '石川町': 'Ishikawacho', '元町・中華街': 'Motomachi-Chukagai',
};

function slugify(name) {
  return name.toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

// Filter stations in Greater Tokyo
const tokyoStations = raw.filter(s => TARGET_PREFS.has(s.prefecture));

console.log(`Greater Tokyo stations (raw): ${tokyoStations.length}`);

const stations = [];
const seen = new Set();

for (const group of tokyoStations) {
  const kanji = group.name_kanji;
  const romaji = ROMAJI_MAP[kanji] || group.name_romaji || '';

  if (!romaji) continue; // Skip stations without romaji mapping

  const slug = slugify(romaji);
  if (seen.has(slug)) continue;

  const lineCount = group.stations ? group.stations.length : 1;
  const firstStation = group.stations?.[0];
  if (!firstStation || !firstStation.lat || !firstStation.lon) continue;

  const isTokyo = group.prefecture === '13';

  // Include: Tokyo stations with 2+ lines, or any mapped station
  if (!isTokyo && lineCount < 3) continue;
  if (isTokyo && lineCount < 2 && !ROMAJI_MAP[kanji]) continue;

  seen.add(slug);

  stations.push({
    slug,
    name_en: romaji,
    name_jp: kanji,
    lat: firstStation.lat,
    lng: firstStation.lon,
    lines: group.stations.map(s => s.ekidata_line_id),
    line_count: lineCount,
    prefecture: group.prefecture,
    ratings: null,  // To be filled by AI research
    rent_avg: null, // To be filled by Suumo scraper
    transit_minutes: null, // To be filled by AI research
  });
}

stations.sort((a, b) => b.line_count - a.line_count || a.name_en.localeCompare(b.name_en));

console.log(`Filtered stations: ${stations.length}`);
console.log(`Tokyo (13): ${stations.filter(s => s.prefecture === '13').length}`);
console.log(`Kanagawa (14): ${stations.filter(s => s.prefecture === '14').length}`);
console.log(`Saitama (11): ${stations.filter(s => s.prefecture === '11').length}`);
console.log(`Chiba (12): ${stations.filter(s => s.prefecture === '12').length}`);

console.log('\nTop 30 most connected:');
stations.slice(0, 30).forEach((s, i) => {
  console.log(`  ${i+1}. ${s.name_en} (${s.name_jp}) - ${s.line_count} lines`);
});

writeFileSync(
  new URL('../data/stations.json', import.meta.url),
  JSON.stringify(stations, null, 2),
  'utf-8'
);

console.log(`\nWritten to data/stations.json (${stations.length} stations)`);
