# main.py

import os
import traceback

from fastapi import FastAPI, Request, Header
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

GITHUB_APP_NAME = os.getenv("GITHUB_APP_NAME")  # same as on GitHub


# ------------------------------------------------------------
# Optional: Install URL endpoint (for your frontend)
# ------------------------------------------------------------
@app.get("/github/install")
def github_install_redirect():
    """
    Redirect to GitHub App installation page, similar to Vercel's "Connect GitHub".
    """
    if not GITHUB_APP_NAME:
        return JSONResponse(
            status_code=500,
            content={"error": "GITHUB_APP_NAME is not configured"},
        )

    install_url = f"https://github.com/apps/{GITHUB_APP_NAME}/installations/new"
    return RedirectResponse(url=install_url)


# ------------------------------------------------------------
# GitHub Webhook Handler (App-based, like Vercel)
# ------------------------------------------------------------
@app.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),  # TODO: verify with WEBHOOK_SECRET
):
    """
    Handle GitHub App webhooks:
    - installation: (optional) you can log/store installation info
    - pull_request: run AI code review and comment on the PR
    """
    try:
        payload = await request.json()
    except Exception:
        log("❌ Failed to parse webhook JSON")
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    # TODO: verify x_hub_signature_256 with GITHUB_WEBHOOK_SECRET for security

    log(f"📬 Received GitHub event: {x_github_event}")

    # -------------------------------
    # Installation events (optional)
    # -------------------------------
    if x_github_event == "installation":
        try:
            installation_id = payload["installation"]["id"]
            account_login = payload["installation"]["account"]["login"]
            log(f"🔧 App installed for account={account_login}, installation_id={installation_id}")
            # Yahan aap DB me store bhi kar sakte ho agar future UI ke liye zaroori ho
            return {"status": "installation_received"}
        except Exception as e:
            log(f"⚠️ Error handling installation event: {e}")
            return {"status": "installation_error"}

    # -------------------------------
    # Pull Request events → core flow
    # -------------------------------
    if x_github_event == "pull_request":
        try:
            action = payload.get("action")
            if action not in ["opened", "synchronize", "reopened"]:
                log(f"ℹ️ Ignored PR action: {action}")
                return {"status": f"ignored action: {action}"}

            installation_id = payload["installation"]["id"]
            repo_full_name = payload["repository"]["full_name"]
            pr = payload["pull_request"]

            pr_number = pr["number"]
            head_branch = pr["head"]["ref"]
            base_branch = pr["base"]["ref"]

            log(
                f"🔔 PR #{pr_number} {head_branch} → {base_branch} "
                f"({repo_full_name}), installation_id={installation_id}"
            )

            # 1) Get installation access token (for this repo / installation)
            installation_token = create_installation_token(installation_id)

            # 2) Fetch diff via GitHub API
            diff = get_diff_via_api(installation_token, repo_full_name, pr_number)

            if not diff.strip():
                log("⚠️ Empty diff – no changes detected")
                return {
                    "status": "skipped",
                    "message": "No changes detected in PR diff",
                    "pr_number": pr_number,
                }

            log(f"✅ Diff fetched ({len(diff)} chars)")

            # 3) Run AI review (your existing logic)
            ai_review = await run_ai_code_review(diff, pr_number)

            if not ai_review:
                log("⚠️ AI review returned empty response")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "error": "AI review did not generate a response",
                    },
                )

            # 4) Post comment on PR using installation token
            post_github_comment(installation_token, repo_full_name, pr_number, ai_review)

            return {
                "status": "success",
                "message": "Review posted successfully",
                "pr_number": pr_number,
                "repo": repo_full_name,
                "source": "github_app",
            }

        except Exception as e:
            log(f"❌ Error handling pull_request event: {e}")
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={"status": "error", "error": str(e), "event": "pull_request"},
            )

    # -------------------------------
    # Other events (ignored)
    # -------------------------------
    log(f"ℹ️ Ignored event type: {x_github_event}")
    return {"status": "ignored", "event": x_github_event}
