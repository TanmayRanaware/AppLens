# ---------- Base ----------
    FROM node:20-alpine AS base

    ENV NODE_ENV=production \
        NEXT_TELEMETRY_DISABLED=1
    
    # ---------- Dependencies ----------
    FROM base AS deps
    RUN apk add --no-cache libc6-compat
    WORKDIR /app
    COPY package.json package-lock.json* ./
    RUN npm ci
    
    # ---------- Builder ----------
    FROM base AS builder
    RUN apk add --no-cache libc6-compat
    WORKDIR /app
    COPY --from=deps /app/node_modules ./node_modules
    COPY . .
    # If you use sharp or other native deps, this helps during build
    ENV NODE_OPTIONS="--max_old_space_size=2048"
    RUN npm run build
    
    # ---------- Runner ----------
    FROM base AS runner
    RUN apk add --no-cache libc6-compat
    WORKDIR /app
    
    # Create non-root
    RUN addgroup --system --gid 1001 nodejs \
     && adduser --system --uid 1001 nextjs
    USER nextjs
    
    # Copy standalone output
    COPY --from=builder --chown=nextjs:nodejs /app/public ./public
    COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
    COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
    
    ENV PORT=3000 \
        HOSTNAME=0.0.0.0 \
        NODE_ENV=production \
        NEXT_TELEMETRY_DISABLED=1 \
        NODE_OPTIONS="--enable-source-maps"
    
    EXPOSE 3000
    
    # Health check hits a cheap page; change to /health if you have one
    HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
        CMD node -e "require('http').get('http://localhost:3000', r => process.exit(r.statusCode===200?0:1)).on('error', ()=>process.exit(1))" || exit 1
    
    # Next standalone provides server.js in root
    CMD ["node", "server.js"]
    