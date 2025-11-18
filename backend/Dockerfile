# ---------- Builder: build wheels via Poetry ----------
  FROM python:3.12-slim AS builder

  ENV PYTHONDONTWRITEBYTECODE=1 \
      PYTHONUNBUFFERED=1 \
      POETRY_VERSION=1.8.3 \
      PIP_DISABLE_PIP_VERSION_CHECK=1 \
      PATH="/root/.local/bin:${PATH}"
  
  # Faster apt + clean
  RUN --mount=type=cache,target=/var/cache/apt \
      --mount=type=cache,target=/var/lib/apt \
      apt-get update -y \
   && apt-get install -y --no-install-recommends build-essential curl \
   && rm -rf /var/lib/apt/lists/*
  
  # Install Poetry
  RUN curl -sSL https://install.python-poetry.org | python3 - \
   && poetry --version
  
  WORKDIR /app
  
  # Copy lockfiles early for caching
  COPY pyproject.toml poetry.lock* ./
  
  # Export pinned requirements (no hashes to avoid resolver conflicts in slim)
  RUN poetry export -f requirements.txt --without dev --without-hashes -o requirements.txt
  
  # Prebuild wheels
  RUN --mount=type=cache,target=/root/.cache/pip \
      pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels
  
  # Bring in source last to avoid busting previous cache
  COPY . /app
  
  
  # ---------- Runtime: minimal image ----------
  FROM python:3.12-slim AS runtime
  
  # Metadata
  LABEL org.opencontainers.image.source="https://example.com/your/repo" \
        org.opencontainers.image.title="applens-backend" \
        org.opencontainers.image.description="AppLens backend service" \
        org.opencontainers.image.licenses="Apache-2.0"
  
  ENV PYTHONDONTWRITEBYTECODE=1 \
      PYTHONUNBUFFERED=1 \
      PIP_DISABLE_PIP_VERSION_CHECK=1 \
      LANG=C.UTF-8 LC_ALL=C.UTF-8 TZ=UTC
  
  # Optionally install psql client if truly needed
  # RUN --mount=type=cache,target=/var/cache/apt \
  #     --mount=type=cache,target=/var/lib/apt \
  #     apt-get update -y && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
  
  # Add non-root
  RUN addgroup --system app && adduser --system --ingroup app --uid 10001 appuser
  WORKDIR /app
  
  # Install deps strictly from prebuilt wheels
  COPY --from=builder /wheels /wheels
  COPY --from=builder /app/requirements.txt /app/requirements.txt
  RUN --mount=type=cache,target=/root/.cache/pip \
      pip install --no-cache-dir --upgrade --upgrade-strategy only-if-needed pip \
   && pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
   && rm -rf /wheels
  
  # Copy application code
  COPY --from=builder --chown=appuser:app /app /app
  
  EXPOSE 8000
  
  # Health check (adjust path)
  HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python - <<'PY' || exit 1
  import urllib.request, sys
  try:
      with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as r:
          sys.exit(0 if r.status==200 else 1)
  except Exception:
      sys.exit(1)
  PY
  
  USER appuser
  
  # If you prefer Gunicorn+Uvicorn workers in prod:
  # CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-b", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60"]
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  