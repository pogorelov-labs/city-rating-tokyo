import { setRequestLocale } from 'next-intl/server';
import { getMapStations, getThumbnails, getSnippets } from '@/lib/data';
import type { Locale } from '@/i18n/routing';
import CityHome from '@/components/CityHome';

// Locale-agnostic data — computed once at module load
const stations = getMapStations();
const thumbnails = getThumbnails();

export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  // Snippets are locale-specific — each locale's homepage renders its own
  // multilingual atmosphere snippet (from the CRTKY-109 pipeline).
  const snippets = getSnippets(locale as Locale);

  return <CityHome city="tokyo" stations={stations} thumbnails={thumbnails} snippets={snippets} />;
}
