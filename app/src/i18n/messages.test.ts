import { describe, expect, it } from 'vitest';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';

// Include namespaces as well as leaves: replacing an object with a string or
// adding an empty namespace must fail too. No fixed, quickly stale key count.
function shape(value: unknown, path = '', result = new Map<string, string>()) {
  const kind = typeof value === 'string' ? 'message' : value && typeof value === 'object' && !Array.isArray(value) ? 'namespace' : 'invalid';
  if (path) result.set(path, kind);
  if (kind === 'namespace') for (const [key, child] of Object.entries(value as object)) {
    shape(child, path ? `${path}.${key}` : key, result);
  }
  return result;
}
function differences(reference: unknown, candidate: unknown): string[] {
  const expected = shape(reference), actual = shape(candidate);
  return [...new Set([...expected.keys(), ...actual.keys()])].sort().flatMap((key) => {
    if (!expected.has(key)) return [`Unexpected: ${key}`];
    if (!actual.has(key)) return [`Missing: ${key}`];
    if (actual.get(key) === 'invalid' || expected.get(key) !== actual.get(key)) return [`Wrong shape: ${key} (expected ${expected.get(key)}, got ${actual.get(key)})`];
    return [];
  });
}

describe('recursive locale contract (EN is the source of truth)', () => {
  for (const [locale, messages] of Object.entries({ en, ja, ru })) {
    it(`${locale} has every EN namespace and message, with no extras`, () => {
      const diff = differences(en, messages);
      expect(diff, `${locale}/common.json differs from en/common.json:\n${diff.join('\n')}`).toEqual([]);
    });
  }
  it('reports exact nested missing/extra keys and namespace/leaf mismatches', () => {
    expect(differences({ safety: { nested: { label: 'Label' }, value: 'Value' } },
      { safety: { nested: 'wrong', extra: 'Extra' } })).toEqual([
      'Unexpected: safety.extra', 'Wrong shape: safety.nested (expected namespace, got message)',
      'Missing: safety.nested.label', 'Missing: safety.value',
    ]);
    expect(differences({ a: 'a' }, { a: ['a'] })).toEqual(['Wrong shape: a (expected message, got invalid)']);
  });
});
