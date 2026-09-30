import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import slugRedirects from "./src/data/slug-redirects.json";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async redirects() {
    // 301 redirects for renamed station slugs (wapuro→Hepburn romanization fix)
    const slugs = Object.entries(slugRedirects).map(([oldSlug, newSlug]) => ({
      source: `/station/${oldSlug}`,
      destination: `/station/${newSlug}`,
      permanent: true,
    }));
    // City aliases. Temporary (307) on purpose: Tokyo lives at the root today,
    // and a cached 301 would get in the way if it ever moves under /tokyo.
    const cities = [
      { source: '/tokyo', destination: '/', permanent: false },
      { source: '/:locale(ja|ru)/tokyo', destination: '/:locale', permanent: false },
      { source: '/bangkok/district', destination: '/bangkok', permanent: false },
      { source: '/:locale(ja|ru)/bangkok/district', destination: '/:locale/bangkok', permanent: false },
      { source: '/bangkok/station', destination: '/bangkok?lv=station', permanent: false },
      { source: '/:locale(ja|ru)/bangkok/station', destination: '/:locale/bangkok?lv=station', permanent: false },
    ];
    return [...slugs, ...cities];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' https://*.pogorelov.dev",
              "style-src 'self' 'unsafe-inline'",
              // i.ytimg.com: YouTube thumbnail hosts (livecam facade previews)
              // thumb.wikimedia.org: Commons' thumbnail host (Bangkok district photos).
              "img-src 'self' data: https://basemaps.cartocdn.com https://tile.openstreetmap.org https://upload.wikimedia.org https://thumb.wikimedia.org https://commons.wikimedia.org https://img.pogorelov.dev https://i.ytimg.com",
              "connect-src 'self' https://*.pogorelov.dev",
              "font-src 'self'",
              // frame-src: YouTube live camera embeds (CRTKY-116).
              // Without this, CSP falls back to default-src 'self' and all
              // cross-origin iframes (including YouTube) are blocked.
              "frame-src https://www.youtube.com https://www.youtube-nocookie.com",
              "frame-ancestors 'none'",
            ].join("; "),
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
      {
        // Bangkok's packed 200 m grid: the file name carries a content hash
        // (scripts/bangkok/build.py), so it can be cached for good.
        source: "/data/bangkok/:file*",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
