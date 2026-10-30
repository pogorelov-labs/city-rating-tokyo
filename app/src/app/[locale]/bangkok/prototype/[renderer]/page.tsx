import { notFound } from 'next/navigation';
import { hasLocale } from 'next-intl';
import { setRequestLocale } from 'next-intl/server';
import { routing, type Locale } from '@/i18n/routing';
import CityHome from '@/components/CityHome';
import { getBangkokMapDistricts, getBangkokMapStationAreas, getBangkokSnippets, getBangkokThumbnails, getBangkokStationAreaThumbnails } from '@/lib/bangkok-data';

export const metadata = { title: 'Bangkok renderer lab', robots: { index: false, follow: false } };
export function generateStaticParams() {
  return process.env.BANGKOK_RENDERER_LAB === '1' ? [{ renderer: 'maplibre' }, { renderer: 'leaflet' }] : [];
}

export default async function RendererLab({ params }: { params: Promise<{ locale: string; renderer: string }> }) {
  const { locale, renderer } = await params;
  if (process.env.BANGKOK_RENDERER_LAB !== '1' || !hasLocale(routing.locales, locale) || !['maplibre', 'leaflet'].includes(renderer)) notFound();
  setRequestLocale(locale);
  return <CityHome city="bangkok" stations={getBangkokMapDistricts()} stationAreas={getBangkokMapStationAreas()}
    thumbnails={{ ...getBangkokThumbnails(), ...getBangkokStationAreaThumbnails() }} snippets={getBangkokSnippets(locale as Locale)}
    prototypeRenderer={renderer as 'maplibre' | 'leaflet'} />;
}
