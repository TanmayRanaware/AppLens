# Running AppLens Locally

## Quick Start

### Option 1: Automated Script
```bash
./start-local.sh
```

### Option 2: Manual Setup

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL (or use Docker for DB only)
- Poetry (for Python dependency management)

## Step-by-Step Setup

### 1. Configure Environment

```bash
cp env.example .env
# Edit .env with your credentials:
# - GITHUB_CLIENT_ID
# - GITHUB_CLIENT_SECRET  
# - OPENAI_API_KEY
# - JWT_SECRET
```

### 2. Start PostgreSQL (Docker)

```bash
docker-compose up -d postgres
```

Or use your local PostgreSQL and update `POSTGRES_URL` in `.env`:
```
POSTGRES_URL=postgresql+asyncpg://user:password@localhost:5432/applens
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install poetry
poetry install

# Run migrations
poetry run alembic upgrade head

# Start backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000

### 4. Frontend Setup (New Terminal)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Troubleshooting

### Backend Issues

- **Port already in use**: Change port in uvicorn command: `--port 8001`
- **Database connection error**: Check PostgreSQL is running and `.env` has correct `POSTGRES_URL`
- **Import errors**: Make sure you're in the virtual environment and dependencies are installed

### Frontend Issues

- **Port 3000 in use**: Next.js will automatically use 3001
- **Module not found**: Run `npm install` again
- **API connection errors**: Check `NEXT_PUBLIC_API_URL` in frontend or ensure backend is running

## Stopping Services

- Backend: Press `Ctrl+C` in the backend terminal
- Frontend: Press `Ctrl+C` in the frontend terminal  
- PostgreSQL: `docker-compose stop postgres` (if using Docker)

