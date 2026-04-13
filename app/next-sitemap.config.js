/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: process.env.SITE_URL || 'https://city-rating.pogorelov.dev',
  generateRobotsTxt: true,
  sitemapSize: 5000,
  changefreq: 'weekly',
  priority: 0.7,
  alternateRefs: [
    { href: 'https://city-rating.pogorelov.dev', hreflang: 'en' },
    { href: 'https://city-rating.pogorelov.dev/ja', hreflang: 'ja' },
    { href: 'https://city-rating.pogorelov.dev/ru', hreflang: 'ru' },
  ],
  transform: async (config, path) => {
    // Skip locale-prefixed paths from the EN sitemap — they get their own alternateRefs
    // next-intl generates /en/..., /ja/..., /ru/... paths; we want the canonical
    // EN path without prefix
    if (path.startsWith('/en/') || path.startsWith('/en')) {
      const stripped = path.replace(/^\/en/, '') || '/';
      return {
        loc: stripped,
        changefreq: stripped === '/' ? 'daily' : 'weekly',
        priority: stripped === '/' ? 1.0 : 0.8,
        lastmod: new Date().toISOString(),
        alternateRefs: config.alternateRefs ?? [],
      };
    }

    // JA/RU paths — include with their own alternates pointing to sibling locales
    if (path.startsWith('/ja') || path.startsWith('/ru')) {
      const basePath = path.replace(/^\/(ja|ru)/, '') || '/';
      return {
        loc: path,
        changefreq: basePath === '/' ? 'daily' : 'weekly',
        priority: basePath === '/' ? 1.0 : 0.8,
        lastmod: new Date().toISOString(),
        alternateRefs: (config.alternateRefs ?? []).map((ref) => ({
          ...ref,
          href: ref.hreflang === 'en'
            ? `${ref.href}${basePath === '/' ? '' : basePath}`
            : `${ref.href}${basePath === '/' ? '' : basePath}`,
        })),
      };
    }

    // Fallback for non-locale paths (API, etc.)
    if (path === '/') {
      return { loc: path, changefreq: 'daily', priority: 1.0, lastmod: new Date().toISOString() };
    }
    if (path.startsWith('/station/')) {
      return { loc: path, changefreq: 'weekly', priority: 0.8, lastmod: new Date().toISOString() };
    }
    return { loc: path, changefreq: config.changefreq, priority: config.priority, lastmod: new Date().toISOString() };
  },
};
