"""
Sync State - Track synchronization state and instance identity.

State is stored in data/system/sync/state.json and includes:
- Instance ID (unique identifier for this Euno installation)
- Last sync timestamp and remote info
- Remote server configuration
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent / "data"
SYNC_DIR = DATA_DIR / "system" / "sync"
STATE_PATH = SYNC_DIR / "state.json"


@dataclass
class LastSync:
    """Record of the last successful sync."""
    timestamp: str
    remote_instance_id: str
    success: bool
    direction: str = "bidirectional"  # "push", "pull", or "bidirectional"
    changes_pushed: int = 0
    changes_pulled: int = 0


@dataclass
class RemoteConfig:
    """Remote server configuration."""
    host: str  # user@server.example.com
    path: str = "/opt/euno"


@dataclass
class SyncState:
    """Complete sync state for this instance."""
    version: int = 1
    instance_id: str = ""
    last_sync: Optional[LastSync] = None
    remote: Optional[RemoteConfig] = None

    def __post_init__(self):
        # Generate instance ID if not set
        if not self.instance_id:
            self.instance_id = f"euno-{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "version": self.version,
            "instance_id": self.instance_id,
        }
        if self.last_sync:
            result["last_sync"] = asdict(self.last_sync)
        if self.remote:
            result["remote"] = asdict(self.remote)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SyncState":
        """Create from dictionary."""
        state = cls(
            version=data.get("version", 1),
            instance_id=data.get("instance_id", ""),
        )
        if data.get("last_sync"):
            state.last_sync = LastSync(**data["last_sync"])
        if data.get("remote"):
            state.remote = RemoteConfig(**data["remote"])
        return state


def _ensure_sync_dir():
    """Ensure sync directory exists."""
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    conflicts_dir = SYNC_DIR / "conflicts"
    conflicts_dir.mkdir(exist_ok=True)


def get_sync_state() -> SyncState:
    """Load current sync state, creating default if needed."""
    _ensure_sync_dir()

    if STATE_PATH.exists():
        try:
            with open(STATE_PATH) as f:
                data = json.load(f)
            return SyncState.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    # Create new state with generated instance ID
    state = SyncState()
    save_sync_state(state)
    return state


def save_sync_state(state: SyncState):
    """Save sync state to disk."""
    _ensure_sync_dir()

    with open(STATE_PATH, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


def get_instance_id() -> str:
    """Get this instance's unique ID."""
    return get_sync_state().instance_id


def init_sync(server: str, remote_path: str = "/opt/euno") -> SyncState:
    """Initialize sync with a remote server.

    Args:
        server: SSH server string (user@host or host)
        remote_path: Path to Euno installation on remote

    Returns:
        Updated SyncState
    """
    state = get_sync_state()
    state.remote = RemoteConfig(host=server, path=remote_path)
    save_sync_state(state)
    return state


def record_sync(
    remote_instance_id: str,
    success: bool,
    direction: str = "bidirectional",
    changes_pushed: int = 0,
    changes_pulled: int = 0,
) -> SyncState:
    """Record a sync operation.

    Args:
        remote_instance_id: The remote instance's ID
        success: Whether the sync succeeded
        direction: "push", "pull", or "bidirectional"
        changes_pushed: Number of changes pushed to remote
        changes_pulled: Number of changes pulled from remote

    Returns:
        Updated SyncState
    """
    state = get_sync_state()
    state.last_sync = LastSync(
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        remote_instance_id=remote_instance_id,
        success=success,
        direction=direction,
        changes_pushed=changes_pushed,
        changes_pulled=changes_pulled,
    )
    save_sync_state(state)
    return state


def clear_remote() -> SyncState:
    """Clear remote configuration."""
    state = get_sync_state()
    state.remote = None
    save_sync_state(state)
    return state
