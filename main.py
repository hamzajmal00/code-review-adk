import os
import tempfile
import subprocess
import traceback
from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from services.ai_review_service import run_ai_code_review
from services.github_service import post_github_comment, get_diff_via_api
from services.cleanup_service import safe_rmtree
from utils.logger import log

# ------------------------------------------------------------
# ⚙️ App Initialization
# ------------------------------------------------------------
load_dotenv()
app = FastAPI()

# ✅ Allow UI (HTML/JS) to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# 📬 Webhook Endpoint (Dynamic)
# ------------------------------------------------------------
@app.post("/webhook")
async def handle_pr_event(
    request: Request,
    x_github_token: str = Header(None),
    x_gemini_api_key: str = Header(None)
):
    """
    Handle GitHub PR events dynamically using user-provided tokens.
    """
    payload = await request.json()
    action = payload.get("action")
    pr = payload.get("pull_request", {})

    # Validate required headers
    if not x_github_token or not x_gemini_api_key:
        return {"error": "Missing required headers: X-Github-Token or X-Gemini-Api-Key"}

    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": f"ignored action: {action}"}

    repo_full_name = pr["head"]["repo"]["full_name"]
    repo_url = pr["head"]["repo"]["clone_url"]
    head_branch = pr["head"]["ref"]
    base_branch = pr["base"]["ref"]
    pr_number = pr["number"]

    log(f"🔔 PR #{pr_number} {head_branch} → {base_branch} ({repo_full_name})")

    # Inject token into clone URL
    if repo_url.startswith("https://github.com/"):
        repo_url = repo_url.replace("https://", f"https://{x_github_token}@")

    # ✅ Make Gemini key available globally for ADK Runner
    os.environ["GOOGLE_API_KEY"] = x_gemini_api_key

    # --------------------------------------------------------
    # Try via GitHub API
    # --------------------------------------------------------
    try:
        diff = get_diff_via_api(x_github_token, repo_full_name, pr_number)
        if not diff:
            raise ValueError("Empty diff via API")

        log(f"✅ Diff fetched via API ({len(diff)} chars)")
        ai_review = await run_ai_code_review(diff, pr_number)

        if ai_review:
            post_github_comment(x_github_token, repo_full_name, pr_number, ai_review)
            return {"status": "review complete", "source": "GitHub API"}

        return {"error": "No AI review response"}

    except Exception as e:
        log(f"⚠️ API method failed: {e}")
        traceback.print_exc()

    # --------------------------------------------------------
    # Fallback: Git diff method
    # --------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="code_review_")
    try:
        subprocess.run(["git", "clone", repo_url, tmpdir], check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin"], cwd=tmpdir, check=True)

        diff_result = subprocess.run(
            ["git", "diff", f"origin/{base_branch}..origin/{head_branch}"],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )

        diff = diff_result.stdout.strip()
        if not diff:
            log("⚠️ No diff found between branches.")
            return {"status": "no diff detected"}

        log(f"✅ Diff generated ({len(diff)} chars)")
        ai_review = await run_ai_code_review(diff, pr_number)

        if ai_review:
            post_github_comment(x_github_token, repo_full_name, pr_number, ai_review)
            return {"status": "review complete", "source": "git diff"}

        return {"error": "No AI review response"}

    finally:
        safe_rmtree(tmpdir)
