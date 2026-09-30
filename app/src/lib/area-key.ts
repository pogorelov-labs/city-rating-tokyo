/**
 * Selection keys for a city map.
 *
 * Every city slice in the store has one selection slot, one hover slot and
 * one compare list, all holding string keys. Tokyo keys are station slugs.
 * Bangkok shows three levels of detail whose ids overlap ("phaya-thai" is
 * a district *and* a station), so its keys carry the kind:
 *
 *   watthana        a district (plain slug — share links from before the
 *                   station / grid levels keep working)
 *   st.phrom-phong  a station area
 *   cell.41873      a 200 m grid cell (row-major index into the grid)
 *
 * Slugs never contain '.', and '.' survives URLSearchParams unescaped, so
 * links stay readable: `/bangkok?lv=st&s=st.asok`.
 */

export type AreaKind = 'district' | 'station' | 'cell';

const STATION_PREFIX = 'st.';
const CELL_PREFIX = 'cell.';

export function stationAreaKey(id: string): string {
  return `${STATION_PREFIX}${id}`;
}

export function cellKey(index: number): string {
  return `${CELL_PREFIX}${index}`;
}

export function parseAreaKey(key: string): { kind: AreaKind; id: string; index: number | null } {
  if (key.startsWith(STATION_PREFIX)) {
    return { kind: 'station', id: key.slice(STATION_PREFIX.length), index: null };
  }
  if (key.startsWith(CELL_PREFIX)) {
    const index = Number(key.slice(CELL_PREFIX.length));
    return { kind: 'cell', id: key, index: Number.isInteger(index) && index >= 0 ? index : null };
  }
  return { kind: 'district', id: key, index: null };
}

export function areaKind(key: string): AreaKind {
  return parseAreaKey(key).kind;
}
