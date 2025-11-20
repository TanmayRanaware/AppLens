# Cloud Deployment Guide for AppLens

This guide covers deploying AppLens to various cloud platforms.

## Architecture Overview

- **Backend**: FastAPI (Python 3.11) on port 8000
- **Frontend**: Next.js on port 3000
- **Database**: PostgreSQL with pgvector extension
- **Containerized**: Docker + docker-compose ready

## Recommended Platforms

### 🚀 **Option 1: Railway (Recommended for Quick Start)**

**Best for**: Quick deployment, automatic HTTPS, PostgreSQL included

**Pros**:
- ✅ Easiest setup (connects to GitHub)
- ✅ Automatic HTTPS/SSL
- ✅ Managed PostgreSQL with pgvector
- ✅ Free tier available
- ✅ Environment variables management
- ✅ Auto-deploy from Git

**Steps**:

1. **Sign up**: https://railway.app

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your repository

3. **Deploy Database**:
   - Click "New" → "Database" → "PostgreSQL"
   - Railway automatically provides connection string
   - Note: You may need to enable pgvector extension manually

4. **Deploy Backend**:
   - Click "New" → "GitHub Repo" → Select your repo
   - Root directory: `/backend`
   - Build command: `poetry install --without dev --no-root`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables:
     ```
     POSTGRES_URL=<from database service>
     GITHUB_CLIENT_ID=<your_github_client_id>
     GITHUB_CLIENT_SECRET=<your_github_client_secret>
     JWT_SECRET=<random_secret>
     OPENAI_API_KEY=<your_openai_key>
     ENVIRONMENT=production
     ```
   - Set public port: 8000

5. **Deploy Frontend**:
   - Click "New" → "GitHub Repo" → Select your repo
   - Root directory: `/frontend`
   - Build command: `npm install && npm run build`
   - Start command: `npx next start`
   - Add environment variables:
     ```
     NEXT_PUBLIC_API_URL=<backend_railway_url>
     GITHUB_CLIENT_ID=<your_github_client_id>
     ```
   - Set public port: 3000

6. **Update GitHub OAuth**:
   - Go to GitHub Settings → Developer settings → OAuth Apps
   - Update callback URL to: `https://<your-backend-url>/auth/github/callback`
   - Update Homepage URL to: `https://<your-frontend-url>`

**Cost**: ~$5-20/month (free tier available)

---

### 🎯 **Option 2: Render**

**Best for**: Simple deployment, good free tier

**Pros**:
- ✅ Free tier available
- ✅ Automatic SSL
- ✅ Managed PostgreSQL
- ✅ Easy GitHub integration

**Steps**:

1. **Sign up**: https://render.com

2. **Create PostgreSQL Database**:
   - New → PostgreSQL
   - Name: `applens-db`
   - Plan: Free (or paid for production)
   - Note: You'll need to enable pgvector manually via SQL:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```

3. **Deploy Backend**:
   - New → Web Service
   - Connect GitHub repo
   - Settings:
     - **Name**: `applens-backend`
     - **Root Directory**: `backend`
     - **Environment**: `Docker`
     - **Dockerfile Path**: `backend/Dockerfile`
     - **Build Command**: (auto-detected)
     - **Start Command**: (auto-detected)
   - Environment Variables:
     ```
     POSTGRES_URL=<from_database_internal_url>
     GITHUB_CLIENT_ID=<your_github_client_id>
     GITHUB_CLIENT_SECRET=<your_github_client_secret>
     JWT_SECRET=<random_secret>
     OPENAI_API_KEY=<your_openai_key>
     ENVIRONMENT=production
     ```

4. **Deploy Frontend**:
   - New → Web Service
   - Connect GitHub repo
   - Settings:
     - **Name**: `applens-frontend`
     - **Root Directory**: `frontend`
     - **Environment**: `Docker`
     - **Dockerfile Path**: `frontend/Dockerfile`
   - Environment Variables:
     ```
     NEXT_PUBLIC_API_URL=https://applens-backend.onrender.com
     GITHUB_CLIENT_ID=<your_github_client_id>
     ```

**Cost**: Free tier available, ~$7-25/month for production

---

### ☁️ **Option 3: AWS (ECS/Fargate)**

**Best for**: Enterprise, high scalability, AWS ecosystem

**Pros**:
- ✅ Highly scalable
- ✅ Enterprise-grade
- ✅ Full control
- ✅ AWS services integration

**Steps**:

1. **Prerequisites**:
   - AWS account
   - AWS CLI installed
   - Docker installed locally

2. **Create ECR Repository**:
   ```bash
   aws ecr create-repository --repository-name applens-backend
   aws ecr create-repository --repository-name applens-frontend
   ```

3. **Build and Push Images**:
   ```bash
   # Backend
   docker build -t applens-backend ./backend
   docker tag applens-backend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/applens-backend:latest
   aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/applens-backend:latest

   # Frontend
   docker build -t applens-frontend ./frontend
   docker tag applens-frontend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/applens-frontend:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/applens-frontend:latest
   ```

