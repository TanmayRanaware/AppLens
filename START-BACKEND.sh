#!/bin/bash
cd "$(dirname "$0")/backend"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo ""
    echo "Creating .env template. Please edit it with your actual values:"
    echo ""
    cat > .env << 'ENVEOF'
# Database (PostgreSQL in Docker)
POSTGRES_URL=postgresql+asyncpg://applens:applens@localhost:5432/applens

# GitHub OAuth (REQUIRED - Replace with your actual values)
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here

# JWT (REQUIRED - Change the secret!)
JWT_SECRET=change-me-to-a-random-secret-in-production

# OpenAI (REQUIRED - Replace with your actual API key)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Environment (Optional)
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
ENVEOF
    echo "✅ Created .env file. Please edit backend/.env with your values and run this script again."
    exit 1
fi

echo "🚀 Starting backend..."
python3 -m poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
