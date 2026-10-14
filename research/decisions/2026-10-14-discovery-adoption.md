# ADR: Discovery adoption decisions — 2026-10-14

Owner decisions over the 29-ticket research program (waves 1–3, notes in
`research/notes/` and `research/bangkok/notes/`). Accepted via interview
2026-10-14 (waves answered directly; all recommended options). Reopen
conditions recorded per item. Spin-off implementation tickets to be created
from the adopted items.

## Adopted

| # | Decision | Tickets | Key parameters |
|---|---|---|---|
| 1 | Bangkok flood: adopt ThaiFloodRisk as primary; **mirror the 68 kB Zenodo archive into `data/bangkok/raw/` with SHA pin** (doctrine of ingest-crime) | 139 → 131 | episodes 2021–2026 primary; GISTDA-2011 share secondary |
| 2 | Tokyo flood: replace SRTM<5 m proxy with TMG 浸水予想区域図 (14 zones) + A31b for non-Tokyo stations; **depth threshold 0.5 m (MLIT class ≥2)**; ~630 MB pinned downloads accepted | 171 | rain scenario (計画 vs 想定最大) to be fact-checked against the 図郭割 PDF at implementation — not an owner choice |
| 3 | Air (both cities): composition B — city seasonal panel + live PM2.5 chip (+ pollen Feb–Apr Tokyo); no rating category | 146, 172 | Bangkok metric: % days Dec–Mar ≥ 37.5 µg/m³; history via cron from Dec 2026 and/or archive acquisition |
| 4 | Noise (both cities): modeled day/night pair with measured anchors, honest `estimate` label | 151, 175 | Tokyo calibrated against 267 TMG points (CC BY 4.0); Bangkok anchored by 5 PCD stations |
| 5 | Institutions: fact blocks on station AND district pages — embassies (two-source strong) + English-speaking medicine (JNTO, citation-only display) | 145, 180 | international schools via curated overlay later |
| 6 | Entertainment zones: both curated lists approved (Bangkok 6, Tokyo 7) + shared `kind` taxonomy; family filter triggers on `adult_entertainment` only; no score mixing | 153, 182 | Ёсивара NOT included — can be added later as a separate decision; 錦糸町 South side correction accepted |
| 7 | Michelin: fact-only on pages («N★ / M Bib in 800 m»); annual scrape + one-off geocode; no percentile interference | 142, 177 | Tabelog rejected (terms §9(1)) |
| 8 | Tourist badge: thresholds per city distributions — Tokyo ≥15 hotels/800 m, Bangkok ≥50 hotels OR ≥8 attractions/800 m; unified center-in-circle counting | 152, 173 | estimate-grade label |
| 9 | WorldPop constrained 2020: **full replacement** of DOPA density in Bangkok district quietness | 140 | rasterio build dep, +29 MB cache, CC-BY-4.0 attribution |
| 10 | HotPepper: resilience package now (per-source data_date, freshness canary in refresh-ratings.sh, key runbook) + one HP↔Overture correlation experiment as the gate to a second source | 184 | two-source strong if passed |
| 11 | BMA risk registry: facts + editorial-safety validation only, **no score input** | 150 | publication framing per the ticket's constraints |

## Rejected (with reopen conditions)

- **Mesh census Tokyo** — no consumer improves; reopen if a Tokyo grid level is
  ever built. Ticket 183 closed as done.
- **Tabelog** — terms prohibit storage of scraped data; reopen on a licensed API.
- **WRI Aqueduct as primary flood source** — model-only, ignores flood
  protection; superseded by observed/official data; reopen only for a city
  with neither.
- **A51 as Tokyo flood input** — coverage failure (one municipality, 0/854
  stations); stays valid for Saitama/Kanagawa; reopen on full Tokyo coverage.
- **Air interpolation to districts** — 10 monitors / 50 districts is false
  precision (honesty doctrine); reopen on a materially denser open network.

## Converted by the owner's one-off acquisition policy (2026-10-14)

«If something can be obtained at least once — scraped and mapped via
sub-agents, filled in one-off, or scanned from the internet — do it.»
Under this policy two rejects become acquisition tasks and the accumulated
«manual/blocked» items from all waves enter one acquisition run (wave 4):

- **Coworking (was rejected on OSM sparsity)** → build curated chain-location
  lists (WeWork, Regus, …) as editorial static data for both cities.
- **Bangkok cleanliness (was rejected on access)** → attempt one-off acquisition
  of the CC-BY waste-per-khet CSV (data.go.th behind WAF) and alternatives.
- Air/noise archives (gdcatalog Bangkok, そらまめ bulk, PCD noise station/annual
  CSVs), Bangkok accident XLSX + ThaiRsc clusters, JNTO medicine snapshot,
  Michelin rosters + geocoding, embassy tables, housing 46-khet sweep,
  警視庁 accident Excel + 路上生活調査 PDFs, 港区商店街 GeoJSON — all as one-off
  sub-agent acquisitions under `research/snapshots/` (license per item in the
  run index; graduation into `data/` is a later owner decision per item).

Acceptance source: owner interview 2026-10-14 (waves 1 and 3 in text,
wave 2 via interactive answers; all recommended options; item 12 resolved as
the acquisition policy above).
