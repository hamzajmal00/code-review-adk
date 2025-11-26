# Quick Setup Guide for Render Deployment

## What Was Fixed

1. ✅ **Fixed async SQLite driver issue** - Updated Google ADK session database to use `aiosqlite`
2. ✅ **Added database validation** - Better error messages when DATABASE_URL is missing
3. ✅ **Removed hardcoded credentials** - Moved to environment variables for security
4. ✅ **Updated render.yaml** - Added PostgreSQL database configuration
5. ✅ **Created env.example** - Template for all required environment variables

## Steps to Deploy on Render

### 1. Prerequisites
Before deploying, ensure you have:
- A GitHub account with your code repository
- A Render account (free tier works)
- GitHub OAuth App credentials
- Google API Key for AI features

### 2. Set Up GitHub OAuth App (if not done)
1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: Your app name
   - **Homepage URL**: `https://your-render-app.onrender.com` (update after deployment)
   - **Authorization callback URL**: `https://your-render-app.onrender.com/auth/github/callback`
4. Save the **Client ID** and **Client Secret**

### 3. Deploy to Render

#### Option A: Using render.yaml (Automatic)
1. Push your code to GitHub
2. Go to https://render.com/
3. Click "New +" → "Blueprint"
4. Connect your GitHub repository
5. Render will detect `render.yaml` and create:
   - A Web Service
   - A PostgreSQL Database (automatically linked)

#### Option B: Manual Setup
1. Create a new PostgreSQL Database:
   - Click "New +" → "PostgreSQL"
   - Name it `adk-code-reviewer-db`
   - Choose free tier or paid tier
   - Click "Create Database"

2. Create a Web Service:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: adk-code-reviewer
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

### 4. Set Environment Variables in Render Dashboard

Go to your Web Service → Environment → Add Environment Variables:

```
# Automatically set if you linked PostgreSQL database:
DATABASE_URL = postgres://... (from database)

# You need to add these manually:
GITHUB_APP_NAME = your-github-app-name
GITHUB_CLIENT_ID = your-oauth-client-id
GITHUB_CLIENT_SECRET = your-oauth-client-secret
GITHUB_OAUTH_REDIRECT_URL = https://your-app.onrender.com/auth/github/callback
GOOGLE_API_KEY = your-google-api-key
JWT_SECRET_KEY = generate-a-random-string-here
FRONTEND_URL = http://localhost:3000 (or your frontend URL)
```

**To generate JWT_SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. Deploy!
1. Click "Save Changes" (if manual setup)
2. Render will automatically deploy your application
3. Wait for the build to complete (2-5 minutes)
4. Your app will be live at `https://your-app.onrender.com`

### 6. Update GitHub OAuth App
1. Go back to your GitHub OAuth App settings
2. Update the callback URL with your actual Render URL:
   - `https://your-app.onrender.com/auth/github/callback`

## Verifying the Deployment

### Check if the app is running:
```bash
curl https://your-app.onrender.com/
```

### Check logs in Render Dashboard:
1. Go to your Web Service
2. Click "Logs" tab
3. Look for "Application startup complete"
4. Should NOT see database errors

## Common Issues and Solutions

### Issue: "Could not parse SQLAlchemy URL from given URL string"
**Solution:** DATABASE_URL is not set. Make sure:
- PostgreSQL database is created and linked
- DATABASE_URL environment variable is set in Render

### Issue: "The asyncio extension requires an async driver"
**Solution:** This is now fixed. Make sure you've pulled the latest code with `aiosqlite` in requirements.txt

### Issue: "No open ports detected"
**Solution:** This usually means the app failed to start due to another error. Check the logs above this message for the actual error.

### Issue: OAuth redirect fails
**Solution:** Make sure the GITHUB_OAUTH_REDIRECT_URL in environment variables matches exactly with your GitHub OAuth App callback URL.

## Local Development

### 1. Set up environment:
```bash
# Copy env.example to .env
cp env.example .env

# Edit .env with your local configuration
# Use SQLite for local development:
DATABASE_URL=sqlite:///./code_reviewer.db
```

### 2. Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run locally:
```bash
uvicorn main:app --reload --port 8000
```

### 4. Access the API:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## Need Help?

Check the following files for more details:
- `DEPLOYMENT.md` - Comprehensive deployment guide
- `env.example` - All environment variables with descriptions
- `render.yaml` - Render configuration

## Security Notes

⚠️ **IMPORTANT:**
- Never commit `.env` files to Git
- Never hardcode credentials in your code
- Use environment variables for all sensitive data
- Rotate your JWT_SECRET_KEY periodically
- Use HTTPS in production (Render provides this automatically)

