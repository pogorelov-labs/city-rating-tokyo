import type { Locale } from '@/i18n/routing';

/**
 * Returns locale-appropriate primary + secondary station names.
 *
 * - EN: name_en (primary) + name_jp (secondary)
 * - JA: name_jp (primary) + name_en (secondary)
 * - RU: name_ru (primary, falls back to name_en) + name_jp (secondary)
 *
 * Kanji (name_jp) is always visible as either primary or secondary —
 * users in Tokyo see kanji on station signs regardless of UI language.
 */
export function stationDisplayName(
  station: { name_en: string; name_jp: string; name_ru?: string },
  locale: Locale,
): { primary: string; secondary: string } {
  switch (locale) {
    case 'ja':
      return { primary: station.name_jp, secondary: station.name_en };
    case 'ru':
      return { primary: station.name_ru || station.name_en, secondary: station.name_jp };
    default:
      return { primary: station.name_en, secondary: station.name_jp };
  }
}

/**
 * Returns the display name for a station used in single-line contexts
 * (ranked list, compare chips, scatter tooltip) where only one name fits.
 *
 * Falls back to name_en when locale-specific name isn't available.
 */
export function stationPrimaryName(
  station: { name_en: string; name_jp: string; name_ru?: string },
  locale: Locale,
): string {
  switch (locale) {
    case 'ja':
      return station.name_jp;
    case 'ru':
      return station.name_ru || station.name_en;
    default:
      return station.name_en;
  }
}
