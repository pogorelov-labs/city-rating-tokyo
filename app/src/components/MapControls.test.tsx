import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { useAppStore } from '@/lib/store';
import MapControls from './MapControls';

let resize: (entries: { contentRect: { width: number } }[]) => void;
beforeEach(() => {
  useAppStore.setState(useAppStore.getInitialState(), true);
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: typeof resize) { resize = callback; }
    observe() {}
    disconnect() {}
  });
});
afterEach(() => vi.unstubAllGlobals());

describe('Bangkok compact map layers', () => {
  it('uses the compact control for a tablet-sized narrow map workspace', () => {
    render(<Providers city="bangkok"><div><MapControls /></div></Providers>);
    act(() => resize([{ contentRect: { width: 600 } }]));
    expect(screen.getByRole('button', { name: 'Map layers' })).toBeVisible();
  });
  it('keeps the layer toggles and dimension accessible in a narrow workspace', () => {
    render(<Providers city="bangkok"><div><MapControls /></div></Providers>);
    act(() => resize([{ contentRect: { width: 320 } }]));
    const trigger = screen.getByRole('button', { name: 'Map layers' });
    expect(trigger.querySelector('svg')).not.toHaveClass('md:hidden');
    expect(trigger.parentElement).toHaveClass('md:top-3');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger.parentElement).toHaveClass('z-[1000]');
    fireEvent.click(trigger);
    expect(trigger.parentElement).toHaveClass('z-[1003]');
    const panel = screen.getByRole('group', { name: 'Map layers' });
    const heat = within(panel).getByRole('button', { name: 'Heatmap' });
    fireEvent.click(heat);
    expect(heat).toHaveAttribute('aria-pressed', 'true');
    const dimension = within(panel).getByRole('combobox', { name: 'Heatmap' });
    fireEvent.change(dimension, { target: { value: 'food' } });
    expect(useAppStore.getState().heatmapDimension).toBe('food');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(trigger);
    fireEvent.keyDown(trigger, { key: 'Escape' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(trigger);
    fireEvent.focusIn(document.body);
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(trigger);
    fireEvent.pointerDown(document.body);
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(trigger);
    act(() => resize([{ contentRect: { width: 700 } }]));
    act(() => resize([{ contentRect: { width: 320 } }]));
    expect(screen.getByRole('button', { name: 'Map layers' })).toHaveAttribute('aria-expanded', 'false');
  });
});
