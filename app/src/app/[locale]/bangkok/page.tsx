import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import {
  getBangkokMapDistricts,
  getBangkokMapStationAreas,
  getBangkokSnippets,
  getBangkokStationAreaThumbnails,
  getBangkokThumbnails,
} from '@/lib/bangkok-data';
import type { Locale } from '@/i18n/routing';
import CityHome from '@/components/CityHome';

// Locale-agnostic data — computed once at module load
const districts = getBangkokMapDistricts();
const stationAreas = getBangkokMapStationAreas();
// One map keyed like the selection: district slugs + `st.<id>` station areas.
const thumbnails = { ...getBangkokThumbnails(), ...getBangkokStationAreaThumbnails() };

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'bangkok.metadata' });
  return {
    title: t('title'),
    description: t('description'),
    openGraph: { title: t('title'), description: t('description'), type: 'website' },
  };
}

export default async function BangkokHome({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const snippets = getBangkokSnippets(locale as Locale);

  return (
    <CityHome
      city="bangkok"
      stations={districts}
      stationAreas={stationAreas}
      thumbnails={thumbnails}
      snippets={snippets}
    />
  );
}
