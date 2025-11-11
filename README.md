# AppLens

**AppLens** is a microservice dependency visualization and analysis tool that scans your GitHub repositories to build an interactive 3D graph of service interactions, including HTTP calls and Kafka message flows.

## Features

- 🔍 **Multi-Repo Scanning**: Scan multiple GitHub repositories simultaneously
- 📊 **3D Graph Visualization**: Interactive force-directed graph showing service dependencies
- 🤖 **AI-Powered Analysis**: Error analyzer and what-if simulator powered by CrewAI
- 🔗 **Static Code Analysis**: Detects HTTP calls, Kafka producers/consumers across Python, JavaScript, and Java
- 💬 **Natural Language Queries**: Ask questions about your service graph in plain English
- 🔐 **GitHub OAuth**: Secure authentication with GitHub

## Architecture

- **Backend**: Python 3.11 + FastAPI, CrewAI, SQLAlchemy, PostgreSQL with pgvector
- **Frontend**: Next.js 14, React, TypeScript, react-force-graph-3d, Tailwind CSS
- **Database**: PostgreSQL with pgvector extension for embeddings
- **Containerization**: Docker + docker-compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- GitHub OAuth App (for authentication)
- OpenAI API key (for embeddings and LLM features)

### Setup

1. **Clone and navigate to the project**:
   ```bash
   cd RCA
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables** in `.env`:
   - `GITHUB_CLIENT_ID`: Your GitHub OAuth app client ID
   - `GITHUB_CLIENT_SECRET`: Your GitHub OAuth app client secret
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `JWT_SECRET`: A random secret for JWT tokens

4. **Start services**:
   ```bash
   docker-compose up -d
   ```

5. **Run database migrations**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

6. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### GitHub OAuth Setup

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create a new OAuth App:
   - Application name: AppLens
   - Homepage URL: http://localhost:3000
   - Authorization callback URL: http://localhost:8000/auth/github/callback
3. Copy the Client ID and Client Secret to your `.env` file

## Usage

1. **Sign in with GitHub** on the landing page
2. **Select repositories** to scan (search or enter manually)
3. **Click Scan** to start the analysis
4. **View the 3D graph** of service dependencies
5. **Use the AI Chat** for:
   - **Error Analyzer**: Paste error logs to identify affected services
   - **What-If Simulator**: Analyze potential impact of code changes

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

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
# Create a new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend alembic upgrade head
```

## API Endpoints

- `GET /health` - Health check
- `GET /auth/github/login` - Initiate GitHub OAuth
- `GET /auth/github/callback` - OAuth callback
- `GET /repos/search?q=...` - Search repositories
- `POST /scan/start` - Start a scan
- `GET /scan/status/{scan_id}` - Get scan status
- `GET /graph?repos=...` - Get graph data
- `POST /chat/error-analyzer` - Analyze error logs
- `POST /chat/what-if` - Simulate code changes
- `POST /nlq` - Natural language query

## Testing

```bash
# Backend tests
docker-compose exec backend pytest

# Frontend E2E tests
cd frontend
npm run test:e2e
```

## License

MIT

