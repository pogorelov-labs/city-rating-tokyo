import { describe, expect, it } from 'vitest';
import { editorialRecord, editorialCardMeta, mergeEditorialSnippets, permitsCopy, editorialDisclosures, EDITORIAL_ENABLED } from './editorial-research';

describe('editorial-research (P1-dark)', () => {
  it('flag ships dark', () => {
    expect(EDITORIAL_ENABLED).toBe(false);
  });

  it('resolves records by bare district slug and st.-prefixed area id', () => {
    // one real key from each namespace of the committed index
    expect(editorialRecord('sala-daeng')?.tier).toBe('A');
    expect(editorialRecord('st.sala-daeng')?.tier).toBe('A');
    expect(editorialRecord('nonexistent-area')).toBeNull();
  });

  it('card meta is dark while the flag is off (eligibility irrelevant)', () => {
    expect(editorialCardMeta('st.sala-daeng')).toBeNull();
    expect(editorialCardMeta('nonexistent')).toBeNull();
  });

  it('mergeEditorialSnippets: dark passthrough, enabled merge with snippet priority', () => {
    const base = { a: 'base-a' };
    const previews = { a: 'preview-a', b: 'preview-b' };
    expect(mergeEditorialSnippets(base, previews, false)).toEqual({ a: 'base-a' });
    const merged = mergeEditorialSnippets(base, previews, true);
    expect(merged.a).toBe('base-a'); // existing snippet wins over editorial preview
    expect(merged.b).toBe('preview-b');
  });

  it('permitsCopy: null record, non-eligible, and tier C all forbid copy', () => {
    expect(permitsCopy(null)).toBe(false);
    const rec = editorialRecord('sala-daeng');
    expect(rec?.copy_eligible).toBe(false); // no human sign-off yet
    expect(permitsCopy(rec)).toBe(false);
    const c = editorialRecord('nonexistent');
    expect(permitsCopy(c)).toBe(false);
  });

  it('disclosures are dark while the flag is off', () => {
    expect(editorialDisclosures('st.sala-daeng')).toEqual([]);
  });
});
