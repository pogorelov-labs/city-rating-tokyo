import type { GridHeader } from './bangkok-grid';

export const mercatorX = (lng: number) => (lng + 180) / 360;
export const mercatorY = (lat: number) => (1 - Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360)) / Math.PI) / 2;

/** Exact projected row boundaries; a single affine image would distort latitude. */
export function gridMesh(h: GridHeader) {
  const origin = [mercatorX(h.west), mercatorY(h.north)];
  const vertices = new Float32Array((h.ny + 1) * 2 * 4);
  const indices = new Uint16Array(h.ny * 6);
  for (let row = 0; row <= h.ny; row++) {
    const lat = h.north - row / h.ny * (h.north - h.south);
    for (let side = 0; side < 2; side++) {
      vertices.set([side ? mercatorX(h.east) - origin[0] : 0, mercatorY(lat) - origin[1], side, row / h.ny], (row * 2 + side) * 4);
    }
    if (row < h.ny) { const a = row * 2; indices.set([a, a + 1, a + 2, a + 1, a + 3, a + 2], row * 6); }
  }
  return { origin, vertices, indices };
}
