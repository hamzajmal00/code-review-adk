# main.py

import os
import traceback
import requests

from fastapi import FastAPI, Request, Header,HTTPException ,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from dotenv import load_dotenv

from services.ai_review_service import run_ai_code_review
from services.github_service import (
    create_installation_token,
    get_diff_via_api,
    post_github_comment,
)
from utils.logger import log

from database import Base, engine
import models 
from fastapi import Depends,status
from sqlalchemy.orm import Session
from jose import JWTError
from auth import create_jwt_token


from crud.user_crud import get_user_by_github_id, create_user, increment_user_pr_usage
from crud.installation_crud import create_installation, get_installation_by_installation_id
from crud.repo_crud import upsert_repository
from crud.plan_crud import get_plan_by_slug
from database import SessionLocal ,get_db
from models import User  # optional, mainly for typing
from crud.user_crud import (
    get_user_by_github_id,
    create_user,
)
from crud.plan_crud import get_plan_by_slug

from utils.jwt_utils import create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordBearer

from auth_dependency import get_current_user

load_dotenv()

app = FastAPI()

# CORS – allow your UI to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # TODO: restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/github/login") 

# Create tables on startup (dev only; prod me Alembic best practice)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)




@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "github_username": current_user.github_username,
        "plan": current_user.plan.slug if current_user.plan else None
    }


GITHUB_APP_NAME = os.getenv("GITHUB_APP_NAME")  # same as on GitHub





GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_OAUTH_REDIRECT_URL = os.getenv("GITHUB_OAUTH_REDIRECT_URL")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@app.get("/auth/github/login")
def github_login():
    """
    Step 1: Frontend isko call karega.
    Hum user ko GitHub ke authorize page par redirect kar denge.
    """
    if not GITHUB_CLIENT_ID or not GITHUB_OAUTH_REDIRECT_URL:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth not configured properly.",
        )

    github_authorize_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_OAUTH_REDIRECT_URL}"
        f"&scope=read:user user:email"
    )

    return RedirectResponse(url=github_authorize_url)



# ------------------------------------------------------------
@app.get("/auth/github/callback")
def github_callback(code: str, db: Session = Depends(get_db)):
    """
    Step 2: GitHub yahan par `code` ke sath redirect karega.
    Hum:
      - code se access_token lenge
      - user ka GitHub profile lenge
      - DB me user find/create karenge
      - default plan = 'free' set karenge (agar new user hai)
      - frontend ko minimal info + token (for now just user data) return karenge
    """
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth not configured properly.",
        )

    # 1) Exchange code -> access token
    token_resp = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_OAUTH_REDIRECT_URL,
        },
        timeout=10,
    )

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail="Failed to exchange code for access token.",
        )

    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="No access token returned from GitHub.",
        )

    # 2) Fetch GitHub user profile
    user_resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if user_resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail="Failed to fetch GitHub user profile.",
        )

    gh_user = user_resp.json()
    github_user_id = gh_user["id"]
    github_username = gh_user["login"]
    avatar_url = gh_user.get("avatar_url")
    email = gh_user.get("email")  # kabhi None bhi hota hai

    # 3) Check if user exists in DB
    user = get_user_by_github_id(db, github_user_id)

    if not user:
        # DEFAULT PLAN: 'free'
        plan = get_plan_by_slug(db, "free")
        if not plan:
            # fallback: create a default free plan
            from models import Plan

            plan = Plan(
                name="Free",
                slug="free",
                monthly_pr_limit=20,
                monthly_token_limit=None,
                is_active=True,
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)

        user = create_user(
            db=db,
            username=github_username,
            github_user_id=github_user_id,
            email=email,
            avatar_url=avatar_url,
            plan_id=plan.id,
        )

    # ✅ at this point user exists and has a plan (default: free)
    # TODO: yahan par JWT generate kar sakte ho (auth token for UI)
    # For now, simple JSON return kar dete hain
    # app_token = create_access_token({"sub": str(user.id)})

    # return {
    #     "status": "ok",
    #     "user": {
    #         "id": user.id,
    #         "github_user_id": user.github_user_id,
    #         "github_username": user.github_username,
    #         "email": user.email,
    #         "avatar_url": user.avatar_url,
    #         "plan": user.plan.slug if user.plan else None,
    #     },
    #     "access_token": access_token,  # optional: frontend store kare ya ignore kare
    #     "app_token": app_token,  
    # }
    jwt_payload = {
         "github_user_id": user.github_user_id,
        "user_id": user.id,
        "github_username": user.github_username,
        "plan": user.plan.slug,
    }

    jwt_token = create_jwt_token(jwt_payload)

    return {
        "status": "ok",
        "user": jwt_payload,
        "token": jwt_token
    }


# ------------------------------------------------------------
# Optional: Install URL endpoint (for your frontend)
# ------------------------------------------------------------
@app.get("/github/install/callback")
def github_install_callback(
    request: Request,
    installation_id: int = Query(...),
    state: str = Query(...),
    setup_action: str = Query(None),
    db: Session = Depends(get_db)
):
    print("🔥 CALLBACK HIT")
    print("installation_id =", installation_id)
    print("state =", state)
    print("setup_action =", setup_action)

    # Convert state → user_id
    user_id = int(state)

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    # Save installation
    create_installation(
        db=db,
        installation_id=installation_id,
        account_login=user.github_username or "unknown", 
        account_type="User",
        user_id=user_id,
    )

    return {"status": "installation_linked", "installation_id": installation_id}


