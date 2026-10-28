import type { ComponentProps, ReactNode } from 'react';
import { Link } from '@/i18n/navigation';
import LocaleSwitcher from '@/components/LocaleSwitcher';

export default function DetailHeader({ homeHref, backLabel, primary, secondary, mapsUrl, mapsTitle, mapsLabel, areaKey, score, scoreColor, scoreTitle, tokyo = false, badge }: {
  homeHref: ComponentProps<typeof Link>['href']; backLabel: string; primary: string; secondary: string; mapsUrl: string; mapsTitle: string; mapsLabel: string;
  areaKey: string; score: number | null; scoreColor: string; scoreTitle?: string; tokyo?: boolean; badge?: ReactNode;
}) {
  return <header className="bg-white border-b border-gray-200">
    <div className={tokyo ? 'max-w-4xl mx-auto px-4 py-3 flex items-center gap-4' : 'max-w-4xl mx-auto px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-1'}>
      <Link href={homeHref} className="text-sm text-blue-600 hover:underline flex items-center gap-1" data-umami-event="back-to-map">
        &larr; {backLabel}
      </Link>
      <span className="text-gray-300">|</span>
      {tokyo ? <span className="font-bold text-lg">{primary}</span> : <h1 className="font-bold text-lg">{primary}</h1>}
      {badge}
      <span className="text-gray-400">{secondary}</span>
      <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline flex items-center gap-1"
        title={mapsTitle} data-umami-event="open-google-maps" data-umami-event-station={areaKey}>
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
        {mapsLabel}
      </a>
      <LocaleSwitcher />
      {score !== null && <span className="ml-auto text-2xl font-bold" style={{ color: scoreColor }} title={scoreTitle}>{score.toFixed(1)}</span>}
    </div>
  </header>;
}
