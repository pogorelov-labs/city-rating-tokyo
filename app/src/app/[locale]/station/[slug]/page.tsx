import { hasLocale } from 'next-intl';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { routing, type Locale } from '@/i18n/routing';
import { stationDisplayName } from '@/lib/station-name';
import { CityProvider } from '@/lib/city-context';
import AreaGuide from '@/components/area/AreaGuide';
import AreaGuideExtras from '@/components/area/AreaGuideExtras';
import { getStation, getStations } from '@/lib/data';

export function generateStaticParams() {
  const slugs = getStations()
    .filter((s) => s.ratings !== null)
    .map((s) => s.slug);
  return routing.locales.flatMap((locale) =>
    slugs.map((slug) => ({ locale, slug }))
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const t = await getTranslations({ locale, namespace: 'station' });
  const station = getStation(slug);
  if (!station) {
    const errors = await getTranslations({ locale, namespace: 'error' });
    return { title: errors('stationNotFound') };
  }
  const { primary, secondary } = stationDisplayName(station, locale as Locale);
  const atmosphere = station.description?.[locale as Locale]?.atmosphere;
  const desc = atmosphere
    ? atmosphere.slice(0, 155)
    : t('metaDescriptionFallback', { name: primary });
  return {
    title: t('metaTitle', { name: primary, secondary }),
    description: t('metaDescription', { name: primary, description: desc }),
    openGraph: {
      title: `${primary} (${secondary})`,
      description: desc,
      type: 'article',
    },
  };
}


export default async function StationPage({
  params,
}: { params: Promise<{ locale: string; slug: string }> }) {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const { buildAreaGuide } = await import('@/lib/area-guide-data');
  const area = await buildAreaGuide('tokyo', 'station', slug, locale);
  if (!area) notFound();
  // A weighted score is not an aggregate of human reviews.
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Place',
    name: `${area.name} Station Area`,
    alternateName: area.localName,
    inLanguage: locale,
    geo: { '@type': 'GeoCoordinates', latitude: area.map.center[0], longitude: area.map.center[1] },
  };
  return <CityProvider city="tokyo">
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }} />
    <AreaGuide key={area.key} area={area}><AreaGuideExtras area={area} /></AreaGuide>
  </CityProvider>;
}
