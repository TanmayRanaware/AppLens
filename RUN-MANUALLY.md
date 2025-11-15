# How to Run Frontend and Backend Manually

## Prerequisites

1. **Python 3.11+** installed
2. **Node.js 20+** and npm installed
3. **PostgreSQL** with pgvector extension running
4. **Environment variables** configured in `.env` file

## Step 1: Setup Environment Variables

Create a `.env` file in the root directory:

```bash
# Database
POSTGRES_URL=postgresql+asyncpg://applens:applens@localhost:5432/applens

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8000/auth/github/callback

# JWT
JWT_SECRET=change-me-to-a-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# MCP GitHub Server (optional)
MCP_GITHUB_HOST=localhost
MCP_GITHUB_PORT=8000

# Environment
ENVIRONMENT=development
DEBUG=false

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

## Step 2: Setup Database

Make sure PostgreSQL is running with pgvector extension:

```bash
# Start PostgreSQL (if using Docker)
docker run -d \
  --name applens-postgres \
  -e POSTGRES_USER=applens \
  -e POSTGRES_PASSWORD=applens \
  -e POSTGRES_DB=applens \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Or use your local PostgreSQL installation
# Then enable pgvector extension:
psql -U applens -d applens -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## Step 3: Setup Backend

### 3.1 Navigate to backend directory:
```bash
cd backend
```

### 3.2 Create virtual environment (if not exists):
```bash
python3 -m venv venv
```

### 3.3 Activate virtual environment:

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 3.4 Install dependencies:

**Using Poetry (recommended):**
```bash
poetry install
```

**Or using pip:**
```bash
pip install -r requirements.txt
# (If requirements.txt exists, or install from pyproject.toml)
pip install fastapi uvicorn sqlalchemy alembic asyncpg httpx python-jose[cryptography] python-multipart pydantic pydantic-settings crewai langchain langchain-openai openai pgvector psycopg2-binary python-dotenv
```

### 3.5 Run database migrations:
```bash
alembic upgrade head
```

### 3.6 Start the backend server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at: **http://localhost:8000**

You should see logs in your terminal like:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal window open** - the backend will show logs here.

## Step 4: Setup Frontend

### 4.1 Open a NEW terminal window (keep backend running)

### 4.2 Navigate to frontend directory:
```bash
cd frontend
```

### 4.3 Install dependencies (first time only):
```bash
npm install
```

### 4.4 Start the frontend development server:
```bash
npm run dev
```

The frontend will be available at: **http://localhost:3000**

You should see logs in your terminal like:
```
▲ Next.js 14.0.4
- Local:        http://localhost:3000
- Ready in 2.3s
```

**Keep this terminal window open** - the frontend will show logs here.

## Step 5: View Logs

### Backend Logs:
- Logs appear in the terminal where you ran `uvicorn`
- You'll see:
  - API requests
  - Database queries
  - Error messages
  - AI agent activity

### Frontend Logs:
- Logs appear in the terminal where you ran `npm run dev`
- You'll see:
  - Next.js compilation
  - Build errors
  - Runtime errors

### Both Logs:
- Each service logs to its own terminal
- Backend: Python/FastAPI logs
- Frontend: Next.js/React logs

## Stopping the Services

### Stop Backend:
- Go to the backend terminal
- Press `Ctrl+C`

### Stop Frontend:
- Go to the frontend terminal
- Press `Ctrl+C`

## Troubleshooting

### Backend won't start:
- Check if PostgreSQL is running: `psql -U applens -d applens`
- Check if port 8000 is available: `lsof -i :8000`
- Verify `.env` file exists and has correct values
- Check virtual environment is activated

### Frontend won't start:
- Check if port 3000 is available: `lsof -i :3000`
- Try deleting `node_modules` and running `npm install` again
- Check if backend is running (frontend needs backend API)

### Database connection errors:
- Verify PostgreSQL is running
- Check `POSTGRES_URL` in `.env` matches your database
- Ensure pgvector extension is installed

### Port already in use:
- Change port in backend: `uvicorn app.main:app --port 8001`
- Change port in frontend: `npm run dev -- -p 3001`
- Update `NEXT_PUBLIC_API_URL` in frontend if backend port changed

## Quick Reference

**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

