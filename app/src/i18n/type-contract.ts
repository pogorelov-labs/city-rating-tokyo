import type { AppConfig, useTranslations } from 'next-intl';

// Checked by CI's tsc, never executed. Each expect-error becomes an error itself
// if a future config change silently removes the locale or message contract.
export function verifyTranslationTypes(t: ReturnType<typeof useTranslations<never>>) {
  const locale: AppConfig['Locale'] = 'ja';
  t('loading.map');
  t('station.sourcesLabel');
  // @ts-expect-error Unknown message keys must not compile.
  t('loading.nonexistentMapLabel');
  // @ts-expect-error A namespace is not a leaf message.
  t('loading');
  // @ts-expect-error Unsupported locales must not compile.
  const unsupported: AppConfig['Locale'] = 'fr';
  return { locale, unsupported };
}
