# Research: Green/Parks Rating Data Sources

## 1. Overpass Area Query

### The Core Problem
Currently `green_area_sqm` is 0 for all stations because the scraper runs with `--skip-area`. The `green_count` metric alone is misleading: a station near Yoyogi Park (54ha) might score lower than one near 20 tiny pocket parks. Area data is essential.

### Recommended Overpass Query (Tested)

The most effective query combines multiple green-related tags in a union block with `out geom` to retrieve full polygon geometry:

```
[out:json][timeout:120];
(
  way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lng});
  relation["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lng});
  way["natural"="wood"](around:{radius},{lat},{lng});
  relation["natural"="wood"](around:{radius},{lat},{lng});
  way["landuse"~"forest|cemetery"](around:{radius},{lat},{lng});
  relation["landuse"~"forest|cemetery"](around:{radius},{lat},{lng});
  way["landuse"="religious"](around:{radius},{lat},{lng});
  relation["landuse"="religious"](around:{radius},{lat},{lng});
  way["leisure"="garden"](around:{radius},{lat},{lng});
  relation["leisure"="garden"](around:{radius},{lat},{lng});
);
out geom;
```

**Parameters**: `radius=1000` (meters), `lat`/`lng` = station coordinates.

### Area Calculation from Geometry

Overpass API does NOT compute area server-side. The `out geom` modifier returns full coordinate arrays for ways and resolved geometries for relations (including multipolygon outer/inner rings). Area must be calculated client-side.

**Recommended approach using pyproj (geodesic, most accurate)**:
```python
from pyproj import Geod
from shapely.geometry import shape
import osm2geojson

geod = Geod(ellps="WGS84")

# Convert Overpass response to Shapely shapes
shapes = osm2geojson.json2shapes(overpass_response)

total_area = 0
for s in shapes:
    geom = s['shape']
    if geom.geom_type in ('Polygon', 'MultiPolygon'):
        area_m2, _ = geod.geometry_area_perimeter(geom)
        total_area += abs(area_m2)
```

Key libraries:
- `osm2geojson` (PyPI) -- converts Overpass JSON to Shapely geometries, handles multipolygon relations with inner/outer rings correctly
- `pyproj.Geod.geometry_area_perimeter()` -- computes geodesic area in m^2 directly from WGS84 lat/lng polygons without projection
- Alternative: project to UTM Zone 54N (EPSG:32654) for Tokyo, then use `shapely.area`, but pyproj geodesic method is simpler and more accurate

### Validation Test: Harajuku Station (35.6702, 139.7027)

Tested Overpass query for leisure=park around Harajuku. Results:
- **Relation 19862716**: Yoyogi Park (代々木公園 / 都立代々木公園), established 1967, operated by Tokyo Parks Association. This is the main park relation (~54 ha expected).
- **Way 1029462259**: Another Yoyogi Park way
- **Way 209678410**: Shibuya Ward Yoyogi 2-chome Aoi Park (small local park)
- **Way 209695342**: Yoyogi Pony Park (small)
- **Way 898085561**: Yoyogi Midori Park (small)

For Meiji Jingu shrine grounds: Searching specifically returned individual features (shrine buildings, inner garden, museum, torii gate) but NOT a single boundary polygon for the 70-hectare forested grounds. The shrine grounds are tagged as individual `amenity=place_of_worship` buildings, NOT as a single `landuse=religious` or `leisure=park` boundary in this area.

**Key finding**: Meiji Jingu's 70ha forest is NOT captured by standard park queries. It requires `landuse=religious` or a dedicated boundary query. This is a significant gap -- one of Tokyo's largest green spaces is invisible to naive park queries.

### Batch Strategy for 1493 Stations

