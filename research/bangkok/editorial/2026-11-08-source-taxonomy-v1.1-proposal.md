# B-12 proposal — source-type taxonomy v1.1 (measured, 2026-11-08)

Measured over all 665 source records (post-repair). The current enum sends
**58% of sources to the collapsed `other` bucket**, hiding the corpus's
evidential spine (encyclopedia + map data). Proposal for the editorial line
(owner: SL; adoption decision recorded here or superseded):

## Observed distribution

`other` 386 (58%) · news 81 (12%) · editorial_guide 78 (12%) ·
commercial_property 57 (9%) · tourism_publisher 19 (3%) · government 17 (3%)
· official_operator 13 (2%) · expat_publication 9 (1%) · resident_report 3 ·
academic 2.

Inside `other`, the top publishers are Wikipedia (~200 records across
spelling/language variants), OpenStreetMap/Overpass (~25), property portals
mislabeled `other` (HipFlat/FazWaz/Superagent ~15), and operator/corporate
pages (the old NORM_TYPE mapping sent `official_site`/`corporate_site` to
`other`).

## Proposed enum additions (additive only — no reclassification of existing values)

1. `encyclopedia` — Wikipedia/Wikimedia projects (the corpus's largest family
   deserves visibility; corroboration already canonicalizes it via
   `kit/canonical.py`, so this is reporting, not independence logic).
2. `openstreetmap` — OSM/Overpass/Nominatim dataset records.
3. `aggregator_dataset` — Overpass-derived or portal-statistics records that
   are query outputs rather than pages.

## Migration policy

- Enum extension is additive; old bundles keep `other` (provenance intact) —
  the reporting layer may map `other` records through the B-11 registry when
  it needs the finer view, so **no bundle rewrite is required**.
- From the next batch, the prompt template's `type` enum gains the three
  values and `assemble.py`'s NORM_TYPE stops routing encyclopedia/OSM to
  `other` (they become their own types; one-line map change).
- Source-mix per bundle: report at manifest level (counts per type) — cheap
  and makes the independence-concentration visible per batch.

Decision needed (SL): adopt v1.1 for the next batch, or keep `other` and rely
on the B-11 registry for reporting. Either is honest; v1.1 is recommended
because the 58% bucket hides exactly the concentration the deep review
flagged (C-ep1).
