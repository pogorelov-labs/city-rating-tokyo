/** Tile requests may be cancelled during normal map navigation. */
export function classifyMapError(error: { message?: string; name?: unknown } | undefined, loaded: boolean): 'ignore' | 'load' | 'tile' {
  const message = error?.message ?? '';
  if (error?.name === 'AbortError' || /abort|cancelled|canceled/i.test(message)) return 'ignore';
  if (!loaded) return /tiles\.openfreemap\.org\/styles\/positron/i.test(message) ? 'load' : 'ignore';
  return 'tile';
}

/** Bound both context restoration and the subsequent style rebuild. */
export class ContextRecoveryTimer {
  private timer: ReturnType<typeof setTimeout> | undefined;
  constructor(private fail: () => void, private timeout = 20_000) {}
  start() { this.clear(); this.timer = setTimeout(() => { this.timer = undefined; this.fail(); }, this.timeout); }
  clear() { clearTimeout(this.timer); this.timer = undefined; }
}