- **Rate limits**: Overpass allows ~10,000 requests/day, ~1 GB download/day
- **Query per station**: Each `out geom` query with ~1000m radius typically returns 0.5-2 MB of geometry data
- **Timeout**: Default 180s, can extend to 900s. Individual station queries should complete in 5-30s
- **Strategy**: Query one station at a time with 2-3 second delays between requests. 1493 stations = ~1-2 hours total
- **Alternative endpoints**: Use multiple Overpass instances (overpass-api.de, maps.mail.ru/osm/tools/overpass, overpass.kumi.systems) for parallel querying
- **Deduplication**: Large parks (e.g., Yoyogi Park) will appear in results for multiple nearby stations. Deduplicate by OSM element ID before summing area per station

## 2. Additional Green Tags (Which Add Value)

### High Value -- Include

| Tag | Value for Green Rating | Tokyo Coverage |
|-----|----------------------|----------------|
| `leisure=park` | Core signal. Most parks tagged this way. | Excellent |
| `leisure=garden` | Formal gardens (Shinjuku Gyoen, Rikugien, etc.) | Good |
| `leisure=nature_reserve` | Nature reserves in outer Tokyo | Good for Tama/Okutama |
| `natural=wood` | Essential for western Tokyo (Takao, Okutama) | Good |
| `landuse=forest` | Overlaps with natural=wood, captures forested areas | Good |
| `landuse=cemetery` | Japanese cemeteries (Yanaka, Aoyama) often feel like parks with mature trees | Good. Adds ~5-15% more green per station |
| `landuse=religious` | Large shrine/temple grounds with forest. Critical for Meiji Jingu (70ha), and other major shrines | Variable. Not consistently mapped |
| `waterway=river` + buffer | Rivers with green walking paths (Tama, Sumida, Ara, Edo rivers) | Good for proximity signal |

### Medium Value -- Consider

| Tag | Notes |
|-----|-------|
| `natural=tree_row` | Tree-lined streets. Mapping completeness in Tokyo is LOW and inconsistent. Not reliable enough to use. |
| `amenity=place_of_worship` (area) | Only useful if tagged as a polygon with large area. Many shrines are mapped as points only. Better to use `landuse=religious` which captures the grounds. |
| `amenity=university` | Large campuses (Todai, Waseda) have green areas, but the campus polygon includes buildings. Would overcount. Not recommended. |
| `leisure=pitch` / `leisure=sports_centre` | Sports fields are green but not really "nature." Skip. |

### Recommended Tag Combination

```
leisure = park | garden | nature_reserve
natural = wood
landuse = forest | cemetery | religious
```

This captures: parks, gardens, forests, cemeteries (green), shrine/temple grounds (forested).

## 3. Government Green Data Sources

### 3a. Tokyo Metropolitan Green Rate Survey (みどり率調査)

**Source**: Tokyo Metropolitan Government Environmental Bureau
**URL**: https://www.kankyo.metro.tokyo.lg.jp/information/press/2024/10/2024102801
**Press release**: https://www.metro.tokyo.lg.jp/information/press/2024/10/2024102816

**Latest data**: Reiwa 5 (2023) survey, published October 2024

**Overall figures (2023)**:
- Tokyo total: 52.1%
- Special wards (区部): 24.0%
- Tama area (多摩部): 67.4%

**Definition**: みどり率 = (vegetation cover + park areas + water surface) / total area

**Ward-level data availability**: The metropolitan-level report groups data by broad regions (区部/多摩部/島しょ), but individual ward-level percentages are published separately by each ward in their own green surveys (みどりの実態調査). Known ward values:
- Minato-ku: 22.62% (緑被率, 2022 survey)
- Shibuya-ku: 22.77% (緑被率, 2022 survey)
- Nerima-ku: historically ranked 1st among 23 wards
- Chiyoda-ku: historically ranked high (has Imperial Palace grounds)

**Format**: PDF reports from Tokyo Metropolitan Government. No CSV or machine-readable download found. Would need to manually extract or scrape from PDF.

**Limitation**: This is a WARD-level metric, not station-level. Would need to map stations to wards (already have ward codes for 274 stations in `station-area-codes.json`). Only covers Tokyo's 23 special wards, not Kanagawa/Saitama/Chiba prefectures.

