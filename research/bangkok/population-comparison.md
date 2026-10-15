# Bangkok population replacement: owner review (CRTKY-197)

Adoption comparison against `505ae726489fffc6548bd7bb789a1d8d0e0089cb`, computed 2026-10-15. **Owner review of this diff is required before merge.**

## Observed result

All **50/50 districts** covered. WorldPop constrained 2020 sums to **10,887,568** people, versus **5,588,222** DOPA-registered people (2020 via Wikidata): **1.9483×**, or **5,299,346** more in the model. Registration is **48.67% below the model** (the model is 94.83% above registration; these denominators differ).

**20/50 ratings change, all by one point; 30 are unchanged.** Higher crowd/quietness scores mean quieter. The POI term, official-area denominator, normalization and other scoring behavior are preserved. Pathum Wan changes 2→1, Bang Rak 1→2, Chatuchak 5→4. Watthana stays 2; Nong Chok stays 10. All facts, non-crowd ratings, station areas, resident weights, grid binaries and noise data remain unchanged.

The 20 changed districts and directions match the research simulation. The measured population total is **7,063 (+0.065%) higher** than its quoted 10,880,505. Watthana is 221,729 vs the note’s 221,663; Samphanthawong is 20,440 vs 19,868. Eight of the ten quoted district totals reproduce to rounding. The note retained neither a raster SHA nor executable aggregation code, so the remaining difference cannot be attributed conclusively. Independent per-district cropped raster masks and direct Shapely pixel-center selection agree with this implementation’s total. We do not force the earlier number.

## What the gap means—and what it does not

This is a model-to-registration comparison, not a census measurement of unregistered residents. WorldPop redistributes census/projection estimates using a settlement model; the result is consistent with the expected registration gap in central residential districts but does not independently measure that gap. Both population epochs are 2020; neither describes 2026 construction or daytime visitors.

Methodological artifacts are kept visible:

- **Denominator:** WorldPop is summed inside published OSM polygons but divided by the same official district area as before. OSM and official areas differ, especially along rivers. The all-50 CSV includes UTM 47N polygon area for audit; it is not substituted into scoring. Thus district ratios can contain boundary mismatch as well as population-model effects.
- **Pixel geometry:** the source is EPSG:4326, float32, 9,952×17,816, with 3 arc-second angular cells. Bangkok cell areas are approximately **8,300–8,321 m²**, not 10,000 m². Values already represent people per pixel: no pixel-area multiplier or density resampling is applied.
- **Coverage:** 188,638 district pixel centers, of which 132,767 have modeled population. NoData −99,999 means BSGM-unsettled and contributes zero. Holes are excluded. No pixel is assigned to two districts; the sum of all districts equals the union total within 0.000001 people.
- **Saved POI precision:** the original committed crowd signal has four decimals. Replay preserves its inferred POI log term with at most ±0.00005 raw uncertainty; every new rating is stable under the worst-case interval. Integer POI counts are not reconstructed. A full build uses its original exact count directly.
- **Historical cache:** the original OSM/Overture/Wikidata raw cache is unavailable. Full historical `build.py` replay remains **unverified** and fails explicitly on missing `boundaries.json`; the verified population-only replay uses the committed geometry/signals and refreshes no unrelated sources.

Selected density comparisons (people/km²; unrounded inputs are in the CSV):

| District | Registered | WorldPop | Ratio | Official km² | OSM polygon km² | Quietness |
|---|---:|---:|---:|---:|---:|---|
| bang-kapi | 5,074 | 15,294 | 3.01× | 28.52 | 27.62 | 5 → 5 |
| chatuchak | 4,719 | 13,671 | 2.90× | 32.91 | 32.56 | 5 → 4 |
| watthana | 6,496 | 17,654 | 2.72× | 12.56 | 12.97 | 2 → 2 |
| nong-chok | 753 | 948 | 1.26× | 236.26 | 238.00 | 10 → 10 |
| samphanthawong | 15,059 | 14,394 | 0.96× | 1.42 | 1.43 | 1 → 1 |
| bang-rak | 8,259 | 13,516 | 1.64× | 5.54 | 3.94 | 1 → 2 |

