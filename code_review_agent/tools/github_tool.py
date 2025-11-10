# tools/github_tool.py
import os
from github import Github
from typing import Dict

def post_github_comment(pr_number: int, message: str, repo_full_name: str) -> Dict:
    """
    ADK Tool: Posts a comment on a specific GitHub Pull Request.

    Parameters:
    - pr_number (int): Pull Request number.
    - message (str): Text or markdown comment to post.
    - repo_full_name (str): e.g. "username/repo"

    Returns:
    - dict: Status response
    """
    try:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return {"error": "Missing GITHUB_TOKEN"}

        g = Github(token)
        repo = g.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(message)

        return {"status": "Comment posted successfully", "success": True}

    except Exception as e:
        return {"error": str(e), "success": False}
