'use client';

import { useTranslations } from 'next-intl';
import {
  StationPlace,
  PlaceCategory,
  getGoogleMapsSearchUrl,
} from '@/lib/types';

const CATEGORY_ICONS: Record<PlaceCategory, string> = {
  gym: '🏋️',
  mall: '🛍️',
  park: '🌳',
  landmark: '📍',
  cafe: '☕',
  restaurant: '🍜',
  bar: '🍺',
};

const DEFAULT_CATEGORIES: PlaceCategory[] = ['gym', 'mall', 'park', 'restaurant', 'cafe', 'bar'];

interface NearbyPlacesProps {
  places: StationPlace[];
  lat: number;
  lng: number;
  stationName: string;
}

export default function NearbyPlaces({ places, lat, lng, stationName }: NearbyPlacesProps) {
  const t = useTranslations();
  const grouped = new Map<PlaceCategory, StationPlace[]>();
  for (const p of places) {
    const list = grouped.get(p.category) || [];
    list.push(p);
    grouped.set(p.category, list);
  }

  // Show categories that have places first, then remaining default categories
  const categoriesWithPlaces = Array.from(grouped.keys());
  const remainingCategories = DEFAULT_CATEGORIES.filter(
    (c) => !categoriesWithPlaces.includes(c)
  );
  const allCategories = [...categoriesWithPlaces, ...remainingCategories];

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="font-bold text-lg mb-4">{t('station.nearbyPlaces')}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {allCategories.map((category) => {
          const categoryPlaces = grouped.get(category) || [];
          const searchUrl = getGoogleMapsSearchUrl(lat, lng, category);

          return (
            <div key={category} className="space-y-2">
              <div className="flex items-center gap-2">
                <span>{CATEGORY_ICONS[category]}</span>
                <span className="font-medium text-sm">
                  {t(`placeCategories.${category}`)}
                </span>
              </div>
              {categoryPlaces.length > 0 && (
                <ul className="space-y-1 ml-7">
                  {categoryPlaces.map((place, i) => (
                    <li key={i}>
                      <a
                        href={place.google_maps_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline"
                        data-umami-event="open-place"
                        data-umami-event-category={category}
                      >
                        {place.name}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
              <a
                href={searchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-7 text-xs text-gray-500 hover:text-blue-600 hover:underline inline-flex items-center gap-1"
                data-umami-event="find-more"
                data-umami-event-category={category}
              >
                {t('station.findMoreOnMaps')}
                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M7 17L17 7M17 7H7M17 7V17" />
                </svg>
              </a>
            </div>
          );
        })}
      </div>
    </section>
  );
}
