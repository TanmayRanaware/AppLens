FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system deps
RUN apt-get update -y && apt-get install -y build-essential curl postgresql-client && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.3
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Only copy lockfiles first to maximize caching
COPY pyproject.toml poetry.lock* ./

# Install deps (no dev)
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --without dev

# Now copy the application code
COPY . /app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Adjust to your app's entrypoint; example for FastAPI with uvicorn:
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
