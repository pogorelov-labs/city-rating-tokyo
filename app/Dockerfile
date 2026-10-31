FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
# The lint adapter is a packed local dependency, resolved entirely inside app/.
COPY package.json package-lock.json .npmrc ./
COPY tooling/minimatch-compat ./tooling/minimatch-compat
RUN npm ci

# Rebuild source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Bound build memory so an oversized compile fails with a useful heap error.
ENV NODE_OPTIONS=--max-old-space-size=4096
# The normal Bangkok renderer is selected during static generation.
ARG BANGKOK_MAP_RENDERER=maplibre
ENV BANGKOK_MAP_RENDERER=$BANGKOK_MAP_RENDERER
RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
