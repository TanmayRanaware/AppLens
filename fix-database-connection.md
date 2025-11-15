# Fix Database Connection Issue

## Problem
The backend is getting error: `"Database error: role \"applens\" does not exist"`

## Solution

The PostgreSQL container is running and the user exists, but the backend might have a stale connection. 

### Option 1: Restart the Backend (Recommended)

1. **Stop the current backend process:**
   ```bash
   # Find the process
   ps aux | grep uvicorn
   
   # Kill it (replace PID with actual process ID)
   kill <PID>
   ```

2. **Restart the backend:**
   ```bash
   cd /Users/tanmayranaware/Desktop/Projects/RCA/backend
   source venv/bin/activate
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Option 2: Recreate Database Container

If restarting doesn't work, recreate the database:

```bash
cd /Users/tanmayranaware/Desktop/Projects/RCA
docker-compose down postgres
docker-compose up -d postgres
sleep 5
```

### Option 3: Verify Database Connection

Test the connection directly:

```bash
# Test connection
docker exec applens-postgres psql -U applens -d applens -c "SELECT current_user;"

# Should output: applens
```

### Option 4: Check Environment Variables

Make sure the backend is reading the correct `.env` file:

```bash
cd /Users/tanmayranaware/Desktop/Projects/RCA
cat .env | grep POSTGRES_URL
# Should show: POSTGRES_URL=postgresql+asyncpg://applens:applens@localhost:5432/applens
```

## After Fixing

Try the scan again:
```bash
curl 'http://localhost:8000/scan/start' \
  -H 'Content-Type: application/json' \
  -b 'applens_token=YOUR_TOKEN' \
  --data-raw '{"repo_full_names":["TanmayRanaware/applens-user-service"]}'
```



