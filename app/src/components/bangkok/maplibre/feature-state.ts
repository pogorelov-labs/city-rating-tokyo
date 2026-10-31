/** Diff paint/interaction state without serializing geometry back to workers. */
export class FeatureStateCache {
  private values = new Map<string, Record<string, unknown>>();
  clear() { this.values.clear(); }
  set(source: string, id: string, patch: Record<string, unknown>, submit: (patch: Record<string, unknown>) => void): boolean {
    const key = `${source}:${id}`, old = this.values.get(key) ?? {};
    const changed = Object.fromEntries(Object.entries(patch).filter(([k, v]) => old[k] !== v));
    if (!Object.keys(changed).length) return false;
    submit(changed);
    this.values.set(key, { ...old, ...changed });
    return true;
  }
}