## Reproduce and inspect

```sh
uv run scripts/bangkok/fetch-population.py
uv run scripts/bangkok/rebuild-population.py
uv run --with pytest --with requests --with numpy --with shapely --with rasterio pytest scripts/bangkok
```

The fetch verifies bytes and SHA on both download and cache hit. `--refresh` replaces an existing file only after verification; failures leave the old cache intact. Two consecutive offline replays produce byte-identical generated outputs. Replay validates non-crowd snapshot signatures and requires the exact original signal file or verified previous replay; changed POIs, crowd values, provenance or anchors are rejected before any write.

- [All 50 districts, full-precision CSV](../../data/bangkok/population-comparison.csv)
- [Machine-readable comparison and provenance](../../data/bangkok/population-comparison.json)
- [Frozen original inputs](../../data/bangkok/population-baseline.json)
- [Pinned source manifest](../../data/bangkok/population-source.json)

Raster SHA-256: `400dc5435e15e78ce6b5e510327ec863c62d209011ce1b03cad4445773753d42`; **28,878,233 bytes**. Source: [WorldPop record 49890](https://hub.worldpop.org/geodata/summary?id=49890), constrained 2020 BSGM, produced 2020-09-16; Bondarenko, Kerr, Sorichetta and Tatem, WorldPop / University of Southampton, [doi:10.5258/SOTON/WP00684](https://doi.org/10.5258/SOTON/WP00684), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Adaptation: district aggregation and density scoring by City Rating.

## All 50 districts

| District | Registered people | Official km² | Old density input | WorldPop people | New density | Quietness before → after | Δ |
|---|---:|---:|---:|---:|---:|---|---:|
| bang-bon | 104,366 | 34.74 | 3,004 | 179,746 | 5,174 | 9 → 9 | +0 |
| bang-kapi | 144,732 | 28.52 | 5,074 | 436,196 | 15,294 | 5 → 5 | +0 |
| bang-khae | 193,303 | 44.46 | 4,348 | 380,583 | 8,560 | 7 → 7 | +0 |
| bang-khen | 187,377 | 42.12 | 4,448 | 327,092 | 7,766 | 7 → 7 | +0 |
| bang-kho-laem | 82,733 | 10.92 | 7,576 | 161,002 | 14,744 | 4 → 5 | +1 |
| bang-khun-thian | 186,144 | 120.69 | 1,542 | 343,381 | 2,845 | 10 → 10 | +0 |
| bang-na | 88,535 | 18.79 | 4,712 | 213,917 | 11,385 | 6 → 5 | -1 |
| bang-phlat | 89,417 | 11.36 | 7,871 | 240,353 | 21,158 | 4 → 4 | +0 |
| bang-rak | 45,757 | 5.54 | 8,259 | 74,878 | 13,516 | 1 → 2 | +1 |
| bang-sue | 122,410 | 11.50 | 10,644 | 198,279 | 17,242 | 3 → 4 | +1 |
| bangkok-noi | 103,791 | 11.94 | 8,690 | 218,456 | 18,296 | 4 → 3 | -1 |
| bangkok-yai | 63,861 | 6.18 | 10,333 | 124,335 | 20,119 | 4 → 4 | +0 |
| bueng-kum | 140,817 | 24.31 | 5,792 | 179,719 | 7,393 | 6 → 7 | +1 |
| chatuchak | 155,297 | 32.91 | 4,719 | 449,914 | 13,671 | 5 → 4 | -1 |
| chom-thong | 148,290 | 26.27 | 5,646 | 247,900 | 9,437 | 7 → 7 | +0 |
| din-daeng | 115,508 | 8.35 | 13,827 | 209,173 | 25,051 | 2 → 2 | +0 |
| don-mueang | 170,791 | 36.80 | 4,641 | 308,304 | 8,378 | 8 → 8 | +0 |
| dusit | 83,897 | 10.66 | 7,867 | 146,793 | 13,770 | 4 → 5 | +1 |
| huai-khwang | 84,233 | 15.03 | 5,603 | 220,088 | 14,643 | 4 → 4 | +0 |
| khan-na-yao | 96,330 | 25.98 | 3,708 | 166,850 | 6,422 | 7 → 8 | +1 |
| khlong-sam-wa | 204,900 | 110.69 | 1,851 | 301,710 | 2,726 | 9 → 10 | +1 |
| khlong-san | 69,139 | 6.05 | 11,426 | 116,503 | 19,257 | 2 → 2 | +0 |
| khlong-toei | 93,193 | 12.99 | 7,172 | 215,644 | 16,601 | 3 → 3 | +0 |
| lak-si | 102,704 | 22.84 | 4,496 | 255,705 | 11,196 | 7 → 6 | -1 |
| lat-krabang | 178,971 | 123.86 | 1,445 | 368,746 | 2,977 | 10 → 9 | -1 |
| lat-phrao | 117,108 | 21.50 | 5,447 | 229,783 | 10,688 | 5 → 6 | +1 |
| min-buri | 142,197 | 63.65 | 2,234 | 277,683 | 4,363 | 9 → 9 | +0 |
| nong-chok | 177,979 | 236.26 | 753 | 223,901 | 948 | 10 → 10 | +0 |
| nong-khaem | 156,203 | 35.83 | 4,360 | 257,908 | 7,198 | 9 → 8 | -1 |
| pathum-wan | 43,338 | 8.37 | 5,178 | 116,091 | 13,870 | 2 → 1 | -1 |
| phasi-charoen | 124,318 | 17.83 | 6,971 | 255,719 | 14,342 | 5 → 6 | +1 |
| phaya-thai | 67,388 | 9.59 | 7,027 | 176,499 | 18,405 | 3 → 3 | +0 |
| phra-khanong | 87,856 | 13.99 | 6,282 | 186,525 | 13,333 | 6 → 6 | +0 |
| phra-nakhon | 44,923 | 5.54 | 8,115 | 83,132 | 15,006 | 2 → 2 | +0 |
| pom-prap-sattru-phai | 41,524 | 1.93 | 21,504 | 53,404 | 27,670 | 1 → 1 | +0 |
| prawet | 181,821 | 52.50 | 3,463 | 272,062 | 5,182 | 8 → 8 | +0 |
| rat-burana | 78,687 | 15.78 | 4,986 | 146,800 | 9,303 | 7 → 7 | +0 |
| ratchathewi | 69,264 | 7.13 | 9,720 | 143,566 | 20,136 | 2 → 2 | +0 |
| sai-mai | 207,272 | 44.62 | 4,646 | 281,501 | 6,309 | 8 → 8 | +0 |
| samphanthawong | 21,324 | 1.42 | 15,059 | 20,440 | 14,394 | 1 → 1 | +0 |
| saphan-sung | 96,092 | 28.12 | 3,417 | 151,560 | 5,390 | 9 → 9 | +0 |
| sathon | 75,735 | 9.33 | 8,121 | 180,451 | 19,341 | 3 → 3 | +0 |
| suan-luang | 123,609 | 23.68 | 5,220 | 309,605 | 13,075 | 6 → 5 | -1 |
| taling-chan | 103,617 | 29.48 | 3,515 | 211,273 | 7,167 | 8 → 7 | -1 |
| thawi-watthana | 78,749 | 50.22 | 1,568 | 141,020 | 2,808 | 9 → 9 | +0 |
| thon-buri | 103,377 | 8.55 | 12,089 | 193,632 | 22,647 | 3 → 3 | +0 |
| thung-khru | 123,700 | 30.74 | 4,024 | 168,656 | 5,487 | 8 → 9 | +1 |
| wang-thonglang | 107,458 | 18.91 | 5,684 | 296,804 | 15,696 | 5 → 4 | -1 |
| watthana | 81,623 | 12.56 | 6,496 | 221,729 | 17,654 | 2 → 2 | +0 |
| yan-nawa | 76,564 | 16.66 | 4,595 | 202,554 | 12,158 | 6 → 6 | +0 |
