import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Providers, messages } from '@/test/providers';
import { station } from '@/test/stations';
import { DEFAULT_WEIGHTS } from '@/lib/types';
import LeafletAreaCard from './LeafletAreaCard';

const { closePopup } = vi.hoisted(() => ({ closePopup: vi.fn() }));
vi.mock('react-leaflet', () => ({ useMap: () => ({ closePopup }) }));
vi.mock('@/i18n/navigation', () => ({ Link: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));

describe('LeafletAreaCard', () => {
  it('closes the popup and invokes the explicit selection dismissal callback', () => {
    const clear = vi.fn();
    render(<Providers><LeafletAreaCard area={station('alpha')} city="tokyo" score={6} weights={DEFAULT_WEIGHTS} onClose={clear} /></Providers>);
    fireEvent.click(screen.getByRole('button', { name: messages.en.areaGuide.compact.close }));
    expect(closePopup).toHaveBeenCalledOnce();
    expect(clear).toHaveBeenCalledOnce();
  });
});
