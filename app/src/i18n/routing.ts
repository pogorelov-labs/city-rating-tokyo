import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'ja', 'ru'] as const,
  defaultLocale: 'en',
});

export type Locale = (typeof routing.locales)[number];
