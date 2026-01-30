"""Deletion tracking for sync tombstones."""

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Iterable


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DELETIONS_PATH = DATA_DIR / "system" / "deletions.json"


def _default_deletions() -> Dict[str, Any]:
    return {
        "topics": {},
        "memory": {},
    }


def _load_deletions() -> Dict[str, Any]:
    if not DELETIONS_PATH.exists():
        return _default_deletions()
    try:
        with open(DELETIONS_PATH) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_deletions()
        data.setdefault("topics", {})
        data.setdefault("memory", {})
        return data
    except (json.JSONDecodeError, OSError):
        return _default_deletions()


def _save_deletions(data: Dict[str, Any]) -> None:
    DELETIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DELETIONS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def record_topic_deletion(
    topic_id: str,
    delete_children: bool = False,
    deleted_at: str | None = None,
) -> None:
    data = _load_deletions()
    if topic_id in data.get("topics", {}):
        return
    if deleted_at is None:
        deleted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    data["topics"][topic_id] = {
        "deleted_at": deleted_at,
        "delete_children": delete_children,
    }
    _save_deletions(data)


def record_memory_deletion(agent_id: str, entry_id: str, deleted_at: str | None = None) -> None:
    data = _load_deletions()
    if entry_id in data.get("memory", {}).get(agent_id, {}):
        return
    if deleted_at is None:
        deleted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    data["memory"].setdefault(agent_id, {})[entry_id] = deleted_at
    _save_deletions(data)


def record_memory_deletions(agent_id: str, entry_ids: Iterable[str], deleted_at: str | None = None) -> None:
    data = _load_deletions()
    if deleted_at is None:
        deleted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    agent_bucket = data["memory"].setdefault(agent_id, {})
    for entry_id in entry_ids:
        if entry_id not in agent_bucket:
            agent_bucket[entry_id] = deleted_at
    _save_deletions(data)


def get_deletions() -> Dict[str, Any]:
    return _load_deletions()
