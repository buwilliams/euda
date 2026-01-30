"""
Conflicts - Conflict detection, storage, and resolution.

Conflicts are stored in data/system/sync/conflicts/{timestamp}-{type}.json
and tracked until resolved by the user.
"""

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Optional, List, Any, Dict


DATA_DIR = Path(__file__).parent.parent.parent / "data"
CONFLICTS_DIR = DATA_DIR / "system" / "sync" / "conflicts"


class ConflictType(str, Enum):
    """Types of sync conflicts."""
    TOPICS = "topics"
    TOPIC_LOGS = "topic_logs"
    MEMORY_SHORT_TERM = "memory_short_term"
    MEMORY_LONG_TERM = "memory_long_term"
    AGENT_CONFIG = "agent_config"
    AGENT_IDENTITY = "agent_identity"
    SYSTEM_CONFIG = "system_config"
    FILE = "file"


class Resolution(str, Enum):
    """Conflict resolution strategies."""
    KEEP_LOCAL = "keep_local"
    KEEP_REMOTE = "keep_remote"
    KEEP_BOTH = "keep_both"  # For things like topics: duplicate with new ID
    KEEP_NEWEST = "keep_newest"  # Auto-resolve using timestamps
    MERGE = "merge"  # For JSON: deep merge


@dataclass
class Conflict:
    """A sync conflict that needs resolution."""
    id: str
    type: ConflictType
    detected_at: str
    item_id: str  # ID of the conflicting item (topic ID, file path, etc.)
    description: str
    local: Any  # Local version of the data
    remote: Any  # Remote version of the data
    local_timestamp: Optional[str] = None
    remote_timestamp: Optional[str] = None
    resolution: Optional[Resolution] = None
    resolved_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, ConflictType) else self.type,
            "detected_at": self.detected_at,
            "item_id": self.item_id,
            "description": self.description,
            "local": self.local,
            "remote": self.remote,
            "local_timestamp": self.local_timestamp,
            "remote_timestamp": self.remote_timestamp,
            "resolution": self.resolution.value if self.resolution else None,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conflict":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=ConflictType(data["type"]),
            detected_at=data["detected_at"],
            item_id=data["item_id"],
            description=data["description"],
            local=data["local"],
            remote=data["remote"],
            local_timestamp=data.get("local_timestamp"),
            remote_timestamp=data.get("remote_timestamp"),
            resolution=Resolution(data["resolution"]) if data.get("resolution") else None,
            resolved_at=data.get("resolved_at"),
        )


def _ensure_conflicts_dir():
    """Ensure conflicts directory exists."""
    CONFLICTS_DIR.mkdir(parents=True, exist_ok=True)


def _find_existing_conflict(item_id: str, conflict_type: ConflictType) -> Optional[tuple]:
    """Find an existing unresolved conflict for the same item_id and type.

    Returns:
        Tuple of (filepath, Conflict) if found, None otherwise
    """
    for filepath in CONFLICTS_DIR.glob("*.json"):
        try:
            with open(filepath) as f:
                data = json.load(f)
            if (data.get("item_id") == item_id
                    and data.get("type") == conflict_type.value
                    and data.get("resolution") is None):
                return filepath, Conflict.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return None


def create_conflict(
    conflict_type: ConflictType,
    item_id: str,
    description: str,
    local: Any,
    remote: Any,
    local_timestamp: str = None,
    remote_timestamp: str = None,
) -> Conflict:
    """Create and save a new conflict, or update an existing one for the same item.

    If an unresolved conflict already exists for the same item_id and type,
    it is updated in-place instead of creating a duplicate.

    Args:
        conflict_type: Type of conflict
        item_id: ID of the conflicting item
        description: Human-readable description
        local: Local version of the data
        remote: Remote version of the data
        local_timestamp: When local version was last modified
        remote_timestamp: When remote version was last modified

    Returns:
        The created or updated Conflict
    """
    _ensure_conflicts_dir()

    # Check for existing unresolved conflict on the same item_id and type
    existing = _find_existing_conflict(item_id, conflict_type)
    if existing:
        filepath, conflict = existing
        # Update in-place: refresh data, clear any stale resolution
        now = datetime.now(UTC)
        conflict.detected_at = now.isoformat().replace("+00:00", "Z")
        conflict.description = description
        conflict.local = local
        conflict.remote = remote
        conflict.local_timestamp = local_timestamp
        conflict.remote_timestamp = remote_timestamp
        conflict.resolution = None
        conflict.resolved_at = None

        with open(filepath, "w") as f:
            json.dump(conflict.to_dict(), f, indent=2)

        return conflict

    now = datetime.now(UTC)
    timestamp_str = now.strftime("%Y%m%d-%H%M%S")
    conflict_id = f"conflict-{uuid.uuid4().hex[:8]}"

    conflict = Conflict(
        id=conflict_id,
        type=conflict_type,
        detected_at=now.isoformat().replace("+00:00", "Z"),
        item_id=item_id,
        description=description,
        local=local,
        remote=remote,
        local_timestamp=local_timestamp,
        remote_timestamp=remote_timestamp,
    )

    # Save to file
    filename = f"{timestamp_str}-{conflict_type.value}-{conflict_id}.json"
    filepath = CONFLICTS_DIR / filename
    with open(filepath, "w") as f:
        json.dump(conflict.to_dict(), f, indent=2)

    return conflict


