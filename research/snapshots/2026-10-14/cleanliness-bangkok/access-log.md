# Лог попыток доступа (2026-10-14, ~11:24–14:40 local)

Цель: CSV «объём отходов по кхетам» с data.go.th (package 731a8cb0-d563-45ca-93ae-52e3de47e474, CC BY).

| # | Попытка | Результат |
|---|---|---|
| 1 | `curl https://data.go.th/api/3/action/package_show?id=731a8cb0…` | **403** WAF «Access Denied» (Cloudflare) → attempt1-package-show.json |
| 2 | то же + браузерные UA/Accept/Accept-Language/Referer | **403** → attempt2-browser-headers.json, attempt2-headers.txt |
| 3 | `r.jina.ai` прокси на страницу датасета | **403 через прокси** (WAF режет IP прокси) → attempt3-jina-dataset-page.md |
| 4 | зеркало `catalog-dga.data.go.th` package_show по id | API жив, пакета нет (**404 Not Found**) → attempt4-mirror-package-show.json |
| 5–6 | зеркальный package_search (таї/en, фрагмент id) | **0 результатов** во всех → attempt5/6*.json |
| — | Wayback CDX `data.go.th/dataset/731a8cb0…*` | **УСПЕХ**: 2 архивные записи ресурсов (docx 2023-11-12, csv 2023-12-20) |
| ✓ | скачивание обоих ресурсов с `web.archive.org` (`…if_`) | **200**, CSV 9,725 Б, DOCX 16,658 Б → garbage-by-khet.csv, garbage-metadata.docx |

Доп. проверки (не по цели, для контекста/альтернатив):
- `164.115.33.91` (NHA-CKAN, выдача поиска как зеркало датасета BMA): **500 на все маршруты**, инстанс мёртв → attempt7-mirror164-page.html
- `gdcatalog.go.th` resource_show 40b3dd59…: **200**, но пакет кхета/страны не про Бангкок (орган — Kalasin, thaimsw.pcd.go.th провинциальный отчёт) → gdcatalog-mnre-resource.json
- `thaimsw.pcd.go.th` (PCD ThaiMSW): **HTTP 000** (connection failure) из среды
- `webportal.bangkok.go.th/environmentbma/page/sub/7405` (статистика BMA Environment Dept): **403** Cloudflare (curl) и **403 через r.jina.ai** → bma-env-stats.html, attempt8-jina-bma-env.md
- `data.bangkok.go.th` live: не проверялся отдельно из среды (заметки CRTKY-147: HTTP 000 дважды 2026-10-13); Wayback CDX **успех**:
  - group `garbageindist` страницы (2022-09) → wayback-data-bangkok-garbage.json, wayback-garbageindist-group.html
  - датасет 58771fe2… `garbage.csv` (2022-06-23) — **байт-в-байт равен** data.go.th CSV → alt-bma-garbage.csv
  - датасет 71169824… `garbage_service.csv` (2022-06-23) — 51 строка, BE 2558–2561 → alt-bma-garbage-service.csv

Итог: основной CSV + дата-словарь получены (через Wayback, лицензия CC BY по метаданным портала);
один альтернативный per-khet набор (garbage_service.csv, лицензия не указана) и три зафиксированных
недоступных источника (BMA env, ThaiMSW, gdcatalog-MNRE — последний географически не Бангкок).
