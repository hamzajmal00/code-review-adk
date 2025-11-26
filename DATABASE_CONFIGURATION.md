# Database Configuration Guide

## Overview

Your application now uses **TWO databases** that can be configured independently:

1. **Main Application Database** - For users, plans, installations, etc.
2. **AI Session Database** - For Google ADK conversation sessions

## Database Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Your Application                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────┐      ┌──────────────────┐    │
│  │  Main Database   │      │  AI Session DB   │    │
│  │  (database.py)   │      │ (ai_review_svc)  │    │
│  ├──────────────────┤      ├──────────────────┤    │
│  │ • Users          │      │ • Sessions       │    │
│  │ • Plans          │      │ • Chat History   │    │
│  │ • Installations  │      │ • Contexts       │    │
│  │ • Repositories   │      │                  │    │
│  │ • PR Logs        │      │                  │    │
│  └──────────────────┘      └──────────────────┘    │
│         ↓                          ↓                │
│  DATABASE_URL           AI_SESSION_DB_URL          │
│                         (or DATABASE_URL)           │
└─────────────────────────────────────────────────────┘
```

## Configuration Options

### Option 1: Use PostgreSQL for Everything (Recommended for Production)

**Environment Variables:**
```bash
DATABASE_URL=postgresql://user:pass@host:5432/main_db
# AI sessions will automatically use the same database
```

**What happens:**
- Main app uses PostgreSQL
- AI sessions use PostgreSQL (automatically converts to `postgresql+asyncpg://`)
- All data persists across deploys
- Production-ready

### Option 2: Separate Databases (Advanced)

**Environment Variables:**
```bash
DATABASE_URL=postgresql://user:pass@host:5432/main_db
AI_SESSION_DB_URL=postgresql://user:pass@host:5432/ai_sessions_db
```

**What happens:**
- Main app uses one PostgreSQL database
- AI sessions use a different PostgreSQL database
- Better isolation and scalability

### Option 3: SQLite for Development (Default Fallback)

**Environment Variables:**
```bash
# Don't set DATABASE_URL (or set to sqlite)
```

**What happens:**
- Main app falls back to SQLite (`code_reviewer.db`)
- AI sessions use SQLite (`code_review_sessions.db`)
- Good for local development
- ⚠️ Data lost on Render redeploy

## How It Works

### Main Database (`database.py`)

```python
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Falls back to SQLite
    DATABASE_URL = "sqlite:///./code_reviewer.db"

engine = create_engine(DATABASE_URL)
```

**Driver:** Synchronous (`psycopg2` for PostgreSQL, `pysqlite` for SQLite)

### AI Session Database (`services/ai_review_service.py`)

```python
AI_SESSION_DB_URL = os.getenv("AI_SESSION_DB_URL") or os.getenv("DATABASE_URL")

if not AI_SESSION_DB_URL or AI_SESSION_DB_URL.startswith("sqlite://"):
    # Use async SQLite
    AI_SESSION_DB_URL = "sqlite+aiosqlite:///code_review_sessions.db"
elif AI_SESSION_DB_URL.startswith("postgresql://"):
    # Convert to async PostgreSQL
    AI_SESSION_DB_URL = AI_SESSION_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
```

**Driver:** Asynchronous (`asyncpg` for PostgreSQL, `aiosqlite` for SQLite)

## Required Packages

### For PostgreSQL:
```
psycopg2-binary  # Synchronous PostgreSQL (main app)
asyncpg          # Async PostgreSQL (AI sessions)
```

### For SQLite:
```
aiosqlite        # Async SQLite (AI sessions)
# pysqlite comes with Python (main app)
```

## Render Deployment Setup

### Step 1: Set DATABASE_URL

Your PostgreSQL URL:
```
postgresql://codedb_kgug_user:d7apjGSHoJ4d1BbknDfkA02hum6IxTQZ@dpg-d4jkrim3jp1c73b94p70-a.oregon-postgres.render.com/codedb_kgug
```

In Render Dashboard:
1. Go to your web service
2. Environment → Add Environment Variable
3. Key: `DATABASE_URL`
4. Value: (your PostgreSQL URL above)
5. Save

### Step 2: AI Session Database (Automatic)

**You don't need to do anything!** 

The AI session database will automatically:
- Use the same `DATABASE_URL` you just set
- Convert it to use async driver (`postgresql+asyncpg://`)
- Store sessions in the same database

### Step 3: Verify

After deployment, check logs for:
```
✅ Connected to PostgreSQL for main database
✅ AI Session Service initialized with postgresql+asyncpg://
✅ Application startup complete
```

## Local Development Setup

### 1. Create `.env` file:
```bash
# Use SQLite for local development
DATABASE_URL=sqlite:///./code_reviewer.db
```

### 2. Or use PostgreSQL locally:
```bash
# If you have PostgreSQL installed
DATABASE_URL=postgresql://postgres:password@localhost:5432/code_reviewer
```

### 3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 4. Run:
```bash
uvicorn main:app --reload
```

## Troubleshooting

### Error: "The asyncio extension requires an async driver"
**Solution:** This is now fixed! The code automatically uses `asyncpg` for PostgreSQL.

### Error: "Could not parse SQLAlchemy URL"
**Cause:** `DATABASE_URL` is empty or malformed
**Solution:** 
1. Check environment variable is set
2. Verify PostgreSQL URL format: `postgresql://user:pass@host:port/dbname`

### Error: "asyncpg.exceptions.InvalidPasswordError"
**Cause:** Wrong database credentials
**Solution:** Double-check your PostgreSQL connection string

### Warning: "Falling back to SQLite"
**This is normal for local development.** In production, make sure `DATABASE_URL` is set.

### AI Sessions Not Persisting
**Cause:** Using SQLite on Render
**Solution:** Set `DATABASE_URL` to PostgreSQL (already done!)

## Best Practices

### ✅ DO:
- Use PostgreSQL for production (Render)
- Use SQLite for local development
- Let AI sessions use the same database as main app
- Keep your DATABASE_URL in environment variables

### ❌ DON'T:
- Hardcode database URLs in code
- Use SQLite in production (data loss on redeploy)
- Commit `.env` file to git
- Mix sync and async drivers incorrectly

## Summary

| Environment | Main Database | AI Session Database |
|-------------|---------------|---------------------|
| **Local Dev** | SQLite (sync) | SQLite (async) |
| **Production** | PostgreSQL (sync) | PostgreSQL (async) |
| **Drivers** | `psycopg2-binary` | `asyncpg` |
| **Files Created** | `code_reviewer.db` | `code_review_sessions.db` (dev only) |

Your database configuration is now **production-ready** and will automatically work with PostgreSQL on Render! 🎉

