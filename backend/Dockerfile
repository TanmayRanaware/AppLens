# ---------- Builder: make wheels from Poetry lock ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    PATH="/root/.local/bin:${PATH}"

# Only build tooling here (kept out of final image)
RUN apt-get update -y \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
 && poetry --version

WORKDIR /app

# Copy lockfiles first to maximize cache hits
COPY pyproject.toml poetry.lock* ./

# Export pinned requirements and prebuild wheels (fast/small installs later)
RUN poetry export -f requirements.txt --without dev -o requirements.txt
RUN pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

# Bring in source last (doesn't invalidate wheels cache)
COPY . /app


# ---------- Runtime: minimal image with just what you need ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# If you truly need psql inside the container (e.g., manual migrations),
# uncomment the next two lines. Otherwise keep it lean.
# RUN apt-get update -y && apt-get install -y --no-install-recommends postgresql-client \
#  && rm -rf /var/lib/apt/lists/*

# Add a non-root user
RUN addgroup --system app && adduser --system --ingroup app --uid 10001 appuser

WORKDIR /app

# Install deps from prebuilt wheels (small + quick)
COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir /wheels/* \
 && rm -rf /wheels

# Copy application code
COPY --from=builder --chown=appuser:app /app /app

EXPOSE 8000

# Health check (adjust path if different)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Drop privileges
USER appuser

# Start server (update module path if your app isn't app.main:app)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
