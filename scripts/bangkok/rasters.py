"""Raster counting and polygon rasterization for Bangkok."""
from __future__ import annotations
import math
import numpy as np
import shapely
from shapely.geometry import Polygon

def fft_convolve_same(a: np.ndarray, k: np.ndarray) -> np.ndarray:
    ky, kx = k.shape
    sy, sx = a.shape[0] + ky - 1, a.shape[1] + kx - 1
    full = np.fft.irfft2(np.fft.rfft2(a, s=(sy, sx)) * np.fft.rfft2(k, s=(sy, sx)), s=(sy, sx))
    cy, cx = ky // 2, kx // 2
    return np.clip(np.round(full[cy : cy + a.shape[0], cx : cx + a.shape[1]], 6), 0, None)

class Raster:
    """Regular grid over the POI bbox; turns point sets into 'count within r'."""

    def __init__(self, bounds: tuple[float, float, float, float], cell: float):
        self.x0, self.y0 = bounds[0], bounds[1]
        self.cell = cell
        self.nx = int(math.ceil((bounds[2] - bounds[0]) / cell))
        self.ny = int(math.ceil((bounds[3] - bounds[1]) / cell))
        self._kernels: dict[float, np.ndarray] = {}

    def index(self, xs: np.ndarray, ys: np.ndarray):
        ix = np.floor((xs - self.x0) / self.cell).astype(int)
        iy = np.floor((ys - self.y0) / self.cell).astype(int)
        ok = (ix >= 0) & (ix < self.nx) & (iy >= 0) & (iy < self.ny)
        return ix, iy, ok

    def hist(self, xs: np.ndarray, ys: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
        h = np.zeros((self.ny, self.nx))
        if len(xs) == 0:
            return h
        ix, iy, ok = self.index(xs, ys)
        w = np.ones(len(xs)) if weights is None else weights
        np.add.at(h, (iy[ok], ix[ok]), w[ok])
        return h

    def kernel(self, radius: float) -> np.ndarray:
        if radius not in self._kernels:
            r = int(math.ceil(radius / self.cell))
            yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
            self._kernels[radius] = ((xx * xx + yy * yy) * self.cell**2 <= radius**2).astype(float)
        return self._kernels[radius]

    def within(self, h: np.ndarray, radius: float) -> np.ndarray:
        return fft_convolve_same(h, self.kernel(radius))

    def sample(self, a: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        ix, iy, ok = self.index(xs, ys)
        out = np.zeros(len(xs))
        out[ok] = a[iy[ok], ix[ok]]
        return out

    def cell_centres(self, x0: float, y0: float, x1: float, y1: float):
        """Cell-centre coordinates (and indices) inside a bbox."""
        i0 = max(0, int((x0 - self.x0) / self.cell))
        i1 = min(self.nx - 1, int((x1 - self.x0) / self.cell))
        j0 = max(0, int((y0 - self.y0) / self.cell))
        j1 = min(self.ny - 1, int((y1 - self.y0) / self.cell))
        if i1 < i0 or j1 < j0:
            return None
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
        cx = self.x0 + (ii + 0.5) * self.cell
        cy = self.y0 + (jj + 0.5) * self.cell
        return ii.ravel(), jj.ravel(), cx.ravel(), cy.ravel()

def rasterize(polys: list[Polygon], raster: Raster, min_area: float = 0.0) -> np.ndarray:
    """1 where a cell centre lies inside any polygon (each cell = cell² m²)."""
    grid = np.zeros((raster.ny, raster.nx))
    for p in polys:
        if p.area < min_area:
            continue
        cc = raster.cell_centres(*p.bounds)
        if cc is None:
            continue
        ii, jj, cx, cy = cc
        inside = shapely.contains_xy(p, cx, cy)
        grid[jj[inside], ii[inside]] = 1.0
    return grid
