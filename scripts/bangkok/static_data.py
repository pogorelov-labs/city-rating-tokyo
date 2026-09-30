"""Curated static inputs for the Bangkok build (names, rail lines, hubs).

Everything here is hand-maintained reference data that OSM / Wikidata do not
provide consistently:

  * RU_NAMES — Wikidata has Russian labels for only ~20 of 50 khet, in mixed
    styles ("Банг-Рак", "район Пхаятхай"). One consistent practical
    transcription of the RTGS romanisation is used for all 50 instead.
  * LINES — display metadata for the ten rapid-transit lines in service
    (Sept 2026). Lines under construction (Orange East, Purple South, …) are
    intentionally absent: the commute model only uses what runs today.
  * CURATED_SEQUENCES — stop order for lines whose OSM route relations carry
    no/partial stop members (BTS Silom, SRT Light Red).
  * HUBS — the five commute hubs and the station each one is anchored to.
"""

# khet slug → Russian name
RU_NAMES: dict[str, str] = {
    "phra-nakhon": "Пхранакхон",
    "samphanthawong": "Сампхантхавонг",
    "pom-prap-sattru-phai": "Помпрап-Саттрупхай",
    "bang-rak": "Банграк",
    "pathum-wan": "Патхумван",
    "ratchathewi": "Ратчатхеви",
    "phaya-thai": "Пхаятхай",
    "dusit": "Дусит",
    "bang-sue": "Бангсы",
    "chatuchak": "Чатучак",
    "don-mueang": "Донмыанг",
    "lak-si": "Лакси",
    "bang-khen": "Бангкхен",
    "din-daeng": "Диндэнг",
    "huai-khwang": "Хуайкхванг",
    "khlong-toei": "Кхлонгтой",
    "lat-phrao": "Латпхрао",
    "sai-mai": "Саймай",
    "watthana": "Ваттхана",
    "bang-kapi": "Бангкапи",
    "bangkok-yai": "Бангкок-Яй",
    "taling-chan": "Талингчан",
    "thawi-watthana": "Тхави-Ваттхана",
    "wang-thonglang": "Вангтхонгланг",
    "bang-phlat": "Бангпхлат",
    "bangkok-noi": "Бангкок-Ной",
    "nong-khaem": "Нонгкхэм",
    "bang-khae": "Бангкхэ",
    "bueng-kum": "Бынгкум",
    "khan-na-yao": "Кханнаяо",
    "phasi-charoen": "Пхасичароен",
    "khlong-sam-wa": "Кхлонгсамва",
    "bang-na": "Бангна",
    "min-buri": "Минбури",
    "prawet": "Правет",
    "saphan-sung": "Сапхансунг",
    "phra-khanong": "Пхракханонг",
    "suan-luang": "Суанлуанг",
    "chom-thong": "Чомтхонг",
    "rat-burana": "Ратбурана",
    "thung-khru": "Тхунгкхру",
    "khlong-san": "Кхлонгсан",
    "thon-buri": "Тхонбури",
    "bang-bon": "Бангбон",
    "bang-khun-thian": "Бангкхунтхиан",
    "sathon": "Сатхон",
    "bang-kho-laem": "Бангкхолэм",
    "yan-nawa": "Яннава",
    "lat-krabang": "Латкрабанг",
    "nong-chok": "Нонгчок",
}

# OSM name:en → slug when the slugified English label is not the common form.
SLUG_OVERRIDES: dict[str, str] = {
    "vadhana": "watthana",
}

