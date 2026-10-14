# Index — one-off acquisition run 2026-10-14

11 направлений волны-4 (ADR «Conversion by the owner's one-off acquisition policy»,
`research/decisions/2026-10-14-discovery-adoption.md`). Индекс и сводка составлены
2026-10-14 по фактической проверке диска: `find research/snapshots/2026-10-14 -type f`
→ 1313 файлов, все артефакты из отчётов агентов на месте; счётчики записей перепроверены
парсингом (coworking 105/54, JNTO 2721, Michelin 267/71 фич (183/54 с геометрией),
embassies 79/167 фич, housing 50 кхетов, accidents 50/126 строк, waste 459 строк,
keishicho digest 118 строк). Лицензии сверены с LICENSE.txt каждого каталога.

Статусы: **acquired** = полный забор; **partial** = доставлено частично (причина в таблице).

| Направление | Статус | Ключевые файлы | Источник + лицензия | INTERNAL ONLY? | Следующий шаг |
|---|---|---|---|---|---|
| air-bangkok | partial | wayback_rar_2011_2020/PM2.5(2011–2020).xlsx + original_download.rar; download_manifest.json, xlsx_summary.json, air4thai_history_stations.json, notes.md | PCD gdcatalog «gdpublish-air-quality-bangkok-metropolitan-region», CKAN «Open Data Common» (license_url отсутствует); xlsx — из Wayback-каптуры 2022-06-22 официального .rar | **да** (до проверки применимости лицензии) | Докачать CSV 2021–2025 через тайский egress (VPN; все 15 URL в download_manifest.json); конвертация в date×station_id×pm25; связка с реестром станций |
| air-tokyo | acquired | 260 zip (220 TD 確定値 + 20 TJ + 20 TM, 146 МБ) за 2019–2023; stations_2023.csv (375 станций, lat/lon), stations_summary.json, manifest.json | NIES 環境展望台 (tenbou.nies.go.jp), данные 環境省; © NIES, открытой лицензии на републикацию нет | **да** | Распаковать TD в плоский датасет (PrefectureCode 13/11/12/14 × StationCode × вещества) для рейтинговой витрины; TJ — сырьё на будущее |
| noise | partial | TMG: yearbook1911_{2022,2023,2024}.csv, tmg_r1–r5_* (автодорожный шум FY2019–23, сводка tmg_survey_summary.json), hakusho2025_34; chofu_h29_roadnoise.xls; PCD: только pcd_ckan_package_show.json + pcd_resources_index.json | TMG CC BY 4.0 (годоскоп 19-11, шум, 白書); 調布市 CC BY 4.0; PCD «Open Data Common» (метаданные; сами CSV не скачаны) | нет — TMG/調布 публикуемы с атрибуцией; PCD-CSV пока нет на диске | Доскачать PCD CSV (тайский egress; URL в pcd_resources_index.json) или bulk-запрос PCD; принять TMG-набор (FY2018–2024); сообщить TMG о битых 白書 35/39 |
| accidents-bangkok | partial | bkk_accident_risk_2568.csv/.geojson (50 точек, 46 районов), heat_map_100clusters_2565.csv/.geojson (126 кластеров), mymaps_100clusters.kmz, longdo/*.json (кластеры iTIC/RVP + гриды), solutions_pdf_*.txt (частично) | data.bangkok.go.th («License not specified», isopen=false) — контент из харвест-datastore data.go.th; KMZ — Google My Maps BMA; Longdo — iTIC/ThaiRSC/RVP без явной лицензии | **да** (без решения владельца по лицензии) | Таблицы готовы к ingestion по тикету 150 (факты, не скоринг); добрать тексты Solutions PDF 49–126 живым браузером; владельцу решить лицензию и отсутствие полей «погибшие/раненые» |
| cleanliness-bangkok | acquired | garbage-by-khet.csv (CC BY, через Wayback), waste-by-khet-tidy.csv / -named.csv (459 строк), khet-codes.json (50/50); alt-bma-garbage-service.csv | data.go.th CC BY (основной); alt-набор data.bangkok.go.th «License not specified»; wiki-коды CC BY-SA | основной — нет (CC BY); **alt-CSV — да** | Свести tidy с app/src/data/bangkok/districts.json через khet-codes.json в кандидат-факт cleanliness-сигнала (данные до 2018; код 1000 ≠ итог) |
| coworking | acquired | coworking-tokyo.json (105 записей, 31 с коорд.), coworking-bangkok.json (54, 5 с коорд.); сырьё 7 источников (wework-jp/ 30 карточек и др.) | WeWork, IWG/Regus/Spaces, JustCo, the Hive, GBH — все © владельцев, открытых лицензий нет | **да** (весь набор) | Геокодировать 74 записи по адресам; нормализация в редакционный стат-слой; расчёт признака «близость коворкинга» |
| medicine-jnto | acquired | medicine-jnto.json (2721 запись, Tokyo 508); raw/ 94 файла (47 префектур × eng/jpn); fetch_all.py, build.py | JNTO/Japan Tourism Agency «All Rights Reserved» | **да** (републикация строк запрещена; счётчики и ссылки на живой сайт — можно) | haversine-джойн по 800 м для факт-блока english_medicine (счётчики + ссылка, без строк); категории — инференс (hospital 937 / dental 674 / clinic 1110) |
| michelin | acquired | michelin-{tokyo,bangkok}.geojson/.csv/.roster.json (Tokyo 267 = 3★11/2★26/1★119/Bib111; Bangkok 71 = 2/8/29/32); raw/ 351 стр., geocode/cache/ 338 | guide.michelin.com — © Michelin (фактический ростер с атрибуцией); координаты — OSM/Nominatim ODbL | **да** (до лицензионного sign-off владельца; координаты — ODbL) | Point-in-polygon к кварталам/вокруг станций; кросс-чек имён с Wikipedia-ростерами; 101 null-геометрию можно добить по кэшу; тикет 142/177 «N★/M Bib in 800 m» |
| embassies | acquired | embassies-{bangkok,tokyo}.geojson (79/167 фич), summary.json, overpass/wikidata JSON; QA-находки в properties.qa | OSM ODbL 1.0 + Wikidata CC0 1.0 | нет — публикуемо (OSM-атрибуция обязательна) | Залить geojson в факт-блоки (тикет 145/180); owner-review трёх QA-находок: тег-ошибки country=IR/AR, Syldavia-шум, 31 wikidata-only объект без координат |
| housing-sweep | acquired | housing-bangkok.json/.csv (50 кхетов: 15 159 зданий / 3 080 апартаментов / 625 башен ≥20 / 128 станций); raw/ 47 ответов Overpass, run.log | OSM ODbL 1.0 (overpass-api.de, maps.mail.ru), штампы дамп в LICENSE/CSV | нет — публикуемо с ODbL-атрибуцией (с оговорками о нижних границах) | Инжест в facts (housing_apartments, towers_20plus по CRTKY-148 §7); stations_in_khet нормализовать до публикации (дырявое покрытие OSM) |
| tokyo-misc | acquired | kt10-reiwa7-keishicho.xlsx + digest.csv (30 176 ДТП / 134 погибших); homeless-surveys-summary.json (概数 507/557/565 + 実態 r3); minato_shoutengai.geojson (54 точки, из Wayback) | 警視庁/福祉局 — без явной open-data лицензии (цитировать как факт можно); 港区商店街 — CC BY (срез 2020–21, живой портал 403) | keishicho/福紙 PDF — **да**; Minato GeoJSON — нет (CC BY, с атрибуцией и пометкой среза) | digest/summary готовы к ingestion; для свежего Minato-среза скачать файл в браузере или зафиксировать archived-версию как канон |

## Сводка

1. **Объём и верификация.** 11 каталогов, 1313 файлов проверены фактическим перебором
   (`find research/snapshots/2026-10-14 -type f`); все артефакты из отчётов агентов
   присутствуют; счётчики записей перепроверены парсингом JSON/CSV — расхождений с
   отчётами нет. Лицензионные пометки сверены с LICENSE.txt всех каталогов.
2. **Полностью доставлено 8 из 11**: air-tokyo (280 zip, 146 МБ, 2019–2023),
   cleanliness-bangkok, coworking, medicine-jnto, michelin, embassies, housing-sweep,
   tokyo-misc.
3. **Частично 3**: air-bangkok (есть 2011–2020, нет 2021–2025), noise (TMG полностью,
   PCD — только метаданные), accidents-bangkok (таблицы/кластеры есть, тексты
   Solutions PDF — 1–40 полностью, 41–126 частично).
4. **Причина недобора одна и та же для тайских хостов**: pcd.gdcatalog.go.th и
   data.bangkok.go.th дропают TLS-хендшейк с этого IP (геоблок; 12 попыток в
   `noise/pcd_fetch_attempts.log`, все — в `accidents-bangkok/attempts.txt`); Wayback-каптур
   2021–2025 нет, Air4Thai API держит только последние месяцы, envilink.go.th — за
   интерактивной капчей. Разблокировка — тайский egress (VPN/прокси) или bulk-запрос в PCD.
5. **Открыто для публикации с атрибуцией**: embassies (ODbL + CC0), TMG-шум
   (CC BY 4.0: годоскоп 19-11 FY2018–2024, автодорожный шум FY2019–23), основной CSV
   cleanliness (CC BY, данные до 2018), housing-sweep (ODbL, нижние границы),
   Minato 商店街 GeoJSON (CC BY, срез 2020–21), координаты Michelin (ODbL).
6. **INTERNAL ONLY**: air-bangkok (лицензия не верифицирована), air-tokyo (© NIES),
   accidents-bangkok («License not specified»), coworking (7 © владельцев),
   medicine-jnto (JNTO All Rights Reserved — только счётчики/ссылки), ростер Michelin
   (© Michelin — до sign-off), keishicho/ホームレス PDF (без явной лицензии),
   alt-bma-garbage-service.csv. Единственный смешанный набор — michelin: координаты
   ODbL, гайд-контент проприетарен.
7. **ADR №3 «Air» (тики 146/172)** — токийская половина готова: годовые/месячные 確定値
   2019–2023 по 4 префектурам достаточно для сезонной панели; бангкокская — после
   докачки 2021–2025 (ежегодная cron-история с дек. 2026 не зависит от этого).
8. **ADR №4 «Noise» (151/175)** — токийские измерительные якоря в руках (267 точек
   FY2023 + годоскоп); тайский якорь (5 станций PCD) не достался — калибровка
   бангкокской модели ждёт егресс.
9. **ADR №5 «Institutions» (145/180) — готов к имплементационным тикетам полностью**:
   посольства (79/167 фич, двух-источниковая связка OSM+Wikidata) и JNTO-медицина
   (2721, Tokyo 508) с дисплеем «счётчики + ссылка», как и предписано решением.
10. **ADR №7 «Michelin» (142/177) — готов к тикету**: ростеры + геокодинг обоих
    городов (183/267 и 54/71), факт-блок «N★/M Bib in 800 m» считается сразу;
    формальный лицензионный sign-off владельца — по пометке LICENSE.txt.
11. **ADR №11 «BMA risk registry» (150) — данные в руках** (50 точек, 126 кластеров,
    кросс-чек KMZ 123/126, Longdo-гриды); тикет — факты + editorial-safety валидация;
    в источниках нет поля «погибшие/раненые», лицензия не указана → INTERNAL до
    решения владельца.
12. **Wave-4 конверсии ADR** (coworking, cleanliness из политики разовых закупок) —
    готовы к тикетам: геокодинг 74 записей коворкинга и свод waste-by-khet с
    districts.json (маппинг 50/50) — чисто механические шаги.
13. **Не покрыто этим забегом** (снапшотов нет): flood-решения №1–2, entertainment-зоны
    №6, tourist badge №8, WorldPop №9, HotPepper №10 — по ним данных волна-4 не завозила.
14. **Честные оговорки к качеству**: michelin — 101/338 null-геометрий и смена оценки
    Бангкока (~156 → 71 starred+Bib); coworking — 74/159 без координат, бренд «CCOC» не
    идентифицирован; JNTO-категории — инференс правила, не данные источника (276 записей
    без пробелов в eng-полях — артефакт источника); Minato GeoJSON — архивный срез
    (живой набор удалён с портала);TMG 白書-ресурсы 35/39 битые на стороне издателя
    (перекачаны как доказательство).
