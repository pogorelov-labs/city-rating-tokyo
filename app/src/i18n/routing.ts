import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'ja', 'ru'] as const,
  defaultLocale: 'en',
  // 'as-needed' = the default locale (EN) gets NO URL prefix (/station/shibuya,
  // not /en/station/shibuya). Non-default locales are prefixed (/ja/, /ru/).
  // This matches the sitemap's canonical-URL transform (which strips /en/) and
  // the hreflang alternates. Without this, next-intl defaults to 'always' which
  // prefixes ALL locales including EN, creating a redirect chain that conflicts
  // with the sitemap's declared canonicals.
  localePrefix: 'as-needed',
});

export type Locale = (typeof routing.locales)[number];
