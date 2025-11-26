# ⚡ QUICK FIX - DATABASE_URL Not Set in Render

## The Problem
```
Could not parse SQLAlchemy URL from given URL string
```
This means `DATABASE_URL` is missing in Render.

## 🚀 Quick Solution (2 minutes)

### Option 1: Use SQLite Temporarily (Already Fixed in Code)
✅ **I've already updated the code to use SQLite as a fallback**

Just push this change and the app will start:
```bash
git add .
git commit -m "Add SQLite fallback for DATABASE_URL"
git push
```

⚠️ **Warning:** SQLite data will be lost on each redeploy. Not for production!

---

### Option 2: Set Up PostgreSQL (Recommended - 5 minutes)

#### 1️⃣ Create PostgreSQL Database in Render
- Dashboard → New + → PostgreSQL
- Name: `adk-code-reviewer-db`
- Click Create

#### 2️⃣ Link to Your Web Service
- Go to your web service
- Environment tab
- Add Environment Variable
  - Key: `DATABASE_URL`
  - Value: Select Database → `adk-code-reviewer-db` → Internal Connection String
- Save

#### 3️⃣ Add Other Required Variables
Click "Add Environment Variable" for each:

| Key | Example Value | Where to Get It |
|-----|---------------|-----------------|
| `GITHUB_CLIENT_ID` | `Ov23lisaj8nXzoK709f6` | GitHub OAuth App settings |
| `GITHUB_CLIENT_SECRET` | `214a7c7523...` | GitHub OAuth App settings |
| `GITHUB_OAUTH_REDIRECT_URL` | `https://your-app.onrender.com/auth/github/callback` | Your Render URL + `/auth/github/callback` |
| `GOOGLE_API_KEY` | `AIza...` | Google Cloud Console |
| `JWT_SECRET_KEY` | `random-string-here` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

#### 4️⃣ Done!
Render will auto-redeploy. Check logs for "Application startup complete" ✅

---

## 📋 Current Status

✅ **Fixed in your local code:**
- Added SQLite fallback
- Better error messages
- Async SQLite driver configured

❌ **Still need to do in Render:**
- Set environment variables (see Option 2 above)

---

## 🔍 How to Check if It's Working

### In Render Logs, you should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:xxxxx
```

### In Render Logs, you should NOT see:
```
❌ Could not parse SQLAlchemy URL
❌ DatabaseSessionService failed
❌ ValueError: DATABASE_URL environment variable is not set
```

---

## 🆘 Still Having Issues?

1. **Check Environment Variables:** Go to your web service → Environment tab → Verify all variables are set
2. **Check Database:** Go to your PostgreSQL database → Should show "Available"
3. **Clear Cache:** Manual Deploy → Clear build cache & deploy
4. **Check Logs:** Look for the actual error message (not just "Exited with status 1")

For detailed instructions: See `RENDER_ENV_SETUP.md`

