# Batch-2 selection memo — 2026-11-07

Three selection axes kept separate (no combined "priority score"). Axis-1 data
from `raw/coverage-scan.json` (window 2024-11-05 → 2026-11-07, publisher-family
dedup; coverage breadth ≠ popularity). Scores are the existing model's raw
composites under the recorded default weights, snapshot `bkk-d6499618507e7561` —
research selection does not change them.

## Scanned candidates (8)

| Entity | Kind | Model score (cohort rank) | Coverage band (axis 1) |
| --- | --- | --- | --- |
| pom-prap-sattru-phai | district | 8.16 (#3/50) | **broad** (Time Out, Bangkok Post, The Nation, Thai PBS, Condé Nast undated) |
| phaya-thai | district | 8.00 (#4/50) | **broad** (Bangkok Post, Time Out, Koktail, Daily News, Thailand Starter Kit, Rainmaker) |
| st.ratchathewi | station_area | 7.92 (#3/133) | **some** (Thai PBS World, Thailand Starter Kit, The Way to Coffee; heavy property content excluded) |
| st.charoen-nakhon | station_area | 7.96 (#2/133) | **thin** (Fullsuitcase Feb 2025, partial; BK weekend guide Aug 2024 outside window) |
| st.nana | station_area | 7.86 (#4/133) | **thin** (single undated family, Travel Happy) |
| st.phloen-chit | station_area | 7.78 (#6/133) | **thin** (single undated family; dated in-window items are property/OTA) |
| st.sam-yot | station_area | 7.74 (#8/133) | **thin** (Visit Thailand Today, Sep 2026) |
| st.wat-mangkon | station_area | 7.70 (#10/133) | **thin** (Thaiger Dec 2025 station event; Chinatown coverage mostly not station-specific) |

Not scanned (no coverage data — unknown, not zero): st.ha-yaek-lat-phrao
(7.82, #5), st.ratchaprarop (7.68, #12).

## Selected for batch 2 (6)

1. **pom-prap-sattru-phai** — axes 1+2+3 all strong: broad coverage, district
   #3, and direct boundary interplay with the pilot (owns Chinatown Soi Nana
   bars, Khlong Thom, Golden Mount — all things the pilot's Samphanthawong
   bundle placed *outside* the khet). Another green-vs-geometry test: green 9
   with only 0.7 ha mapped park (0.3% share).
2. **phaya-thai** — axes 1+2: broad coverage, district #4; district-level
   counterpart to the pilot's st.ari findings (which found no park inside the
   *station-area* unit while the district carries green 9 and 14.8 ha).
3. **st.ratchathewi** — axes 1+2: only station area with "some" coverage and
   rank #3/133; safety 5 (lowest in the pilot set) vs vibe 10 needs testing.
4. **st.charoen-nakhon** — axis 2+3: rank #2/133 with **thin** coverage —
   exactly the high-score/low-coverage pattern the handoff wants surfaced;
   transport 10 for a Gold Line feeder station needs a mechanism check.
5. **st.nana** — axis 3 (+2): popular-but-contested nightlife identity; the
   Soi Nana (Sukhumvit) vs Soi Nana (Chinatown) confusion is itself a Q01
   test; green 10 with only 1.4 ha park is a green-geometry outlier.
6. **st.wat-mangkon** — axis 3 control: catchment split Pom Prap 51.4% /
   Samphanthawong 48.6% — a direct corridor-vs-catchment probe on both sides
   of the pilot's Samphanthawong findings (station straddles the boundary).

## Deferred to batch 3 (with reasons)

- st.phloen-chit: dated in-window coverage is all commercial (property/OTA);
  axis-1 basis weak, revisit after a better window or with local-language
  sources.
- st.sam-yot: thin coverage; queue with the old-town group (sam-yot,
  sanam-chai, itsaraphap, phra-nakhon) as a themed batch.
- st.ha-yaek-lat-phrao, st.ratchaprarop: coverage unknown — scan before
  selection.
