"""Shared point-grid state for proximity and transit signals."""
from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np

from bangkok.bkk_config import FEEDER_WAIT, ROAD_DETOUR, ROAD_OVERHEAD, WALK_DETOUR, WALK_M_PER_MIN
from bangkok.rail import feeder_m_per_min, road_m_per_min
from bangkok.rasters import Raster


@dataclass
class SignalGrid:
    raster: Raster
    histograms: dict[str, np.ndarray]
    x: np.ndarray
    y: np.ndarray
    stations: list[dict] = field(default_factory=list)
    hub_times: dict[str, dict] = field(default_factory=dict)

    def near(self, cat: str, radius: float, extra: np.ndarray | None = None) -> np.ndarray:
        h = self.histograms.get(cat, np.zeros((self.raster.ny, self.raster.nx)))
        if extra is not None:
            h = h + extra
        return self.raster.sample(self.raster.within(h, radius), self.x, self.y)

    def both(self, cat: str, radius: float, osm_extra: np.ndarray | None = None) -> np.ndarray:
        """Blend the OSM and denser Overture POI counts."""
        return 0.35 * np.log1p(self.near(cat, radius, extra=osm_extra)) + 0.65 * np.log1p(self.near(f"ovt_{cat}", radius))

    def commute_at(self, xs: np.ndarray, ys: np.ndarray, dist: np.ndarray | None = None) -> dict[str, np.ndarray]:
        """Peak door-to-hub minutes by rail, road or walking."""
        sx = np.array([s["x"] for s in self.stations])
        sy = np.array([s["y"] for s in self.stations])
        dx = np.hypot(xs[:, None] - sx[None, :], ys[:, None] - sy[None, :]) if dist is None else dist
        walk = dx * WALK_DETOUR / WALK_M_PER_MIN
        feeder = FEEDER_WAIT + dx * ROAD_DETOUR / feeder_m_per_min(dx)
        access = np.minimum(walk, feeder)
        out: dict[str, np.ndarray] = {}
        for hub, times in self.hub_times.items():
            hx, hy = times["_xy"]
            tvec = np.array([times[s["id"]] for s in self.stations])
            via_rail = (access + tvec[None, :]).min(axis=1)
            dh = np.hypot(xs - hx, ys - hy)
            road = ROAD_OVERHEAD + dh * ROAD_DETOUR / road_m_per_min(dh)
            on_foot = dh * WALK_DETOUR / WALK_M_PER_MIN
            out[hub] = np.minimum(np.minimum(via_rail, road), on_foot)
        return out


def build_point_signals(signal_grid, pool_h, park_ha_1k, green_ha_1k, d_park,
                        d_station, lines_near, commute_min_pt):
    near, both = signal_grid.near, signal_grid.both
    print("→ per-point signals")
    L = np.log1p

    pt = {
        "food": both("food", 800),
        "nightlife": (
            0.80 * both("night", 1000)
            + 0.15 * L(2 * (near("karaoke", 1000) + near("ovt_karaoke", 1000)))
            # Hostels only weakly: airport-side guesthouses (Don Mueang, Lat
            # Krabang) are not a nightlife signal, Khao San's are.
            + 0.05 * L(near("hostel", 1000) + near("ovt_hostel", 1000))
        ),
        "daily_essentials": (
            0.30 * both("grocery", 800) + 0.15 * both("pharmacy", 800) + 0.20 * both("health", 1000)
            + 0.10 * both("bank", 800) + 0.10 * both("laundry", 800) + 0.05 * both("post", 1200)
            + 0.10 * both("school", 1000)
        ),
        "gym_sports": both("sports", 1200, osm_extra=0.3 * pool_h),
        "vibe": (
            0.40 * both("venue", 1000) + 0.20 * both("cafe", 800)
            + 0.20 * L(near("temple", 1000) + near("ovt_temple", 1000) + 0.5 * near("historic", 800))
            + 0.10 * L(near("attraction", 1000)) + 0.10 * L(near("pedestrian", 1000) + near("market", 1000))
        ),
        "green": 0.6 * L(park_ha_1k) + 0.25 * L(green_ha_1k) + 0.15 * np.exp(-d_park / 600),
        "transport": (
            0.45 * np.exp(-d_station / 800)
            + 0.25 * np.minimum(1, L(lines_near) / math.log1p(4))
            + 0.10 * np.minimum(1, L(near("bus", 500)) / math.log1p(8))
            + 0.05 * np.minimum(1, near("pier", 800))
            + 0.15 * np.clip(1 - (commute_min_pt - 10) / 80, 0, 1)
        ),
    }

    # Busyness around a point for the station-area / grid levels, where no
    # population density exists: every place within 400 m (Overture's full
    # POI set — shops, eateries, offices, services). Inverted → quietness.
    pt_crowd = L(near("ovt_all", 400))

    return pt, pt_crowd
