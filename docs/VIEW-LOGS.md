# Viewing Logs in Terminal

## Quick Commands

### View All Logs (All Services)
```bash
docker-compose logs -f
```

### View Specific Service Logs

**Backend logs:**
```bash
docker-compose logs -f backend
```

**Frontend logs:**
```bash
docker-compose logs -f frontend
```

**Database logs:**
```bash
docker-compose logs -f postgres
```

### View Last N Lines
```bash
# Last 100 lines of backend
docker-compose logs --tail=100 backend

# Last 50 lines of all services
docker-compose logs --tail=50
```

### View Logs Without Following
```bash
docker-compose logs backend
```

## Real-Time Log Viewing

### Option 1: Follow All Logs (Recommended)
```bash
docker-compose logs -f
```
Press `Ctrl+C` to stop following.

### Option 2: Follow Specific Service
```bash
docker-compose logs -f backend
```

### Option 3: Follow Multiple Services
```bash
docker-compose logs -f backend frontend
```

## View Logs While Starting Services

Start services and view logs simultaneously:
```bash
docker-compose up
```

This shows logs in real-time. Press `Ctrl+C` to stop services.

Or run in detached mode and follow logs:
```bash
docker-compose up -d
docker-compose logs -f
```

## Filter Logs

### By Time
```bash
# Logs since 10 minutes ago
docker-compose logs --since 10m backend

# Logs since specific time
docker-compose logs --since 2024-01-15T10:00:00 backend
```

### By Service Name in Logs
```bash
# Using grep to filter
docker-compose logs backend | grep "ERROR"
docker-compose logs backend | grep "INFO"
```

## View Logs from Running Container

If you know the container name:
```bash
# Backend
docker logs -f applens-backend

# Frontend
docker logs -f applens-frontend

# Database
docker logs -f applens-postgres
```

## Color-Coded Logs

For better readability, use `docker-compose logs` with color:
```bash
docker-compose logs -f --no-log-prefix
```

Or use a tool like `multitail`:
```bash
# Install multitail (macOS)
brew install multitail

# View multiple logs
multitail -l "docker-compose logs -f backend" -l "docker-compose logs -f frontend"
```

## Save Logs to File

```bash
# Save all logs
docker-compose logs > logs.txt

# Save specific service
docker-compose logs backend > backend-logs.txt

# Append to file
docker-compose logs -f backend >> backend-logs.txt
```

## Useful Log Commands

```bash
# View last 100 lines and follow
docker-compose logs --tail=100 -f backend

# View logs with timestamps
docker-compose logs -f -t backend

# View logs since container started
docker-compose logs --since 0 backend
```

