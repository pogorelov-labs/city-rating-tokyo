import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import slugRedirects from "./src/data/slug-redirects.json";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async redirects() {
    // 301 redirects for renamed station slugs (wapuro→Hepburn romanization fix)
    return Object.entries(slugRedirects).map(([oldSlug, newSlug]) => ({
      source: `/station/${oldSlug}`,
      destination: `/station/${newSlug}`,
      permanent: true,
    }));
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
              "img-src 'self' data: https://*.basemaps.cartocdn.com https://upload.wikimedia.org https://commons.wikimedia.org https://img.pogorelov.dev https://i.ytimg.com",
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
    ];
  },
};

export default withNextIntl(nextConfig);
