// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('next-intl', () => ({ useTranslations: () => (key: string) => key }));
vi.mock('@/i18n/navigation', () => ({ Link: ({ href, children, ...props }: React.PropsWithChildren<{ href: string }>) => <a href={href} {...props}>{children}</a> }));
import { AreaCardActions } from './area-card';

describe('area card actions', () => {
  it('keeps detail links and popup compare actions with propagation stopped', () => {
    const add = vi.fn(); const remove = vi.fn(); const parent = vi.fn();
    const { rerender } = render(<div onClick={parent}><AreaCardActions city="tokyo" slug="akihabara" isCompared={false} compareFull={false} onCompare={add} onUncompare={remove} /></div>);
    expect(screen.getByRole('link', { name: 'map.viewDetails' })).toHaveAttribute('href', '/station/akihabara');
    fireEvent.click(screen.getByRole('button', { name: 'map.compare' }));
    expect(add).toHaveBeenCalledOnce(); expect(parent).not.toHaveBeenCalled();
    rerender(<AreaCardActions city="tokyo" slug="akihabara" isCompared compareFull onCompare={add} onUncompare={remove} />);
    fireEvent.click(screen.getByRole('button', { name: 'map.removeCompare' }));
    expect(remove).toHaveBeenCalledOnce();
  });
  it('keeps full compare disabled and touch targets sized for mobile', () => {
    render(<AreaCardActions city="bangkok" slug="pathum-wan" isCompared={false} compareFull onCompare={vi.fn()} onUncompare={vi.fn()} touch />);
    expect(screen.getByRole('link', { name: 'map.viewDetails' })).toHaveAttribute('href', '/bangkok/district/pathum-wan');
    expect(screen.getByRole('button', { name: 'map.compare' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'map.compare' })).toHaveStyle({ minHeight: '44px' });
  });
});
