import { hasLocale } from 'next-intl';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { routing, type Locale } from '@/i18n/routing';
import { stationDisplayName } from '@/lib/station-name';
import { CityProvider } from '@/lib/city-context';
import AreaGuide from '@/components/area/AreaGuide';
import AreaGuideExtras from '@/components/area/AreaGuideExtras';
import { getBangkokDistrict, getBangkokSlugs } from '@/lib/bangkok-data';

export function generateStaticParams() {
  const slugs = getBangkokSlugs();
  return routing.locales.flatMap((locale) => slugs.map((slug) => ({ locale, slug })));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  const district = getBangkokDistrict(slug);
  const t = await getTranslations({ locale, namespace: 'bangkok.district' });
  if (!district) return { title: t('notFound') };
  const { primary } = stationDisplayName(district, locale as Locale);
  const atmosphere = district.description?.[locale as Locale]?.atmosphere;
  const desc = atmosphere ? atmosphere.slice(0, 155) : t('metaDescriptionFallback', { name: primary });
  return {
    title: t('metaTitle', { name: primary, nameTh: district.name_th }),
    description: desc,
    openGraph: {
      title: `${primary} (${district.name_th})`,
      description: desc,
      type: 'article',
      ...(district.image && { images: [{ url: district.image.hero }] }),
    },
  };
}


export default async function DistrictPage({
  params,
}: { params: Promise<{ locale: string; slug: string }> }) {
  const { locale, slug } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const { buildAreaGuide } = await import('@/lib/area-guide-data');
  const area = await buildAreaGuide('bangkok', 'district', slug, locale);
  if (!area) notFound();
  const source = getBangkokDistrict(slug);
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'AdministrativeArea',
    name: `${area.name} District, Bangkok`,
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
