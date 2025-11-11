#!/bin/bash

echo "🚀 Starting AppLens locally..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit .env and add your credentials before continuing"
    echo ""
    read -p "Press Enter after configuring .env, or Ctrl+C to exit..."
fi

# Start PostgreSQL (if using Docker for DB only)
echo "🐘 Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Backend setup
echo ""
echo "🐍 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install poetry
poetry install

echo "Running database migrations..."
poetry run alembic upgrade head

echo ""
echo "✅ Backend ready! Starting in background..."
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

cd ..

# Frontend setup
echo ""
echo "⚛️  Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

echo ""
echo "✅ Frontend ready! Starting..."
echo ""
echo "🌐 Services starting:"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null; docker-compose stop postgres" EXIT

