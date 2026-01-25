"""
Fresh Start - Reset user data while preserving configuration.

This module provides shared logic for the fresh-start functionality
used by both the CLI and web API.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
BACKUP_PREFIX = "data_backup-"
CORE_AGENTS = {"user", "worker"}


def create_backup() -> str:
    """
    Create a timestamped backup of the data directory.

    Returns the backup name.
    """
    project_dir = DATA_DIR.parent
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_name = f"{BACKUP_PREFIX}{timestamp}"
    backup_path = project_dir / backup_name

    if DATA_DIR.exists():
        shutil.copytree(str(DATA_DIR), str(backup_path))

    return backup_name


def perform_fresh_start(create_backup_first: bool = True) -> dict:
    """
    Reset all user data for a clean slate.

    Optionally creates a backup first, then deletes user data while
    preserving configuration files and git-tracked assets.

    Args:
        create_backup_first: If True, backup data before resetting

    Returns dict with:
        - backup_name: Name of backup (if created)
        - deleted: List of deleted items
        - reset: List of reset items
    """
    from ..data.topics import _clear_connection, _ensure_schema

    backup_name = None
    if create_backup_first:
        backup_name = create_backup()

    deleted = []
    reset = []

    # Close any open database connections before modifying files
    _clear_connection()

    # Clear logger caches
    _clear_logger_caches()

    # 1. Clear user data (costs)
    user_dir = DATA_DIR / "agents" / "user"
    if user_dir.exists():
        costs_dir = user_dir / "costs"
        if costs_dir.exists():
            for f in costs_dir.glob("*.jsonl"):
                f.unlink()
                deleted.append(f"agents/user/costs/{f.name}")

    # 2. Clear topics database and assets
    topics_dir = DATA_DIR / "topics"
    if topics_dir.exists():
        # Remove SQLite database
        db_file = topics_dir / "db.sqlite"
        if db_file.exists():
            db_file.unlink()
            deleted.append("topics/db.sqlite")
        # Remove database journal files
        for pattern in ["db.sqlite-journal", "db.sqlite-wal", "db.sqlite-shm"]:
            journal = topics_dir / pattern
            if journal.exists():
                journal.unlink()
                deleted.append(f"topics/{pattern}")
        # Remove assets directory
        assets_dir = topics_dir / "assets"
        if assets_dir.exists():
            shutil.rmtree(assets_dir)
            deleted.append("topics/assets/")

    # 3. Process agents - clear data for core agents, remove non-core agents entirely
    agents_dir = DATA_DIR / "agents"
    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                agent_id = agent_dir.name

                if agent_id in CORE_AGENTS:
                    # Core agent: clear logs, state, memory but keep config
                    # Remove logs
                    logs_dir = agent_dir / "logs"
                    if logs_dir.exists():
                        shutil.rmtree(logs_dir)
                        deleted.append(f"agents/{agent_id}/logs/")
                    # Remove state directory (conversation history)
                    state_dir = agent_dir / "state"
                    if state_dir.exists():
                        shutil.rmtree(state_dir)
                        deleted.append(f"agents/{agent_id}/state/")
                    # Remove state.json (last_ran timestamp)
                    state_file = agent_dir / "state.json"
                    if state_file.exists():
                        state_file.unlink()
                        deleted.append(f"agents/{agent_id}/state.json")
                    # Remove memory directory (short-term and long-term)
                    memory_dir = agent_dir / "memory"
                    if memory_dir.exists():
                        shutil.rmtree(memory_dir)
                        deleted.append(f"agents/{agent_id}/memory/")
                    # Remove uploads directory (user agent)
                    uploads_dir = agent_dir / "uploads"
                    if uploads_dir.exists():
                        shutil.rmtree(uploads_dir)
                        deleted.append(f"agents/{agent_id}/uploads/")

                    # Reset identity from template if available
                    identity_template = agent_dir / "identity.template.md"
                    identity_file = agent_dir / "identity.md"
                    if identity_template.exists():
                        template_content = identity_template.read_text()
                        identity_file.write_text(template_content)
                        reset.append(f"agents/{agent_id}/identity.md")
                    elif identity_file.exists():
                        # No template, just remove the identity
                        identity_file.unlink()
                        deleted.append(f"agents/{agent_id}/identity.md")

                    # Reset agent state to enabled and clear pause info
                    config_file = agent_dir / "config.json"
                    if config_file.exists():
                        try:
                            import json
                            with open(config_file) as f:
                                config = json.load(f)
                            # Reset state to enabled
                            if config.get("state") != "enabled":
                                config["state"] = "enabled"
                                # Remove pause-related fields
                                config.pop("pause_reason", None)
                                config.pop("pause_timestamp", None)
                                with open(config_file, "w") as f:
                                    json.dump(config, f, indent=2)
                                    f.write("\n")
                                reset.append(f"agents/{agent_id}/config.json (state)")
                        except (json.JSONDecodeError, IOError):
                            pass
                else:
                    # Non-core agent: remove entirely
                    shutil.rmtree(agent_dir)
                    deleted.append(f"agents/{agent_id}/ (entire agent)")

    # 4. Remove system state, logs, and password
    system_dir = DATA_DIR / "system"
    if system_dir.exists():
        # Remove system state (trigger tracking)
        state_file = system_dir / "state.json"
        if state_file.exists():
            state_file.unlink()
            deleted.append("system/state.json")
        # Remove password
        auth_file = system_dir / "auth.json"
        if auth_file.exists():
            auth_file.unlink()
            deleted.append("system/auth.json")
        # Remove quotes (daily quote history)
        quotes_file = system_dir / "quotes.json"
        if quotes_file.exists():
            quotes_file.unlink()
            deleted.append("system/quotes.json")
        # Remove token usage data (usage tracking and call logs)
        token_usage_dir = system_dir / "token_usage"
        if token_usage_dir.exists():
            shutil.rmtree(token_usage_dir)
            deleted.append("system/token_usage/")
        # Remove consolidation logs
        consolidation_logs = system_dir / "logs" / "consolidation"
        if consolidation_logs.exists():
            shutil.rmtree(consolidation_logs)
            deleted.append("system/logs/consolidation/")
        # Remove prompt logs
        prompt_logs = system_dir / "logs" / "prompts"
        if prompt_logs.exists():
            shutil.rmtree(prompt_logs)
            deleted.append("system/logs/prompts/")

    # 5. Reinitialize database schema
    _ensure_schema()

    return {
        "backup_name": backup_name,
        "deleted": deleted,
        "reset": reset
    }


def list_backups() -> List[dict]:
    """List all available backups sorted by date (newest first)."""
    project_dir = DATA_DIR.parent
    backups = []

    for item in project_dir.iterdir():
        if item.is_dir() and item.name.startswith(BACKUP_PREFIX):
            timestamp_str = item.name[len(BACKUP_PREFIX):]
            try:
                mtime = item.stat().st_mtime
                backups.append({
                    "name": item.name,
                    "timestamp": timestamp_str,
                    "path": str(item),
                    "mtime": mtime
                })
            except OSError:
                continue

    backups.sort(key=lambda x: x["mtime"], reverse=True)
    return backups


def restore_backup(backup_name: str) -> dict:
    """
    Restore from a backup by swapping directories.

    The current data becomes a new backup, and the selected backup becomes data.
    """
    from ..data.topics import _clear_connection

    project_dir = DATA_DIR.parent
    backup_path = project_dir / backup_name

    if not backup_path.exists():
        return {"error": f"Backup not found: {backup_name}"}

    if not backup_path.is_dir():
        return {"error": f"Invalid backup: {backup_name}"}

    # Close any open database connections
    _clear_connection()

    # Clear logger caches
    _clear_logger_caches()

    # Create a backup of current data before restoring
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    current_backup_name = f"{BACKUP_PREFIX}{timestamp}"
    current_backup_path = project_dir / current_backup_name

    # Move current data to backup
    if DATA_DIR.exists():
        shutil.move(str(DATA_DIR), str(current_backup_path))

    # Restore selected backup as data
    shutil.move(str(backup_path), str(DATA_DIR))

    return {
        "restored_from": backup_name,
        "current_backed_up_as": current_backup_name
    }


def delete_backup(backup_name: str) -> dict:
    """Delete a backup permanently."""
    project_dir = DATA_DIR.parent
    backup_path = project_dir / backup_name

    if not backup_path.exists():
        return {"error": f"Backup not found: {backup_name}"}

    if not backup_name.startswith(BACKUP_PREFIX):
        return {"error": "Invalid backup name"}

    shutil.rmtree(backup_path)
    return {"deleted": backup_name}


def _clear_logger_caches():
    """Clear all logger caches and in-memory state to prevent stale data."""
    # Clear general loggers
    try:
        from ...agent.logger import _loggers
        _loggers.clear()
    except Exception:
        pass

    # Clear LLM prompt logger cache
    try:
        import src.llms.base as llm_base
        llm_base._prompt_logger = None
    except Exception:
        pass

    # Reset token awareness singleton to clear in-memory usage data
    try:
        import src.agent.cognition.metacognition.regulation.tokens as tokens_module
        if tokens_module._token_awareness is not None:
            # Clear in-memory state by resetting the singleton
            tokens_module._token_awareness = None
    except Exception:
        pass
