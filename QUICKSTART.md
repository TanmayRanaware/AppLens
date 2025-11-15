# Quick Start Guide - Local Development

## Prerequisites Check

✅ Python 3.9+ (you have 3.9.6)
✅ Node.js 20+ (you have v24.8.0)
✅ PostgreSQL running (Docker container is up)

## Step 1: Configure Environment

Make sure you have a `.env` file in the root directory:

```bash
cd /Users/tanmayranaware/Desktop/Projects/RCA
cp env.example .env
```

Edit `.env` and add:
- `GITHUB_CLIENT_ID` - Your GitHub OAuth app client ID
- `GITHUB_CLIENT_SECRET` - Your GitHub OAuth app client secret
- `OPENAI_API_KEY` - Your OpenAI API key
- `JWT_SECRET` - Any random string (e.g., `my-secret-key-123`)

**Important**: The `POSTGRES_URL` should be:
```
POSTGRES_URL=postgresql+asyncpg://applens:applens@localhost:5432/applens
```

## Step 2: Start Backend (Terminal 1)

```bash
cd /Users/tanmayranaware/Desktop/Projects/RCA/backend

# Activate virtual environment
source venv/bin/activate

# Run database migrations
poetry run alembic upgrade head

# Start the backend server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 3: Start Frontend (Terminal 2)

```bash
cd /Users/tanmayranaware/Desktop/Projects/RCA/frontend

# Start the development server
npm run dev
```

You should see:
```
- ready started server on 0.0.0.0:3000
```

## Step 4: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Troubleshooting

### Backend won't start
- Check PostgreSQL is running: `docker-compose ps postgres`
- Verify `.env` file exists and has correct `POSTGRES_URL`
- Make sure virtual environment is activated: `source venv/bin/activate`

### Frontend won't start
- Make sure you're in the `frontend` directory
- Run `npm install` if you see module errors
- Check if port 3000 is available

### Database connection errors
- Ensure PostgreSQL container is running: `docker-compose up -d postgres`
- Check the connection string in `.env` uses `localhost` not `postgres`

## Stopping Services

- Backend: Press `Ctrl+C` in Terminal 1
- Frontend: Press `Ctrl+C` in Terminal 2
- PostgreSQL: `docker-compose stop postgres` (optional)

