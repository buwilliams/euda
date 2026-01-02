"""
FastAPI Web Application

Provides REST API for the Euno system.
"""

import asyncio
import json
import random
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pathlib import Path
from pydantic import BaseModel

from .routes import jobs, agents, chat, user
from ..tools.jobs import list_jobs


app = FastAPI(
    title="Euno",
    description="Personal Intelligence System",
    version="3.0.0"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(user.router, prefix="/api/user", tags=["user"])


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "3.0.0"}


@app.get("/api/about")
def get_about():
    """Get about/pitch content for the About tab."""
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    pitch_file = docs_dir / "1_pitch.md"

    if pitch_file.exists():
        return {"content": pitch_file.read_text()}
    return {"content": "# Euno\n\nPersonal Intelligence System"}


# ============== Conversations ==============

import re

@app.get("/api/conversations/recent/structured")
def get_recent_conversations(count: int = 20):
    """Get recent conversations for history tab."""
    conversations = []

    # Look for conversation files in the friend agent's state (used by web UI)
    conv_dir = Path(__file__).parent.parent.parent / "data" / "agents" / "friend" / "state" / "conversation"

    if conv_dir.exists():
        # Get all markdown files, sorted by date descending
        files = sorted(conv_dir.glob("*.md"), reverse=True)[:count]

        for file in files:
            date_str = file.stem  # e.g., "2024-01-15"
            content = file.read_text()

            # Extract first timestamp and preview from content
            time_match = re.search(r'\((\d{2}:\d{2}):\d{2}\)', content)
            time_str = time_match.group(1) if time_match else "00:00"

            # Get preview from first user message
            preview = ""
            user_match = re.search(r'## User \([^)]+\)\n\n(.+?)(?:\n\n##|\Z)', content, re.DOTALL)
            if user_match:
                preview = user_match.group(1).strip()[:100]

            # Count messages (## headers)
            message_count = len(re.findall(r'^## (User|Assistant)', content, re.MULTILINE))

            conversations.append({
                "session_id": date_str,
                "date": date_str,
                "time": time_str,
                "preview": preview,
                "message_count": message_count
            })

    return {"conversations": conversations}


class ForkRequest(BaseModel):
    session_id: str


@app.post("/api/conversations/fork")
def fork_conversation(request: ForkRequest):
    """Load a past conversation to continue it."""
    conv_dir = Path(__file__).parent.parent.parent / "data" / "agents" / "friend" / "state" / "conversation"
    conv_file = conv_dir / f"{request.session_id}.md"

    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    content = conv_file.read_text()
    messages = []

    # Parse markdown format: ## User (HH:MM:SS) or ## Assistant (HH:MM:SS)
    parts = re.split(r'^## (User|Assistant) \([^)]+\)\n\n', content, flags=re.MULTILINE)

    # parts will be: ['', 'User', 'message1', 'Assistant', 'message2', ...]
    i = 1
    while i < len(parts) - 1:
        role = parts[i].lower()
        msg_content = parts[i + 1].strip()
        if msg_content:
            messages.append({"role": role, "content": msg_content})
        i += 2

    return {
        "new_session_id": request.session_id,
        "messages": messages
    }


# ============== Auth ==============

from fastapi import Request, Response, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..auth import (
    is_password_set, verify_password, create_session,
    verify_session, invalidate_session
)

security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    password: str


def get_session_token(request: Request) -> str | None:
    """Extract session token from cookie or header."""
    # Try cookie first
    token = request.cookies.get("session")
    if token:
        return token
    # Try Authorization header
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return None


def require_auth(request: Request):
    """Dependency that requires authentication."""
    if not is_password_set():
        return True  # No auth required
    token = get_session_token(request)
    if not token or not verify_session(token):
        raise HTTPException(status_code=401, detail="Authentication required")
    return True


@app.get("/api/auth/check")
def auth_check(request: Request):
    """Check authentication status."""
    password_required = is_password_set()
    if not password_required:
        return {"authenticated": True, "password_required": False}

    token = get_session_token(request)
    authenticated = token is not None and verify_session(token)
    return {"authenticated": authenticated, "password_required": True}


@app.post("/api/auth/login")
def auth_login(request_body: LoginRequest, response: Response):
    """Login with password."""
    if not is_password_set():
        return {"success": True, "message": "No password required"}

    if not verify_password(request_body.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_session()
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="strict",
        max_age=86400 * 30  # 30 days
    )
    return {"success": True}


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    """Logout and invalidate session."""
    token = get_session_token(request)
    if token:
        invalidate_session(token)
    response.delete_cookie("session")
    return {"success": True}


# ============== Daily Quote ==============

QUOTES = [
    {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"quote": "Be yourself; everyone else is already taken.", "author": "Oscar Wilde"},
    {"quote": "The unexamined life is not worth living.", "author": "Socrates"},
    {"quote": "In the middle of difficulty lies opportunity.", "author": "Albert Einstein"},
    {"quote": "What you are is what you have been. What you'll be is what you do now.", "author": "Buddha"},
    {"quote": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
    {"quote": "We suffer more often in imagination than in reality.", "author": "Seneca"},
    {"quote": "The obstacle is the way.", "author": "Marcus Aurelius"},
]


@app.get("/api/daily-quote")
def daily_quote():
    """Get a daily quote."""
    return random.choice(QUOTES)


# ============== SSE Events ==============

async def event_generator():
    """Generate SSE events for real-time updates."""
    # Send initial data
    all_jobs = list_jobs()
    yield f"event: init\ndata: {json.dumps({'jobs': all_jobs})}\n\n"

    # Keep connection alive with pings
    while True:
        await asyncio.sleep(30)
        yield f"event: ping\ndata: {{}}\n\n"


@app.get("/api/events")
async def events():
    """SSE endpoint for real-time updates."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============== Settings (simplified) ==============

@app.get("/api/settings")
def get_settings():
    """Get settings - minimal for v3."""
    return {
        "llm": {
            "default_provider": "anthropic",
            "providers": {
                "anthropic": {"default_model": "claude-sonnet-4-20250514"}
            }
        }
    }


# Serve static files
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from fastapi.responses import FileResponse

    @app.get("/")
    def serve_index():
        return FileResponse(static_dir / "index.html")
