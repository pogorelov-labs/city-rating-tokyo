import type { ReactNode } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { CityProvider } from '@/lib/city-context';
import type { CityId } from '@/lib/cities';
import type { Locale } from '@/i18n/routing';
import en from '@/messages/en/common.json';
import ja from '@/messages/ja/common.json';
import ru from '@/messages/ru/common.json';

export const messages = { en, ja, ru };

export function Providers({ children, city = 'tokyo', locale = 'en' }: {
  children: ReactNode; city?: CityId; locale?: Locale;
}) {
  return <NextIntlClientProvider locale={locale} messages={messages[locale]} timeZone="UTC"
    onError={(error) => { throw error; }}>
    <CityProvider city={city}>{children}</CityProvider>
  </NextIntlClientProvider>;
}
