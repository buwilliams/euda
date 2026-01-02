"""
Authentication - Simple password-based auth for the API.

Password is stored as a bcrypt hash in data/system/auth.json.
"""

import json
import secrets
from pathlib import Path
from typing import Optional

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


DATA_DIR = Path(__file__).parent.parent / "data"
AUTH_FILE = DATA_DIR / "system" / "auth.json"


def _ensure_system_dir():
    """Ensure system directory exists."""
    (DATA_DIR / "system").mkdir(parents=True, exist_ok=True)


def _load_auth() -> dict:
    """Load auth config."""
    if AUTH_FILE.exists():
        with open(AUTH_FILE) as f:
            return json.load(f)
    return {}


def _save_auth(auth: dict):
    """Save auth config."""
    _ensure_system_dir()
    with open(AUTH_FILE, "w") as f:
        json.dump(auth, f, indent=2)


def is_password_set() -> bool:
    """Check if a password has been set."""
    auth = _load_auth()
    return bool(auth.get("password_hash"))


def set_password(password: str) -> bool:
    """Set the password (stores bcrypt hash)."""
    if not BCRYPT_AVAILABLE:
        raise RuntimeError("bcrypt not installed. Run: pip install bcrypt")

    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters")

    # Generate bcrypt hash
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    auth = _load_auth()
    auth["password_hash"] = password_hash
    _save_auth(auth)

    return True


def verify_password(password: str) -> bool:
    """Verify a password against the stored hash."""
    if not BCRYPT_AVAILABLE:
        return True  # No auth if bcrypt not available

    auth = _load_auth()
    password_hash = auth.get("password_hash")

    if not password_hash:
        return True  # No password set, allow access

    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


def create_session_token() -> str:
    """Create a new session token."""
    return secrets.token_urlsafe(32)


# Session storage (in-memory for simplicity)
_sessions: set = set()


def create_session() -> str:
    """Create and store a new session."""
    token = create_session_token()
    _sessions.add(token)
    return token


def verify_session(token: str) -> bool:
    """Verify a session token is valid."""
    if not is_password_set():
        return True  # No auth required if no password
    return token in _sessions


def invalidate_session(token: str):
    """Invalidate a session token."""
    _sessions.discard(token)


def remove_password():
    """Remove the password (disables authentication)."""
    auth = _load_auth()
    if "password_hash" in auth:
        del auth["password_hash"]
        _save_auth(auth)
    # Clear all sessions
    _sessions.clear()
