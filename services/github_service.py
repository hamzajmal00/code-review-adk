from github import Github
from utils.logger import log

def get_diff_via_api(token: str, repo_full_name: str, pr_number: int) -> str:
    """Fetch diff via GitHub API."""
    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    diff = ""
    for file in pr.get_files():
        if file.patch:
            diff += f"\n--- a/{file.filename}\n+++ b/{file.filename}\n{file.patch}\n"
    return diff

def post_github_comment(token: str, repo_full_name: str, pr_number: int, ai_review: str):
    """Post AI review as GitHub comment."""
    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    message = f"### 🤖 AI Code Review\n\n{ai_review}"
    pr.create_issue_comment(message)
    log("✅ Comment posted successfully.")
