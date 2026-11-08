# A-6 AG sweep — Thai-language sources in copy-bearing claims (2026-11-08)

The A-6 gate (G13) requires Thai-capable verification of Thai-sourced claims
that surface in copy — or their exclusion from copy. This pass is the
**agent-executable half**: the census, the in-session verifications, and the
exclusion rule. The **human Thai-capable pass remains open** (HR/DEC-2).

## Census

**238 copy-bearing claim-uses cite 117 distinct Thai-language sources across
36 bundles** (machine-readable list:
[`2026-11-08-a6-thai-census.json`](2026-11-08-a6-thai-census.json) — URL,
usage count, body_read state, and the citing claim IDs per source).

Composition of the top of the list: Thai Wikipedia district/station articles
(bang-phlat, khlong-san, saphan-taksin, sathon, thon-buri, phaya-thai,
bang-sue, dusit, chatuchak-park), operator pages (Chao Phraya Express Boat),
and Thai neighborhood guides (PropertySights, ThaiHometown). Nearly all were
`body_read=true` at research time, and their structured facts were
cross-checked during the program (EN-Wikipedia cross-refs, geometry passes,
app-data comparisons).

## Verified in this session (9 sources)

Seven Thai bodies were fetched and term-matched during the A-8 rework
(tiewgan, thaipost, baanlaesuan, aroundonline, thipsamai, wongnai ×2 — see
the rework ledger), plus this pass: the PropertySights Asok 2569 guide
(อโศก + 2569 matched). These verifications are at **body-presence +
term-match** level — the semantic-reading check for the surrounding Thai
prose still belongs to the human pass.

## Flagged (JS shells — not re-verifiable from this environment)

- `thaihometown.com` Soi Nana guide (5 claim-uses): 200 but terms absent —
  likely a JS shell.
- `chaophrayaexpressboat.com` operator site (5 claim-uses): SPA shell; terms
  absent from the static fetch.

The claims these two sources support are corroborated by additional sources
in their bundles, so no copy text rests on them alone — but the human A-6
pass should confirm them in a browser.

## Rule going forward (E-5/A-6 interlock)

At adapter time, copy citing a claim whose corroboration **rests on Thai
sources not covered by the human A-6 pass** stays excluded until that pass
signs off. The census JSON is the worklist for that pass: 117 sources, sorted
by copy usage; the seven already-verified + the two flagged are marked.

## Residual risk carried

Reading-quality risk (subtle Thai qualifiers) is exactly what the human pass
exists for; the agent-level checks (fetch, term-match, corroboration counts,
canonical families) bound it but do not eliminate it.
