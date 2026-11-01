import { describe, expect, it } from 'vitest';
import { GRID_HEADER, decodeGrid, scoreCells, passMask, cellInfo } from '../bangkok-grid';
import { calculateWeightedScore } from '../scoring';
import { gridPixels } from '../bangkok-grid-colors';
import { gridMesh, mercatorX, mercatorY } from '../bangkok-grid-mesh';
import { getBangkokMapDistricts } from '../bangkok-data';
import { DEFAULT_WEIGHTS } from '../types';
import { CITIES } from '../cities';
import { gunzipSync } from 'node:zlib';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('Bangkok rendering contract', () => {
  it('scores a selected cell identically without allocating/rescoring the city', () => {
    const packed = readFileSync(resolve(__dirname, '../../../public', GRID_HEADER.file.slice(1)));
    const grid = decodeGrid(new Uint8Array(gunzipSync(packed)), GRID_HEADER);
    const districts = getBangkokMapDistricts().map((d) => ({ ratings: d.ratings!, rent_1k: d.rent_1k }));
    const zero = { ...DEFAULT_WEIGHTS };
    for (const key of Object.keys(zero) as (keyof typeof zero)[]) zero[key] = 0;
    for (const weights of [DEFAULT_WEIGHTS, zero, { ...zero, food: 100 }, { ...zero, rent: 30, safety: 70 }]) {
      const expected = scoreCells(grid, weights, districts);
      const actual = new Float32Array(expected.length).fill(NaN);
      for (const i of grid.cells) actual[i] = calculateWeightedScore(cellInfo(grid, i, districts)!.ratings, weights);
      expect(Buffer.from(actual.buffer).equals(Buffer.from(expected.buffer))).toBe(true);
    }
  });
  it('projects every row boundary correctly with a bounded shared mesh', () => {
    const h = GRID_HEADER, mesh = gridMesh(h);
    expect(mesh.vertices.length / 4).toBe((h.ny + 1) * 2);
    expect(mesh.indices.length).toBe(h.ny * 6);
    for (let r = 0; r <= h.ny; r++) {
      const lat = h.north - r * (h.north - h.south) / h.ny;
      for (let side = 0; side < 2; side++) {
        const o = (r * 2 + side) * 4;
        // Float32 offsets retain better than 1 cm at the equator.
        expect(Math.abs(mesh.origin[0] + mesh.vertices[o] - mercatorX(side ? h.east : h.west)) * 40_075_017).toBeLessThan(0.01);
        expect(Math.abs(mesh.origin[1] + mesh.vertices[o + 1] - mercatorY(lat)) * 40_075_017).toBeLessThan(0.01);
        expect(mesh.vertices[o + 3]).toBeCloseTo(r / h.ny, 6);
      }
    }
    // A stretched quad would put the middle latitude at the wrong Mercator Y.
    expect(Math.abs(mercatorY((h.north + h.south) / 2) - (mercatorY(h.north) + mercatorY(h.south)) / 2)).toBeGreaterThan(1e-7);
  });

  it('gives both renderers the same pixels, preserves outside transparency and family filtering', () => {
    const packed = readFileSync(resolve(__dirname, '../../../public', GRID_HEADER.file.slice(1)));
    const grid = decodeGrid(new Uint8Array(gunzipSync(packed)), GRID_HEADER);
    const districts = getBangkokMapDistricts().map((d) => ({ ratings: d.ratings!, rent_1k: d.rent_1k }));
    const defaults = CITIES.bangkok.defaultFilters;
    const scores = scoreCells(grid, DEFAULT_WEIGHTS, districts);
    const pass = passMask(grid, defaults, defaults, districts, false, true);
    const args = [grid, scores, pass, GRID_HEADER.default_anchors, null, districts] as const;
    const leaf = new Uint8ClampedArray(grid.header.nx * grid.header.ny * 4);
    const gpu = new Uint8Array(leaf.length);
    expect(gridPixels(...args, leaf)).toBe(leaf);
    gridPixels(...args, gpu);
    expect(Buffer.from(leaf).equals(Buffer.from(gpu))).toBe(true);
    for (let i = 0; i < pass.length; i++) {
      if (!grid.planes.district[i]) expect(leaf[i * 4 + 3]).toBe(0);
      else if (!pass[i]) expect([...leaf.slice(i * 4, i * 4 + 4)]).toEqual([229, 231, 235, 140]);
    }
  });
});