### 3b. Town-Block Level Vegetation Cover (町丁目別緑被率)

**Source**: Academic dataset using Google Earth Engine + Sentinel-2
**Paper**: https://www.jstage.jst.go.jp/article/aijt/28/68/28_521/_article/-char/ja/
**Published**: February 2022

This is a nationwide dataset at the 町丁目 (town block) level -- much finer granularity than ward-level. Uses Sentinel-2 satellite imagery processed in GEE. Validated in nine Tokyo cities with RMSE of 2.8 percentage points.

**Status**: Published as academic research. Need to check if raw data is downloadable (likely available as supplementary material or via the authors).

**Very promising** -- if accessible, this would give vegetation percentage for each station's neighborhood directly.

### 3c. National Land Numerical Information -- Urban Parks (都市公園 P13)

**Source**: Ministry of Land, Infrastructure, Transport and Tourism
**URL**: https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P13.html
**Also**: https://www.geospatial.jp/ckan/dataset/060512

**Data**: All urban parks defined under the Urban Park Law
**Format**: GML (JPGIS 2.1) and Shapefile
**Latest**: FY2011 data (based on March 2010) -- quite old
**Coverage**: Nationwide, download by prefecture

**Attributes**:
- Park name (公園名)
- Park type code (公園種別コード)
- Managing authority
- Service start year
- **Service area in m^2 (供用済面積)** -- key field
- Geographic coordinates

**Download for Greater Tokyo**:
| Prefecture | File | Size |
|-----------|------|------|
| Tokyo (13) | P13-11_13_GML.zip | 0.43 MB |
| Kanagawa (14) | P13-11_14_GML.zip | 0.39 MB |
| Saitama (11) | P13-11_11_GML.zip | 0.24 MB |
| Chiba (12) | P13-11_12_GML.zip | 0.37 MB |

**Pros**: Official dataset with exact areas. Covers all four prefectures. Point data with area field, easy to query by proximity.
**Cons**: 2010 data (15 years old). Point geometry only (not polygons). Missing parks established after 2010.

### 3d. National Land Numerical Information -- Land Use Mesh (土地利用細分メッシュ L03-b)

**Source**: MLIT
**URL**: https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L03-b.html

**Data**: 100m x 100m mesh grid covering all of Japan. Each cell classified by land use type.
**Format**: GML and Shapefile
**Years available**: 1976, 1987, 1991, 1997, 2006, 2009, 2014, 2016
**Latest**: 2016 data

**Land use classification codes (relevant to green)**:
| Code | Type | Green? |
|------|------|--------|
| 0100 | Paddy fields (田) | Partial (seasonal green) |
| 0200 | Other agricultural land | Partial |
| 0500 | Forest (森林) | YES |
| 0600 | Wasteland (荒地) | Partial |
| 1000 | Other land (includes parks, sports facilities, schools) | Partial |
| 1100 | Rivers and lakes | Water (contributes to green feeling) |
| 1600 | Golf courses | YES |

**Note**: Code `1000` (その他の用地) lumps parks together with airports, schools, and ports. There is no dedicated "park" code, which limits granularity.

**Download pattern**: Files organized by mesh code, not prefecture.
Tokyo-area mesh codes: 5339, 5340, 5439, 5440, etc.
File naming: `L03-b-16_5339-jgd_GML.zip` (for 2016 data, mesh 5339, JGD2000)

**Usage**: For each station, identify the surrounding 100m mesh cells within 1km, count cells classified as forest (0500) or other green types. Gives a vegetation percentage estimate.

**Pros**: 100m resolution, nationwide, includes all green types. Great for suburban/rural areas.
**Cons**: No dedicated park code. 2016 latest data. Requires GIS processing.

### 3e. Tokyo Open Data Portal

**URL**: https://catalog.data.metro.tokyo.lg.jp/
**GeoJSON filter**: https://catalog.data.metro.tokyo.lg.jp/dataset?res_format=GeoJSON

