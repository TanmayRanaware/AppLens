# ---------- Base ----------
    FROM node:20-alpine AS base
    ENV NODE_ENV=production \
        NEXT_TELEMETRY_DISABLED=1
    
    # ---------- Dependencies ----------
    FROM base AS deps
    RUN apk add --no-cache libc6-compat
    WORKDIR /app
    COPY package.json package-lock.json* ./
    RUN npm ci --no-audit --no-fund
    
    # ---------- Builder ----------
    FROM base AS builder
    RUN apk add --no-cache libc6-compat
    WORKDIR /app
    
    # Build-time knobs from CI
    ARG NEXT_IGNORE_LINT=1
    ARG NEXT_IGNORE_TSC=1
    ARG NODE_OPTIONS="--max-old-space-size=4096"
    
    # Apply envs
    ENV NEXT_IGNORE_LINT=$NEXT_IGNORE_LINT
    ENV NEXT_IGNORE_TSC=$NEXT_IGNORE_TSC
    ENV NODE_OPTIONS=$NODE_OPTIONS
    ENV NEXT_TELEMETRY_DISABLED=1
    
    # Strictly cap all thread pools to avoid OOM during "Collecting page data"
    ENV NEXT_CPU_COUNT=1 \
        SWC_NODE_THREADS=1 \
        RAYON_NUM_THREADS=1
    
    COPY --from=deps /app/node_modules ./node_modules
    COPY . .
    
    # Log effective build env
    RUN node -e "console.log('BUILD_ENV', {NEXT_IGNORE_LINT:process.env.NEXT_IGNORE_LINT,NEXT_IGNORE_TSC:process.env.NEXT_IGNORE_TSC,NODE_OPTIONS:process.env.NODE_OPTIONS,NEXT_CPU_COUNT:process.env.NEXT_CPU_COUNT,SWC_NODE_THREADS:process.env.SWC_NODE_THREADS,RAYON_NUM_THREADS:process.env.RAYON_NUM_THREADS})"
    
    # IMPORTANT: invoke next via node to ensure heap flag sticks
    RUN node --max-old-space-size=4096 node_modules/next/dist/bin/next build
    
    # ---------- Runner ----------
    FROM base AS runner
    RUN apk add --no-cache libc6-compat
    WORKDIR /app
    
    # Non-root runtime
    RUN addgroup --system --gid 1001 nodejs \
     && adduser  --system --uid 1001 nextjs
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
    
    HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
      CMD node -e "require('http').get('http://localhost:3000', r => process.exit(r.statusCode===200?0:1)).on('error', ()=>process.exit(1))" || exit 1
    
    CMD ["node", "server.js"]
    