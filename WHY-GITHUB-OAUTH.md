# Why GitHub OAuth is Required

## AppLens Needs GitHub OAuth Because:

### 1. **User Authentication**
- Users must sign in with GitHub to use the application
- The "Sign in with GitHub" button on the landing page requires OAuth
- Without it, users can't access the dashboard or scan features

### 2. **Repository Access**
- AppLens needs to **read your GitHub repositories** to scan them
- It uses the GitHub API to:
  - List your repositories (public and private)
  - Read file contents from repositories
  - Get commit information
  - Access repository metadata

### 3. **Code Scanning**
- To build the microservice dependency graph, AppLens must:
  - Fetch code files from your repositories
  - Analyze HTTP calls, Kafka topics, service interactions
  - This requires authenticated GitHub API access

### 4. **Security & Permissions**
- OAuth allows users to grant specific permissions:
  - `read:user` - Read user profile
  - `repo` - Read repository contents
- Users control what repositories AppLens can access

## What Happens Without GitHub OAuth?

❌ Users cannot sign in
❌ Cannot search/select repositories
❌ Cannot start scans
❌ Cannot access any features

## Is There a Way to Skip GitHub OAuth?

**For testing/development only**, you could:
1. Modify the code to skip authentication (not recommended)
2. Use mock/test data instead of real GitHub repos
3. Hardcode repository access (not secure)

**But for production use**, GitHub OAuth is essential because:
- It's the only secure way to access GitHub repositories
- Users need to authenticate to use the app
- The app needs repository read permissions

## How to Get GitHub OAuth Credentials

1. Go to: https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: AppLens
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:8000/auth/github/callback`
4. Click "Register application"
5. Copy the **Client ID**
6. Click "Generate a new client secret" and copy it

**Note**: For local development, `http://localhost` URLs are fine. For production, you'll need to update these URLs.

