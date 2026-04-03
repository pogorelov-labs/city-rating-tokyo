const STORAGE_KEY = 'visitor_id';

export function getVisitorId(): string {
  if (typeof window === 'undefined') return '';

  try {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  } catch {
    window.umami?.track('error', { category: 'storage', key: STORAGE_KEY });
    return crypto.randomUUID();
  }
}
