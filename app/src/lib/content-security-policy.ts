/** The document policy must cover both cities across client-side navigation. */
export function contentSecurityPolicy({ development = false }: { development?: boolean } = {}) {
  return [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline' https://*.pogorelov.dev${development ? " 'unsafe-eval'" : ''}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https://basemaps.cartocdn.com https://tile.openstreetmap.org https://upload.wikimedia.org https://thumb.wikimedia.org https://commons.wikimedia.org https://img.pogorelov.dev https://i.ytimg.com https://tiles.openfreemap.org",
    "connect-src 'self' https://*.pogorelov.dev https://tiles.openfreemap.org",
    "font-src 'self'",
    "frame-src https://www.youtube.com https://www.youtube-nocookie.com",
    "frame-ancestors 'none'",
    "worker-src 'self' blob:",
  ].join('; ');
}
