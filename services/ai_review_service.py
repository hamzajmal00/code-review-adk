import uuid
import traceback
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from code_review_agent.agent import agent as code_review_agent
from utils.logger import log

DB_URL = "sqlite+aiosqlite:///code_review_sessions.db"
session_service = DatabaseSessionService(db_url=DB_URL)
runner = Runner(agent=code_review_agent, app_name="agents", session_service=session_service)

async def run_ai_code_review(diff: str, pr_number: int):
    """Send diff to AI agent and get structured feedback."""
    user_id = "github_auto_reviewer"
    session_id = f"pr_{pr_number}_{uuid.uuid4().hex[:8]}"
    final_response = None

    try:
        await session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )
        content = types.Content(
            role="user",
            parts=[types.Part(text=f"Review this code diff:\n\n{diff}")]
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            if getattr(event, "content", None) and getattr(event.content, "parts", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_response = part.text
        if final_response:
            log("✅ AI Review completed.")
            return final_response
        log("⚠️ No response from AI agent.")
    except Exception as e:
        log(f"❌ AI runner failed: {e}")
        traceback.print_exc()
    return None
