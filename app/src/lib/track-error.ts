export function trackError(category: string, details?: Record<string, string>) {
  window.umami?.track('error', { category, ...details });
}
