# notes — air-bangkok (2026-10-14)

Задача: датасет `gdpublish-air-quality-bangkok-metropolitan-region` на gdcatalog.go.th, годовые CSV PM2.5 по станциям, 2011–2025.

## Итог по годам
- **Получено: 2011–2020 (10 из 15 лет)** — официальные годовые книги PCD `PM2.5(2011..2020).xlsx`
  (лист «PM2.5» = даты × ID станций, лист «รายละเอียด» = метаданные станций).
  Путь: `wayback_rar_2011_2020/`.
- **Не получено: 2021–2025 (5 лет)** — файловый хост недоступен из этой сети; зеркал нет (см. лог).

Проверка содержимого (xlsx_summary.json): полный календарный год в каждом файле
(365/366 строк-дат, 2011: 1 станция 54T → 2019–2020: 23 станции 02T/05T/10T/…, сеть росла).

## Как добыты 2011–2020
CKAN API `gdcatalog.go.th/api/3/action/package_show` отдал 15 ресурсов (метаданные целы),
но файлы лежат на `pcd.gdcatalog.go.th`. В Wayback Machine нашёлся capture 2022-06-22 официального
`.rar`-бандла, прицепленного к ресурсу 2011: внутри xlsx за 2011–2020.
URL: `https://web.archive.org/web/20220622044235if_/https://pcd.gdcatalog.go.th/dataset/78495048-.../resource/d15285e8-.../download/.rar`

## Лог попыток достать CSV (особенно 2021–2025)
1. `curl` прямой на pcd.gdcatalog.go.th (дефолт и браузерный UA): TCP-коннект ок (~6 мс), **TLS-handshake падает по таймауту**; plain HTTP :80 — чёрная дыра (0 байт). Признак серверного/SNI-геоблока не-тайских IP.
2. `--resolve` через CNAME `asfour.gdcatalog.go.th` (164.115.45.230) как SNI — тот же SSL timeout.
3. Маршрут скачивания через главный портал `gdcatalog.go.th/dataset/<pkg>/resource/<res>/download/...` — **404** (федеративный каталог, файлов у себя не хранит).
4. WebFetch (другой egress) — connect timeout.
5. r.jina.ai-прокси — сам не резолвит хост («Could not resolve hostname»).
6. MCP-браузер (Chromium) на прямой URL — навигация по таймауту.
7. envilink: `envilink.gdcatalog.go.th` не резолвится; `envilink.go.th` (актуальный CKAN Envilink) за **Cloudflare interactive challenge** (audio-captcha) — программно не преодолеваю намеренно (обход капчи не делаем).
8. Wayback CDX по всему каталогу датасета: только страница датасета + этот `.rar`; годовых CSV 2021+ **нет**.
9. Wayback Save Page Now на pm2.52021.csv — HTTP 520.
10. archive.today (`archive.ph/newest/...`) — 404, каптур нет.
11. Поиск зеркал: GitHub code search по точным именам файлов (`aqpm2.5bangkok…`, `pm2.52022.csv`, slug датасета) — 0; HuggingFace datasets — 0.
12. Air4Thai (тот же PCD, хост доступен): `air4thai.com/forweb/getHistoryData.php` (эндпоинт найден в open-source репо dookda/envi_aqi_bot) отвечает 200 и возвращает почасовой PM25, **но глубина архива — только последние месяцы** (2025 и ранее: 0 строк) → заменой для 2021–2025 служить не может.
13. aqmthai.com (старый портал PCD) — соединение не устанавливается (000).
14. `air4thai.com/forweb/getBooks.php` — годовые PDF-отчёты (нарративные), не сырые данные.

## Побочные полезные артефакты
- `gdcatalog_package_show.json` — полные метаданные всех 15 ресурсов (URL для повторной попытки, когда хост станет доступен).
- `air4thai_history_stations.json` — реестр станций Air4Thai с тайскими/английскими названиями и адресами (121 КБ).
- `download_manifest.json` — статус по каждому году: URL ресурса, источник, причина неудачи для 2021–2025.
- `xlsx_summary.json` — машинно-читаемая сводка каждого xlsx (диапазон дат, станции, заполненность).

## Рекомендация для следующей попытки
Скачивание 2021–2025 с pcd.gdcatalog.go.th через тайский egress (VPN/прокси в Таиланде) — метаданные и точные URL уже в манифесте; либо прямая переписка с PCD (aqnis.web@gmail.com, процедура в manual_2569.pdf).
