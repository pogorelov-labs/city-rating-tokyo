# CRTKY-166 characterization baselines

Captured from `d2f53570bccfe9a3b1636f7f6b331cb19e237935` before extracting
shared math. No live calls or generated application data are involved.

- `tokyo-golden.json`: 13 synthetic stations through the complete compute
  function, including every output field and serialized confidence/source/date
  string. Exercises both/HP-only/OSM-only/zero/missing/null inputs, ties,
  Suumo/eStat/ward/regression rent, passenger/safety/essentials fallbacks.
  `normalization_replay.fixture_inputs()` is the input definition. Admission
  gates and the remote store are replaced in memory; their existing integration
  tests remain separate. Date is fixed to 2026-10-15.
- `bangkok-golden.json`: existing committed `data/bangkok/signals.json`,
  50 districts and 133 station areas. Replays eight normalized categories,
  rent, five threshold-based source/confidence pairs and index anchors. These
  are rounded aggregate inputs, **not** a geometry/grid rebuild. Resident-
  weighted grid routines and composite summation are deliberately untouched.

Run `pytest scripts/test_normalization.py` for stable golden regression checks.
For a fresh old/new comparison against the recorded revision:

```sh
python3 scripts/check-normalization-equivalence.py
# Optional internal snapshot supplied by the separate pilot lane:
python3 scripts/check-normalization-equivalence.py --historical-census /path/to/historical-census.json.gz
```

The optional snapshot has `tables.hotpepper.rows` and `tables.osm_pois.rows`.
It stays outside git. The script prints its SHA, counts, dates and explicit
missing-table limitations. The observed 2026-04-03 census has 1,493 HP and
1,398 OSM rows; extraction completeness does not establish original query
completeness. Other remote tables (extended OSM, livability, wards) are omitted
in that replay; the OSM green-area field is also unavailable. Committed slug redirects and
local rent, police and passenger inputs are used. Therefore
this is **partial historical input equivalence**, not full refresh equivalence
or proof that current published ratings match a fresh run. Source admission
and store gates are stubbed, no credentials are used and no database is read
or written.

Golden files intentionally retain source-list and record order. When source
inputs change, review and regenerate the corresponding baseline explicitly;
do not update expected values merely to silence a behavioral regression.
