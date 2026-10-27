# Bangkok acquisition and build

Run these commands from the repository root. Raw downloads and caches live in
`data/bangkok/raw/` (gitignored). Fetch-only dependencies are declared in each
script's PEP 723 metadata; no pyosmium dependency is needed by the app or CI.

## Geofabrik OSM path

```sh
uv run scripts/bangkok/fetch-geofabrik.py
uv run scripts/bangkok/fetch.py --only wikidata commons station_wikidata station_commons overture_places
uv run scripts/bangkok/fetch-population.py
uv run scripts/bangkok/build.py
```

The full builder also reads the committed editorial, rent, description and
flood inputs. `fetch-population.py` verifies the pinned WorldPop raster; an
existing verified cache is sufficient. Flood scores use committed
`data/bangkok/flood.json`, not the ZIP directly. Rebuilding that independent
input with `fetch-flood.py` is a separate, deliberately reviewed refresh.

The first command downloads [Geofabrik Thailand](https://download.geofabrik.de/asia/thailand.html)
from `https://download.geofabrik.de/asia/thailand-latest.osm.pbf` using the public
Python `osmium` package (pyosmium API, no osmium CLI). It replaces these 12 OSM
tasks without sending any Overpass requests:

- `boundaries`, `province`;
- `pois_food`, `pois_nightlife`, `pois_essentials`, `pois_sports`, `pois_culture`, `pois_transit_other`;
- `green`, `rail_routes`, `rail_stops`, `rail_stations`.

The downloaded `thailand.osm.pbf.source.json` records requested/resolved URLs,
HTTP Last-Modified, retrieval time, byte count and SHA-256. Reuse verifies the
hash and size. `--refresh` replaces the download; `--url` with `--refresh` can
select a dated Geofabrik URL. `--download-only` only downloads/verifies it.
`--pbf /path/to/file.osm.pbf` explicitly uses a local file without downloading;
its hash, size and PBF replication timestamp are still recorded, but source
URL/retrieval provenance is only available if its `.pbf.source.json` accompanies
it. Geofabrik can remove historical downloads, so preserve the original PBF
and manifest when reproducibility matters.

Every extraction regenerates the entire OSM cache set, including existing
files; it does not skip individual JSONs. It validates coverage and direct
member geometry before writing any output. Writes are atomic per file, not
transactional across the full set: after an interrupted write, rerun extraction
before building. `geofabrik-source.json` and each JSON's `_source` include the
same PBF hash, source timestamp, bbox and output counts. The PBF source date
comes from `osmosis_replication_timestamp`, not the download/build date. The
five non-OSM API tasks retain fetch.py's existence-based cache behavior; use
its `--refresh` explicitly when a new acquisition is intended.

## Selection and schema contracts

`osm_filters.py` defines the shared exact tag and element-type selectors and
renders the existing Overpass query bodies. Access restrictions and duplicate
POI handling remain the builder's responsibility.

The extractor uses four passes: relation inventory, bbox node/way selection
with a compact libosmium location index, selected-member way references, and
the nodes needed to complete those members. It keeps full member geometry
outside the bbox instead of cutting district rings or routes at the border.
Only selected relations' node/way geometry is retained in Python after the
bbox pass. Allow memory for a Thailand node-location index and disk for the
PBF (about 330 MB as of October 2026), cache JSONs and other build inputs.

- POI/station nodes have `type`, `id`, `tags`, `lat`, `lon`. Ways and POI
  relations have `center: {lat, lon}`: the midpoint of the full bounding box,
  **not** a centroid or the mean of vertices. As with [Overpass out center](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#Print_(out)),
  direct node/way members contribute; nested relation members do not.
- Bbox selection includes nodes inside the box and ways with an inside vertex
  or a segment that crosses/touches the box, even when both endpoints are
  outside. A relation also qualifies through such a direct member way,
  including an untagged one. Selection retains full geometry and does not
  require the computed center to lie inside the box.
- Green ways contain full `geometry: [{lat, lon}, ...]`. Relations preserve
  ordered `{type, ref, role}` members, direct node coordinates, and complete
  way-member `geometry`, including inner rings and route direction roles.
  Nested relations remain references, matching Overpass `out geom`; the
  current builder assembles direct way members only.
- District candidates are administrative level 6 relations. Their assembled
  interior representative point must lie in the Bangkok level 4 polygon;
  exactly 50 distinct district Wikidata IDs are required. This uses the PBF
  province polygon rather than Overpass's independently updated area index.
  `province.json` is emitted for parity, though the builder uses the district
  union instead.
- All 20 IDs in `static_data.RAIL_ROUTE_RELATIONS` must exist, with complete
  direct members even outside the bbox. `rail_stops` contains tags for every
  direct route-node reference. `rail_stations` selects the same station nodes
  and ways as the Overpass path.

The existing Overpass workflow remains available:

```sh
uv run scripts/bangkok/fetch.py
```

Avoid mixing its OSM tasks with Geofabrik JSONs in one cache. A completed
Geofabrik run restores a coherent OSM snapshot. WD/Commons are live APIs;
Overture uses the release pinned in fetch.py. These inputs have independent
dates and licenses. A build-month `data_date` does not refresh rent, safety,
population, flood, or editorial descriptions. The full build now automatically
reapplies the pinned tourism/Michelin/legacy-embassy observations before output
writes. Missing source hashes/joins fail; the standalone
`uv run scripts/bangkok/apply-enrichments.py` is an idempotent replay.

The **full spatial refresh was excluded from v0.1.0** and merged post-release in
[PR #147](https://github.com/pogorelov-labs/city-rating-tokyo/pull/147) on
**2026-10-27** at [ba7aa47](https://github.com/pogorelov-labs/city-rating-tokyo/commit/ba7aa477fb3e06ceada1fad5df2dc5954428cdf4).
The refreshed data is now on **main**; the v0.1.0 tag/release remains unchanged.
All **10 original validation gates are resolved**; see the
[completed remediation](../../docs/DATA_REFRESH_REMEDIATION.md) and
[committed evidence note](../../research/bangkok/notes/2026-10-26-frozen-refresh.md).
Historical population/normalization fixtures remain unchanged. The current
binary is `grid-1d6ed2ef00c3.bin` (**143,925 bytes**).

For exact frozen-input rebuilds, restore the archived raw payloads and caches:

```sh
uv run scripts/bangkok/freeze-inputs.py --verify
uv run scripts/bangkok/build.py --inputs-manifest data/bangkok/refresh-inputs.json
```

The committed manifest records all raw hashes and Wikimedia revisions; its
build date also fixes the output date. Live Wikimedia refetches cannot promise
identical bytes. The pinned Overture acquisition inventories all source-entry
licenses and sorts its slim output by ID. Population-only replay explicitly
selects `--baseline refresh-2026-10-24`; `--baseline adoption` is historical and
requires the old geometry/snapshot. The new immutable baseline includes precise
POI terms; do not overwrite the historical baseline or golden.

## Verification and attribution

```sh
uv run --with pytest python -m pytest scripts/bangkok/test_fetch_geofabrik.py -q
uv run --with pytest python -m pytest scripts/bangkok/test_bangkok.py -q
uv run --with pytest --with pydantic python -m pytest scripts/test_normalization.py -q
```

The focused tests use synthetic dictionaries and temporary bytes only: no PBF
download, network or fetch-only dependency is added to CI. The existing
Bangkok CI job discovers them under `scripts/bangkok`.

OSM data is © OpenStreetMap contributors under [ODbL 1.0](https://www.openstreetmap.org/copyright),
distributed by Geofabrik; retain attribution and follow ODbL obligations for
published derived databases. See [Geofabrik technical details](https://download.geofabrik.de/technical.html)
for extract completeness and public metadata exclusions. Keep other sources'
license and per-image Commons attribution alongside OSM provenance.

Overture Places **2026-09-23.1** includes CDLA-Permissive-2.0 (Meta, Microsoft,
PinMeTo, DAC and Overture), **Apache-2.0 (Foursquare)** and **CC0-1.0
(AllThePlaces)**. See [Overture attribution](https://docs.overturemaps.org/attribution/#places)
and the shipped [notice/license copies](../../app/public/data/bangkok/licenses/NOTICE.txt).
The source manifest inventories all source entries, including secondary ones.
Per-image Commons attribution remains independent; exact revision IDs do not
freeze transcluded metadata or hosted thumbnail bytes.

Grid header medians and composite anchors use published integer resident-weight
units (scale 250), so summaries can be reproduced from the binary. Cell rating
normalization continues to use the original full precision weights. The
threshold-crossing regression documents the refresh's transport median of 5.