Could not access the catalog directly (403 error). The portal exists and supports GeoJSON format filtering, but specific park/green datasets could not be confirmed.

### 3f. HUGSI (Husqvarna Urban Green Space Index)

**URL**: https://hugsi.green/cities/Tokyo
**Data for Tokyo**:
- Urban green space: 20%
- Tree coverage: 14%
- Total urban area: 1,311.09 km^2
- Rating: E (low among global cities)

City-wide metric only. Not useful at station level. But provides a global baseline comparison.

## 4. Satellite/NDVI Data

### 4a. Google Earth Engine (GEE)

**Best option for custom NDVI computation.**

**Data sources in GEE**:
- Sentinel-2 (COPERNICUS/S2_SR_HARMONIZED): 10m resolution, 5-day revisit
- MODIS (MOD13A1): 500m resolution, 16-day revisit
- Landsat: 30m resolution

**Approach for station-level green scoring**:
1. Create 1km buffer circles around each station as ee.FeatureCollection
2. Select summer Sentinel-2 imagery (June-August for peak vegetation)
3. Compute NDVI = (B8 - B4) / (B8 + B4) for each pixel
4. Use `image.reduceRegions(stations_buffered, ee.Reducer.mean())` to get mean NDVI per station
5. Export results as CSV

**Python API**:
```python
import ee
ee.Initialize()

# Sentinel-2 summer composite
s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
    .filterDate('2024-06-01', '2024-08-31') \
    .filterBounds(tokyo_geometry) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
    .median()

ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')

# Reduce over station buffers
results = ndvi.reduceRegions(
    collection=station_buffers,  # 1493 features with 1km buffers
    reducer=ee.Reducer.mean(),
    scale=10
)
```

**Licensing**: Free for research, education, nonprofit. Noncommercial tier requires selecting a quota by April 2026. For a one-time batch of 1493 points, the free tier is more than sufficient.

**Pros**: 10m resolution NDVI = actual vegetation measurement. Most accurate green metric possible. Works for all 4 prefectures uniformly.
**Cons**: Requires GEE account setup and authentication. Cloud processing (but free). One-time batch computation, not real-time.

### 4b. Copernicus Data Space Ecosystem

**URL**: https://dataspace.copernicus.eu
**Data**: Same Sentinel-2 imagery as GEE, but via different APIs

- Sentinel Hub APIs for direct pixel access
- OpenEO for cloud processing
- Free account required
- 10m resolution available

**Less convenient than GEE** for this use case because GEE handles the compositing and reduction natively. Copernicus is better for downloading raw tiles.

### 4c. Pre-computed NDVI Products

- **Copernicus NDVI 300m** (2020-2025): https://land.copernicus.eu/en/products/vegetation/normalised-difference-vegetation-index-v2-0-300m
  - 300m resolution, 10-daily updates, global coverage
  - Too coarse for neighborhood-level analysis (300m cells blur park/concrete boundaries)
- **MODIS NDVI 250m/500m**: Available in GEE
  - Also too coarse for urban neighborhood analysis

**Conclusion**: Only Sentinel-2 at 10m resolution is fine enough to distinguish parks from surrounding urban areas.

## 5. Recommended Green Score Formula

### Component Weights

```python
green_score = normalize_to_10(
    0.45 * park_area_score +      # Total green area within 1km (most important)
    0.20 * ndvi_score +            # Satellite vegetation index (actual green coverage)
    0.15 * park_count_score +      # Number of distinct green spaces
    0.10 * large_park_bonus +      # Bonus for proximity to major parks (>5 ha)
    0.10 * water_proximity_score   # River/canal within 500m
)
```

### Component Details

