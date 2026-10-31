import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import slugRedirects from "./src/data/slug-redirects.json";
import path from "node:path";
import { contentSecurityPolicy } from "./src/lib/content-security-policy";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.resolve(__dirname),
  turbopack: { root: path.resolve(__dirname) },
  // Keep next-intl's rewrite origin aligned with the standalone bind origin.
  // Normalizing loopback to localhost can otherwise turn an EN rewrite external.
  skipProxyUrlNormalize: true,
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
    const rules = [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: contentSecurityPolicy({ development: process.env.NODE_ENV === 'development' }),
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
    // The common policy also applies to the worker response. A city-specific
    // document policy would block Tokyo → Bangkok client-side navigation.
    rules.push({ source: '/map-assets/:file*', headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }] });
    return rules;
  },
};

export default withNextIntl(nextConfig);
