import { hasLocale } from 'next-intl';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { routing, type Locale } from '@/i18n/routing';
import { stationDisplayName } from '@/lib/station-name';
import { CityProvider } from '@/lib/city-context';
import AreaGuide from '@/components/area/AreaGuide';
import AreaGuideExtras from '@/components/area/AreaGuideExtras';
import { getBangkokDistrict, getBangkokStationArea, getBangkokStationAreaIds } from '@/lib/bangkok-data';
import { stationPrimaryName } from '@/lib/station-name';

export function generateStaticParams() {
  const ids = getBangkokStationAreaIds();
  return routing.locales.flatMap((locale) => ids.map((id) => ({ locale, id })));
}

/** JA pages lead with the katakana name, every other locale with the Latin
 *  name on the station signs; Thai is always the secondary line. */
function areaNames(id: string, locale: Locale) {
  const a = getBangkokStationArea(id)!;
  return stationDisplayName({ name_en: a.name_en, name_jp: a.name_jp, name_th: a.name_th }, locale);
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}): Promise<Metadata> {
  const { locale, id } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const area = getBangkokStationArea(id);
  const t = await getTranslations({ locale, namespace: 'bangkok.station' });
  if (!area) return { title: t('notFound') };
  const { primary } = areaNames(id, locale as Locale);
  const district = getBangkokDistrict(area.district);
  const districtName = district ? stationPrimaryName(district, locale as Locale) : area.district;
  const desc = t('metaDescription', { name: primary, district: districtName });
  return {
    title: t('metaTitle', { name: primary, nameTh: area.name_th }),
    description: desc,
    openGraph: {
      title: `${primary} (${area.name_th})`,
      description: desc,
      type: 'article',
      ...(area.image && { images: [{ url: area.image.hero }] }),
    },
  };
}


export default async function StationAreaPage({
  params,
}: { params: Promise<{ locale: string; id: string }> }) {
  const { locale, id } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const { buildAreaGuide } = await import('@/lib/area-guide-data');
  const area = await buildAreaGuide('bangkok', 'station', id, locale);
  if (!area) notFound();
  const source = getBangkokStationArea(id);
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Place',
    name: `${area.name} station area, Bangkok`,
    alternateName: [source?.name_th, source?.name_en].filter((name): name is string => typeof name === 'string' && name !== area.name),
    inLanguage: locale,
    geo: { '@type': 'GeoCoordinates', latitude: area.map.center[0], longitude: area.map.center[1] },
    containedInPlace: { '@type': 'City', name: 'Bangkok' },
    ...(source?.wikipedia.en && { sameAs: source.wikipedia.en }),
  };
  return <CityProvider city="bangkok">
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }} />
    <AreaGuide key={area.key} area={area}><AreaGuideExtras area={area} /></AreaGuide>
  </CityProvider>;
}
