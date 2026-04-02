import { StationRatings, TransitMinutes, RentAvg } from '@/lib/types';

interface DemoData {
  ratings: StationRatings;
  transit_minutes: TransitMinutes;
  rent_avg: RentAvg;
  description?: {
    atmosphere: string;
    landmarks: string;
    food: string;
    nightlife: string;
  };
}

// Station data from AI research - 50 stations
export const DEMO_RATINGS: Record<string, DemoData> = {
  // === Original 20 stations ===
  shinjuku: {
    ratings: { food: 9, nightlife: 10, transport: 10, rent: 3, safety: 6, green: 5, gym_sports: 8, vibe: 8, crowd: 2 },
    transit_minutes: { shibuya: 5, shinjuku: 0, tokyo: 15, ikebukuro: 8, shinagawa: 18 },
    rent_avg: { '1k_1ldk': 135000, '2ldk': 250000, source: 'estimate', updated: '2026-04' },
  },
  shibuya: {
    ratings: { food: 9, nightlife: 9, transport: 10, rent: 3, safety: 7, green: 6, gym_sports: 8, vibe: 9, crowd: 2 },
    transit_minutes: { shibuya: 0, shinjuku: 5, tokyo: 25, ikebukuro: 20, shinagawa: 15 },
    rent_avg: { '1k_1ldk': 140000, '2ldk': 260000, source: 'estimate', updated: '2026-04' },
  },
  ikebukuro: {
    ratings: { food: 8, nightlife: 8, transport: 9, rent: 4, safety: 6, green: 4, gym_sports: 7, vibe: 7, crowd: 3 },
    transit_minutes: { shibuya: 20, shinjuku: 8, tokyo: 20, ikebukuro: 0, shinagawa: 25 },
    rent_avg: { '1k_1ldk': 110000, '2ldk': 200000, source: 'estimate', updated: '2026-04' },
  },
  tokyo: {
    ratings: { food: 7, nightlife: 5, transport: 10, rent: 2, safety: 9, green: 5, gym_sports: 6, vibe: 6, crowd: 3 },
    transit_minutes: { shibuya: 25, shinjuku: 15, tokyo: 0, ikebukuro: 20, shinagawa: 10 },
    rent_avg: { '1k_1ldk': 155000, '2ldk': 300000, source: 'estimate', updated: '2026-04' },
  },
  ueno: {
    ratings: { food: 8, nightlife: 6, transport: 8, rent: 5, safety: 7, green: 9, gym_sports: 5, vibe: 8, crowd: 4 },
    transit_minutes: { shibuya: 30, shinjuku: 25, tokyo: 8, ikebukuro: 18, shinagawa: 18 },
    rent_avg: { '1k_1ldk': 105000, '2ldk': 185000, source: 'estimate', updated: '2026-04' },
  },
  akihabara: {
    ratings: { food: 7, nightlife: 7, transport: 8, rent: 4, safety: 7, green: 3, gym_sports: 5, vibe: 9, crowd: 3 },
    transit_minutes: { shibuya: 28, shinjuku: 20, tokyo: 5, ikebukuro: 22, shinagawa: 15 },
    rent_avg: { '1k_1ldk': 120000, '2ldk': 210000, source: 'estimate', updated: '2026-04' },
  },
  shinagawa: {
    ratings: { food: 6, nightlife: 5, transport: 9, rent: 3, safety: 8, green: 5, gym_sports: 6, vibe: 5, crowd: 5 },
    transit_minutes: { shibuya: 15, shinjuku: 18, tokyo: 10, ikebukuro: 25, shinagawa: 0 },
    rent_avg: { '1k_1ldk': 145000, '2ldk': 270000, source: 'estimate', updated: '2026-04' },
  },
  nakano: {
    ratings: { food: 8, nightlife: 7, transport: 7, rent: 6, safety: 8, green: 6, gym_sports: 7, vibe: 8, crowd: 6 },
    transit_minutes: { shibuya: 15, shinjuku: 5, tokyo: 20, ikebukuro: 15, shinagawa: 25 },
    rent_avg: { '1k_1ldk': 95000, '2ldk': 160000, source: 'estimate', updated: '2026-04' },
  },
  kichijoji: {
    ratings: { food: 9, nightlife: 7, transport: 6, rent: 5, safety: 9, green: 10, gym_sports: 8, vibe: 10, crowd: 5 },
    transit_minutes: { shibuya: 20, shinjuku: 15, tokyo: 30, ikebukuro: 25, shinagawa: 35 },
    rent_avg: { '1k_1ldk': 100000, '2ldk': 170000, source: 'estimate', updated: '2026-04' },
  },
  shimokitazawa: {
    ratings: { food: 9, nightlife: 8, transport: 7, rent: 5, safety: 8, green: 6, gym_sports: 6, vibe: 10, crowd: 5 },
    transit_minutes: { shibuya: 5, shinjuku: 10, tokyo: 25, ikebukuro: 20, shinagawa: 20 },
    rent_avg: { '1k_1ldk': 105000, '2ldk': 175000, source: 'estimate', updated: '2026-04' },
  },
  ebisu: {
    ratings: { food: 9, nightlife: 8, transport: 8, rent: 3, safety: 8, green: 6, gym_sports: 7, vibe: 9, crowd: 5 },
    transit_minutes: { shibuya: 3, shinjuku: 8, tokyo: 22, ikebukuro: 18, shinagawa: 12 },
    rent_avg: { '1k_1ldk': 145000, '2ldk': 270000, source: 'estimate', updated: '2026-04' },
  },
  meguro: {
    ratings: { food: 8, nightlife: 6, transport: 7, rent: 4, safety: 9, green: 7, gym_sports: 7, vibe: 8, crowd: 6 },
    transit_minutes: { shibuya: 5, shinjuku: 12, tokyo: 25, ikebukuro: 20, shinagawa: 10 },
    rent_avg: { '1k_1ldk': 125000, '2ldk': 220000, source: 'estimate', updated: '2026-04' },
  },
  koenji: {
    ratings: { food: 8, nightlife: 8, transport: 6, rent: 6, safety: 8, green: 5, gym_sports: 6, vibe: 9, crowd: 6 },
    transit_minutes: { shibuya: 18, shinjuku: 8, tokyo: 22, ikebukuro: 18, shinagawa: 28 },
    rent_avg: { '1k_1ldk': 88000, '2ldk': 145000, source: 'estimate', updated: '2026-04' },
  },
  sangenjaya: {
    ratings: { food: 8, nightlife: 7, transport: 6, rent: 5, safety: 8, green: 5, gym_sports: 6, vibe: 8, crowd: 6 },
    transit_minutes: { shibuya: 5, shinjuku: 15, tokyo: 30, ikebukuro: 25, shinagawa: 20 },
    rent_avg: { '1k_1ldk': 100000, '2ldk': 170000, source: 'estimate', updated: '2026-04' },
  },
  nakameguro: {
    ratings: { food: 9, nightlife: 7, transport: 7, rent: 4, safety: 9, green: 8, gym_sports: 7, vibe: 9, crowd: 5 },
    transit_minutes: { shibuya: 4, shinjuku: 12, tokyo: 25, ikebukuro: 22, shinagawa: 15 },
    rent_avg: { '1k_1ldk': 135000, '2ldk': 240000, source: 'estimate', updated: '2026-04' },
  },
  asakusa: {
    ratings: { food: 9, nightlife: 6, transport: 6, rent: 6, safety: 7, green: 5, gym_sports: 4, vibe: 9, crowd: 3 },
    transit_minutes: { shibuya: 30, shinjuku: 28, tokyo: 15, ikebukuro: 25, shinagawa: 25 },
    rent_avg: { '1k_1ldk': 95000, '2ldk': 155000, source: 'estimate', updated: '2026-04' },
  },
  roppongi: {
    ratings: { food: 8, nightlife: 10, transport: 7, rent: 2, safety: 5, green: 5, gym_sports: 8, vibe: 7, crowd: 3 },
    transit_minutes: { shibuya: 10, shinjuku: 15, tokyo: 18, ikebukuro: 25, shinagawa: 15 },
    rent_avg: { '1k_1ldk': 165000, '2ldk': 320000, source: 'estimate', updated: '2026-04' },
  },
  ginza: {
    ratings: { food: 10, nightlife: 8, transport: 9, rent: 2, safety: 9, green: 4, gym_sports: 7, vibe: 8, crowd: 3 },
    transit_minutes: { shibuya: 15, shinjuku: 18, tokyo: 5, ikebukuro: 22, shinagawa: 12 },
    rent_avg: { '1k_1ldk': 170000, '2ldk': 350000, source: 'estimate', updated: '2026-04' },
  },
  jiyugaoka: {
    ratings: { food: 8, nightlife: 5, transport: 6, rent: 4, safety: 9, green: 7, gym_sports: 7, vibe: 9, crowd: 6 },
    transit_minutes: { shibuya: 10, shinjuku: 20, tokyo: 30, ikebukuro: 28, shinagawa: 20 },
    rent_avg: { '1k_1ldk': 115000, '2ldk': 200000, source: 'estimate', updated: '2026-04' },
  },
  nippori: {
    ratings: { food: 6, nightlife: 3, transport: 8, rent: 7, safety: 8, green: 6, gym_sports: 5, vibe: 7, crowd: 7 },
    transit_minutes: { shibuya: 32, shinjuku: 27, tokyo: 18, ikebukuro: 15, shinagawa: 35 },
    rent_avg: { '1k_1ldk': 88000, '2ldk': 140000, source: 'estimate', updated: '2026-04' },
  },
  // === Batch 1: Yamanote extended ===
  harajuku: {
    ratings: { food: 8, nightlife: 5, transport: 9, rent: 2, safety: 8, green: 9, gym_sports: 7, vibe: 9, crowd: 1 },
    transit_minutes: { shibuya: 2, shinjuku: 5, tokyo: 25, ikebukuro: 20, shinagawa: 15 },
    rent_avg: { '1k_1ldk': 155000, '2ldk': 240000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Харадзюку — это вечный карнавал: уличная мода, косплей, визг подростков на Такэсита-дори и полная тишина в глубине района.", landmarks: "Такэсита-дори, парк Ёёги, святилище Мэйдзи, бутики Омотэсандо.", food: "Крепы с клубникой — местная классика. Отличные кафе и бистро в переулках Урахара.", nightlife: "Ночная жизнь скромная — район не про клубы. Несколько баров на Омотэсандо." },
  },
  yoyogi: {
    ratings: { food: 7, nightlife: 5, transport: 9, rent: 4, safety: 9, green: 10, gym_sports: 8, vibe: 7, crowd: 5 },
    transit_minutes: { shibuya: 5, shinjuku: 3, tokyo: 20, ikebukuro: 15, shinagawa: 18 },
    rent_avg: { '1k_1ldk': 130000, '2ldk': 200000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Ёёги — тихий и немного недооценённый сосед Синдзюку, с расслабленной атмосферой.", landmarks: "Парк Ёёги (54 га), Олимпийский стадион, Ёёги-Кёгидзё.", food: "Много этнической кухни — эфиопские и индийские заведения. До Синдзюку одна остановка.", nightlife: "Не ночной район — камерные бары с живой музыкой до полуночи." },
  },
  takadanobaba: {
    ratings: { food: 8, nightlife: 7, transport: 9, rent: 6, safety: 7, green: 4, gym_sports: 6, vibe: 7, crowd: 3 },
    transit_minutes: { shibuya: 18, shinjuku: 7, tokyo: 25, ikebukuro: 10, shinagawa: 30 },
    rent_avg: { '1k_1ldk': 105000, '2ldk': 165000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Студенческий район с характером: Университет Васэда, дешёвая еда, энергичная атмосфера.", landmarks: "Университет Васэда, музей Астробоя, улица Бабадори.", food: "Рай дешёвой еды: рамэн, гёдза, корейская и вьетнамская кухня за 500-900 иен.", nightlife: "Студенческая ночная жизнь: дешёвые изакая, хайбол по 300 иен, караоке до утра." },
  },
  sugamo: {
    ratings: { food: 7, nightlife: 2, transport: 8, rent: 7, safety: 10, green: 6, gym_sports: 5, vibe: 6, crowd: 5 },
    transit_minutes: { shibuya: 25, shinjuku: 20, tokyo: 25, ikebukuro: 8, shinagawa: 40 },
    rent_avg: { '1k_1ldk': 95000, '2ldk': 150000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "«Харадзюку для бабушек»: торговая улица Дзидзо-дори, сладости, красное бельё на удачу.", landmarks: "Храм Кога-нэй-дзи, торговая улица Дзидзо-дори (800м).", food: "Традиционные сладости — данго, сэмбэй, моти. Большие порции, разумные цены.", nightlife: "Ночной жизни нет — район засыпает около 20:00." },
  },
  'nishi-nippori': {
    ratings: { food: 6, nightlife: 3, transport: 8, rent: 8, safety: 8, green: 6, gym_sports: 5, vibe: 6, crowd: 7 },
    transit_minutes: { shibuya: 30, shinjuku: 25, tokyo: 20, ikebukuro: 15, shinagawa: 40 },
    rent_avg: { '1k_1ldk': 85000, '2ldk': 135000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Тихий жилой район на Яманотэ с отличным транспортом и доступной арендой.", landmarks: "Кладбище Янака, торговая улица Янака Гиндза.", food: "Добротные рамэн и соба, домашние кофейни в старых деревянных домах в Янаке.", nightlife: "Минимальная — несколько номия для работяг." },
  },
  gotanda: {
    ratings: { food: 8, nightlife: 7, transport: 8, rent: 6, safety: 7, green: 4, gym_sports: 7, vibe: 7, crowd: 4 },
    transit_minutes: { shibuya: 8, shinjuku: 20, tokyo: 25, ikebukuro: 35, shinagawa: 7 },
    rent_avg: { '1k_1ldk': 115000, '2ldk': 180000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Деловой и живой район: днём офисы, вечером оживлённые бары и корейские рестораны.", landmarks: "Набережная реки Мэгуро, корейский квартал.", food: "Корейская кухня — главная фишка: самгёпсаль, пулькоги, холодная лапша.", nightlife: "Живая ночь: корейские барбекю до 3 утра, изакая для офисных после 19:00." },
  },
  // === Batch 2: Yamanote continued ===
  komagome: {
    ratings: { food: 7, nightlife: 4, transport: 7, rent: 7, safety: 8, green: 9, gym_sports: 6, vibe: 7, crowd: 8 },
    transit_minutes: { shibuya: 28, shinjuku: 22, tokyo: 30, ikebukuro: 8, shinagawa: 38 },
    rent_avg: { '1k_1ldk': 95000, '2ldk': 155000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Тихий район с садом Рикугиэн — одним из красивейших в Токио.", landmarks: "Сад Рикугиэн (эпоха Эдо), святилище Фудзимэ Инари.", food: "Семейные ресторанчики: якитори, суши, рамэн. Без претензий, по-японски.", nightlife: "Несколько изакая до 23:00 — и всё." },
  },
  tabata: {
    ratings: { food: 5, nightlife: 3, transport: 7, rent: 8, safety: 8, green: 7, gym_sports: 5, vibe: 6, crowd: 9 },
    transit_minutes: { shibuya: 32, shinjuku: 25, tokyo: 28, ikebukuro: 12, shinagawa: 35 },
    rent_avg: { '1k_1ldk': 88000, '2ldk': 140000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Малоизвестный тихий район Яманотэ — дёшево и без туристов.", landmarks: "Бывший квартал художников, мемориальный центр Табата Бункамура.", food: "Скромный выбор: несколько изакая и рамэн-кафе у станции.", nightlife: "Философия «лечь пораньше» — несколько баров, и всё." },
  },
  otsuka: {
    ratings: { food: 7, nightlife: 6, transport: 8, rent: 7, safety: 7, green: 5, gym_sports: 6, vibe: 7, crowd: 7 },
    transit_minutes: { shibuya: 25, shinjuku: 15, tokyo: 28, ikebukuro: 5, shinagawa: 33 },
    rent_avg: { '1k_1ldk': 98000, '2ldk': 160000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Живой район с трамваем Тодэн Аракава и атмосферой старого Токио.", landmarks: "Трамвай Тодэн Аракава, храм Дайэн-дзи.", food: "Корейская кухня, изакая, якитори под навесами вдоль трамвайных рельсов.", nightlife: "Умеренная: бары до 1-2 ночи, ночные изакая вдоль трамвайной улицы." },
  },
  mejiro: {
    ratings: { food: 6, nightlife: 3, transport: 6, rent: 5, safety: 9, green: 8, gym_sports: 6, vibe: 8, crowd: 9 },
    transit_minutes: { shibuya: 20, shinjuku: 12, tokyo: 32, ikebukuro: 5, shinagawa: 28 },
    rent_avg: { '1k_1ldk': 115000, '2ldk': 185000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Элегантный тихий район: Университет Гакусюин, широкие зелёные улицы.", landmarks: "Кампус Гакусюин, аллея сакуры вдоль канала.", food: "Качественные итальянские и французские рестораны для местных.", nightlife: "Мэдзиро засыпает рано — несколько вино-баров, и всё." },
  },
  osaki: {
    ratings: { food: 7, nightlife: 5, transport: 9, rent: 5, safety: 8, green: 5, gym_sports: 8, vibe: 6, crowd: 6 },
    transit_minutes: { shibuya: 12, shinjuku: 18, tokyo: 22, ikebukuro: 28, shinagawa: 5 },
    rent_avg: { '1k_1ldk': 120000, '2ldk': 195000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Корпоративный урбанистический район: Sony, Canon, высотные офисы.", landmarks: "ThinkPark, Gate City Osaki.", food: "Бизнес-ланчи в торговых комплексах. Готанда рядом для разнообразия.", nightlife: "Корпоративные бары. После 22:00 улицы пустеют." },
  },
  hamamatsucho: {
    ratings: { food: 6, nightlife: 4, transport: 10, rent: 4, safety: 7, green: 6, gym_sports: 5, vibe: 5, crowd: 5 },
    transit_minutes: { shibuya: 20, shinjuku: 25, tokyo: 10, ikebukuro: 35, shinagawa: 10 },
    rent_avg: { '1k_1ldk': 130000, '2ldk': 210000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Деловой район залива: офисы, монорельс на Ханэда, паромы.", landmarks: "Токийская башня (10 мин), сад Хамарикю, паромный терминал Такэсиба.", food: "Бизнес-ланчи. Вечером и в выходные выбор сужается.", nightlife: "Практически нет — строго деловой район." },
  },
  // === Batch 3: Metro stations ===
  omotesando: {
    ratings: { food: 9, nightlife: 7, transport: 9, rent: 2, safety: 9, green: 7, gym_sports: 8, vibe: 9, crowd: 3 },
    transit_minutes: { shibuya: 6, shinjuku: 14, tokyo: 22, ikebukuro: 22, shinagawa: 22 },
    rent_avg: { '1k_1ldk': 165000, '2ldk': 280000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Токийский ответ Парижу: бульвар с кедрами, бутики, архитектура Тадао Андо.", landmarks: "Бульвар Омотэсандо, святилище Мэйдзи, парк Ёёги.", food: "Безупречная сцена: мишленовские адреса, Blue Bottle, % Arabica.", nightlife: "Сдержанная но качественная: hidden bars, лаунжи, натуральные вина." },
  },
  'azabu-juban': {
    ratings: { food: 9, nightlife: 7, transport: 7, rent: 1, safety: 10, green: 5, gym_sports: 7, vibe: 8, crowd: 5 },
    transit_minutes: { shibuya: 14, shinjuku: 22, tokyo: 24, ikebukuro: 30, shinagawa: 16 },
    rent_avg: { '1k_1ldk': 175000, '2ldk': 310000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Один из самых дорогих и уютных районов: послы, банкиры, старые токийские семьи.", landmarks: "Летний фестиваль Норё Дайкай, Токийская башня, храм Дзэнпукудзи.", food: "Гастрономический квартал: суши, фугу, ливанская кухня, легендарные пекарни.", nightlife: "Тихие коктейльные бары, вино-бары, джазовые клубы." },
  },
  'kiyosumi-shirakawa': {
    ratings: { food: 8, nightlife: 5, transport: 7, rent: 6, safety: 9, green: 8, gym_sports: 6, vibe: 9, crowd: 7 },
    transit_minutes: { shibuya: 24, shinjuku: 32, tokyo: 14, ikebukuro: 36, shinagawa: 28 },
    rent_avg: { '1k_1ldk': 105000, '2ldk': 175000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Столица третьей волны кофе — богемный оазис на восточном берегу Сумиды.", landmarks: "Сад Киёсуми, Музей современного искусства Токио (MOT).", food: "Blue Bottle, Allpress, Arise Coffee. Фермерские рынки и органика.", nightlife: "Рано засыпает. Несколько крафтовых баров у реки." },
  },
  'monzen-nakacho': {
    ratings: { food: 8, nightlife: 8, transport: 7, rent: 6, safety: 8, green: 6, gym_sports: 6, vibe: 8, crowd: 5 },
    transit_minutes: { shibuya: 26, shinjuku: 34, tokyo: 16, ikebukuro: 38, shinagawa: 26 },
    rent_avg: { '1k_1ldk': 98000, '2ldk': 165000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Один из самых «токийских» районов: сётамати, фестивали, изакая.", landmarks: "Святилище Томиока Хатиман-гу, храм Фукагава Фудо-до.", food: "Угорь, стоячие суши-бары, фукагава-мэси. Изакая на каждом шагу.", nightlife: "Неожиданно живая: изакая и яки-тон-бары работают до рассвета." },
  },
  iidabashi: {
    ratings: { food: 7, nightlife: 6, transport: 10, rent: 5, safety: 9, green: 7, gym_sports: 7, vibe: 7, crowd: 4 },
    transit_minutes: { shibuya: 18, shinjuku: 12, tokyo: 18, ikebukuro: 14, shinagawa: 28 },
    rent_avg: { '1k_1ldk': 115000, '2ldk': 195000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Транспортный узел с романтичной набережной канала Канда.", landmarks: "Сады Коисикава Коракуэн, набережная Канда-гава для ханами.", food: "Надёжные рестораны для офисных, хорошие независимые кофейни.", nightlife: "Бары для офисных и студентов — без сюрпризов." },
  },
  jimbocho: {
    ratings: { food: 7, nightlife: 5, transport: 8, rent: 6, safety: 9, green: 5, gym_sports: 6, vibe: 8, crowd: 6 },
    transit_minutes: { shibuya: 20, shinjuku: 14, tokyo: 16, ikebukuro: 18, shinagawa: 30 },
    rent_avg: { '1k_1ldk': 108000, '2ldk': 182000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Мировая столица подержанных книг — 200+ букинистических магазинов.", landmarks: "Книжный квартал, университеты Мэйдзи и Нихон.", food: "Столица японского карри! Кисса-тэн (старые кафе) сохранились лучше всего.", nightlife: "Бары для завсегдатаев, джазовые клубы старой закваски." },
  },
  // === Batch 4: Popular living areas ===
  'futako-tamagawa': {
    ratings: { food: 8, nightlife: 5, transport: 8, rent: 3, safety: 9, green: 9, gym_sports: 8, vibe: 8, crowd: 5 },
    transit_minutes: { shibuya: 16, shinjuku: 28, tokyo: 45, ikebukuro: 40, shinagawa: 25 },
    rent_avg: { '1k_1ldk': 130000, '2ldk': 210000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Район для жизни у реки: набережные, Tamagawa Rise, молодые семьи с колясками.", landmarks: "Берег реки Тамагава, торговый комплекс Tamagawa Rise.", food: "Итальянские рестораны, specialty-кофе. Ориентировано на платёжеспособную аудиторию.", nightlife: "Практически нет — район засыпает рано." },
  },
  denenchofu: {
    ratings: { food: 6, nightlife: 2, transport: 7, rent: 1, safety: 10, green: 9, gym_sports: 5, vibe: 7, crowd: 9 },
    transit_minutes: { shibuya: 20, shinjuku: 35, tokyo: 40, ikebukuro: 45, shinagawa: 18 },
    rent_avg: { '1k_1ldk': 160000, '2ldk': 280000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Токийский Беверли-Хиллз: широкие улицы, особняки, закрытая респектабельность.", landmarks: "Станция 1923 года, центральный круг с аллеями.", food: "Минималистично: добротные рестораны для местных. За разнообразием — в Дзиюгаоку.", nightlife: "Нет совсем — и это принципиальная позиция района." },
  },
  ogikubo: {
    ratings: { food: 8, nightlife: 6, transport: 8, rent: 6, safety: 8, green: 6, gym_sports: 6, vibe: 8, crowd: 5 },
    transit_minutes: { shibuya: 28, shinjuku: 12, tokyo: 30, ikebukuro: 20, shinagawa: 38 },
    rent_avg: { '1k_1ldk': 95000, '2ldk': 155000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Живой богемный район: антиквариат, художники, рамэн.", landmarks: "Антикварный квартал, храм Дзэнриндзи.", food: "Отличные рамэн, крепкие изакая, curry-сцена.", nightlife: "Тихая но живая: барная улочка, джазовые бары." },
  },
  asagaya: {
    ratings: { food: 7, nightlife: 7, transport: 7, rent: 7, safety: 8, green: 6, gym_sports: 5, vibe: 9, crowd: 6 },
    transit_minutes: { shibuya: 32, shinjuku: 15, tokyo: 35, ikebukuro: 22, shinagawa: 42 },
    rent_avg: { '1k_1ldk': 88000, '2ldk': 140000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Аутентичный живой район: джаз, инди-музыка, независимые книжные.", landmarks: "Аркада Pearl Center, фестиваль Танабата.", food: "Авторские заведения: маленькие рамэн-бары, кафе с самообжаренным кофе.", nightlife: "Джазовые и рок-клубы, бары с характером — весело и без показухи." },
  },
  kinshicho: {
    ratings: { food: 8, nightlife: 8, transport: 9, rent: 8, safety: 6, green: 4, gym_sports: 6, vibe: 7, crowd: 3 },
    transit_minutes: { shibuya: 35, shinjuku: 30, tokyo: 12, ikebukuro: 35, shinagawa: 28 },
    rent_avg: { '1k_1ldk': 82000, '2ldk': 130000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Восточный Токио без прикрас: шумный, плотный, живой shitamachi.", landmarks: "Зал Сумида, река Сумида, парк Кибо с видом на Sky Tree.", food: "Лучшее соотношение цена/качество: изакая, якинику, рынок Кинситё.", nightlife: "Бурная и без снобизма: изакая, бары, живая музыка до утра." },
  },
  toyosu: {
    ratings: { food: 7, nightlife: 4, transport: 7, rent: 5, safety: 9, green: 5, gym_sports: 7, vibe: 6, crowd: 6 },
    transit_minutes: { shibuya: 35, shinjuku: 45, tokyo: 18, ikebukuro: 50, shinagawa: 22 },
    rent_avg: { '1k_1ldk': 115000, '2ldk': 185000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Новый район на заливе: кондоминиумы, широкие тротуары, молодые семьи.", landmarks: "Рыбный рынок Тоёсу, LaLaport, Teamlab Planets.", food: "Морепродукты у рынка на высшем уровне. Остальное — сетевые рестораны.", nightlife: "Район засыпает с торговыми центрами. Для вечера — в Гиндзу." },
  },
  // === Batch 5: Key business/transit stations ===
  yurakucho: {
    ratings: { food: 9, nightlife: 8, transport: 9, rent: 2, safety: 9, green: 4, gym_sports: 5, vibe: 8, crowd: 3 },
    transit_minutes: { shibuya: 18, shinjuku: 22, tokyo: 4, ikebukuro: 30, shinagawa: 20 },
    rent_avg: { '1k_1ldk': 160000, '2ldk': 280000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Деловой центр с душой старого Токио: под арками JR кипит жизнь.", landmarks: "Якитория под путепроводом, Tokyo International Forum, парк Хибия.", food: "Гастрономический рай: тесные якитория, изакая и рамэн-лавки под арками.", nightlife: "Арки вечером — цепочка забитых баров. Атмосфера послевоенных сацэмасэ." },
  },
  kanda: {
    ratings: { food: 8, nightlife: 6, transport: 9, rent: 4, safety: 8, green: 3, gym_sports: 5, vibe: 7, crowd: 4 },
    transit_minutes: { shibuya: 22, shinjuku: 18, tokyo: 5, ikebukuro: 22, shinagawa: 24 },
    rent_avg: { '1k_1ldk': 130000, '2ldk': 220000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Рабочий Токио: книжные, электроника, бюджетные закусочные.", landmarks: "Святилище Канда Мёдзин, квартал Дзимботё, близость Акихабары.", food: "Легендарные соба-рестораны с историей 100+ лет. Якитори и тонкацу.", nightlife: "Скромная: изакая для завсегдатаев, пара джаз-баров." },
  },
  okachimachi: {
    ratings: { food: 8, nightlife: 5, transport: 8, rent: 5, safety: 7, green: 4, gym_sports: 6, vibe: 7, crowd: 4 },
    transit_minutes: { shibuya: 28, shinjuku: 30, tokyo: 10, ikebukuro: 25, shinagawa: 32 },
    rent_avg: { '1k_1ldk': 115000, '2ldk': 195000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Шумный рыночный район между Акихабарой и Уэно.", landmarks: "Рынок Амэ-ёко, Уэно парк (5 мин), ювелирный квартал.", food: "Амэ-ёко — лучшая уличная еда: морепродукты, якитори, экзотические фрукты.", nightlife: "Скромная: изакая в переулках. После полуночи тихо." },
  },
  shimbashi: {
    ratings: { food: 8, nightlife: 9, transport: 10, rent: 3, safety: 8, green: 4, gym_sports: 5, vibe: 8, crowd: 3 },
    transit_minutes: { shibuya: 20, shinjuku: 26, tokyo: 8, ikebukuro: 36, shinagawa: 12 },
    rent_avg: { '1k_1ldk': 155000, '2ldk': 270000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Столица японских сарариманов: сотни изакая, вечерний гул до последнего поезда.", landmarks: "Паровоз SL Plaza, монорельс Юрикамомэ на Одайбу.", food: "Лучший район для изакая-хоппинга: под арками всё — от якитори до морепродуктов.", nightlife: "Театр корпоративной культуры: тосты, красные лица, номикай до полуночи и дольше." },
  },
  tamachi: {
    ratings: { food: 6, nightlife: 4, transport: 8, rent: 5, safety: 9, green: 5, gym_sports: 6, vibe: 6, crowd: 7 },
    transit_minutes: { shibuya: 22, shinjuku: 30, tokyo: 14, ikebukuro: 42, shinagawa: 6 },
    rent_avg: { '1k_1ldk': 130000, '2ldk': 215000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Тихий функциональный район: джентрификация, новые жилые комплексы.", landmarks: "Токийский технологический институт, набережная Сибаура, Токийская башня.", food: "Стабильный набор: сетевые рестораны, итальянские кафе, суши-конвейеры.", nightlife: "Не ночной район: несколько баров у станции, и всё." },
  },
  otemachi: {
    ratings: { food: 8, nightlife: 5, transport: 10, rent: 1, safety: 10, green: 5, gym_sports: 6, vibe: 6, crowd: 4 },
    transit_minutes: { shibuya: 20, shinjuku: 20, tokyo: 3, ikebukuro: 18, shinagawa: 20 },
    rent_avg: { '1k_1ldk': 200000, '2ldk': 380000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Финансовое сердце Японии: банки, корпорации, Манхэттен по-токийски.", landmarks: "Связан с Токийской станцией, Императорский дворец рядом.", food: "Подземные рестораны: от бюджетных рамэн до кайсэки за 15000+.", nightlife: "Нет — после 20:00 район-призрак." },
  },
  // === Batch 6: Yamanote remaining + outer hubs ===
  'shin-okubo': {
    ratings: { food: 9, nightlife: 7, transport: 8, rent: 6, safety: 7, green: 3, gym_sports: 4, vibe: 9, crowd: 3 },
    transit_minutes: { shibuya: 18, shinjuku: 4, tokyo: 28, ikebukuro: 12, shinagawa: 30 },
    rent_avg: { '1k_1ldk': 88000, '2ldk': 155000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Токийский Корея-таун: корейские вывески, непальские рестораны, халяльные лавки — мультикультурный карнавал.", landmarks: "Корейский переулок, мечеть Tokyo Camii, Shinjuku Chuo Park.", food: "Корейский BBQ, тток-пок, непальское карри, тайские кафе — разнообразие зашкаливает.", nightlife: "Корейские norebang, K-pop бары. За клубами — одна станция до Синдзюку." },
  },
  uguisudani: {
    ratings: { food: 6, nightlife: 5, transport: 7, rent: 8, safety: 5, green: 5, gym_sports: 4, vibe: 4, crowd: 7 },
    transit_minutes: { shibuya: 25, shinjuku: 22, tokyo: 14, ikebukuro: 18, shinagawa: 26 },
    rent_avg: { '1k_1ldk': 72000, '2ldk': 128000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Самый тихий район на Яманотэ: лав-отели и дешёвая аренда.", landmarks: "Храм Канъэйдзи, парк Уэно (10-15 мин), музеи.", food: "Несколько проверенных ресторанчиков с якитори и рамэном.", nightlife: "Ограничена — для досуга едут в Уэно или Акихабару." },
  },
  'kita-senju': {
    ratings: { food: 8, nightlife: 7, transport: 10, rent: 8, safety: 7, green: 5, gym_sports: 6, vibe: 7, crowd: 4 },
    transit_minutes: { shibuya: 38, shinjuku: 38, tokyo: 28, ikebukuro: 30, shinagawa: 45 },
    rent_avg: { '1k_1ldk': 75000, '2ldk': 135000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Крупнейший хаб северного Токио: 5 линий, торговые аркады, студенческая энергия.", landmarks: "Крытые торговые аркады, кампус TMU, набережная Аракавы.", food: "Разнообразно и дёшево: рамэн, якинику, суши-кайтен, фудкорты.", nightlife: "Много изакая и баров, «бар-стрит» к западу от станции." },
  },
  akabane: {
    ratings: { food: 8, nightlife: 9, transport: 9, rent: 8, safety: 6, green: 5, gym_sports: 5, vibe: 8, crowd: 4 },
    transit_minutes: { shibuya: 32, shinjuku: 22, tokyo: 30, ikebukuro: 15, shinagawa: 40 },
    rent_avg: { '1k_1ldk': 72000, '2ldk': 130000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Легендарный «питейный город» — культура изакая возведена в абсолют, можно пить с 9 утра.", landmarks: "Аркада Ichibangai, парк Акабанэдай, набережная Аракавы.", food: "Дешёвые изакая, якитори на углях, суши-стойки. Утреннее аса-номи!", nightlife: "Одна из самых аутентичных ночных сцен: десятки тесных баров каждый вечер." },
  },
  nerima: {
    ratings: { food: 6, nightlife: 4, transport: 7, rent: 8, safety: 9, green: 8, gym_sports: 7, vibe: 6, crowd: 8 },
    transit_minutes: { shibuya: 35, shinjuku: 22, tokyo: 40, ikebukuro: 10, shinagawa: 50 },
    rent_avg: { '1k_1ldk': 78000, '2ldk': 140000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Зелёный жилой район: малоэтажная застройка, огороды между домами, семейный уклад.", landmarks: "Парк Нэрима-дзё, Harry Potter Studio Tour Tokyo.", food: "Скромная но добротная сцена: суши, рамэн, домашняя кухня для местных.", nightlife: "Минимальна — несколько баров. За развлечениями едут в Икэбукуро (10 мин)." },
  },
  oji: {
    ratings: { food: 6, nightlife: 4, transport: 7, rent: 8, safety: 8, green: 8, gym_sports: 5, vibe: 7, crowd: 7 },
    transit_minutes: { shibuya: 38, shinjuku: 30, tokyo: 22, ikebukuro: 18, shinagawa: 35 },
    rent_avg: { '1k_1ldk': 73000, '2ldk': 132000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Исторический район: лисы Инари, старые храмы, трамвай, неспешный ритм.", landmarks: "Святилище Одзи Инари, парк Асукаяма, трамвай Тодэн Аракава.", food: "Традиционные соба, якитори, кондитерские с вагаси по старинным рецептам.", nightlife: "Практически нет — несколько камерных баров для местных." },
  },
  // === Batch 7: Metro important ===
  nagatacho: {
    ratings: { food: 6, nightlife: 3, transport: 9, rent: 3, safety: 9, green: 6, gym_sports: 4, vibe: 5, crowd: 8 },
    transit_minutes: { shibuya: 12, shinjuku: 15, tokyo: 14, ikebukuro: 20, shinagawa: 22 },
    rent_avg: { '1k_1ldk': 185000, '2ldk': 380000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Политическое сердце Японии: парламент, резиденция премьера, строгая атмосфера.", landmarks: "Здание парламента, святилище Хиэ-дзиндзя, сад Хинокитё.", food: "Деловые рестораны высокого класса для чиновников. Уличной еды нет.", nightlife: "Практически нет — бары в отелях. За весельем — в Акасака или Роппонги." },
  },
  'aoyama-itchome': {
    ratings: { food: 8, nightlife: 6, transport: 9, rent: 2, safety: 9, green: 7, gym_sports: 7, vibe: 8, crowd: 7 },
    transit_minutes: { shibuya: 8, shinjuku: 16, tokyo: 18, ikebukuro: 25, shinagawa: 18 },
    rent_avg: { '1k_1ldk': 220000, '2ldk': 480000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Престижный и элегантный: мода, дизайн, посольства, сдержанный люкс.", landmarks: "Аояма-дори, Гинкго Аллея Мэйдзи-дзингу Гайэн, Национальный стадион.", food: "Мишленовские рестораны, стильные кафе, субботний фермерский рынок.", nightlife: "Камерная: винные бары, коктейльные лаунжи, джаз для взрослых." },
  },
  'roppongi-itchome': {
    ratings: { food: 8, nightlife: 7, transport: 7, rent: 3, safety: 7, green: 5, gym_sports: 7, vibe: 7, crowd: 6 },
    transit_minutes: { shibuya: 14, shinjuku: 20, tokyo: 20, ikebukuro: 30, shinagawa: 16 },
    rent_avg: { '1k_1ldk': 210000, '2ldk': 450000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Тихая деловая часть Роппонги: международные офисы, экспаты, фешенебельные дома.", landmarks: "Роппонги Хиллз, ARK Hills, храм Ноги-дзиндзя.", food: "Итальянская, французская кухня, бразильские стейк-хаусы, суши.", nightlife: "Стильные бары и лаунжи. До клубов Роппонги — 5 мин пешком." },
  },
  'shinjuku-sanchome': {
    ratings: { food: 10, nightlife: 10, transport: 10, rent: 5, safety: 6, green: 3, gym_sports: 6, vibe: 9, crowd: 1 },
    transit_minutes: { shibuya: 10, shinjuku: 3, tokyo: 18, ikebukuro: 12, shinagawa: 22 },
    rent_avg: { '1k_1ldk': 145000, '2ldk': 300000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Эпицентр торговли и развлечений: неон, толпы, универмаги, квартал Никомэ.", landmarks: "Универмаг Исэтан, Кабукитё, Такасимая Таймс Скуэа.", food: "Тысячи ресторанов: Рамен-стрит, якинику, суши — месяцами без повторений.", nightlife: "Главная ночная арена: Кабукитё, бары Никомэ, клубы до утра." },
  },
  kudanshita: {
    ratings: { food: 6, nightlife: 3, transport: 8, rent: 5, safety: 9, green: 8, gym_sports: 5, vibe: 6, crowd: 7 },
    transit_minutes: { shibuya: 20, shinjuku: 18, tokyo: 12, ikebukuro: 20, shinagawa: 25 },
    rent_avg: { '1k_1ldk': 155000, '2ldk': 320000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Исторический район у Императорского дворца: тихая меланхолия и зелёные склоны.", landmarks: "Ясукуни-дзиндзя, парк Китаномару, рвы Императорского дворца.", food: "Деловые рестораны, лапшичные. Во время ханами — ярмарка уличной еды.", nightlife: "Практически нет — вечерняя прогулка вдоль рва — главное удовольствие." },
  },
  nihonbashi: {
    ratings: { food: 8, nightlife: 5, transport: 9, rent: 3, safety: 9, green: 3, gym_sports: 4, vibe: 7, crowd: 6 },
    transit_minutes: { shibuya: 22, shinjuku: 25, tokyo: 6, ikebukuro: 28, shinagawa: 18 },
    rent_avg: { '1k_1ldk': 190000, '2ldk': 400000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Исторический финансовый центр: торговые дома с 400-летней историей.", landmarks: "Мост Нихонбаси — нулевая точка всех дорог Японии, универмаги Мицукоси/Такасимая.", food: "Рестораны с вековой историей: унаги, тэмпура, кайсэки. Деп'а-тика лучших универмагов.", nightlife: "Корпоративные изакая до полуночи. Клубной жизни нет." },
  },
  mitsukoshimae: {
    ratings: { food: 9, nightlife: 5, transport: 9, rent: 3, safety: 9, green: 3, gym_sports: 4, vibe: 7, crowd: 5 },
    transit_minutes: { shibuya: 20, shinjuku: 22, tokyo: 7, ikebukuro: 26, shinagawa: 18 },
    rent_avg: { '1k_1ldk': 195000, '2ldk': 410000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Перед Мицукоси: благородное потребительское спокойствие, состоятельная публика.", landmarks: "Универмаг Мицукоси (1673), Банк Японии, Коредо Мурома.", food: "Лучшие деп'а-тика Токио, рестораны с вековой историей, Коредо.", nightlife: "Тихие рестораны-бары. Место для ужина, не для приключений." },
  },
  korakuen: {
    ratings: { food: 7, nightlife: 5, transport: 8, rent: 6, safety: 8, green: 7, gym_sports: 10, vibe: 7, crowd: 4 },
    transit_minutes: { shibuya: 22, shinjuku: 18, tokyo: 14, ikebukuro: 10, shinagawa: 28 },
    rent_avg: { '1k_1ldk': 140000, '2ldk': 285000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Район Токио Доум: спорт, развлечения, студенты — энергичный клубок.", landmarks: "Токио Доум, парк аттракционов, сад Коисикава Корэкэн.", food: "Изакая, рамэн, бургерные для молодёжи и болельщиков.", nightlife: "В дни матчей — праздник. В обычные дни — студенческие бары." },
  },
  // === Batch 8: Living/transit areas ===
  'musashi-kosugi': {
    ratings: { food: 8, nightlife: 6, transport: 9, rent: 4, safety: 8, green: 5, gym_sports: 7, vibe: 7, crowd: 4 },
    transit_minutes: { shibuya: 12, shinjuku: 22, tokyo: 18, ikebukuro: 30, shinagawa: 10 },
    rent_avg: { '1k_1ldk': 115000, '2ldk': 185000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Джентрифицированный район с лесом небоскрёбов-кондоминиумов.", landmarks: "Grand Tree, река Тамагава, стадион.", food: "Рамэн, итальянские бистро, семейные кафе в башнях.", nightlife: "Сдержанная — район для семей, не для тусовщиков." },
  },
  tachikawa: {
    ratings: { food: 8, nightlife: 7, transport: 9, rent: 6, safety: 8, green: 8, gym_sports: 8, vibe: 7, crowd: 5 },
    transit_minutes: { shibuya: 45, shinjuku: 35, tokyo: 50, ikebukuro: 45, shinagawa: 60 },
    rent_avg: { '1k_1ldk': 75000, '2ldk': 125000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Крупнейший хаб западного Токио: самодостаточный город с парками.", landmarks: "Парк Сёва Кинэн (165 га), IKEA, Granduo.", food: "Впечатляет для пригорода: якитори, этнические рестораны, уличная еда.", nightlife: "По меркам запада Токио активная: бары, клубы, живые площадки." },
  },
  machida: {
    ratings: { food: 8, nightlife: 6, transport: 8, rent: 6, safety: 8, green: 6, gym_sports: 7, vibe: 6, crowd: 5 },
    transit_minutes: { shibuya: 30, shinjuku: 38, tokyo: 55, ikebukuro: 55, shinagawa: 40 },
    rent_avg: { '1k_1ldk': 70000, '2ldk': 115000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Крупный пригородный торговый центр на границе Токио и Канагавы.", landmarks: "Торговые аркады, Lumine, Odakyu, ботанический сад.", food: "Широкий выбор: удон, суши, кафе на верхних этажах ТЦ.", nightlife: "Бары и караоке у станции, закрываются к 23:00." },
  },
  kamata: {
    ratings: { food: 7, nightlife: 7, transport: 8, rent: 7, safety: 6, green: 4, gym_sports: 5, vibe: 7, crowd: 5 },
    transit_minutes: { shibuya: 20, shinjuku: 30, tokyo: 22, ikebukuro: 40, shinagawa: 12 },
    rent_avg: { '1k_1ldk': 75000, '2ldk': 120000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Рабочий район: узкие улочки с изакая, онсэн, мастерские. Без глянца.", landmarks: "Общественные бани и онсэн, аркада Kamata Ekimae Shotengai.", food: "Тонкацу-рестораны работают поколениями. Якитори, лапша — дёшево и вкусно.", nightlife: "Демократичные изакая под путями работают допоздна. Пятницы особенно живые." },
  },
  kawasaki: {
    ratings: { food: 7, nightlife: 7, transport: 9, rent: 6, safety: 6, green: 4, gym_sports: 6, vibe: 6, crowd: 4 },
    transit_minutes: { shibuya: 28, shinjuku: 35, tokyo: 25, ikebukuro: 50, shinagawa: 10 },
    rent_avg: { '1k_1ldk': 80000, '2ldk': 130000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Бывший промышленный город: коммерческая трансформация, космополитичность.", landmarks: "LaLaport, храм Кавасаки Дайси, Музей Фудзицу.", food: "Сетевые рестораны + старые изакая. Корейские, китайские, южноазиатские кафе.", nightlife: "Бары и клубы у западного выхода. Широкий, но не изысканный выбор." },
  },
  nezu: {
    ratings: { food: 7, nightlife: 3, transport: 6, rent: 5, safety: 9, green: 7, gym_sports: 4, vibe: 9, crowd: 7 },
    transit_minutes: { shibuya: 25, shinjuku: 22, tokyo: 18, ikebukuro: 20, shinagawa: 30 },
    rent_avg: { '1k_1ldk': 90000, '2ldk': 150000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Подлинный дух старого Эдо: мощёные переулки, деревянные домики, галереи.", landmarks: "Святилище Нэдзу с алыми торий, ботанический сад Коисикава.", food: "Крошечные кофейни в старых домах, тофу-лавки, традиционные вагаси.", nightlife: "Не ночной район — после 21:00 тишина, и это достоинство." },
  },
  sendagi: {
    ratings: { food: 7, nightlife: 3, transport: 6, rent: 5, safety: 9, green: 7, gym_sports: 4, vibe: 9, crowd: 8 },
    transit_minutes: { shibuya: 28, shinjuku: 24, tokyo: 20, ikebukuro: 18, shinagawa: 33 },
    rent_avg: { '1k_1ldk': 88000, '2ldk': 145000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Сердце Янака-Нэдзу-Янака: богемные переулки, художники, медленная жизнь.", landmarks: "Торговая улица Янака Гиндза, кладбище Янака, галереи.", food: "Домашние соба, пекарни в мачия, рисовые крекеры нингё-яки.", nightlife: "Нет — несколько баров с натуральным вином до 23:00." },
  },
  yushima: {
    ratings: { food: 7, nightlife: 5, transport: 8, rent: 6, safety: 8, green: 6, gym_sports: 5, vibe: 7, crowd: 6 },
    transit_minutes: { shibuya: 22, shinjuku: 18, tokyo: 12, ikebukuro: 18, shinagawa: 22 },
    rent_avg: { '1k_1ldk': 95000, '2ldk': 155000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Академический район: храм учёбы, книготорговцы, студенты.", landmarks: "Святилище Юсима Тэндзин, парк Уэно (5 мин), Токийский университет.", food: "Традиционные суши и омакасэ, лапшичные. Азиатские кухни рядом.", nightlife: "Камерные бары в стиле сёва. Специфический квартал для взрослых." },
  },
  tsukiji: {
    ratings: { food: 10, nightlife: 4, transport: 8, rent: 5, safety: 9, green: 4, gym_sports: 4, vibe: 8, crowd: 3 },
    transit_minutes: { shibuya: 20, shinjuku: 25, tokyo: 10, ikebukuro: 30, shinagawa: 18 },
    rent_avg: { '1k_1ldk': 110000, '2ldk': 175000, source: 'estimate', updated: '2026-04' },
    description: { atmosphere: "Это прежде всего еда. Внешний рынок кипит с раннего утра.", landmarks: "Внешний рынок Цукидзи, храм Хонгандзи, набережная Харумиудохин.", food: "Мекка: лучшие суши на завтрак, гребешки у ларьков, тамагояки — с 6 утра.", nightlife: "После обеда район затихает. Цукидзи — утренний район, не вечерний." },
  },
};
