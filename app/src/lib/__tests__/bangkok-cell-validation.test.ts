import { describe, expect, it } from 'vitest';
import { bangkokCellKeyStatus, cellInfo, GRID_HEADER, isValidGridCell, type BangkokGrid } from '../bangkok-grid';
import { parseAreaKey } from '../area-key';

const district = new Uint8Array(GRID_HEADER.nx * GRID_HEADER.ny);
district[39725] = 1;
const grid: BangkokGrid = { header: GRID_HEADER, planes: { district }, cells: new Uint32Array([39725]) };

describe('Bangkok cell link validation', () => {
  it.each(['cell.', 'cell.-1', 'cell.1e3', 'cell.1.5', 'cell.+1', 'cell. 1', 'cell.9007199254740992'])('rejects non-decimal or unsafe index %s', key => {
    expect(parseAreaKey(key).index).toBeNull();
    expect(bangkokCellKeyStatus(key, null)).toBe('invalid');
  });
  it('rejects out-of-bounds and masked cells, but keeps valid-looking cells pending until the mask arrives', () => {
    expect(bangkokCellKeyStatus('cell.999999999999999', null)).toBe('invalid');
    expect(bangkokCellKeyStatus('cell.84810', null)).toBe('invalid');
    expect(bangkokCellKeyStatus('cell.0', null)).toBe('pending');
    expect(bangkokCellKeyStatus('cell.0', grid)).toBe('invalid');
    expect(bangkokCellKeyStatus('cell.39725', null)).toBe('pending');
    expect(bangkokCellKeyStatus('cell.39725', grid)).toBe('valid');
    expect(bangkokCellKeyStatus('st.asok', grid)).toBe('not-cell');
    expect(isValidGridCell(grid, 39725)).toBe(true);
    expect(isValidGridCell(grid, 0)).toBe(false);
    expect(isValidGridCell(grid, Number.MAX_SAFE_INTEGER)).toBe(false);
    expect(cellInfo(grid, 0, [])).toBeNull();
    expect(cellInfo(grid, Number.MAX_SAFE_INTEGER, [])).toBeNull();
  });
});
