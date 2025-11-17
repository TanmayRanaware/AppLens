#!/bin/bash
cd "$(dirname "$0")/frontend"

if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

echo "🚀 Starting frontend..."
npm run dev
