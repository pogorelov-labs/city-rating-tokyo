import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { StationRatings } from '@/lib/types';

const translate = (key: string, values?: Record<string, unknown>) => values ? `${key}:${JSON.stringify(values)}` : key;
vi.mock('next-intl/server', () => ({ getTranslations: async () => translate }));
vi.mock('next-intl', () => ({ useTranslations: () => translate }));
vi.mock('@/i18n/navigation', () => ({ Link: ({ children, href, ...props }: React.PropsWithChildren<{ href: string }>) => <a href={href} {...props}>{children}</a> }));
import RatingsBreakdown from './RatingsBreakdown';

const ratings: StationRatings = { transport: 5, rent: 5, daily_essentials: 5, safety: 5, food: 5, green: 5, gym_sports: 5, vibe: 5, nightlife: 5, crowd: 5 };
describe('rating breakdown', () => {
  it('retains Tokyo freshness and hides the confidence legend when no confidence exists', async () => {
    const html = renderToStaticMarkup(await RatingsBreakdown({ kind: 'tokyo', ratings, medians: ratings, dataDate: '2026-01' }));
    expect(html).toContain('station.ratingsCaption');
    expect(html).toContain('2026-01');
    expect(html).not.toContain('confidence.strong.label');
    expect(html).toContain('href="/methodology"');
  });
  it('keeps Bangkok district and station disclosure separate', async () => {
    for (const kind of ['district', 'station'] as const) {
      const html = renderToStaticMarkup(await RatingsBreakdown({ kind, ratings, medians: ratings }));
      expect(html).toContain(`bangkok.${kind}.ratingsCaption`);
      expect(html).toContain(`bangkok.${kind}.relativeNote`);
      expect(html).toContain('confidence.editorial.label');
      expect(html).toContain('href="/methodology#bangkok"');
    }
  });
});
