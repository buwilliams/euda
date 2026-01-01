"""
User Tools - Access user profile and lifelog.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List

from . import tool


DATA_DIR = Path(__file__).parent.parent.parent / "data"
USER_DIR = DATA_DIR / "user"


def _ensure_user_dir():
    """Ensure user directory exists."""
    USER_DIR.mkdir(parents=True, exist_ok=True)
    (USER_DIR / "lifelog").mkdir(exist_ok=True)


@tool("get_user_profile", "Get the user's profile")
def get_user_profile() -> dict:
    """Get the user's profile."""
    _ensure_user_dir()

    profile_path = USER_DIR / "user-profile.md"
    if profile_path.exists():
        return {
            "content": profile_path.read_text(),
            "exists": True
        }
    return {
        "content": "",
        "exists": False
    }


@tool("update_user_profile", "Update the user's profile")
def update_user_profile(content: str) -> dict:
    """Update the user's profile."""
    _ensure_user_dir()

    profile_path = USER_DIR / "user-profile.md"
    profile_path.write_text(content)

    return {"status": "updated"}


@tool("read_lifelog", "Read lifelog entries for a date or date range")
def read_lifelog(date: str = None) -> dict:
    """Read lifelog entries.

    Args:
        date: Specific date (YYYY-MM-DD) or None for today
    """
    _ensure_user_dir()

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    lifelog_path = USER_DIR / "lifelog" / f"{date}.md"

    if lifelog_path.exists():
        return {
            "date": date,
            "content": lifelog_path.read_text(),
            "exists": True
        }
    return {
        "date": date,
        "content": "",
        "exists": False
    }


@tool("write_lifelog", "Add an entry to the lifelog")
def write_lifelog(content: str, date: str = None) -> dict:
    """Add an entry to the lifelog.

    Args:
        content: The content to add
        date: Specific date (YYYY-MM-DD) or None for today
    """
    _ensure_user_dir()

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    lifelog_dir = USER_DIR / "lifelog"
    lifelog_dir.mkdir(exist_ok=True)

    lifelog_path = lifelog_dir / f"{date}.md"
    timestamp = datetime.now().strftime("%H:%M")

    # Append to existing or create new
    if lifelog_path.exists():
        existing = lifelog_path.read_text()
        new_content = f"{existing}\n\n## {timestamp}\n\n{content}"
    else:
        new_content = f"# Lifelog - {date}\n\n## {timestamp}\n\n{content}"

    lifelog_path.write_text(new_content)

    return {"date": date, "status": "added"}


@tool("list_lifelog_dates", "List all dates with lifelog entries")
def list_lifelog_dates() -> List[str]:
    """List all dates that have lifelog entries."""
    _ensure_user_dir()

    lifelog_dir = USER_DIR / "lifelog"
    if not lifelog_dir.exists():
        return []

    dates = []
    for path in lifelog_dir.glob("*.md"):
        # Extract date from filename (YYYY-MM-DD.md)
        dates.append(path.stem)

    dates.sort(reverse=True)
    return dates
