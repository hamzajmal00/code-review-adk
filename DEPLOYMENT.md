# Deployment Guide

## Deploying to Render

### Prerequisites
1. A Render account
2. GitHub OAuth App credentials
3. Google API Key for AI reviews
4. GitHub App credentials

### Steps

#### 1. Database Setup (Automatic with render.yaml)
The `render.yaml` file is configured to automatically create a PostgreSQL database for you. Render will:
- Create a PostgreSQL database named `adk-code-reviewer-db`
- Automatically set the `DATABASE_URL` environment variable

#### 2. Environment Variables
After deployment, you need to add these environment variables in the Render dashboard:

**Required:**
- `DATABASE_URL` - Automatically set by Render (from the PostgreSQL database)
- `GITHUB_APP_NAME` - Your GitHub App name
- `GITHUB_CLIENT_ID` - Your GitHub OAuth App Client ID
- `GITHUB_CLIENT_SECRET` - Your GitHub OAuth App Client Secret
- `GITHUB_OAUTH_REDIRECT_URL` - Your deployed URL + `/auth/github/callback`
- `GOOGLE_API_KEY` - Your Google AI API key
- `JWT_SECRET_KEY` - A secure random string for JWT signing

**Optional:**
- `FRONTEND_URL` - Your frontend URL (default: http://localhost:3000)
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `JWT_EXPIRATION_HOURS` - JWT expiration time (default: 24)

#### 3. Deploy
```bash
# Push your code to GitHub
git add .
git commit -m "Deploy to Render"
git push

# Render will automatically detect render.yaml and deploy
```

#### 4. Manual Setup (Alternative)
If you prefer manual setup without render.yaml:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
4. Create a PostgreSQL database
5. Link the database to your web service
6. Add all required environment variables

## Local Development

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your local configuration:
   ```bash
   DATABASE_URL=sqlite:///./code_reviewer.db
   GITHUB_CLIENT_ID=your-local-oauth-client-id
   # ... other variables
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## Troubleshooting

### Error: "Could not parse SQLAlchemy URL"
- **Cause:** `DATABASE_URL` environment variable is not set
- **Solution:** 
  - For Render: Ensure the PostgreSQL database is created and linked
  - For local: Set `DATABASE_URL` in your `.env` file

### Error: "The asyncio extension requires an async driver"
- **Cause:** Using synchronous SQLite driver with async code
- **Solution:** Use `sqlite+aiosqlite:///` instead of `sqlite:///` for SQLite URLs
- **Note:** This is already fixed in `services/ai_review_service.py`

### Error: "No open ports detected"
- **Cause:** Application failed to start
- **Solution:** Check the logs for the actual error and fix it before the port binding issue

