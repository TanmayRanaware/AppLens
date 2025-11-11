#!/bin/bash

# Script to set up the PostgreSQL database for AppLens

echo "🐘 Setting up PostgreSQL database for AppLens..."

# Check if using Docker
if command -v docker &> /dev/null; then
    echo "📦 Using Docker for PostgreSQL..."
    
    # Start PostgreSQL container
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Check if container is running
    if docker ps | grep -q applens-postgres; then
        echo "✅ PostgreSQL container is running"
        echo ""
        echo "Database connection:"
        echo "  Host: localhost"
        echo "  Port: 5432"
        echo "  User: applens"
        echo "  Password: applens"
        echo "  Database: applens"
        echo ""
        echo "✅ Database is ready!"
    else
        echo "❌ Failed to start PostgreSQL container"
        exit 1
    fi
else
    echo "📝 Setting up local PostgreSQL..."
    echo ""
    echo "Please run these commands manually:"
    echo ""
    echo "1. Connect to PostgreSQL as superuser:"
    echo "   psql -U postgres"
    echo ""
    echo "2. Create user and database:"
    echo "   CREATE USER applens WITH PASSWORD 'applens';"
    echo "   CREATE DATABASE applens OWNER applens;"
    echo "   GRANT ALL PRIVILEGES ON DATABASE applens TO applens;"
    echo "   \\q"
    echo ""
    echo "3. Or use this one-liner (if you have sudo access):"
    echo "   sudo -u postgres psql -c \"CREATE USER applens WITH PASSWORD 'applens';\""
    echo "   sudo -u postgres psql -c \"CREATE DATABASE applens OWNER applens;\""
fi


