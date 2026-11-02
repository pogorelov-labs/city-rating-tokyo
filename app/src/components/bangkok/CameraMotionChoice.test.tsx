import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { Providers } from '@/test/providers';
import { bangkokCameraReduced, bangkokMotion, cameraMotion, prefersReducedMotion, setBangkokMotion } from '@/lib/map-motion';
import CameraMotionChoice from './CameraMotionChoice';

const key = 'city-rating:bangkok:camera-motion';
beforeEach(() => {
  vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  setBangkokMotion('system');
});
afterEach(() => { vi.restoreAllMocks(); setBangkokMotion('system'); vi.unstubAllGlobals(); });

it('opts in locally without changing device motion or the shared URL, then follows the device again', () => {
  const url = window.location.href;
  render(<Providers city="bangkok"><CameraMotionChoice /></Providers>);
  const select = screen.getByRole('combobox', { name: 'Map motion' });
  expect(select).toHaveValue('system');
  expect(cameraMotion('step')).toMatchObject({ duration: 0, essential: false });
  fireEvent.change(select, { target: { value: 'smooth' } });
  expect(localStorage.getItem(key)).toBe('smooth');
  expect(prefersReducedMotion()).toBe(true);
  expect(bangkokCameraReduced()).toBe(false);
  expect(cameraMotion('step').essential).toBe(true);
  expect(window.location.href).toBe(url);
  act(() => {
    localStorage.removeItem(key);
    window.dispatchEvent(new StorageEvent('storage', { key }));
  });
  expect(select).toHaveValue('system');
  expect(bangkokCameraReduced()).toBe(true);
});

it('keeps an explicit choice in memory if browser storage is unavailable', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Storage blocked'); });
  setBangkokMotion('smooth');
  expect(bangkokMotion()).toBe('smooth');
  expect(cameraMotion('view').duration).toBeGreaterThan(0);
  setBangkokMotion('system');
  expect(bangkokCameraReduced()).toBe(true);
});
