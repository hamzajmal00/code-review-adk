import os
import tempfile
import subprocess
import traceback
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from github import Github
from services.ai_review_service import run_ai_code_review
from services.github_service import post_github_comment, get_diff_via_api
from services.cleanup_service import safe_rmtree
from utils.logger import log

# ------------------------------------------------------------
# ⚙️ App Initialization
# ------------------------------------------------------------
load_dotenv()
app = FastAPI()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("❌ Missing GITHUB_TOKEN in .env")

# ------------------------------------------------------------
# 📬 Webhook Endpoint
# ------------------------------------------------------------
@app.post("/webhook")
async def handle_pr_event(request: Request):
    payload = await request.json()
    action = payload.get("action")
    pr = payload.get("pull_request", {})

    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": f"ignored action: {action}"}

    repo_full_name = pr["head"]["repo"]["full_name"]
    repo_url = pr["head"]["repo"]["clone_url"]
    head_branch = pr["head"]["ref"]
    base_branch = pr["base"]["ref"]
    pr_number = pr["number"]

    log(f"🔔 PR #{pr_number} for {repo_full_name} → {base_branch}")

    if repo_url.startswith("https://github.com/"):
        repo_url = repo_url.replace("https://", f"https://{GITHUB_TOKEN}@")

    # Try API method first
    try:
        diff = get_diff_via_api(GITHUB_TOKEN, repo_full_name, pr_number)
        if not diff:
            raise ValueError("Empty diff via API")

        log(f"✅ Diff fetched via API ({len(diff)} chars)")
        ai_review = await run_ai_code_review(diff, pr_number)
        if ai_review:
            post_github_comment(GITHUB_TOKEN, repo_full_name, pr_number, ai_review)
            return {"status": "review complete", "source": "GitHub API"}
        return {"error": "No AI review response"}

    except Exception as e:
        log(f"⚠️ API method failed: {e}")
        traceback.print_exc()

    # Fallback: use Git diff
    tmpdir = tempfile.mkdtemp(prefix="code_review_")
    try:
        subprocess.run(["git", "clone", repo_url, tmpdir], check=True)
        subprocess.run(["git", "fetch", "origin"], cwd=tmpdir, check=True)
        diff = subprocess.run(
            ["git", "diff", f"origin/{base_branch}..origin/{head_branch}"],
            cwd=tmpdir, capture_output=True, text=True
        ).stdout.strip()

        if not diff:
            log("⚠️ No diff found between branches.")
            return {"status": "no diff detected"}

        log(f"✅ Diff generated ({len(diff)} chars)")
        ai_review = await run_ai_code_review(diff, pr_number)
        if ai_review:
            post_github_comment(GITHUB_TOKEN, repo_full_name, pr_number, ai_review)
            return {"status": "review complete", "source": "git diff"}
        return {"error": "No AI review response"}

    finally:
        safe_rmtree(tmpdir)
