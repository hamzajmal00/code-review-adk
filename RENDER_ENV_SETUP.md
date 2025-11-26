# Render Environment Variables Setup Guide

## Problem
Your app is failing on Render with:
```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string
```

This means `DATABASE_URL` is not set in Render.

## Solution: Set Up Environment Variables in Render Dashboard

### Step 1: Log into Render Dashboard
1. Go to https://dashboard.render.com/
2. Log in with your account
3. Find your web service (adk-code-reviewer)

### Step 2: Add PostgreSQL Database (Recommended)

#### Create Database:
1. Click on "New +" in the top menu
2. Select "PostgreSQL"
3. Configure:
   - **Name**: `adk-code-reviewer-db`
   - **Database**: `code_reviewer`
   - **User**: `code_reviewer`
   - **Region**: Same as your web service
   - **Plan**: Free (or paid if needed)
4. Click "Create Database"
5. Wait for it to be created (1-2 minutes)

#### Link Database to Web Service:
1. Go to your web service (adk-code-reviewer)
2. Click on "Environment" in the left sidebar
3. Click "Add Environment Variable"
4. Add:
   - **Key**: `DATABASE_URL`
   - **Value**: Click "Select Database" → Choose `adk-code-reviewer-db` → Select "Internal Connection String"
5. Click "Save Changes"

### Step 3: Add Required Environment Variables

Still in the Environment section, add these variables one by one:

```
GITHUB_APP_NAME = your-github-app-name
GITHUB_CLIENT_ID = your-github-oauth-client-id
GITHUB_CLIENT_SECRET = your-github-oauth-client-secret
GITHUB_OAUTH_REDIRECT_URL = https://your-app.onrender.com/auth/github/callback
GOOGLE_API_KEY = your-google-api-key
JWT_SECRET_KEY = (generate a random string - see below)
FRONTEND_URL = http://localhost:3000
```

#### How to add each variable:
1. Click "Add Environment Variable"
2. Enter **Key** (e.g., `GITHUB_CLIENT_ID`)
3. Enter **Value** (e.g., `Ov23lisaj8nXzoK709f6`)
4. Click "Save Changes"
5. Repeat for all variables

#### Generate JWT_SECRET_KEY:
Run this command locally:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Copy the output and use it as the value for `JWT_SECRET_KEY`.

### Step 4: Redeploy

After adding all environment variables:
1. Render will automatically trigger a redeploy
2. Wait for the build to complete (3-5 minutes)
3. Check the logs for "Application startup complete"

## Alternative: Use SQLite (Temporary/Development)

If you don't want to set up PostgreSQL right now, the app will now automatically fall back to SQLite. However, **this is NOT recommended for production** because:
- SQLite database will be lost on every redeploy
- Not suitable for concurrent access
- Limited scalability

The app will work but **you'll lose all data on redeploy**.

## Verify Setup

### Check Environment Variables:
1. Go to your web service
2. Click "Environment" tab
3. You should see:
   - `DATABASE_URL` (from PostgreSQL database)
   - `GITHUB_CLIENT_ID`
   - `GITHUB_CLIENT_SECRET`
   - `GITHUB_OAUTH_REDIRECT_URL`
   - `GOOGLE_API_KEY`
   - `JWT_SECRET_KEY`
   - And any other variables you added

### Check Logs:
1. Go to your web service
2. Click "Logs" tab
3. Look for:
   - ✅ "Application startup complete"
   - ✅ "Uvicorn running on..."
   - ❌ NO database errors

### Test the App:
```bash
# Replace with your actual Render URL
curl https://your-app.onrender.com/
```

Should return a response without errors.

## Troubleshooting

### Error: "Could not parse SQLAlchemy URL"
**Cause:** `DATABASE_URL` is not set or is empty
**Solution:** 
1. Check if the environment variable is actually set in Render
2. Make sure you linked the PostgreSQL database correctly
3. Try manually copying the connection string from the database page

### Error: "Database connection failed"
**Cause:** Database connection string is incorrect
**Solution:**
1. Go to your PostgreSQL database in Render
2. Copy the "Internal Connection String" (not External)
3. Manually set it in the `DATABASE_URL` environment variable

### Warning: "Falling back to SQLite"
**Cause:** `DATABASE_URL` is not set
**Solution:** This means the app is using SQLite as a fallback. Set up PostgreSQL following Step 2 above.

### App Still Not Starting
**Debug Steps:**
1. Check logs for the exact error
2. Verify all required environment variables are set
3. Make sure the start command is correct:
   ```
   gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
   ```
4. Try manual deploy: Click "Manual Deploy" → "Clear build cache & deploy"

## Quick Checklist

- [ ] PostgreSQL database created in Render
- [ ] DATABASE_URL linked to web service
- [ ] GITHUB_CLIENT_ID set
- [ ] GITHUB_CLIENT_SECRET set
- [ ] GITHUB_OAUTH_REDIRECT_URL set (with your actual Render URL)
- [ ] GOOGLE_API_KEY set
- [ ] JWT_SECRET_KEY set (random string)
- [ ] FRONTEND_URL set
- [ ] App redeployed after adding variables
- [ ] Logs show "Application startup complete"
- [ ] No database errors in logs

## Need Help?

If you're still having issues:
1. Share the complete error log from Render
2. Verify all environment variables are set (screenshot)
3. Check if the database is created and running
4. Try clearing build cache and redeploying

