import type { Locale } from '@/i18n/routing';

type Named = { name_en: string; name_jp: string; name_ru?: string; name_th?: string };

/**
 * Returns locale-appropriate primary + secondary names for a rated area.
 *
 * Tokyo stations:
 * - EN: name_en (primary) + name_jp (secondary)
 * - JA: name_jp (primary) + name_en (secondary)
 * - RU: name_ru (primary, falls back to name_en) + name_jp (secondary)
 *
 * Bangkok districts (have `name_th`) — the local script is Thai, so Thai
 * takes the always-visible secondary slot that kanji holds in Tokyo:
 * - EN: name_en + name_th · JA: name_jp (katakana) + name_th · RU: name_ru + name_th
 *
 * The native script is always visible — it is what residents see on
 * station signs and street plates regardless of UI language.
 */
export function stationDisplayName(
  station: Named,
  locale: Locale,
): { primary: string; secondary: string } {
  if (station.name_th) {
    return { primary: stationPrimaryName(station, locale), secondary: station.name_th };
  }
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
 * Returns the display name for an area used in single-line contexts
 * (ranked list, compare chips, scatter tooltip) where only one name fits.
 *
 * Falls back to name_en when locale-specific name isn't available.
 */
export function stationPrimaryName(station: Named, locale: Locale): string {
  switch (locale) {
    case 'ja':
      return station.name_jp || station.name_en;
    case 'ru':
      return station.name_ru || station.name_en;
    default:
      return station.name_en;
  }
}

/**
 * Case-insensitive search over an area's names and aliases. Returns the
 * alias that matched when the hit came from an alias ("Thong Lo" → the
 * Watthana district), so result rows can say which neighbourhood matched.
 */
export function matchArea(
  area: Named & { aliases?: string[] },
  query: string,
): { matched: boolean; alias?: string } {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return { matched: false };
  if (
    area.name_en.toLowerCase().includes(q) ||
    area.name_jp.includes(query.trim()) ||
    (area.name_ru && area.name_ru.toLowerCase().includes(q)) ||
    (area.name_th && area.name_th.includes(query.trim()))
  ) {
    return { matched: true };
  }
  const alias = area.aliases?.find((a) => a.toLowerCase().includes(q));
  return alias ? { matched: true, alias } : { matched: false };
}
