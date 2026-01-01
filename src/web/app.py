"""
FastAPI Web Application

Provides REST API for the Euno system.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .routes import jobs, agents, chat, user


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

# Serve static files
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "3.0.0"}
