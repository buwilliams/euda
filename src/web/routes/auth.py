"""
Authentication routes for Euno web API.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..auth import (
    is_password_set, authenticate, validate_session,
    invalidate_session, verify_password, set_password, _load_auth_data
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_session_token(request: Request) -> str | None:
    """Extract session token from cookie or Authorization header."""
    token = request.cookies.get("euno_session")
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate with password and get session token."""
    if not is_password_set():
        raise HTTPException(status_code=400, detail="No password configured. Use CLI to set password.")

    token = authenticate(request.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid password")

    response = JSONResponse(content={"success": True, "message": "Login successful"})
    response.set_cookie(
        key="euno_session",
        value=token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,  # 30 days
        samesite="lax",
        path="/"
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    """Invalidate session and clear cookie."""
    token = get_session_token(request)
    if token:
        invalidate_session(token)

    response = JSONResponse(content={"success": True, "message": "Logged out"})
    response.delete_cookie("euno_session")
    return response


@router.get("/check")
async def check_auth(request: Request):
    """Check if current session is authenticated."""
    if not is_password_set():
        return {"authenticated": True, "password_required": False}

    token = get_session_token(request)
    if token and validate_session(token):
        return {"authenticated": True, "password_required": True}

    return {"authenticated": False, "password_required": True}


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest):
    """Change password (requires current password)."""
    if not is_password_set():
        raise HTTPException(status_code=400, detail="No password configured")

    auth_data = _load_auth_data()
    stored_hash = auth_data.get("password_hash", "")
    if not verify_password(request.current_password, stored_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    if len(request.new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")

    result = set_password(request.new_password)
    return {"success": True, "message": result}
