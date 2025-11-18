# syntax=docker/dockerfile:1.7

############## Builder: build wheels via Poetry ##############
ARG TARGETPLATFORM
ARG TARGETARCH
FROM python:3.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/root/.local/bin:${PATH}"

# Faster apt + clean
# Note: Removed cache mounts to avoid lock conflicts when building for multiple platforms in parallel
RUN rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock-frontend \
 && apt-get update -y \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# Install Poetry + export plugin (required for `poetry export` in 1.8.x)
RUN curl -sSL https://install.python-poetry.org | python3 - \
 && poetry self add poetry-plugin-export \
 && poetry --version

WORKDIR /app

# Copy lockfiles early for better cache hits
COPY pyproject.toml poetry.lock* ./

# Export pinned requirements (no hashes => wheel build friendly)
RUN poetry export -f requirements.txt --without dev --without-hashes -o requirements.txt

# Prebuild wheels for all deps
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

# Bring in the rest of the source late to preserve the cache above
COPY . /app


############## Runtime: minimal image ##############
ARG TARGETPLATFORM
ARG TARGETARCH
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/TanmayRanaware/AppLens" \
      org.opencontainers.image.title="applens-backend" \
      org.opencontainers.image.description="AppLens backend service" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC

# Optional: psql client if you truly need it at runtime
# RUN --mount=type=cache,id=apt-lists-${TARGETARCH},target=/var/lib/apt/lists \
#     --mount=type=cache,id=apt-cache-${TARGETARCH},target=/var/cache/apt \
#     apt-get update -y \
#  && apt-get install -y --no-install-recommends postgresql-client \
#  && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN addgroup --system app && adduser --system --ingroup app --uid 10001 appuser

WORKDIR /app

# Install only from prebuilt wheels (no network)
COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# Copy application code
COPY --from=builder --chown=appuser:app /app /app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; u=urllib.request.urlopen('http://localhost:8000/health', timeout=5); sys.exit(0 if getattr(u,'status',200)==200 else 1)"]

# Drop privileges
USER appuser

# Start server (adjust module if needed)
# For production consider Gunicorn:
# CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-b", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
