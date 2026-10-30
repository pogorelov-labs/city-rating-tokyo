import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getPrototypeAreas } from '@/components/prototype/cards/data';
import AreaCardsPrototype from '@/components/prototype/cards/AreaCardsPrototype';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = {
  title: 'Area guide prototype · City Rating',
  robots: { index: false, follow: false },
};

export default async function CardsPrototypePage({ searchParams }: { searchParams: Promise<{ area?: string; view?: string }> }) {
  // Opt-in for any production preview; never expose a prototype by default.
  if (process.env.NODE_ENV === 'production' && process.env.ENABLE_CARD_PROTOTYPE !== 'true') notFound();
  const query = await searchParams;
  const areas = getPrototypeAreas();
  const initialArea = areas.some(a => a.id === query.area) ? query.area! : 'bangkok-station-asok';
  return <AreaCardsPrototype areas={areas} initialArea={initialArea} initialView={query.view === 'compact' ? 'compact' : 'detail'} />;
}
