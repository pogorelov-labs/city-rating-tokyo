import type { useTranslations } from 'next-intl';

export type AppTranslator = ReturnType<typeof useTranslations<never>>;
export type MessageKey = Parameters<AppTranslator>[0];

/** Only data-provided identifiers need this boundary. Literal UI keys remain
 * compiler-checked. Unknown source/hub IDs retain their readable raw fallback. */
export function dataLabel(t: AppTranslator, namespace: 'sources' | 'hubs', id: string): string {
  const key = `${namespace}.${id}` as MessageKey;
  return t.has(key) ? t(key) : id;
}
