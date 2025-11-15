#!/bin/bash

echo "🚀 Starting AppLens services..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit .env and add your:"
    echo "   - GITHUB_CLIENT_ID"
    echo "   - GITHUB_CLIENT_SECRET"
    echo "   - OPENAI_API_KEY"
    echo "   - JWT_SECRET"
    echo ""
    read -p "Press Enter after you've configured .env, or Ctrl+C to exit..."
fi

# Start services
echo "🐳 Starting Docker containers..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Run migrations
echo "📊 Running database migrations..."
docker-compose exec -T backend alembic upgrade head || echo "⚠️  Migrations may need to run after backend is fully up"

# Check status
echo ""
echo "📋 Service status:"
docker-compose ps

echo ""
echo "✅ Services should be starting!"
echo ""
echo "🌐 Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📝 To view logs:"
echo "   ./view-logs.sh              # View all logs"
echo "   ./view-logs.sh backend      # View backend logs only"
echo "   docker-compose logs -f      # Alternative method"
echo "🛑 To stop: docker-compose down"

