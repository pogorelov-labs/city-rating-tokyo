import { TransitMinutes, HUB_LABELS } from '@/lib/types';

export default function HubStrip({
  transitMinutes,
  mapsUrl,
}: {
  transitMinutes: TransitMinutes;
  mapsUrl: string;
}) {
  const hubs = Object.entries(transitMinutes) as [keyof TransitMinutes, number][];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <span className="text-xs text-gray-400 shrink-0">Hubs</span>
        <div className="flex flex-wrap gap-2">
          {hubs.map(([hub, minutes]) => (
            <span
              key={hub}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
            >
              {HUB_LABELS[hub]} {minutes}m
            </span>
          ))}
        </div>
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-600 hover:underline sm:ml-auto shrink-0"
        >
          Google Maps &rarr;
        </a>
      </div>
    </div>
  );
}