def list_conflicts(resolved: bool = False) -> List[Conflict]:
    """List all conflicts.

    Args:
        resolved: If True, include resolved conflicts; if False, only unresolved

    Returns:
        List of Conflict objects, newest first
    """
    _ensure_conflicts_dir()

    conflicts = []
    for filepath in sorted(CONFLICTS_DIR.glob("*.json"), reverse=True):
        try:
            with open(filepath) as f:
                data = json.load(f)
            conflict = Conflict.from_dict(data)

            # Filter by resolution status
            if resolved or conflict.resolution is None:
                conflicts.append(conflict)
        except (json.JSONDecodeError, KeyError):
            continue

    return conflicts


def get_conflict(conflict_id: str) -> Optional[Conflict]:
    """Get a specific conflict by ID.

    Args:
        conflict_id: The conflict ID

    Returns:
        Conflict or None if not found
    """
    _ensure_conflicts_dir()

    for filepath in CONFLICTS_DIR.glob(f"*-{conflict_id}.json"):
        try:
            with open(filepath) as f:
                data = json.load(f)
            return Conflict.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            continue

    return None


def resolve_conflict(
    conflict_id: str,
    resolution: Resolution,
) -> Optional[Conflict]:
    """Resolve a conflict.

    Args:
        conflict_id: The conflict ID
        resolution: How to resolve the conflict

    Returns:
        Updated Conflict or None if not found
    """
    _ensure_conflicts_dir()

    # Find the conflict file
    for filepath in CONFLICTS_DIR.glob(f"*-{conflict_id}.json"):
        try:
            with open(filepath) as f:
                data = json.load(f)

            # Update resolution
            data["resolution"] = resolution.value
            data["resolved_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

            # Save back
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            return Conflict.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            continue

    return None


def delete_conflict(conflict_id: str) -> bool:
    """Delete a conflict file.

    Args:
        conflict_id: The conflict ID

    Returns:
        True if deleted, False if not found
    """
    _ensure_conflicts_dir()

    for filepath in CONFLICTS_DIR.glob(f"*-{conflict_id}.json"):
        filepath.unlink()
        return True

    return False


def clear_resolved_conflicts() -> int:
    """Delete all resolved conflicts.

    Returns:
        Number of conflicts deleted
    """
    _ensure_conflicts_dir()

    deleted = 0
    for filepath in CONFLICTS_DIR.glob("*.json"):
        try:
            with open(filepath) as f:
                data = json.load(f)
            if data.get("resolution"):
                filepath.unlink()
                deleted += 1
        except (json.JSONDecodeError, KeyError):
            continue

    return deleted


def has_unresolved_conflicts() -> bool:
    """Check if there are any unresolved conflicts.

    Returns:
        True if there are unresolved conflicts
    """
    return len(list_conflicts(resolved=False)) > 0


def get_resolved_data(conflict: Conflict) -> Any:
    """Get the data to use based on the conflict resolution.

    Args:
        conflict: The resolved conflict

    Returns:
        The data to use, or None if not resolved or KEEP_BOTH
    """
    if not conflict.resolution:
        return None

    if conflict.resolution == Resolution.KEEP_LOCAL:
        return conflict.local
    elif conflict.resolution == Resolution.KEEP_REMOTE:
        return conflict.remote
    elif conflict.resolution == Resolution.KEEP_NEWEST:
        # Compare timestamps
        if conflict.local_timestamp and conflict.remote_timestamp:
            if conflict.local_timestamp >= conflict.remote_timestamp:
                return conflict.local
            return conflict.remote
        # If no timestamps, prefer local
        return conflict.local
    elif conflict.resolution == Resolution.KEEP_BOTH:
        # Caller must handle this case specifically
        return None
    elif conflict.resolution == Resolution.MERGE:
        # Only works for dicts
        if isinstance(conflict.local, dict) and isinstance(conflict.remote, dict):
            return deep_merge(conflict.remote, conflict.local)
        return conflict.local

    return None


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries.

    Values from override take precedence for non-dict values.
    Nested dicts are merged recursively.

    Args:
        base: Base dictionary
        override: Dictionary with overriding values

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result
