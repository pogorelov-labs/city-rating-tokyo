import data from '@/data/noise/quietness.json';
import type { QuietnessFact } from './schema/noise-types';

const facts = data as unknown as {
  tokyo: Record<string, QuietnessFact>;
  bangkok: Record<string, QuietnessFact>;
};

/** Detail-page facts only; never included in map payloads or ranking inputs. */
export function getQuietness(city: 'tokyo' | 'bangkok', id: string): QuietnessFact | undefined {
  return facts[city][id];
}
