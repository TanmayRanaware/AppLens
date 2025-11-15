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

5. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Development

### Backend Development

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## License

MIT

