/**
 * Editorial research layer (E-1/P1-dark) — the Bangkok research program's
 * surface in the app. Named editorial-research to avoid the existing
 * editorial.ts (Tokyo rating-provenance helper).
 *
 * The exporter (scripts/export-editorial.mjs) generates the preview index and
 * per-entity chunks from the research program's bundles. Everything here is
 * DARK until both switches are on:
 *   1. `EDITORIAL_ENABLED` — code flag (P1-dark: false; flip at launch);
 *   2. `copy_eligible` — per-entity human-sign-off key (E-5): false until a
 *      human reviewer signs the bundle. Agent-reviewed bundles NEVER render
 *      editorial copy, regardless of the code flag.
 *
 * Client-safety: only this module imports the index; UI components consume
 * the plain records it returns (or nothing while dark).
 */
import editorialIndex from '@/data/bangkok/editorial-index.json';

/** P1-dark code flag — flip only after A-1 human sign-off lands. */
export const EDITORIAL_ENABLED = false;

export interface EditorialReview { status: string; signatory: string; reviewer: string | null; reviewed_at: string | null }
export interface EditorialRecord {
  tier: 'A' | 'B' | 'C';
  card?: 'data_only';
  copy_eligible: boolean;
  as_of: string | null;
  chunk: string | null;
  review: EditorialReview;
  stats?: { sources: number; body_read: number; claims: number };
  disclosures?: string[];
  recheck_due: string | null;
  superseded_by?: boolean | null;
}

const index = editorialIndex as unknown as { entities: Record<string, EditorialRecord> };

export function editorialRecord(areaId: string): EditorialRecord | null {
  return index.entities[areaId] ?? index.entities[`st.${areaId}`] ?? null;
}

export interface EditorialCardMeta {
  dataOnly: boolean;
  asOf: string | null;
  recheckDue: string | null;
  /** Card preview sentence — present only when copy-eligible (P1: via snippets merge). */
  preview: null;
}

/** Card meta for an area id. Dark while the flag is off; eligibility-gated. */
export function editorialCardMeta(areaId: string): EditorialCardMeta | null {
  if (!EDITORIAL_ENABLED) return null;
  const rec = editorialRecord(areaId);
  if (!rec) return null;
  if (rec.tier === 'C' || rec.card === 'data_only') {
    return { dataOnly: true, asOf: null, recheckDue: rec.recheck_due, preview: null };
  }
  return { dataOnly: false, asOf: rec.as_of, recheckDue: rec.recheck_due, preview: null };
}

/** Pure: merge eligible previews into a snippet record (server-side helper). */
export function mergeEditorialSnippets(
  snippets: Record<string, string>,
  eligiblePreviews: Record<string, string>,
  enabled: boolean,
): Record<string, string> {
  if (!enabled) return snippets;
  return { ...eligiblePreviews, ...snippets };
}

/** Pure: does this record permit editorial copy in the UI? */
export function permitsCopy(rec: EditorialRecord | null): boolean {
  return Boolean(EDITORIAL_ENABLED && rec?.copy_eligible && rec.tier !== 'C');
}

/** Pure: disclosure keys for an area (empty while dark). */
export function editorialDisclosures(areaId: string): string[] {
  if (!EDITORIAL_ENABLED) return [];
  return editorialRecord(areaId)?.disclosures ?? [];
}
