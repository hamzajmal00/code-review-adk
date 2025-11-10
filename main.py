import os
import subprocess
import tempfile
import pathlib
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from github import Github
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from code_review_agent.agent import agent as code_review_agent
import shutil
import stat

load_dotenv()

app = FastAPI()

DB_URL = os.getenv("DATABASE_URL", "sqlite:///code_review_sessions.db")
session_service = DatabaseSessionService(db_url=DB_URL)

runner = Runner(
    agent=code_review_agent,
    app_name="agents",
    session_service=session_service,
)

def remove_readonly(func, path, excinfo):
    """Error handler for Windows readonly files during rmtree."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"⚠️ Could not remove {path}: {e}")

def safe_rmtree(path):
    """Safely remove a directory tree, handling Windows permission issues."""
    try:
        shutil.rmtree(path, onerror=remove_readonly)
    except Exception as e:
        print(f"⚠️ Failed to clean up {path}: {e}")

@app.post("/webhook")
async def handle_pr_event(request: Request):
    """
    Handles GitHub webhook events for pull requests.
    """
    payload = await request.json()
    action = payload.get("action")
    pr = payload.get("pull_request", {})

    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": f"ignored action: {action}"}

    # --- Extract PR metadata ---
    repo_full_name = pr.get("head", {}).get("repo", {}).get("full_name")
    repo_url = pr.get("head", {}).get("repo", {}).get("clone_url")
    
    # Get BOTH head (source) and base (target) branches
    head_branch = pr.get("head", {}).get("ref")  # Branch with changes
    base_branch = pr.get("base", {}).get("ref")  # Target branch (e.g., 'main', 'develop')
    
    pr_number = pr.get("number")

    print(f"🔔 Triggered PR #{pr_number} for {repo_full_name} ({action})")
    print(f"📍 Comparing {head_branch} → {base_branch}")

    # --- Prepare authenticated clone URL ---
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Missing GITHUB_TOKEN in .env")
        return {"error": "Missing GITHUB_TOKEN"}

    if repo_url.startswith("https://github.com/"):
        repo_url = repo_url.replace("https://", f"https://{token}@")

    original_dir = os.getcwd()
    tmpdir = None
    
    # --- Try GitHub API first (more reliable) ---
    try:
        print("📡 Fetching diff from GitHub API...")
        gh = Github(token)
        repo = gh.get_repo(repo_full_name)
        pr_obj = repo.get_pull(pr_number)
        
        # Get files changed in the PR
        files = pr_obj.get_files()
        diff = ""
        
        for file in files:
            diff += f"\n--- a/{file.filename}\n+++ b/{file.filename}\n"
            if file.patch:  # patch contains the actual diff
                diff += file.patch + "\n"
        
        if diff.strip():
            print(f"✅ Diff fetched from API ({len(diff)} characters)")
            print("\n" + "="*80)
            print("📄 DIFF CONTENT:")
            print("="*80)
            print(diff)
            print("="*80 + "\n")
            
            # --- Run AI Code Review ---
            print("🤖 Running AI code review...")
            try:
                # Generate a unique session ID for this PR review
                import uuid
                user_id = "github_auto_reviewer"
                session_id = f"pr_{pr_number}_{uuid.uuid4().hex[:8]}"
                
                # Debug info
                print(f"Runner app_name: {runner.app_name}")
                print(f"User ID: {user_id}")
                print(f"Session ID: {session_id}")
                
                # Create the session first (AWAIT it!)
                print(f"Creating session...")
                try:
                    await session_service.create_session(
                        app_name=runner.app_name,
                        user_id=user_id,
                        session_id=session_id
                    )
                    print(f"✅ Session created successfully")
                except Exception as session_error:
                    print(f"⚠️ Session creation error: {session_error}")
                    import traceback
                    traceback.print_exc()
                    return {"error": f"Session creation failed: {session_error}"}
                
                content = types.Content(
                    role="user",
                    parts=[types.Part(text=f"Review the following code diff and provide structured feedback:\n\n{diff}")]
                )
                
                final_response = None
                
                print(f"Starting runner.run_async...")
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content
                ):
                    print(f"Event received: {type(event).__name__}")
                    # Get the final response from the agent
                    if hasattr(event, 'content') and event.content:
                        if hasattr(event.content, 'parts') and event.content.parts:
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    final_response = part.text
                                    print(f"Got response: {final_response[:100]}...")
                
                if not final_response:
                    print("⚠️ No response from AI agent")
                    return {"error": "No response from AI agent"}
                
                print(f"✅ AI Review completed ({len(final_response)} characters)")
                
            except Exception as e:
                print(f"❌ AI runner failed: {e}")
                import traceback
                traceback.print_exc()
                return {"error": str(e)}

            # --- Format Review Output ---
            # Post the AI response directly as the review
            message = f"### 🤖 AI Code Review\n\n{final_response}"

            # --- Post Review to GitHub ---
            print("💬 Posting review to GitHub...")
            try:
                pr_obj.create_issue_comment(message)
                print("✅ Review comment posted successfully.")
            except Exception as e:
                print(f"❌ GitHub comment error: {e}")
                return {"error": str(e)}

            return {
                "status": "review complete",
                "repo": repo_full_name,
                "pr": pr_number,
                "head": head_branch,
                "base": base_branch,
                "files_changed": len(list(files))
            }
        else:
            print("⚠️ No diff found via API, falling back to Git...")
            
    except Exception as e:
        print(f"⚠️ GitHub API method failed ({e}), falling back to Git...")
    
    # --- Fallback: Use Git if API fails ---
    try:
        # --- Clone repository ---
        tmpdir = tempfile.mkdtemp(prefix="code_review_")
        
        print(f"📦 Cloning repository...")
        try:
            # Clone with full history to ensure we get all commits
            subprocess.run(
                ["git", "clone", repo_url, tmpdir],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Git clone failed:\n{e.stderr}")
            return {"error": f"Git clone failed: {e.stderr}"}

        # --- Checkout head branch ---
        print(f"🌿 Checking out {head_branch}...")
        try:
            subprocess.run(
                ["git", "checkout", head_branch],
                cwd=tmpdir,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Branch checkout failed:\n{e.stderr}")
            return {"error": f"Branch checkout failed: {e.stderr}"}

        # --- Generate diff between head and base ---
        print(f"📊 Generating diff: origin/{base_branch}..origin/{head_branch}")
        try:
            # Try two-dot diff first (shows all changes between branches)
            diff_process = subprocess.run(
                ["git", "diff", f"origin/{base_branch}..origin/{head_branch}"],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            diff = diff_process.stdout.strip()
            
            # If no diff, try alternative method
            if not diff:
                print("⚠️ Trying alternative diff method...")
                diff_process = subprocess.run(
                    ["git", "diff", f"origin/{base_branch}", f"origin/{head_branch}"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True
                )
                diff = diff_process.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"❌ Git diff failed:\n{e.stderr}")
            return {"error": f"Git diff failed: {e.stderr}"}

        if not diff:
            print("⚠️ No diff found between branches.")
            # Get commit info for debugging
            try:
                log_process = subprocess.run(
                    ["git", "log", "--oneline", f"origin/{base_branch}..{head_branch}"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True
                )
                commits = log_process.stdout.strip()
                if commits:
                    print(f"📝 Commits found:\n{commits}")
                else:
                    print("📝 No new commits in this branch.")
            except:
                pass
            
            return {"status": "no diff detected", "head": head_branch, "base": base_branch}

        print(f"✅ Diff generated ({len(diff)} characters)")

        # --- Run AI Code Review ---
        print("🤖 Running AI code review...")
        try:
            # Use a unique session ID or None to create a new session
            session_id = None  # This will create a new session each time
            
            content = types.Content(
                role="user",
                parts=[types.Part(text=f"Review the following code diff and provide structured feedback:\n\n{diff}")]
            )
            
            final_response = None
            async for event in runner.run_async(
                user_id="github_auto_reviewer",
                session_id=session_id,
                new_message=content
            ):
                # Get the final response from the agent
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts') and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                final_response = part.text
            
            if not final_response:
                print("⚠️ No response from AI agent")
                return {"error": "No response from AI agent"}
            
            print(f"✅ AI Review completed ({len(final_response)} characters)")
            print("\n" + "="*80)
            print("📝 AI REVIEW RESPONSE:")
            print("="*80)
            print(final_response)
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"❌ AI runner failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

        # --- Format Review Output ---
        # Post the AI response directly as the review
        message = f"### 🤖 AI Code Review\n\n{final_response}"

        # --- Post Review to GitHub ---
        try:
            gh = Github(token)
            repo = gh.get_repo(repo_full_name)
            pr_obj = repo.get_pull(pr_number)
            pr_obj.create_issue_comment(message)
            print("✅ Review comment posted successfully.")
        except Exception as e:
            print(f"❌ GitHub comment error: {e}")
            return {"error": str(e)}

        return {
            "status": "review complete",
            "repo": repo_full_name,
            "pr": pr_number,
            "head": head_branch,
            "base": base_branch
        }
    
    finally:
        os.chdir(original_dir)
        if tmpdir and os.path.exists(tmpdir):
            safe_rmtree(tmpdir)