# Rail line metadata for the UI + the commute model (build.py `transit_model`).
# `speed_kmh` is the average *commercial* speed including station dwell,
# calibrated on published end-to-end times: BTS Mo Chit–On Nut 17 km ≈ 30 min
# (~34 km/h); MRT Purple 23 km ≈ 33 min; Yellow 30 km ≈ 45 min; Pink 34.5 km ≈
# 50 min; ARL Suvarnabhumi–Phaya Thai 28.6 km ≈ 26 min; Dark Red Bang Sue–Rangsit
# 26 km ≈ 25 min. `wait_min` ≈ half the peak headway. `dwell_min` stays 0
# (folded into the average speed) but is kept as a tuning knob.
LINES: dict[str, dict] = {
    "bts_sukhumvit": {
        "name_en": "BTS Sukhumvit Line", "name_th": "รถไฟฟ้าบีทีเอส สายสุขุมวิท",
        "name_ja": "BTSスクンビット線", "name_ru": "BTS, линия Сукхумвит",
        "operator": "BTS", "color": "#65B724", "kind": "metro",
        "speed_kmh": 32, "dwell_min": 0, "wait_min": 2.5,
    },
    "bts_silom": {
        "name_en": "BTS Silom Line", "name_th": "รถไฟฟ้าบีทีเอส สายสีลม",
        "name_ja": "BTSシーロム線", "name_ru": "BTS, линия Силом",
        "operator": "BTS", "color": "#02817D", "kind": "metro",
        "speed_kmh": 32, "dwell_min": 0, "wait_min": 2.5,
    },
    "bts_gold": {
        "name_en": "Gold Line", "name_th": "รถไฟฟ้าสายสีทอง",
        "name_ja": "ゴールドライン", "name_ru": "Золотая линия",
        "operator": "BTS", "color": "#A58704", "kind": "metro",
        "speed_kmh": 22, "dwell_min": 0, "wait_min": 4.0,
    },
    "mrt_blue": {
        "name_en": "MRT Blue Line", "name_th": "รถไฟฟ้ามหานคร สายสีน้ำเงิน",
        "name_ja": "MRTブルーライン", "name_ru": "MRT, синяя линия",
        "operator": "MRT", "color": "#1E398D", "kind": "metro",
        "speed_kmh": 34, "dwell_min": 0, "wait_min": 2.5,
    },
    "mrt_purple": {
        "name_en": "MRT Purple Line", "name_th": "รถไฟฟ้ามหานคร สายสีม่วง",
        "name_ja": "MRTパープルライン", "name_ru": "MRT, фиолетовая линия",
        "operator": "MRT", "color": "#893B90", "kind": "metro",
        "speed_kmh": 42, "dwell_min": 0, "wait_min": 3.5,
    },
    "mrt_yellow": {
        "name_en": "MRT Yellow Line", "name_th": "รถไฟฟ้าสายสีเหลือง",
        "name_ja": "MRTイエローライン", "name_ru": "MRT, жёлтая линия",
        "operator": "MRT", "color": "#E3B800", "kind": "monorail",
        "speed_kmh": 40, "dwell_min": 0, "wait_min": 3.0,
    },
    "mrt_pink": {
        "name_en": "MRT Pink Line", "name_th": "รถไฟฟ้าสายสีชมพู",
        "name_ja": "MRTピンクライン", "name_ru": "MRT, розовая линия",
        "operator": "MRT", "color": "#E76589", "kind": "monorail",
        "speed_kmh": 41, "dwell_min": 0, "wait_min": 3.0,
    },
    "arl": {
        "name_en": "Airport Rail Link", "name_th": "แอร์พอร์ต เรล ลิงก์",
        "name_ja": "エアポート・レール・リンク", "name_ru": "Airport Rail Link",
        "operator": "ARL", "color": "#8A1538", "kind": "airport_link",
        "speed_kmh": 66, "dwell_min": 0, "wait_min": 6.0,
    },
    "srt_dark_red": {
        "name_en": "SRT Dark Red Line", "name_th": "รถไฟชานเมือง สายสีแดงเข้ม",
        "name_ja": "SRTダークレッドライン", "name_ru": "SRT, тёмно-красная линия",
        "operator": "SRT", "color": "#B5191E", "kind": "commuter",
        "speed_kmh": 62, "dwell_min": 0, "wait_min": 6.0,
    },
    "srt_light_red": {
        "name_en": "SRT Light Red Line", "name_th": "รถไฟชานเมือง สายสีแดงอ่อน",
        "name_ja": "SRTライトレッドライン", "name_ru": "SRT, светло-красная линия",
        "operator": "SRT", "color": "#F26B6B", "kind": "commuter",
        "speed_kmh": 60, "dwell_min": 0, "wait_min": 9.0,
    },
}

# Stop order where the OSM relation lacks stop members (or only has termini).
CURATED_SEQUENCES: dict[str, list[str]] = {
    "bts_silom": [
        "National Stadium", "Siam", "Ratchadamri", "Sala Daeng", "Chong Nonsi",
        "Saint Louis", "Surasak", "Saphan Taksin", "Krung Thon Buri", "Wongwian Yai",
        "Pho Nimit", "Talat Phlu", "Wutthakat", "Bang Wa",
    ],
    "srt_light_red": ["Krung Thep Aphiwat", "Bang Son", "Bang Bamru", "Taling Chan"],
}

# Station-name spellings in OSM stop nodes → canonical station name.
# Thai names missing on some OSM station nodes outside Bangkok.
STATION_TH_FALLBACK: dict[str, str] = {
    "Rangsit": "รังสิต",
}

STATION_NAME_ALIASES: dict[str, str] = {
    "don muang": "Don Mueang",
    "จรัญฯ 13": "Charan 13",
    "lak hok (rangsit u.)": "Lak Hok",
    "taling chan junction": "Taling Chan",
    "st. louis": "Saint Louis",
}

# Commute hubs: id → the station name the hub is anchored on.
HUBS: dict[str, str] = {
    "siam": "Siam",
    "asok": "Asok",
    "silom": "Sala Daeng",
    "rama9": "Phra Ram 9",
    "mochit": "Mo Chit",
}


# Bangkok (admin_level 4) plus a ~2 km margin so sample points near the
# provincial border also "see" POIs and stations just across it (Nonthaburi,
# Samut Prakan, Pathum Thani). Order: south, west, north, east.
BBOX = (13.47, 100.30, 13.98, 100.96)

# Rapid-transit route relations (one direction per line is enough for the
# stop sequence; both are fetched so the line geometry is complete). Intercity
# / ordinary SRT services and the airport-internal APM are deliberately left
# out: they are not everyday commuting options.
RAIL_ROUTE_RELATIONS = {
    "bts_sukhumvit": [444651, 7989376],
    "bts_silom": [2067854, 7989385],
    "bts_gold": [11681439, 11681440],
    "mrt_blue": [444659, 7725025],
    "mrt_purple": [6988563, 7725057],
    "mrt_yellow": [15806897, 15806898],
    "mrt_pink": [16740886, 16740887],
    "arl": [2148241, 9921500],
    "srt_dark_red": [13058384, 13058390],
    "srt_light_red": [13178788, 14071495],
}
