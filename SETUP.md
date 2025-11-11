# AppLens Setup Guide

## Quick Start

1. **Copy environment file**:
   ```bash
   cp env.example .env
   ```

2. **Configure `.env`** with your:
   - GitHub OAuth credentials
   - OpenAI API key
   - JWT secret

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Run migrations**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## GitHub OAuth Setup

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create a new OAuth App:
   - Application name: AppLens
   - Homepage URL: http://localhost:3000
   - Authorization callback URL: http://localhost:8000/auth/github/callback
3. Copy the Client ID and Client Secret to your `.env` file

## Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install poetry
poetry install
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
applens/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Configuration
│   │   ├── auth/                # GitHub OAuth
│   │   ├── routes/              # API routes
│   │   ├── services/            # Business logic
│   │   ├── agents/              # CrewAI agents
│   │   └── db/                  # Database models
│   ├── alembic/                 # Database migrations
│   └── Dockerfile
├── frontend/
│   ├── app/                     # Next.js pages
│   ├── components/              # React components
│   ├── lib/                     # Utilities
│   └── Dockerfile
└── docker-compose.yml
```

## Features Implemented

✅ Multi-repo scanning
✅ 3D graph visualization with react-force-graph-3d
✅ GitHub OAuth authentication
✅ Static code analysis (HTTP/Kafka detectors for Python, JS, Java)
✅ Error analyzer agent
✅ What-if simulator agent
✅ Natural language query agent
✅ PostgreSQL with pgvector support
✅ Docker containerization

## Next Steps

- Add pgvector extension setup in migrations
- Enhance service name extraction heuristics
- Add more detector patterns
- Implement caching for GitHub API calls
- Add unit tests
- Add E2E tests with Playwright

