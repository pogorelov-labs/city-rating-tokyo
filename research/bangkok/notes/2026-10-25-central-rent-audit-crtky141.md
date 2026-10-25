# Central Bangkok asking-rent audit (CRTKY-141 / CRTKY-136)

Accessed **2026-10-25**. This extends the [2026-10-13 anchor audit](2026-10-13-rent-anchors-crtky141.md).

## Metric and adoption decision

The reference metric remains **asking rent, THB/month, for a roughly 30–35 m²
1BR or 60–70 m² 2BR condominium**, excluding serviced apartments and short
stays. It is a typical corridor estimate, not a transaction price or a
statistical median. No district value or district confidence changes in this
audit: none of the sources below isolates that exact size/tenure cohort over
an entire khet.

Ten station areas instead receive a clearly named **proxy: published median
condominium asking rent by bedroom count, all floor areas, within the source's
800 m station radius**. All ten have **estimate** confidence, never strong.
These are direct transcriptions of the bedroom-table medians, not calculations
from per-m² rates, adjusted rents, or a blend with the old editorial figures.
The UI must show the different metric, source, date and separate 1BR/2BR n.
The provider does not disclose a minimum lease-duration filter. Consequently
these proxies cannot claim the reference metric's short-stay exclusion.

## Independent source table

Each row links the public DooAsset station page, independent of Vurel. Numbers
are THB/month; n is the rental count for that bedroom row, not total listings,
sales, projects, or all-unit rentals. All rows were accessed 2026-10-25.
Dates are the dates printed on the source, not this application's build date.