**park_area_score** (45% weight):
- Source: Overpass API with `out geom`, calculated via osm2geojson + pyproj
- Metric: Total green area in m^2 within 1000m
- Tags: leisure=park|garden|nature_reserve, natural=wood, landuse=forest|cemetery|religious
- Normalization: log-scale (area varies from 0 to 1,000,000+ m^2)
- Formula: `min(10, log10(area_sqm + 1) / log10(600000) * 10)`
  - 600,000 m^2 (~60ha, like Yoyogi Park) = score 10
  - 100,000 m^2 (~10ha) = score ~8.6
  - 10,000 m^2 (~1ha) = score ~6.9
  - 1,000 m^2 = score ~5.2
  - 0 m^2 = score 0

**ndvi_score** (20% weight):
- Source: Google Earth Engine, Sentinel-2 summer composite
- Metric: Mean NDVI within 1km buffer
- Range: typically 0.1 (concrete) to 0.7 (dense forest) for Tokyo
- Normalization: `(ndvi - 0.10) / (0.55 - 0.10) * 10`

**park_count_score** (15% weight):
- Source: Overpass API (already collected as green_count)
- Metric: Count of distinct green features within 1000m
- Normalization: `min(10, count / 30 * 10)` (30+ = max score)

**large_park_bonus** (10% weight):
- Source: Overpass area query
- Metric: 1 if any single park >50,000 m^2 (5ha) exists within 1km; 0.5 if >10,000 m^2 (1ha); 0 otherwise
- Scaled to 0-10

**water_proximity_score** (10% weight):
- Source: Overpass query for `waterway=river` or `waterway=canal` within 500m
- Metric: Binary (river present = 10, absent = 0)
- Could refine with distance weighting

### Simplified Formula (if NDVI not feasible)

If GEE is too complex to set up, a simpler 3-component formula:

```python
green_score = normalize_to_10(
    0.55 * park_area_score +
    0.25 * park_count_score +
    0.10 * large_park_bonus +
    0.10 * water_proximity_score
)
```

## 6. Implementation Plan

### Phase 1: Overpass Green Area (Priority -- HIGH)

1. **Modify `scrape-osm-pois.py`** to remove `--skip-area` and add `out geom` to the green query
2. **Add expanded tags**: natural=wood, landuse=forest|cemetery|religious, leisure=garden
3. **Implement area calculation**: Use `osm2geojson.json2shapes()` + `pyproj.Geod.geometry_area_perimeter()`
4. **Add deduplication**: Track OSM element IDs to avoid double-counting parks shared between stations
5. **Compute new fields per station**:
   - `green_area_sqm`: Total green area within 1000m
   - `green_area_max_sqm`: Area of the single largest green feature
   - `green_area_forest_sqm`: Area from forest/wood tags specifically
   - `green_area_cemetery_sqm`: Cemetery area (separate for potential down-weighting)
   - `has_large_park`: Boolean, any feature > 50,000 m^2
   - `has_river`: Boolean, waterway=river within 500m
6. **Batch execution**: ~1493 queries, 2-3s delay each, total ~1.5 hours
7. **Dependencies**: `pip install osm2geojson pyproj shapely`

### Phase 2: Government Park Data (Priority -- MEDIUM)

1. Download MLIT urban park data (P13) for Tokyo/Kanagawa/Saitama/Chiba (4 shapefiles, ~1.5 MB total)
2. Load with GeoPandas, spatial join to find parks within 1km of each station
3. Sum `供用済面積` (service area) per station as `official_park_area_sqm`
4. Use as validation/supplement to OSM data (especially for parks that may be poorly mapped in OSM)

### Phase 3: Land Use Mesh (Priority -- MEDIUM)

1. Download MLIT L03-b mesh data for Tokyo-area mesh codes (2016 data)
2. For each station, identify 100m cells within 1km radius
3. Count cells with code 0500 (forest) and compute green percentage
4. Store as `mesh_green_pct` per station
5. Especially useful for suburban/rural stations where OSM coverage may be sparse

### Phase 4: NDVI Satellite (Priority -- LOW, high impact)

1. Set up Google Earth Engine account (free, noncommercial)
2. Upload station coordinates as ee.FeatureCollection with 1km buffers
3. Compute summer Sentinel-2 NDVI composite
4. Extract mean NDVI per station
5. Export CSV, upload to NocoDB as `ndvi_mean` field
6. One-time computation, ~30 min in GEE

