"""
FastAPI Web Application

Provides REST API for the Euno system.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .routes import jobs, agents, chat, user, auth, system, upload, transcribe, synthesize, rate_limiting, patterns
from .routes.auth import get_session_token
from ..auth import is_password_set, verify_session
from ..events import trigger_shutdown


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/api/auth/check",
    "/api/auth/login",
    "/api/health",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown."""
    # Startup
    yield
    # Shutdown - signal all SSE connections to close
    trigger_shutdown()


app = FastAPI(
    title="Euno",
    description="Personal Intelligence System",
    version="3.0.0",
    lifespan=lifespan
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Check authentication for protected routes."""
    path = request.url.path

    # Allow public paths
    if path in PUBLIC_PATHS:
        return await call_next(request)

    # Allow web files
    if path.startswith("/web"):
        return await call_next(request)

    # If no password set, allow all
    if not is_password_set():
        return await call_next(request)

    # Check session
    token = get_session_token(request)
    if not token or not verify_session(token):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"}
        )

    return await call_next(request)


# Include routers
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(patterns.router, prefix="/api/agents", tags=["patterns"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(transcribe.router, prefix="/api/transcribe", tags=["transcribe"])
app.include_router(synthesize.router, prefix="/api/synthesize", tags=["synthesize"])
app.include_router(rate_limiting.router, prefix="/api/rate-limiting", tags=["rate-limiting"])

# Serve web files
web_dir = Path(__file__).parent.parent.parent / "web"
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")

    @app.get("/")
    def serve_index():
        return FileResponse(web_dir / "index.html")