| Area / station-area id | Source | Source as-of | 1BR median / n | 2BR median / n | Published typical size | Decision |
|---|---|---|---:|---:|---|---|
| Thong Lo / `thong-lo` | [DooAsset](https://dooasset.com/en/area/bts-thong-lo/) | 2026-09-29 | 28,000 / 33 | 56,500 / 24 | 1BR 38 m²; 2BR not stated | estimate proxy |
| Ekkamai / `ekkamai` | [DooAsset](https://dooasset.com/en/area/bts-ekkamai/) | 2026-10-25 | 27,000 / 38 | 50,000 / 16 | 1BR 35 m²; 2BR not stated | estimate proxy |
| Phrom Phong / `phrom-phong` | [DooAsset](https://dooasset.com/en/area/bts-phrom-phong/) | 2026-10-25 | 48,000 / 19 | 52,500 / 26 | 1BR not stated; 2BR 68.2 m² | estimate proxy |
| Asok / `asok` (MRT Sukhumvit interchange) | [DooAsset](https://dooasset.com/en/area/bts-asok/) | 2026-10-25 | 26,500 / 30 | 55,000 / 18 | 1BR 35 m²; 2BR not stated | estimate proxy |
| Nana / `nana` | [DooAsset](https://dooasset.com/en/area/bts-nana/) | 2026-10-17 | 28,000 / 27 | 60,000 / 11 | 1BR 35 m²; 2BR not stated | estimate proxy |
| Chit Lom / `chit-lom` | [DooAsset](https://dooasset.com/en/area/bts-chit-lom/) | 2026-10-21 | 45,000 / 11 | 120,000 / 11 | 1BR 56 m²; 2BR not stated | estimate proxy; pronounced size/luxury skew |
| Siam / `siam` | [DooAsset](https://dooasset.com/en/area/bts-siam/) | 2026-10-25 | suppressed / 3 | suppressed / 2 | not stated | retain editorial; no bedroom medians |
| Sala Daeng / `sala-daeng` (MRT Si Lom interchange) | [DooAsset](https://dooasset.com/en/area/bts-sala-daeng/) | 2026-10-07 | 38,000 / 13 | 60,000 / 13 | 1BR 44 m²; 2BR not stated | estimate proxy |
| Sathon / `chong-nonsi` | [DooAsset](https://dooasset.com/en/area/bts-chong-nonsi/) | 2026-10-01 | 24,000 / 9 | 72,000 / 16 | 1BR not stated; 2BR 93.3 m² | estimate proxy; larger 2BR cohort |
| Ari / `ari` | [DooAsset](https://dooasset.com/en/area/bts-ari/) | 2026-10-22 | 27,000 / 8 | suppressed / 3 | 1BR 44.5 m² | retain editorial; incomplete pair, larger 1BR cohort |
| Ratchathewi / `ratchathewi` | [DooAsset](https://dooasset.com/en/area/bts-ratchathewi/) | 2026-10-07 | 21,500 / 10 | 38,000 / 5 | 1BR 34 m²; 2BR not stated | estimate proxy; 2BR at publication threshold |
| Phaya Thai / `phaya-thai` | [DooAsset](https://dooasset.com/en/area/bts-phaya-thai/) | 2026-10-10 | 25,000 / 23 | 43,500 / 6 | 1BR 34 m²; 2BR not stated | estimate proxy; small 2BR cohort |

These are single-provider snapshots, not representative market samples. The
large Phrom Phong 1BR median and the Chit Lom 2BR median are preserved exactly
as published, rather than made to fit an expected ordering or scaled down to
our reference size. A typical size in the table is a sample descriptor, **not
a filter**. Unknown sizes stay null in the input file.

## Method, access, rights and limitations

[DooAsset's methodology](https://dooasset.com/en/methodology/) describes:
available inventory; medians published from at least five listings;
deduplication of the same unit; an 800 m straight-line station radius;
daily availability checks with unconfirmed listings retained for up to 30
days; and periodically recalculated aggregates. These are provider claims,
not independently verified controls. Its full-radius cohorts can overlap
neighboring stations and differ from our nearest-station catchments. They do
not identify every unit's lease term. Condo-only tables separate apartments,
but do not establish a serviced-unit exclusion for every listing.

Public pages were individually researched through web search and public-page
text, without pagination, listing extraction, private APIs, paid access, or
copying listing descriptions/photos. A subsequent direct HTTP request to the
Thong Lo page returned **403**; automated access was stopped, with no retry,
agent spoofing, or alternative extractor to bypass the block. PropertySights
also returned 403 and was not pursued. The isolated factual aggregates above
are attributed citations, not republication of a portal database or page text.
The methodology separately says **market-data CSV files** are CC BY 4.0;
no CSV was retrieved and this audit does **not** assert that license covers
the website. [Terms](https://dooasset.com/en/terms/) prohibit bulk scraping
and republication without permission. No bulk scraper is added to the project.

The pages are live. Search summaries and page representations can have
different dates (Thong Lo's search result had an October snapshot, whereas
the readable page showed September 29). We pin the complete bedroom-table
snapshot actually read, not a combination of dates. Some FAQ/count sections
lag their bedroom tables (notably Asok, Ekkamai and Phaya Thai); only the
dated bedroom rows set both medians and n. This inconsistency is another
reason for estimate confidence and a future refresh, not a strong rating.

## Additional checks and rejected substitutions

* [PropertyScout Thong Lo](https://propertyscout.co.th/en/bangkok/thong-lo/rentals/condo/),
  accessed 2026-10-25: comparison table 1BR 33,168 (4,223 advertised listings),
  2BR 63,207 (2,357); FAQ instead 33,772 / 65,426. All-size **means**, not
  fixed-size medians, no separate data-as-of. Not used to set values.
* [PropertyScout Siam](https://propertyscout.co.th/en/bangkok/siam/rentals/condo/),
  accessed 2026-10-25: table 1BR 26,247 (308), 2BR 40,170 (89); FAQ
  26,759 / 50,218. Its advertised Siam geography includes Sam Yan and National
  Stadium properties. No station override: inconsistent statistics and
  geography wider than the Siam catchment.
* [FazWaz Thong Lo](https://www.fazwaz.co.th/en/property-for-rent/thailand/bangkok/khlong-toei/phra-khanong/near-thong-lo-bts),
  public search summary accessed 2026-10-25, no dated observation window:
  1BR **average** 40,700 (1,582), 2BR average 72,800 (1,105), all-property
  median 49,800 (3,111). Different mix, no size filter; cross-check only.
* [Vurel September 2026](https://vurel.io/blog/bangkok-condo-rents-by-zone-2026),
  accessed 2026-10-25, data window 2026-08-29–2026-09-28: Chidlom–Ploenchit
  38,000; Sathorn–Silom 35,000; Khlong Toei–Rama 4 35,000; Sukhumvit 32,000;
  Ratchathewi–Phaya Thai 29,000; Ari–Saphan Khwai 23,000. All-bedroom condo
  medians, eight portals, at least 1,900 live rentals per zone. The source
  says listings are **not** merged across portals. Self-published cross-check
  only; no Vurel value becomes a 1BR or 2BR input.

## Coverage and remaining gaps

Ten overrides, two target gaps (Ari and Siam), 123 unchanged resident-weighted
area estimates. Surasak, Saint Louis and the other areas get no extrapolated
Chong Nonsi/Silom value. All 50 district rents remain editorial, including
Pathum Wan, Watthana, Khlong Toei, Bang Rak, Sathon, Ratchathewi and Phaya Thai.
The 200 m grid continues to inherit its owning district's rent; station
overrides affect station-area values and affordability ratings only.

A later exact-metric study still needs dated, licensed, deduplicated
long-lease condo cohorts in the two reference size bands. These proxies
provide neighborhood-specific evidence with visible limits, not a claim
that this exact-metric gap has been solved.

## Regeneration and scope checks

The untracked OSM/Wikidata/Overture raw cache is absent from this AO worktree.
`uv run scripts/bangkok/build.py` was attempted and stopped at missing
`data/bangkok/raw/boundaries.json`. Reacquiring today's POIs would change
unrelated categories, so this PR adds `--rent-only` to refresh the committed
spatial baseline. It validates all 50 districts and the area/grid join,
rejects district rent changes that require recomputing resident shares,
retains each area's original editorial pair for override removal, and checks
the committed grid binary against its content hash. It uses the same rent
functions as the full spatial build. The full spatial build remains unverified
in this worktree until its original raw inputs are available.

The successful rent-only refresh preserves all 50 district rent pairs, the
123 non-overridden area pairs, every non-rent rating/confidence/source, and
the 39,149-cell grid binary (`grid-4ab45661dc7b.bin`). Source observation dates
remain separate from the baseline's spatial generation date.

Phrom Phong **1BR 48,000**, Chit Lom **2BR 120,000**, and Chong Nonsi
**2BR 72,000** are explicitly flagged in the UI as composition-skewed published
proxies, not typical reference-size rents. Published typical sizes are shown
beside the values when available; unknown sizes are identified as unpublished.
