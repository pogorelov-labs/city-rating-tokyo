"""Shared Bangkok build paths and model constants."""
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RAW = ROOT / "data" / "bangkok" / "raw"
DATA = ROOT / "data" / "bangkok"
APP = ROOT / "app" / "src" / "data" / "bangkok"
PUBLIC = ROOT / "app" / "public" / "data" / "bangkok"
SCHEMA_CONSTANTS = ROOT / "packages" / "schema" / "constants.json"

# Local equirectangular projection in metres; scale error across Bangkok is
# under 0.3%, below the positional uncertainty of the source geometry.
LAT0, LON0 = 13.75, 100.60
KX = 111_320.0 * math.cos(math.radians(LAT0))
KY = 110_574.0
GRID_M = 200  # resident sample grid
CELL_M = 100  # raster cell for "count within radius" convolutions
SIMPLIFY_M = 18  # polygon simplification tolerance for the app geometry
WALK_M_PER_MIN = 75.0  # 4.5 km/h
AREA_RADIUS_M = 800  # station area = nearest-station cell within this walk (≈ 10–14 min)
# Only nearby stations of different lines can form an interchange area.
INTERCHANGE_MERGE_M = 450
WALK_DETOUR = 1.3
FEEDER_WAIT = 6.0  # motorbike taxi / bus / songthaew to a station
ROAD_OVERHEAD = 10.0  # door-to-door taxi or bus: hail/wait + last walk
ROAD_DETOUR = 1.4
TRANSFER_WALK_MAX_M = 500.0
RAIL_DETOUR = 1.05  # track length vs. straight line between station nodes
RATING_KEYS = [
    "transport", "rent", "daily_essentials", "safety", "food",
    "green", "gym_sports", "vibe", "nightlife", "crowd",
]
