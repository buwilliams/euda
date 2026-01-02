"""
Auth API Routes
"""

from fastapi import APIRouter, Request, Response, HTTPException
from pydantic import BaseModel

from ...auth import (
    is_password_set, verify_password, create_session,
    verify_session, invalidate_session
)


router = APIRouter()


class LoginRequest(BaseModel):
    password: str


def get_session_token(request: Request) -> str | None:
    """Extract session token from cookie or header."""
    token = request.cookies.get("session")
    if token:
        return token
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return None


def require_auth(request: Request):
    """Dependency that requires authentication."""
    if not is_password_set():
        return True
    token = get_session_token(request)
    if not token or not verify_session(token):
        raise HTTPException(status_code=401, detail="Authentication required")
    return True


@router.get("/check")
def auth_check(request: Request):
    """Check authentication status."""
    password_required = is_password_set()
    if not password_required:
        return {"authenticated": True, "password_required": False}

    token = get_session_token(request)
    authenticated = token is not None and verify_session(token)
    return {"authenticated": authenticated, "password_required": True}


@router.post("/login")
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


@router.post("/logout")
def auth_logout(request: Request, response: Response):
    """Logout and invalidate session."""
    token = get_session_token(request)
    if token:
        invalidate_session(token)
    response.delete_cookie("session")
    return {"success": True}
