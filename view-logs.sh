#!/bin/bash

# Script to view logs easily
# Usage: ./view-logs.sh [service] [options]
# Examples:
#   ./view-logs.sh              # View all logs
#   ./view-logs.sh backend      # View backend logs
#   ./view-logs.sh backend -f   # Follow backend logs
#   ./view-logs.sh all -f       # Follow all logs

SERVICE=${1:-all}
OPTIONS=${2:-"-f"}

if [ "$SERVICE" == "all" ]; then
    echo "📋 Viewing logs for all services (Press Ctrl+C to stop)..."
    docker-compose logs $OPTIONS
elif [ "$SERVICE" == "backend" ]; then
    echo "📋 Viewing backend logs (Press Ctrl+C to stop)..."
    docker-compose logs $OPTIONS backend
elif [ "$SERVICE" == "frontend" ]; then
    echo "📋 Viewing frontend logs (Press Ctrl+C to stop)..."
    docker-compose logs $OPTIONS frontend
elif [ "$SERVICE" == "db" ] || [ "$SERVICE" == "postgres" ]; then
    echo "📋 Viewing database logs (Press Ctrl+C to stop)..."
    docker-compose logs $OPTIONS postgres
else
    echo "Usage: ./view-logs.sh [service] [options]"
    echo ""
    echo "Services:"
    echo "  all       - View all services (default)"
    echo "  backend   - View backend logs"
    echo "  frontend  - View frontend logs"
    echo "  db        - View database logs"
    echo ""
    echo "Options:"
    echo "  -f        - Follow logs (default)"
    echo "  --tail=N  - Show last N lines"
    echo ""
    echo "Examples:"
    echo "  ./view-logs.sh              # Follow all logs"
    echo "  ./view-logs.sh backend      # Follow backend logs"
    echo "  ./view-logs.sh backend --tail=100  # Last 100 lines of backend"
fi