@app.get("/github/install/callback")
def github_install_callback(installation_id: int, state: str, db: Session = Depends(get_db)):
    print("i am here")
    user_id = int(state)  # your user ID
    create_installation(
        db,
        installation_id=installation_id,
        account_login="...",
        account_type="User",
        user_id=user_id
    )
    return {"status": "linked"}



# ------------------------------------------------------------
# GitHub Webhook Handler (App-based, like Vercel)
# ------------------------------------------------------------
@app.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
):
    """
    Handle GitHub App webhooks:
    - installation: save installation to DB
    - pull_request: check plan → run AI review → post comment
    """

    try:
        payload = await request.json()
    except Exception:
        log("❌ Failed to parse webhook JSON")
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    log(f"📬 Received GitHub event: {x_github_event}")

    # --------------------------------------------------------------------
    # 1) INSTALLATION EVENT → Save installation in DB
    # --------------------------------------------------------------------
    if x_github_event == "installation":
        try:
            installation_id = payload["installation"]["id"]
            account_login = payload["installation"]["account"]["login"]
            account_type = payload["installation"]["account"]["type"]  # "User" / "Organization"

            db = SessionLocal()

            create_installation(
                db,
                installation_id,
                account_login,
                account_type,
                None      # user_id will be updated when user logs in
            )

            log(f"🔧 Installation saved: id={installation_id}, account={account_login}")
            return {"status": "installation_received"}

        except Exception as e:
            log(f"⚠️ Installation error: {e}")
            return {"status": "installation_error"}

    # --------------------------------------------------------------------
    # 2) PULL REQUEST EVENT → Main logic
    # --------------------------------------------------------------------
    if x_github_event == "pull_request":
        try:
            action = payload.get("action")
            if action not in ["opened", "synchronize", "reopened"]:
                log(f"ℹ️ Ignored PR action: {action}")
                return {"status": f"ignored_action: {action}"}

            installation_id = payload["installation"]["id"]
            repo_full_name = payload["repository"]["full_name"]
            pr = payload["pull_request"]
            pr_number = pr["number"]
            head_branch = pr["head"]["ref"]
            base_branch = pr["base"]["ref"]

            log(f"🔔 PR #{pr_number} {head_branch} → {base_branch} ({repo_full_name})")

            # ----------------------------------------------------------------
            # Load installation → user → plan from DB
            # ----------------------------------------------------------------
            db = SessionLocal()
            inst = get_installation_by_installation_id(db, installation_id)
            if not inst:
                log("❌ Installation not found in DB")
                return {"status": "installation_not_found"}

            user = inst.user
            if not user:
                log("❌ Installation found but no linked user")
                return {"status": "user_not_linked"}

            plan = user.plan
            if not plan:
                log("❌ User has no plan")
                return {"status": "plan_not_found"}

            used = user.pr_used_this_period or 0
            limit = plan.monthly_pr_limit or 0

            log(f"📊 User={user.email}, Plan={plan.name}, Used={used}/{limit}")

            # ----------------------------------------------------------------
            # PLAN LIMIT CHECK — Free plan allows only 2 PRs
            # ----------------------------------------------------------------
            if used >= limit:
                installation_token = create_installation_token(installation_id)

                upgrade_msg = (
                    f"🚫 **Review Limit Reached**\n\n"
                    f"Your **{plan.name} plan** allows only **{limit} PR reviews**.\n"
                    f"👉 Upgrade your plan to continue using AI Review.\n"
                )

                post_github_comment(
                    installation_token,
                    repo_full_name,
                    pr_number,
                    upgrade_msg,
                )

                log("❌ Limit reached — upgrade required")
                return {"status": "limit_reached"}

            # ----------------------------------------------------------------
            # 1) INSTALLATION TOKEN
            # ----------------------------------------------------------------
            installation_token = create_installation_token(installation_id)

            # ----------------------------------------------------------------
            # 2) FETCH PR DIFF
            # ----------------------------------------------------------------
            diff = get_diff_via_api(installation_token, repo_full_name, pr_number)
            if not diff.strip():
                log("⚠️ Empty diff")
                return {"status": "skipped_no_diff"}

            log(f"✅ Diff fetched ({len(diff)} chars)")

            # ----------------------------------------------------------------
            # 3) RUN AI REVIEW
            # ----------------------------------------------------------------
            ai_review = await run_ai_code_review(diff, pr_number)
            if not ai_review:
                log("⚠️ AI review failed")
                return {"status": "error_ai_review"}

            # ----------------------------------------------------------------
            # 4) POST COMMENT
            # ----------------------------------------------------------------
            post_github_comment(installation_token, repo_full_name, pr_number, ai_review)
            log("💬 Review comment posted")

            # ----------------------------------------------------------------
            # 5) INCREMENT PR USAGE
            # ----------------------------------------------------------------
            increment_user_pr_usage(db, user.id)
            log("📈 PR usage incremented")

            return {
                "status": "success",
                "pr_number": pr_number,
                "used": used + 1,
                "limit": limit,
            }

        except Exception as e:
            log(f"❌ Error in PR event: {e}")
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    # --------------------------------------------------------------------
    # 3) Other events ignored
    # --------------------------------------------------------------------
    return {"status": "ignored", "event": x_github_event}
