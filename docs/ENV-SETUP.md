# Environment Variables Configuration Guide

## Required Variables (Must Have)

These are **required** for the backend to start:

### 1. GitHub OAuth Credentials

**GITHUB_CLIENT_ID** - Your GitHub OAuth App Client ID
**GITHUB_CLIENT_SECRET** - Your GitHub OAuth App Client Secret

**How to get them:**
1. Go to GitHub → Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: AppLens (or any name)
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:8000/auth/github/callback`
4. Click "Register application"
5. Copy the **Client ID** and generate a **Client Secret**

### 2. OpenAI API Key

**OPENAI_API_KEY** - Your OpenAI API key for AI features

**How to get it:**
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (you won't see it again!)

### 3. Database Connection

**POSTGRES_URL** - PostgreSQL connection string

**For local development (PostgreSQL in Docker):**
```
POSTGRES_URL=postgresql+asyncpg://applens:applens@localhost:5432/applens
```

**For local PostgreSQL:**
```
POSTGRES_URL=postgresql+asyncpg://your_username:your_password@localhost:5432/applens
```

## Optional Variables (Have Defaults)

These have default values but you can customize them:

### JWT Configuration
- **JWT_SECRET** (default: `change-me-in-production`)
  - Generate a random string: `openssl rand -hex 32`
  - Or use any secure random string
  
- **JWT_ALGORITHM** (default: `HS256`)
- **JWT_EXPIRATION_HOURS** (default: `24`)

### GitHub OAuth
- **GITHUB_OAUTH_REDIRECT_URI** (default: `http://localhost:8000/auth/github/callback`)

### MCP GitHub Server (Optional)
- **MCP_GITHUB_HOST** (default: `localhost`)
- **MCP_GITHUB_PORT** (default: `8000`)
- Note: The app uses GitHub API directly, so these are optional

### Environment Settings
- **ENVIRONMENT** (default: `development`)
- **DEBUG** (default: `false`)
- **FRONTEND_URL** (default: `http://localhost:3000`)

## Complete .env File Example

```bash
# Database (REQUIRED - update if using different PostgreSQL)
POSTGRES_URL=postgresql+asyncpg://applens:applens@localhost:5432/applens

# GitHub OAuth (REQUIRED)
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8000/auth/github/callback

# JWT (REQUIRED - change the secret!)
JWT_SECRET=your-random-secret-key-here-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# OpenAI (REQUIRED)
OPENAI_API_KEY=sk-your-openai-api-key-here

# MCP GitHub Server (Optional)
MCP_GITHUB_HOST=localhost
MCP_GITHUB_PORT=8000

# Environment (Optional)
ENVIRONMENT=development
DEBUG=false
FRONTEND_URL=http://localhost:3000
```

## Quick Setup Steps

1. **Copy the example file:**
   ```bash
   cd /Users/tanmayranaware/Desktop/Projects/RCA
   cp env.example .env
   ```

2. **Edit .env and replace:**
   - `your_github_client_id_here` → Your actual GitHub Client ID
   - `your_github_client_secret_here` → Your actual GitHub Client Secret
   - `your_openai_api_key_here` → Your actual OpenAI API key
   - `change-me-to-a-random-secret-in-production` → A random secret string

3. **Update POSTGRES_URL if needed:**
   - If using Docker PostgreSQL: `postgresql+asyncpg://applens:applens@localhost:5432/applens`
   - If using local PostgreSQL: Update with your credentials

4. **Generate a secure JWT secret (optional but recommended):**
   ```bash
   openssl rand -hex 32
   ```
   Copy the output and use it as your `JWT_SECRET`

## Minimum Required for Backend to Start

At minimum, you need these 4 variables:
1. `GITHUB_CLIENT_ID`
2. `GITHUB_CLIENT_SECRET`
3. `OPENAI_API_KEY`
4. `POSTGRES_URL` (if different from default)

The rest have sensible defaults for local development.