### Phase 5: Ward-Level Green Rate (Priority -- LOW)

1. Manually collect みどり率 data from individual ward PDFs (labor-intensive)
2. Map to stations via ward code
3. Only covers Tokyo 23 wards (264 stations), not useful for Kanagawa/Saitama/Chiba
4. Could skip this if Phases 1-4 provide sufficient coverage

## 7. Validation Against Known Green Stations

Expected scores with the recommended formula:

| Station | Expected | Rationale |
|---------|----------|-----------|
| Kichijoji | 9-10 | Inokashira Park (~43ha) within walking distance |
| Yoyogi/Harajuku | 9-10 | Yoyogi Park (54ha) + Meiji Shrine forest (70ha) |
| Ueno | 8-9 | Ueno Park (13ha) + Ueno Zoo grounds |
| Koganei | 9-10 | Koganei Park (80ha), largest in central Tokyo |
| Mitaka | 8-9 | Inokashira Park southern edge + residential green |
| Takao-san-guchi | 10 | Mt. Takao, massive forest coverage |
| Akihabara | 2-3 | Dense electronics district, minimal green |
| Shibuya | 4-5 | Some green near Yoyogi/NHK but center is concrete |
| Ikebukuro | 3-4 | Very little green space |
| Shinjuku | 5-6 | Shinjuku Gyoen (58ha) is nearby but station is commercial core |
| Nishi-Kokubunji | 8-9 | Musashino area, Musashi Kokubun-ji Park |
| Futako-Tamagawa | 7-8 | Tama River green corridor + parks |
| Shin-Kiba | 3-4 | Waterfront industrial area, Yumenoshima Park is modest |

## 8. Data Source Summary

| Source | Coverage | Granularity | Freshness | Effort | Priority |
|--------|----------|-------------|-----------|--------|----------|
| OSM Overpass (area) | 100% stations | Station-level | Current | Medium | HIGH |
| MLIT Urban Parks (P13) | 4 prefectures | Park-level | 2010 | Low | MEDIUM |
| MLIT Land Use Mesh (L03-b) | Nationwide | 100m grid | 2016 | Medium | MEDIUM |
| GEE Sentinel-2 NDVI | 100% stations | 10m pixels | Current | High (setup) | LOW |
| Tokyo Green Rate (みどり率) | 23 wards only | Ward-level | 2023 | High (manual) | LOW |
| Town-block green cover (academic) | Nationwide | Town-block | ~2021 | Unknown | INVESTIGATE |

### Key URLs

- Overpass API: https://overpass-api.de/api/interpreter
- Overpass Turbo (testing): https://overpass-turbo.eu/
- osm2geojson: https://pypi.org/project/osm2geojson/
- pyproj Geod docs: https://pyproj4.github.io/pyproj/stable/api/geod.html
- MLIT Urban Parks (P13): https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P13.html
- MLIT Land Use Mesh (L03-b): https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L03-b.html
- Land use codes: https://nlftp.mlit.go.jp/ksj/gml/codelist/LandUseCd-09.html
- G-Spatial Info Center (parks): https://www.geospatial.jp/ckan/dataset/060512
- Tokyo Green Rate 2023: https://www.kankyo.metro.tokyo.lg.jp/information/press/2024/10/2024102801
- Tokyo Greenery portal: https://www.tokyogreenery.metro.tokyo.lg.jp/green-situation/situation.html
- Town-block green cover paper: https://www.jstage.jst.go.jp/article/aijt/28/68/28_521/_article/-char/ja/
- Google Earth Engine: https://earthengine.google.com/
- Copernicus NDVI 300m: https://land.copernicus.eu/en/products/vegetation/normalised-difference-vegetation-index-v2-0-300m
- HUGSI Tokyo: https://hugsi.green/cities/Tokyo
- Tokyo Open Data catalog: https://catalog.data.metro.tokyo.lg.jp/
