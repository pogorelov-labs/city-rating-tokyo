// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/i18n/navigation', () => ({ Link: ({ href, children, ...props }: React.PropsWithChildren<{ href: string }>) => <a href={href} {...props}>{children}</a> }));
vi.mock('@/components/LocaleSwitcher', () => ({ default: () => <span>Locales</span> }));
import DetailHeader from './DetailHeader';
import { FactsGrid, WikiLinks } from './DetailFacts';

describe('shared detail sections', () => {
  it('preserves Tokyo and Bangkok header variants and map links', () => {
    const props = { homeHref: '/', backLabel: 'Back', primary: 'Name', secondary: 'Native', mapsUrl: 'https://example.com/map', mapsTitle: 'Map', mapsLabel: 'Open map', areaKey: 'name', score: 7.2, scoreColor: 'red' };
    const { rerender } = render(<DetailHeader {...props} tokyo />);
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open map' })).toHaveAttribute('data-umami-event-station', 'name');
    rerender(<DetailHeader {...props} scoreTitle="District score" />);
    expect(screen.getByRole('heading', { name: 'Name' })).toBeInTheDocument();
    expect(screen.getByTitle('District score')).toHaveTextContent('7.2');
  });
  it('preserves ordered wiki links and the definition-list grid', () => {
    const { rerender } = render(<><FactsGrid><div><dt>Transit</dt><dd>5</dd></div></FactsGrid><WikiLinks label="Read" links={[{ lang: 'ja', url: 'https://ja.example' }, { lang: 'en', url: 'https://en.example' }]} /></>);
    expect(screen.getByText('Transit').closest('dl')).toHaveClass('grid', 'grid-cols-2');
    expect(screen.getAllByRole('link').map((link) => link.textContent)).toEqual(['Wikipedia (JA)', 'Wikipedia (EN)']);
    rerender(<WikiLinks label="Read" links={[]} />);
    expect(screen.queryByText('Read')).not.toBeInTheDocument();
  });
});
