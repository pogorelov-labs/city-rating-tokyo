import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import LocaleSwitcher from './LocaleSwitcher';

const replace = vi.hoisted(() => vi.fn());
vi.mock('@/i18n/navigation', () => ({ useRouter: () => ({ replace }), usePathname: () => '/station/kichijoji' }));

beforeEach(() => { replace.mockClear(); });
describe('locale navigation retains the selected guide/map context', () => {
  it('keeps weights, destination and comparison when switching to Japanese', () => {
    window.history.replaceState(null, '', '/station/kichijoji?w=12,8,20,25,0,20,0,0,0,15&hub=tokyo&reference=mitaka');
    render(<Providers><LocaleSwitcher /></Providers>);
    fireEvent.click(screen.getByRole('button', { name: 'JA' }));
    expect(replace).toHaveBeenCalledWith({ pathname: '/station/kichijoji', query: {
      w: '12,8,20,25,0,20,0,0,0,15', hub: 'tokyo', reference: 'mitaka',
    } }, { locale: 'ja' });
  });
});
