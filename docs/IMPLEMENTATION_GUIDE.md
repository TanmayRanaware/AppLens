**IMPLEMENTATION GUIDE**

This document summarizes sequential steps to run the application locally and describes deployment considerations. It is a concise, step-by-step companion to the other docs in `docs/` (especially `README-LOCAL.md`, `ENV-SETUP.md`, `RUN-MANUALLY.md`, and `DEPLOYMENT.md`). If you need detailed environment values or troubleshooting, open those files.

**Prerequisites:**
- **Code:** Clone the repo and checkout the intended branch.
- **Tools:** Git, Docker (optional but recommended for containerized runs), Node.js (for frontend), and a Python toolchain (Poetry or pip + venv). See `docs/ENV-SETUP.md` for exact versions and `.env` examples.

**Quick local sequence (development):**

1. **Prepare environment:**
   - Copy or create the `.env` file for the backend. See `docs/ENV-SETUP.md` for required variables (e.g. `DATABASE_URL`, OAuth keys, secrets).
   - Ensure a local Postgres (or configured DB) is running and reachable by `DATABASE_URL`.

2. **Backend dependencies & migrations:**
   - From the project root, change to the backend folder:
     - `cd backend`
   - Install dependencies:
     - If using Poetry: `poetry install`.
     - Or using a venv: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` (or follow `pyproject.toml` tooling instructions).
   - Apply DB migrations:
     - `alembic upgrade head` (alembic config is at `backend/alembic.ini`).

3. **Start backend (development mode):**
   - Run using Uvicorn from the `backend` folder:
     - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
   - Confirm the API is reachable (default `http://localhost:8000/`) and consult `docs/VIEW-LOGS.md` for logging guidance.

4. **Frontend (Next.js) setup and run:**
   - From project root:
     - `cd frontend`
     - `npm install` (or `pnpm install`/`yarn` depending on project tooling)
     - `npm run dev`
   - Open the Next.js app (default `http://localhost:3000`). The frontend talks to the backend endpoints; ensure any proxy or env vars for API base URL are set (see `frontend/lib/api.ts` and `docs/README-LOCAL.md`).

5. **Run end-to-end locally:**
   - With backend and frontend running, exercise main flows (login via GitHub OAuth if enabled, repo selection, scanning, graph/chat features).
   - If OAuth is in use, ensure callback URLs in the OAuth provider match local URLs. See `docs/WHY-GITHUB-OAUTH.md`.

**Alternative: Run with Docker / Docker Compose (recommended for parity with production):**
- Build and run (development or quick local containerized test):
  - `docker-compose up --build`
- For production-style containers (detached):
  - `docker-compose -f docker-compose.prod.yml up -d --build`
- To update containers during rolling deploys:
  - `docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d --build`

**Deployment notes (high level):**

- **Config & secrets:** Keep environment variables and secrets (DB URL, OAuth client secrets, API keys) outside the image — provide them at runtime via the host, secret manager, or orchestration tool. See `docs/ENV-SETUP.md` for required keys.
- **Reverse proxy / TLS:** The repo includes a `Caddyfile` for handling TLS and reverse proxying in production. Use it (or another proxy) to terminate TLS and forward to backend/frontend services.
- **CI/CD:** There is a `Jenkinsfile` in the repo as a starting point for pipeline automation. Use CI to build images, run tests, migrate DB (carefully, with backups), and deploy.
- **Database migrations:** Always run `alembic upgrade head` as part of deployment (can be run from a one-off migration job). Backup DB or snapshot before applying migrations in production.
- **Scaling:** The backend is a stateless web app; scale by running multiple backend containers behind the reverse proxy. Keep long-lived state or stateful services in managed services (DB, caches, object storage).

**Health checks & logs:**
- Expose a basic health endpoint (the backend has route modules under `app/routes/`) — configure your orchestrator to call it.
- Centralize logs (stdout/stderr from containers) and use `docs/VIEW-LOGS.md` for local guidance. For production, send logs to a log aggregator.

**Troubleshooting common issues:**
- Database connection: consult `docs/fix-database-connection.md` and verify `DATABASE_URL` and network access.
- Missing env vars: See `docs/ENV-SETUP.md` and `docs/README-LOCAL.md` to validate variables.
- OAuth login failure: Confirm OAuth client ID, secret, and redirect/callback URLs in the provider and in your `.env`.

**Where to find more detail:**
- Local run and manual commands: `docs/README-LOCAL.md`, `docs/RUN-MANUALLY.md`, and `docs/QUICKSTART.md`.
- Deployment-specific considerations: `docs/DEPLOYMENT.md`.
- Environment variables and examples: `docs/ENV-SETUP.md`.