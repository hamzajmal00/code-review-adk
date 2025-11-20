# services/github_service.py

import os
import time
import jwt
import requests
from utils.logger import log
from dotenv import load_dotenv

load_dotenv()

GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
GITHUB_PRIVATE_KEY = os.getenv("GITHUB_PRIVATE_KEY")
GITHUB_PRIVATE_KEY_PATH = os.getenv("GITHUB_PRIVATE_KEY_PATH")

# Load private key from file if not directly in env
if not GITHUB_PRIVATE_KEY and GITHUB_PRIVATE_KEY_PATH:
    with open(GITHUB_PRIVATE_KEY_PATH, "r", encoding="utf-8") as f:
        GITHUB_PRIVATE_KEY = f.read()

if not GITHUB_APP_ID:
    raise RuntimeError("GITHUB_APP_ID is not set")

if not GITHUB_PRIVATE_KEY:
    raise RuntimeError("GitHub App private key is not configured (GITHUB_PRIVATE_KEY or GITHUB_PRIVATE_KEY_PATH).")


def create_app_jwt() -> str:
    """
    Create a short-lived JWT for GitHub App authentication.
    Used only to request installation access tokens.
    """
    now = int(time.time())
    payload = {
        "iat": now - 60,         # issued at
        "exp": now + (10 * 60),  # max 10 minutes
        "iss": int(GITHUB_APP_ID),
    }

    encoded = jwt.encode(
        payload,
        GITHUB_PRIVATE_KEY,
        algorithm="RS256",
    )
    # pyjwt v2 returns str, v1 returns bytes
    if isinstance(encoded, bytes):
        encoded = encoded.decode("utf-8")
    return encoded


def create_installation_token(installation_id: int) -> str:
    """
    Exchange App JWT for an installation access token.
    This token is used in all GitHub API calls (PR diff, comments, etc.).
    """
    app_jwt = create_app_jwt()

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    log(f"🔑 Creating installation token for installation_id={installation_id}")

    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
        },
    )

    if res.status_code >= 400:
        log(f"❌ Failed to create installation token: {res.status_code} {res.text}")
        res.raise_for_status()

    data = res.json()
    token = data["token"]
    log("✅ Installation token created successfully")
    return token


def get_diff_via_api(installation_token: str, repo_full_name: str, pr_number: int) -> str:
    """
    Fetch PR diff via GitHub API using the installation access token.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    log(f"📥 Fetching diff for {repo_full_name} PR #{pr_number}")

    res = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {installation_token}",
            # This Accept header tells GitHub to return a unified diff
            "Accept": "application/vnd.github.v3.diff",
        },
    )

    if res.status_code >= 400:
        log(f"❌ Failed to fetch diff: {res.status_code} {res.text}")
        res.raise_for_status()

    diff = res.text or ""
    return diff


def post_github_comment(installation_token: str, repo_full_name: str, pr_number: int, body: str):
    """
    Post a normal PR comment (issue comment) using the installation access token.
    Appears as `your-app-name[bot]`.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    log(f"💬 Posting comment to {repo_full_name} PR #{pr_number}")

    res = requests.post(
        url,
        json={"body": body},
        headers={
            "Authorization": f"Bearer {installation_token}",
            "Accept": "application/vnd.github+json",
        },
    )

    if res.status_code >= 400:
        log(f"❌ Failed to post comment: {res.status_code} {res.text}")
        res.raise_for_status()

    log("✅ Comment posted successfully")
    return res.json()
