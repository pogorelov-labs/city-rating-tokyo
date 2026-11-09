# Bangkok rail operator/line/status audit — findings (CRTKY-209, 2026-11-09)

Evidence: [`operator-audit.csv`](operator-audit.csv) (178 rows, one per station in
`app/src/data/bangkok/rail.json`), assembled from two independent research
passes (89+89, roster-first; raw records in [`raw/`](raw/), seeds and assembler
in this folder). Method: official rosters first — BTS route map, NBM map, MRTA
line/project pages, SRTET route + per-station pages — OSM strictly as
cross-check, dated news only for 2025–2026 changes. Status: **all 178 stations
operational** as of 2026-11-09; no under-construction/planned/closed rows.

## Classification: 119 match · 57 naming · 2 factual

### Factual (pipeline-ticket material — 2)
Both are **missing dark-red-line membership** on shared station complexes,
source: SRTET official served-station roster:
1. `bang-bamru` — recorded `srt_light_red` only; the complex is served by both
   SRT red lines.
2. `bang-son` — recorded `mrt_purple` + `srt_light_red`; the roster also lists
   the dark red route (Purple interchange).
Proposed correction: add `srt_dark_red` to both stations' `lines` (pipeline
change via the deterministic replay contract, not a hand edit).

### Naming (owner decision — 57)
`rail.json` records **service/brand labels**; the audit records the
**operating concessionaire**:
- Yellow Line (20 stations): label "MRT" → operator **Eastern Bangkok Monorail
  Co. (EBM)**, BTS Group subsidiary under MRTA concession.
- Pink Line (29): "MRT" → **Northern Bangkok Monorail Co. (NBM)**, same structure.
- ARL (8): "ARL" is the line brand; operator is **Asia Era One Co., Ltd.**
  (under SRT agreement since 2021). Dated development: SRT/Asia Era One
  dispute → 4-month SRT MOU from 2026-10-01, **SRTET takeover from 2027-02-01**
  (Nation Thailand, 2026-09-25). The audit's per-station operator field keeps
  the current-era operator; a convention decision below covers this.
- Blue/Purple (MRTA-owned, BEM-operated), BTS, Red lines: labels verified
  consistent; not flagged.

No convention change is proposed unilaterally: either keep service-name labels
(today's app behavior; cheapest) or switch to concessionaire strings (more
precise; touches rail.json + any operator-displaying surface). Owner decides.

### Consistency notes (for the pipeline ticket draft)
- `si-rat` (Pink): MRTA calls main-line PK10 "formerly named Si Rat" while
  current operator maps list PK09 Si Rat + PK10 Muang Thong Thani (extension,
  commercial open 2025-06-17 per Thai PBS World, 2026-05-20 trial report).
  rail.json's separate `si-rat` entry should be re-checked against the current
  NBM/MRTA maps before any copy cites it.
- Pink western section (4 Nonthaburi stations) was suspended 2025-09-13 →
  2025-12-03 after a power-rail failure; full service resumed (MRTA release).
  Historical only — no status change.
- 3 Purple stations (`bang-krasor`, `bang-rak-yai`, `ministry-of-public-health`)
  verified medium-confidence: Purple membership confirmed via OSM relation
  cross-check only; no reachable official page names them individually.

## Gates
- Link health: 12/12 sampled source URLs live (29 distinct URLs in the CSV);
  one MRTA deep link now 302s to the homepage — domain alive, path moved.
- Personal-data scan: **P1=0, P2=0** (kit scanner, 2026-11-09).
- Coverage: 178/178 ids, each exactly once, each with ≥1 HTTPS source.

## Source-access limits (documented, worked around)
`bangkokmetro.co.th` (BEM) connect-timeout; `airportraillink.railway.co.th` DNS
failure; `railway.co.th` (SRT) timeout; AOT Suvarnabhumi page is a JS SPA with
no extractable ARL list. Compensating official coverage: BTS route map (all
BTS/Yellow/Pink stations), MRTA pages, srtet.co.th (Red Line roster + station
pages), NBM official map. Wikipedia line tables were used as a compiled
cross-check only and are not cited as evidence.
