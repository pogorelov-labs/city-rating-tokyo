import type { ReactNode } from 'react';

export function FactsGrid({ children }: { children: ReactNode }) {
  return <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">{children}</dl>;
}

export function WikiLinks({ links, label }: { links: { lang: string; url: string }[]; label: string }) {
  if (links.length === 0) return null;
  return <p className="text-xs text-gray-500">
    {label}{' '}
    {links.map((link, i) => <span key={link.lang}>
      {i > 0 && ' · '}
      <a href={link.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Wikipedia ({link.lang.toUpperCase()})</a>
    </span>)}
  </p>;
}
