'use client';

import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { routing, Locale } from '@/i18n/routing';

const LOCALE_LABELS: Record<Locale, string> = {
  en: 'EN',
  ja: 'JA',
  ru: 'RU',
};

export default function LocaleSwitcher() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();

  function switchLocale(next: Locale) {
    if (next === locale) return;
    router.replace(pathname, { locale: next });
  }

  return (
    <div className="inline-flex items-center rounded-lg border border-gray-200 bg-white overflow-hidden text-xs">
      {routing.locales.map((loc) => (
        <button
          key={loc}
          onClick={() => switchLocale(loc)}
          data-umami-event="switch-locale"
          data-umami-event-locale={loc}
          className={`px-2 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset ${
            loc === locale
              ? 'bg-blue-600 text-white font-semibold'
              : 'text-gray-500 hover:bg-gray-50'
          }`}
        >
          {LOCALE_LABELS[loc]}
        </button>
      ))}
    </div>
  );
}
