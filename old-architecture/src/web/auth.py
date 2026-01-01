"""
Euno - Authentication Module

Simple password-based authentication with session tokens.
Password stored as bcrypt hash in flat file.
"""

import json
import secrets
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Auth storage location
AUTH_DIR = Path(__file__).parent.parent.parent / "data" / "shared" / "state" / "auth"
AUTH_FILE = AUTH_DIR / "auth.json"

# Session config
SESSION_DURATION_DAYS = 30
TOKEN_LENGTH = 32

# In-memory session cache
_sessions: dict[str, dict] = {}


def _ensure_auth_dir():
    """Ensure auth directory exists."""
    AUTH_DIR.mkdir(parents=True, exist_ok=True)


def _load_auth_data() -> dict:
    """Load auth data from file."""
    _ensure_auth_dir()
    if AUTH_FILE.exists():
        with open(AUTH_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_auth_data(data: dict):
    """Save auth data to file."""
    _ensure_auth_dir()
    with open(AUTH_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    if ':' not in stored_hash:
        return False
    salt, hashed = stored_hash.split(':', 1)
    check_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return secrets.compare_digest(hashed, check_hash)


def is_password_set() -> bool:
    """Check if a password has been configured."""
    data = _load_auth_data()
    return bool(data.get("password_hash"))


def set_password(password: str) -> str:
    """Set or update the password."""
    if len(password) < 4:
        return "Error: Password must be at least 4 characters"

    data = _load_auth_data()
    data["password_hash"] = hash_password(password)
    data["updated"] = datetime.now().isoformat()
    _save_auth_data(data)

    # Invalidate all existing sessions
    data["sessions"] = {}
    _save_auth_data(data)
    _sessions.clear()

    return "Password set successfully"


def authenticate(password: str) -> Optional[str]:
    """
    Authenticate with password, return session token if valid.
    Returns None if authentication fails.
    """
    data = _load_auth_data()
    stored_hash = data.get("password_hash")

    if not stored_hash:
        return None

    if not verify_password(password, stored_hash):
        return None

    # Generate session token
    token = secrets.token_urlsafe(TOKEN_LENGTH)
    expires = datetime.now() + timedelta(days=SESSION_DURATION_DAYS)

    # Store session
    session_data = {
        "created": datetime.now().isoformat(),
        "expires": expires.isoformat(),
    }

    # Save to file (for persistence across restarts)
    if "sessions" not in data:
        data["sessions"] = {}
    data["sessions"][token] = session_data
    _save_auth_data(data)

    # Cache in memory
    _sessions[token] = session_data

    return token


def validate_session(token: str) -> bool:
    """Check if a session token is valid."""
    if not token:
        return False

    # Check memory cache first
    if token in _sessions:
        session = _sessions[token]
        expires = datetime.fromisoformat(session["expires"])
        if datetime.now() < expires:
            return True
        else:
            # Expired, remove from cache
            del _sessions[token]

    # Check file storage
    data = _load_auth_data()
    sessions = data.get("sessions", {})

    if token in sessions:
        session = sessions[token]
        expires = datetime.fromisoformat(session["expires"])
        if datetime.now() < expires:
            # Cache for future checks
            _sessions[token] = session
            return True
        else:
            # Expired, clean up
            del sessions[token]
            _save_auth_data(data)

    return False


def invalidate_session(token: str):
    """Invalidate a session token."""
    if token in _sessions:
        del _sessions[token]

    data = _load_auth_data()
    if token in data.get("sessions", {}):
        del data["sessions"][token]
        _save_auth_data(data)


def cleanup_expired_sessions():
    """Remove expired sessions from storage."""
    data = _load_auth_data()
    sessions = data.get("sessions", {})
    now = datetime.now()

    expired = [
        token for token, session in sessions.items()
        if datetime.fromisoformat(session["expires"]) < now
    ]

    for token in expired:
        del sessions[token]
        if token in _sessions:
            del _sessions[token]

    if expired:
        _save_auth_data(data)

    return len(expired)