4. **Create RDS PostgreSQL**:
   - AWS Console → RDS → Create Database
   - Engine: PostgreSQL 16
   - Enable pgvector extension
   - Note connection details

5. **Create ECS Cluster and Services**:
   - Use AWS Console or Terraform
   - Create Fargate tasks for backend and frontend
   - Configure load balancer
   - Set environment variables

**Cost**: ~$50-200/month (depends on usage)

---

### 🐳 **Option 4: DigitalOcean App Platform**

**Best for**: Simple, good pricing, Docker support

**Pros**:
- ✅ Simple interface
- ✅ Good pricing
- ✅ Managed databases
- ✅ Auto-scaling

**Steps**:

1. **Sign up**: https://www.digitalocean.com

2. **Create App**:
   - Create → App Platform
   - Connect GitHub repo

3. **Add Database**:
   - Add Resource → Database → PostgreSQL
   - Plan: Basic ($15/month) or higher
   - Enable pgvector extension

4. **Add Backend Component**:
   - Add Component → Web Service
   - Source: GitHub repo
   - Dockerfile: `backend/Dockerfile`
   - Environment Variables: (same as Railway)

5. **Add Frontend Component**:
   - Add Component → Web Service
   - Source: GitHub repo
   - Dockerfile: `frontend/Dockerfile`
   - Environment Variables: (same as Railway)

**Cost**: ~$15-50/month

---

### 🚀 **Option 5: Fly.io**

**Best for**: Global edge deployment, fast

**Pros**:
- ✅ Global edge network
- ✅ Fast deployment
- ✅ Good free tier
- ✅ PostgreSQL included

**Steps**:

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Create Apps**:
   ```bash
   # Backend
   cd backend
   fly launch --name applens-backend
   
   # Frontend
   cd ../frontend
   fly launch --name applens-frontend
   ```

4. **Create PostgreSQL**:
   ```bash
   fly postgres create --name applens-db
   fly postgres attach applens-db -a applens-backend
   ```

5. **Deploy**:
   ```bash
   fly deploy
   ```

**Cost**: Free tier available, ~$10-30/month

---

## Common Setup Steps (All Platforms)

### 1. Update GitHub OAuth App

For all platforms, update your GitHub OAuth app:

1. Go to: https://github.com/settings/developers
2. Edit your OAuth App
3. Update:
   - **Homepage URL**: `https://your-frontend-url.com`
   - **Authorization callback URL**: `https://your-backend-url.com/auth/github/callback`

### 2. Environment Variables

Set these in your cloud platform:

**Backend**:
```env
POSTGRES_URL=postgresql+asyncpg://user:pass@host:5432/dbname
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
JWT_SECRET=generate-random-secret-here
OPENAI_API_KEY=your_openai_api_key
ENVIRONMENT=production
MCP_GITHUB_HOST=localhost  # or your MCP server URL
MCP_GITHUB_PORT=8000
```

**Frontend**:
```env
NEXT_PUBLIC_API_URL=https://your-backend-url.com
GITHUB_CLIENT_ID=your_github_client_id
```

### 3. Database Migrations

After deployment, run migrations:

```bash
# Via SSH/Console or using platform's CLI
alembic upgrade head
```

Or add to deployment script:
```bash
# In backend Dockerfile or startup script
RUN alembic upgrade head
```

### 4. Enable pgvector Extension

For PostgreSQL databases, enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Production Checklist

- [ ] Use strong `JWT_SECRET` (generate with: `openssl rand -hex 32`)
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable HTTPS/SSL (usually automatic on most platforms)
- [ ] Configure CORS properly
- [ ] Set up database backups
- [ ] Configure monitoring/logging
- [ ] Set up CI/CD for auto-deployment
- [ ] Configure rate limiting
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Review security settings
- [ ] Test OAuth flow in production
- [ ] Test all AI features (Error Analyzer, What-If, NLQ)

---

## Cost Comparison

| Platform | Free Tier | Production Cost | Best For |
|----------|-----------|----------------|----------|
| Railway | ✅ Yes | $5-20/month | Quick start |
| Render | ✅ Yes | $7-25/month | Simple deployment |
| Fly.io | ✅ Yes | $10-30/month | Global edge |
| DigitalOcean | ❌ No | $15-50/month | Balanced |
| AWS | ❌ No | $50-200/month | Enterprise |

---

## Troubleshooting

### Database Connection Issues
- Check connection string format
- Verify database is accessible from your app
- Check firewall/security group settings

### OAuth Not Working
- Verify callback URL matches exactly
- Check environment variables are set
- Ensure HTTPS is enabled

### Build Failures
- Check Dockerfile paths
- Verify all dependencies are in requirements
- Check build logs for specific errors

### pgvector Extension
- Some platforms require manual extension enable
- Run: `CREATE EXTENSION IF NOT EXISTS vector;`

---

## Need Help?

- Check platform-specific documentation
- Review application logs
- Test locally with production-like environment
- Check GitHub Issues

