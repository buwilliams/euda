"""Web skill storage for watches and snapshots."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def _get_skill_dir() -> Path:
    """Get the skill data directory."""
    data_dir = os.environ.get("EUNO_DATA_DIR")
    if data_dir:
        base = Path(data_dir)
    else:
        base = Path(__file__).parent.parent.parent.parent / "data"

    skill_dir = base / "skills" / "web"
    skill_dir.mkdir(parents=True, exist_ok=True)
    return skill_dir


def _get_watches_path() -> Path:
    """Get path to watches storage file."""
    return _get_skill_dir() / "watches.json"


def _get_snapshots_dir() -> Path:
    """Get path to snapshots directory."""
    snapshots_dir = _get_skill_dir() / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    return snapshots_dir


def _get_config_path() -> Path:
    """Get path to config file."""
    return _get_skill_dir() / "config.json"


def _generate_watch_id(url: str) -> str:
    """Generate a short ID from URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:8]


def load_config() -> dict:
    """Load skill configuration."""
    config_path = _get_config_path()
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {
        "default_check_interval_hours": 24,
        "min_check_interval_hours": 1,
        "max_check_interval_hours": 168,
        "snapshot_max_size_kb": 500,
        "user_agent": "Euno/1.0 (Web Skill)",
    }


def save_config(config: dict) -> None:
    """Save skill configuration."""
    config_path = _get_config_path()
    config_path.write_text(json.dumps(config, indent=2) + "\n")


def load_watches() -> list[dict]:
    """Load all watches."""
    watches_path = _get_watches_path()
    if watches_path.exists():
        data = json.loads(watches_path.read_text())
        return data.get("watches", [])
    return []


def save_watches(watches: list[dict]) -> None:
    """Save watches list."""
    watches_path = _get_watches_path()
    watches_path.write_text(json.dumps({"watches": watches}, indent=2) + "\n")


def get_watch(watch_id: str) -> Optional[dict]:
    """Get a specific watch by ID."""
    watches = load_watches()
    for watch in watches:
        if watch.get("id") == watch_id:
            return watch
    return None


def get_watch_by_url(url: str) -> Optional[dict]:
    """Get a watch by URL."""
    watches = load_watches()
    for watch in watches:
        if watch.get("url") == url:
            return watch
    return None


def add_watch(
    url: str,
    name: str,
    check_interval_hours: int = 24,
    credentials_id: Optional[str] = None,
) -> dict:
    """Add a new watch.

    Args:
        url: URL to monitor
        name: Display name
        check_interval_hours: Check interval
        credentials_id: Optional credential ID (for future use)

    Returns:
        The created watch dict or error dict
    """
    watches = load_watches()

    # Check if already exists
    existing = get_watch_by_url(url)
    if existing:
        return {"error": f"Watch already exists with ID: {existing['id']}"}

    watch_id = _generate_watch_id(url)

    watch = {
        "id": watch_id,
        "url": url,
        "name": name,
        "credentials_id": credentials_id,
        "check_interval_hours": check_interval_hours,
        "added_at": datetime.now().isoformat(),
        "last_checked": None,
        "last_changed": None,
        "check_count": 0,
        "change_count": 0,
        "last_error": None,
        "error_count": 0,
    }

    watches.append(watch)
    save_watches(watches)

    return watch


def update_watch(watch_id: str, updates: dict) -> Optional[dict]:
    """Update a watch's metadata.

    Args:
        watch_id: Watch ID to update
        updates: Dict of fields to update

    Returns:
        Updated watch or None if not found
    """
    watches = load_watches()

    for i, watch in enumerate(watches):
        if watch.get("id") == watch_id:
            # Don't allow changing id or url
            updates.pop("id", None)
            updates.pop("url", None)
            watches[i].update(updates)
            save_watches(watches)
            return watches[i]

    return None


def remove_watch(watch_id: str) -> bool:
    """Remove a watch.

    Args:
        watch_id: Watch ID to remove

    Returns:
        True if removed, False if not found
    """
    watches = load_watches()
    original_count = len(watches)

    watches = [w for w in watches if w.get("id") != watch_id]

    if len(watches) < original_count:
        save_watches(watches)
        # Also clean up snapshot
        snapshot_path = _get_snapshots_dir() / f"{watch_id}.txt"
        if snapshot_path.exists():
            snapshot_path.unlink()
        return True

    return False


def load_snapshot(watch_id: str) -> Optional[str]:
    """Load the content snapshot for a watch.

    Args:
        watch_id: Watch ID

    Returns:
        Snapshot content or None if not found
    """
    snapshot_path = _get_snapshots_dir() / f"{watch_id}.txt"
    if snapshot_path.exists():
        return snapshot_path.read_text()
    return None


def save_snapshot(watch_id: str, content: str) -> None:
    """Save a content snapshot for a watch.

    Args:
        watch_id: Watch ID
        content: Plain text content to save
    """
    config = load_config()
    max_size = config.get("snapshot_max_size_kb", 500) * 1024

    # Truncate if too large
    if len(content.encode("utf-8")) > max_size:
        content = content[:max_size]

    snapshot_path = _get_snapshots_dir() / f"{watch_id}.txt"
    snapshot_path.write_text(content)
