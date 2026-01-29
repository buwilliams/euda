"""
Topics - CRUD operations for topics.

Topics are the primary unit of work in the system.
They can be nested via parent_id to form hierarchies.

Storage: SQLite database at data/topics/db.sqlite
"""

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, List



DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
TOPICS_DIR = DATA_DIR / "topics"
DB_PATH = TOPICS_DIR / "db.sqlite"

# Thread-local storage for database connections
_local = threading.local()


def _clear_connection():
    """Clear thread-local connection. Call after fresh-start/restore."""
    if hasattr(_local, 'connection') and _local.connection is not None:
        try:
            _local.connection.close()
        except Exception:
            pass
        _local.connection = None


def _get_connection() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        TOPICS_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.connection = conn
    return _local.connection


@contextmanager
def _transaction():
    """Context manager for database transactions."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _ensure_schema():
    """Create tables if they don't exist."""
    conn = _get_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS topics (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT REFERENCES topics(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'working', 'done', 'error', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'user',
            description TEXT,
            due_date TEXT,
            someday INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            tags TEXT
        );

        CREATE TABLE IF NOT EXISTS topic_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
            timestamp TEXT NOT NULL,
            agent TEXT NOT NULL,
            action TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_topics_status ON topics(status);
        CREATE INDEX IF NOT EXISTS idx_topics_parent_id ON topics(parent_id);
        CREATE INDEX IF NOT EXISTS idx_topics_updated_at ON topics(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_topic_logs_topic_id ON topic_logs(topic_id);
    ''')
    conn.commit()

    # Migration: add assignee column if it doesn't exist
    try:
        conn.execute("SELECT assignee FROM topics LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE topics ADD COLUMN assignee TEXT")
        conn.commit()

    # Migration: add agent_id column if it doesn't exist (for agent inbox topics)
    try:
        conn.execute("SELECT agent_id FROM topics LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE topics ADD COLUMN agent_id TEXT")
        conn.commit()

    # Migration: add pending_from column if it doesn't exist (for topic handoff tracking)
    try:
        conn.execute("SELECT pending_from FROM topics LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE topics ADD COLUMN pending_from TEXT")
        conn.commit()

    # Migration: rename 'completed' status to 'done' and update CHECK constraint
    # SQLite doesn't support ALTER TABLE to change constraints, so we check and migrate data
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM topics WHERE status = 'completed'")
        completed_count = cursor.fetchone()[0]
        if completed_count > 0:
            conn.execute("UPDATE topics SET status = 'done' WHERE status = 'completed'")
            conn.commit()
            print(f"Migrated {completed_count} topics from 'completed' to 'done' status")
    except Exception:
        pass  # Table may not exist yet


# Initialize schema on module import
_ensure_schema()


def _emit_event(event: str, scope: str = None, data: dict = None):
    """Emit an event to the event bus (for agent-scoped events like topic:assigned)."""
    from src.events import emit_event
    emit_event(event, scope=scope, data=data)


def _emit_system_event(event: str, data: dict = None, source: str = "system"):
    """Emit a system event for trigger matching."""
    from src.events import emit_system_event
    emit_system_event(event, data=data, source=source)


def _emit_topics_update():
    """Notify UI clients that topics have changed."""
    from src.web.events import emit_ui_event
    all_topics = list_topics()
    emit_ui_event("topics_update", {"topics": all_topics})


def _notify_agent_has_topics(agent_id: str):
    """Notify the topic cache that an agent has pending topics."""
    from src.agent.manager import get_manager
    manager = get_manager()
    if manager:
        manager.agents_with_topics[agent_id] = True


def _row_to_topic(row: sqlite3.Row, logs: List[dict] = None) -> dict:
    """Convert a database row to a topic dictionary."""
    # Handle columns that may not exist in older schemas
    assignee = row["assignee"] if "assignee" in row.keys() else None
    agent_id = row["agent_id"] if "agent_id" in row.keys() else None
    pending_from = row["pending_from"] if "pending_from" in row.keys() else None

    topic = {
        "id": row["id"],
        "name": row["name"],
        "parent_id": row["parent_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "created_by": row["created_by"],
        "description": row["description"],
        "due_date": row["due_date"],
        "someday": bool(row["someday"]),
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "assignee": assignee,
        "agent_id": agent_id,
        "pending_from": pending_from,
        "log": logs if logs is not None else []
    }
    if row["completed_at"]:
        topic["completed_at"] = row["completed_at"]
    return topic


def _get_topic_logs(topic_id: str) -> List[dict]:
    """Get all log entries for a topic."""
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT timestamp, agent, action FROM topic_logs WHERE topic_id = ? ORDER BY id",
        (topic_id,)
    )
    return [{"timestamp": row[0], "agent": row[1], "action": row[2]} for row in cursor]


def _load_topic(topic_id: str) -> Optional[dict]:
    """Load a topic by ID."""
    conn = _get_connection()
    cursor = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    row = cursor.fetchone()
    if row:
        logs = _get_topic_logs(topic_id)
        return _row_to_topic(row, logs)
    return None


def list_topics(status: str = None, parent_id: str = None, tag: str = None, assignee: str = None, actionable: bool = False) -> List[dict]:
    """List topics with optional filters.

    Args:
        status: Filter by status (todo, working, done, error, archived)
        parent_id: Filter by parent topic ID (empty string for root topics)
        tag: Filter to topics containing this tag
        assignee: Filter to topics assigned to this agent ID
        actionable: If True, only return topics with due_date <= today or NULL, and not someday
    """
    from datetime import date

    conn = _get_connection()

    query = "SELECT * FROM topics WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if parent_id is not None:
        if parent_id == "":
            query += " AND parent_id IS NULL"
        else:
            query += " AND parent_id = ?"
            params.append(parent_id)

    if tag:
        # Filter topics that have the specified tag in their tags JSON array
        query += " AND EXISTS (SELECT 1 FROM json_each(tags) WHERE json_each.value = ?)"
        params.append(tag)

    if assignee:
        # Filter topics assigned to this agent (simple string comparison)
        query += " AND assignee = ?"
        params.append(assignee)
        # Exclude system topics - only their descendants should be processed by agents
        query += " AND NOT EXISTS (SELECT 1 FROM json_each(tags) WHERE json_each.value IN ('system:agents', 'system:projects', 'system:assets', 'agent-inbox'))"

    if actionable:
        # Only topics that are due today, past, or have no due date (and not someday)
        today = date.today().isoformat()
        query += " AND (due_date IS NULL OR due_date <= ?)"
        params.append(today)
        query += " AND someday = 0"
        # Exclude topics with blocking tags (waiting:* or blocked:*)
        query += " AND NOT EXISTS (SELECT 1 FROM json_each(tags) WHERE json_each.value LIKE 'waiting:%' OR json_each.value LIKE 'blocked:%')"
        # Only include todo topics (working topics are already being processed)
        query += " AND status = 'todo'"

    query += " ORDER BY updated_at DESC"

    cursor = conn.execute(query, params)
    topics = []
    for row in cursor:
        logs = _get_topic_logs(row["id"])
        topics.append(_row_to_topic(row, logs))

    return topics


def get_topic(topic_id: str) -> Optional[dict]:
    """Get a single topic by ID."""
    return _load_topic(topic_id)


def get_agent_inbox_topic(agent_id: str) -> Optional[dict]:
    """Get an agent's inbox topic (under the Agents container)."""
    all_topics = list_topics()
    for topic in all_topics:
        if topic.get("agent_id") == agent_id:
            return topic
    return None


def _get_default_parent_for_creator(created_by: str) -> Optional[str]:
    """Get the default parent topic ID based on who is creating the topic.

    - user/system -> Projects container
    - other agents -> their agent inbox topic
    """
    from ..agents.agents import list_agents

    # User or system -> Projects
    if created_by in ("user", "system"):
        projects = get_projects_container()
        return projects["id"] if projects else None

    # Check if created_by is a known agent
    agents = list_agents()
    agent_ids = {a["id"] for a in agents}

    if created_by in agent_ids:
        # Agent -> their inbox topic
        inbox = get_agent_inbox_topic(created_by)
        return inbox["id"] if inbox else None

    # Unknown creator -> Projects as fallback
    projects = get_projects_container()
    return projects["id"] if projects else None


def create_topic(
    name: str,
    description: str = None,
    parent_id: str = None,
    tags: list = None,
    assignee: str = None,
    due_date: str = None,
    someday: bool = False,
    created_by: str = "user"
) -> dict:
    """Create a new topic.

    If no parent_id is provided:
    - Topics created by user/system go under Projects
    - Topics created by other agents go under their agent inbox
    """
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    topic_id = f"topic-{uuid.uuid4().hex[:8]}"

    # Set default parent if none provided
    effective_parent_id = parent_id
    if effective_parent_id is None:
        effective_parent_id = _get_default_parent_for_creator(created_by)

    with _transaction() as conn:
        conn.execute('''
            INSERT INTO topics (id, name, parent_id, status, created_at, updated_at,
                            created_by, description, due_date, someday, tags, assignee)
            VALUES (?, ?, ?, 'todo', ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            topic_id, name, effective_parent_id, now, now, created_by,
            description, due_date, int(someday), json.dumps(tags or []),
            assignee
        ))

        conn.execute('''
            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'created')
        ''', (topic_id, now, created_by))

    # Emit topic:created system event (only for non-trigger topics to prevent loops)
    topic = _load_topic(topic_id)
    if created_by != "trigger":
        _emit_system_event("topic:created", data={"topic_id": topic_id, "name": name})

    # Emit topic:assigned (scoped) event for agent wakeup
    if assignee:
        _emit_event("topic:assigned", scope=assignee, data={"topic_id": topic_id, "name": name})
        _notify_agent_has_topics(assignee)

    # Notify UI clients
    _emit_topics_update()

    return topic


def update_topic(
    topic_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    tags: list = None,
    assignee: str = None,
    due_date: str = None,
    someday: bool = None
) -> Optional[dict]:
    """Update a topic's fields."""
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    # Prevent setting status to 'working' - only claim_topic can do that
    if status == "working":
        return {"error": "Cannot set status to 'working' directly. Use claim_topic instead."}

    # Prevent status changes on system topics
    system_tags = {"system:agents", "system:projects", "system:assets", "agent-inbox"}
    if status is not None and any(tag in system_tags for tag in topic.get("tags", [])):
        return {"error": "Cannot change status of system topics"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    updates = ["updated_at = ?"]
    params = [now]

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))
    if assignee is not None:
        updates.append("assignee = ?")
        params.append(assignee if assignee else None)  # Empty string means clear
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date if due_date else None)  # Empty string means clear
    if someday is not None:
        updates.append("someday = ?")
        params.append(int(someday))

    params.append(topic_id)

    with _transaction() as conn:
        conn.execute(f"UPDATE topics SET {', '.join(updates)} WHERE id = ?", params)

    # Emit topic:assigned event if assignee changed
    if assignee is not None:
        old_assignee = topic.get("assignee")
        if assignee != old_assignee and assignee:
            _emit_event("topic:assigned", scope=assignee, data={"topic_id": topic_id, "name": topic["name"]})
            _notify_agent_has_topics(assignee)

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


def handoff_topic(topic_id: str, to: str, note: str = None, agent: str = "user") -> Optional[dict]:
    """Hand off a topic to another agent or user.

    This is the primary mechanism for topic coordination between agents.
    It sets the assignee to the target, resets status to 'todo' if currently
    'working', and records who sent it so the topic can be returned to them.

    If the topic is 'error' or 'archived', the status is left alone as
    handoff to those states is a no-op.

    Args:
        topic_id: The topic to hand off
        to: Agent ID or "user" to hand off to
        note: Optional note explaining what's needed or what was done
        agent: Who is performing the handoff (for logging)

    Returns:
        Updated topic dict or error
    """
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    current_status = topic.get("status", "todo")

    # Update assignee and set pending_from; reset status to 'todo' only if 'working'
    with _transaction() as conn:
        if current_status == "working":
            conn.execute('''
                UPDATE topics SET assignee = ?, status = 'todo', pending_from = ?, updated_at = ?
                WHERE id = ?
            ''', (to, agent, now, topic_id))
        else:
            conn.execute('''
                UPDATE topics SET assignee = ?, pending_from = ?, updated_at = ?
                WHERE id = ?
            ''', (to, agent, now, topic_id))

        # Add log entry
        action = f"Handed off to {to}"
        if note:
            action += f": {note}"
        conn.execute('''
            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
            VALUES (?, ?, ?, ?)
        ''', (topic_id, now, agent, action))

    # Emit topic:assigned event for the target
    _emit_event("topic:assigned", scope=to, data={"topic_id": topic_id, "name": topic["name"]})
    if to != "user":
        _notify_agent_has_topics(to)

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


def complete_topic(topic_id: str, agent: str = "user") -> Optional[dict]:
    """Mark a topic as done."""
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    # Prevent completing system topics (containers and agent inboxes)
    # Exception: Allow completing internal euno:* topics even if they have system tags
    is_internal = topic.get("name", "").startswith("euno:")
    if not is_internal:
        system_tags = {"system:agents", "system:projects", "system:assets", "agent-inbox"}
        if any(tag in system_tags for tag in topic.get("tags", [])):
            return {"error": "Cannot complete system topics"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    with _transaction() as conn:
        conn.execute('''
            UPDATE topics SET status = 'done', completed_at = ?, updated_at = ?
            WHERE id = ?
        ''', (now, now, topic_id))

        conn.execute('''
            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'completed')
        ''', (topic_id, now, agent))

    # Emit topic:completed system event for triggers
    _emit_system_event("topic:completed", data={"topic_id": topic_id, "name": topic["name"]})

    # Emit topic:completed to assignee (scoped event)
    assignee = topic.get("assignee")
    if assignee:
        _emit_event("topic:completed", scope=assignee, data={"topic_id": topic_id, "name": topic["name"]})

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


def restore_topic(topic_id: str, agent: str = "user") -> Optional[dict]:
    """Restore a done topic back to todo status."""
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    with _transaction() as conn:
        conn.execute('''
            UPDATE topics SET status = 'todo', completed_at = NULL, updated_at = ?
            WHERE id = ?
        ''', (now, topic_id))

        conn.execute('''
            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'restored')
        ''', (topic_id, now, agent))

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


def unblock_topic(topic_id: str) -> bool:
    """Remove waiting:* and blocked:* tags from a topic.

    Called automatically when a user interacts with a blocked topic
    (views it, adds an asset, etc.) to put it back in the agent's queue.

    Args:
        topic_id: The topic to unblock

    Returns:
        True if the topic was unblocked, False if it wasn't blocked
    """
    topic = _load_topic(topic_id)
    if not topic:
        return False

    tags = topic.get("tags", [])
    blocking_tags = [t for t in tags if t.startswith(("waiting:", "blocked:"))]

    if not blocking_tags:
        return False  # Not blocked

    # Remove blocking tags
    new_tags = [t for t in tags if not t.startswith(("waiting:", "blocked:"))]

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    with _transaction() as conn:
        conn.execute('''
            UPDATE topics SET tags = ?, updated_at = ?
            WHERE id = ?
        ''', (json.dumps(new_tags), now, topic_id))

        conn.execute('''
            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
            VALUES (?, ?, ?, ?)
        ''', (topic_id, now, "user", f"unblocked: {', '.join(blocking_tags)}"))

    # Notify assignee that topic is actionable again
    assignee = topic.get("assignee")
    if assignee:
        _emit_event("topic:assigned", scope=assignee, data={"topic_id": topic_id, "name": topic["name"]})
        _notify_agent_has_topics(assignee)

    # Notify UI clients
    _emit_topics_update()

    return True


def archive_topic(topic_id: str, agent: str = "user") -> Optional[dict]:
    """Archive a topic."""
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    # Prevent archiving system topics (containers and agent inboxes)
    system_tags = {"system:agents", "system:projects", "system:assets", "agent-inbox"}
    if any(tag in system_tags for tag in topic.get("tags", [])):
        return {"error": "Cannot archive system topics"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    with _transaction() as conn:
        conn.execute('''
            UPDATE topics SET status = 'archived', updated_at = ?
            WHERE id = ?
        ''', (now, topic_id))

        conn.execute('''
            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'archived')
        ''', (topic_id, now, agent))

    # Emit topic:archived to assignee
    assignee = topic.get("assignee")
    if assignee:
        _emit_event("topic:archived", scope=assignee, data={"topic_id": topic_id, "name": topic["name"]})

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


def add_topic_log(topic_id: str, action: str, agent: str = "user") -> Optional[dict]:
    """Add a log entry to a topic."""
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    with _transaction() as conn:
        conn.execute("UPDATE topics SET updated_at = ? WHERE id = ?", (now, topic_id))
        conn.execute('''
            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
            VALUES (?, ?, ?, ?)
        ''', (topic_id, now, agent, action))

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


def get_topic_logs(topic_id: str) -> List[dict]:
    """Get all log entries for a topic.

    Returns:
        List of log entries with timestamp, agent, and action fields.
        Sorted by timestamp ascending (oldest first).
    """
    conn = _get_connection()
    cursor = conn.execute('''
        SELECT timestamp, agent, action
        FROM topic_logs
        WHERE topic_id = ?
        ORDER BY timestamp ASC
    ''', (topic_id,))

    return [dict(row) for row in cursor.fetchall()]


def get_child_topics(parent_id: str) -> List[dict]:
    """Get all child topics of a given parent."""
    return list_topics(parent_id=parent_id)


def delete_topic(topic_id: str, delete_children: bool = False) -> dict:
    """Delete a topic. Optionally delete child topics too."""
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    # Prevent deletion of system topics (containers and agent inboxes)
    system_tags = {"system:agents", "system:projects", "system:assets", "agent-inbox"}
    if any(tag in system_tags for tag in topic.get("tags", [])):
        return {"error": "Cannot delete system topics"}

    # Delete children if requested (must do before parent due to FK)
    if delete_children:
        children = get_child_topics(topic_id)
        for child in children:
            delete_topic(child["id"], delete_children=True)

    with _transaction() as conn:
        # Delete the topic (logs cascade automatically via ON DELETE CASCADE)
        conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))

    # Notify UI clients
    _emit_topics_update()

    return {"deleted": topic_id, "children_deleted": delete_children}


# =============================================================================
# BATCH OPERATIONS - More efficient than multiple single-item calls
# =============================================================================

def create_topics_batch(topics: list, created_by: str = "agent") -> dict:
    """Create multiple topics in a single operation.

    Returns:
        Dict with 'created' (list of topic objects), 'count', and 'errors' if any
    """
    results = []
    errors = []

    for i, topic_spec in enumerate(topics):
        try:
            result = create_topic(
                name=topic_spec["name"],
                description=topic_spec.get("description"),
                parent_id=topic_spec.get("parent_id"),
                tags=topic_spec.get("tags"),
                due_date=topic_spec.get("due_date"),
                someday=topic_spec.get("someday", False),
                created_by=created_by
            )
            results.append(result)
        except Exception as e:
            errors.append({"index": i, "name": topic_spec.get("name"), "error": str(e)})

    return {
        "created": results,
        "count": len(results),
        "errors": errors if errors else None
    }


def update_topics_batch(updates: list) -> dict:
    """Update multiple topics in a single operation.

    Returns:
        Dict with 'updated' (list of topic objects), 'count', and 'errors' if any
    """
    results = []
    errors = []

    for i, update_spec in enumerate(updates):
        topic_id = update_spec.get("topic_id")
        if not topic_id:
            errors.append({"index": i, "error": "topic_id is required"})
            continue

        try:
            # Extract topic_id and pass rest as kwargs
            kwargs = {k: v for k, v in update_spec.items() if k != "topic_id"}
            result = update_topic(topic_id, **kwargs)
            if result and "error" not in result:
                results.append(result)
            else:
                errors.append({"index": i, "topic_id": topic_id, "error": result.get("error", "Unknown error")})
        except Exception as e:
            errors.append({"index": i, "topic_id": topic_id, "error": str(e)})

    return {
        "updated": results,
        "count": len(results),
        "errors": errors if errors else None
    }


def complete_topics_batch(topic_ids: list, agent: str = "user") -> dict:
    """Complete multiple topics in a single operation.

    Returns:
        Dict with 'completed' (list of topic objects), 'count', and 'errors' if any
    """
    results = []
    errors = []

    for topic_id in topic_ids:
        try:
            result = complete_topic(topic_id, agent=agent)
            if result and "error" not in result:
                results.append(result)
            else:
                errors.append({"topic_id": topic_id, "error": result.get("error", "Unknown error")})
        except Exception as e:
            errors.append({"topic_id": topic_id, "error": str(e)})

    return {
        "completed": results,
        "count": len(results),
        "errors": errors if errors else None
    }


def add_topic_logs_batch(logs: list, agent: str = "user") -> dict:
    """Add log entries to multiple topics in a single operation.

    Returns:
        Dict with 'logged' (list of results), 'count', and 'errors' if any
    """
    results = []
    errors = []

    for log_entry in logs:
        topic_id = log_entry.get("topic_id")
        action = log_entry.get("action")

        if not topic_id or not action:
            errors.append({"topic_id": topic_id, "error": "topic_id and action are required"})
            continue

        try:
            result = add_topic_log(topic_id, action, agent=agent)
            if result and "error" not in result:
                results.append({"topic_id": topic_id, "logged": True})
            else:
                errors.append({"topic_id": topic_id, "error": result.get("error", "Unknown error")})
        except Exception as e:
            errors.append({"topic_id": topic_id, "error": str(e)})

    return {
        "logged": results,
        "count": len(results),
        "errors": errors if errors else None
    }


# =============================================================================
# AGENT ASSIGNMENT AND SYSTEM CONTAINERS
# =============================================================================

def assign_agent(topic_id: str, agent_id: str) -> Optional[dict]:
    """Assign an agent to work on a topic. Wakes the agent immediately.

    If the topic is currently 'working', resets status to 'todo' so the new
    agent can pick it up. Other statuses (error, archived) are left alone
    as assignment to those is a no-op.

    Args:
        topic_id: The topic to assign
        agent_id: The agent ID to assign
    """
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    current_assignee = topic.get("assignee")
    if current_assignee == agent_id:
        return {"error": f"Agent {agent_id} already assigned"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    current_status = topic.get("status", "todo")

    with _transaction() as conn:
        # Reset status to 'todo' if currently 'working' so new agent can pick it up
        if current_status == "working":
            conn.execute(
                "UPDATE topics SET assignee = ?, status = 'todo', updated_at = ? WHERE id = ?",
                (agent_id, now, topic_id)
            )
        else:
            conn.execute(
                "UPDATE topics SET assignee = ?, updated_at = ? WHERE id = ?",
                (agent_id, now, topic_id)
            )
        conn.execute(
            "INSERT INTO topic_logs (topic_id, timestamp, agent, action) VALUES (?, ?, ?, ?)",
            (topic_id, now, "system", f"assigned:{agent_id}")
        )

    # Emit topic:assigned event to the agent and notify cache
    _emit_event("topic:assigned", scope=agent_id, data={"topic_id": topic_id, "name": topic["name"]})
    _notify_agent_has_topics(agent_id)

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


def unassign_agent(topic_id: str, agent_id: str) -> Optional[dict]:
    """Remove an agent from a topic.

    Args:
        topic_id: The topic to unassign from
        agent_id: The agent ID to remove
    """
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    current_assignee = topic.get("assignee")
    if current_assignee != agent_id:
        return {"error": f"Agent {agent_id} not assigned to this topic"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    with _transaction() as conn:
        conn.execute(
            "UPDATE topics SET assignee = NULL, updated_at = ? WHERE id = ?",
            (now, topic_id)
        )
        conn.execute(
            "INSERT INTO topic_logs (topic_id, timestamp, agent, action) VALUES (?, ?, ?, ?)",
            (topic_id, now, "system", f"unassigned:{agent_id}")
        )

    # Emit topic:unassigned event to the agent
    _emit_event("topic:unassigned", scope=agent_id, data={"topic_id": topic_id, "name": topic["name"]})

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


def get_assignee(topic_id: str) -> dict:
    """Get the agent ID assigned to a topic.

    Args:
        topic_id: The topic to check

    Returns:
        Dict with assignee field (null if unassigned)
    """
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    return {"assignee": topic.get("assignee")}


def list_available_agents() -> list:
    """Get list of all available agent IDs."""
    from ..agents.agents import list_agents
    agents = list_agents()
    return [a["id"] for a in agents]


def claim_topic(topic_id: str, agent_id: str) -> dict:
    """Claim a topic by setting status to 'working'.

    Only the assigned agent can claim a topic. This is a simple state transition
    since topics have a single assignee.

    Args:
        topic_id: The topic to claim
        agent_id: The agent claiming the topic
    """
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    # Prevent claiming system topics (containers and agent inboxes)
    # Only their descendants should be processed
    system_tags = {"system:agents", "system:projects", "system:assets", "agent-inbox"}
    if any(tag in system_tags for tag in topic.get("tags", [])):
        return {"error": "Cannot claim system topics - only their descendants can be processed"}

    # Verify agent is the assignee
    if topic.get("assignee") != agent_id:
        return {"error": f"Topic not assigned to {agent_id}"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    with _transaction() as conn:
        # Set status to 'working' - only if currently 'todo'
        result = conn.execute(
            """UPDATE topics SET status = 'working', updated_at = ?
               WHERE id = ? AND status = 'todo'""",
            (now, topic_id)
        )

        if result.rowcount == 0:
            # Topic is not in 'todo' status
            return {"error": f"Topic {topic_id} is not in 'todo' status (current: {topic.get('status')})"}

    # Notify UI clients
    _emit_topics_update()

    return {"claimed": True, "topic_id": topic_id, "agent": agent_id}


def get_or_create_system_topic(name: str, system_tag: str) -> dict:
    """Get or create a system container topic (Agents or Projects).

    Args:
        name: Display name for the topic
        system_tag: Tag to identify this system topic (e.g., "system:agents")

    Returns:
        The system topic dict
    """
    all_topics = list_topics()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Find existing system topic by tag at root level
    for topic in all_topics:
        if system_tag in topic.get("tags", []) and topic["parent_id"] is None:
            return topic

    # PROTECTION: Check if there's a system container that was moved or has corrupted tags
    # Look for topics by name that should be system containers
    for topic in all_topics:
        if topic["name"] == name:
            topic_tags = topic.get("tags", []) or []
            needs_repair = False
            repairs = []

            # Check if tags are missing/corrupted
            if system_tag not in topic_tags:
                needs_repair = True
                repairs.append(f"restoring tag '{system_tag}'")

            # Check if it was moved from root level
            if topic["parent_id"] is not None:
                needs_repair = True
                repairs.append("moving back to root level")

            if needs_repair:
                print(f"WARNING: Repairing system container '{name}' (id={topic['id']}): {', '.join(repairs)}")
                # Repair the container
                new_tags = list(set(topic_tags + [system_tag]))
                with _transaction() as conn:
                    conn.execute(
                        "UPDATE topics SET parent_id = NULL, tags = ?, updated_at = ? WHERE id = ?",
                        (json.dumps(new_tags), now, topic["id"])
                    )
                # Notify UI of the repair
                _emit_topics_update()
                return _load_topic(topic["id"])

    # Create new system topic
    topic_id = f"topic-{uuid.uuid4().hex[:8]}"

    with _transaction() as conn:
        conn.execute('''
            INSERT INTO topics (id, name, parent_id, status, created_at, updated_at,
                            created_by, description, tags)
            VALUES (?, ?, NULL, 'todo', ?, ?, 'system', ?, ?)
        ''', (
            topic_id, name, now, now,
            f"System container for {name.lower()}",
            json.dumps([system_tag])
        ))

    print(f"Created system topic: {name}")
    return _load_topic(topic_id)


def get_agents_container() -> dict:
    """Get or create the Agents container topic."""
    return get_or_create_system_topic("Agents", "system:agents")


def get_projects_container() -> dict:
    """Get or create the Projects container topic."""
    return get_or_create_system_topic("Projects", "system:projects")


def get_assets_container() -> dict:
    """Get or create the Assets container topic."""
    return get_or_create_system_topic("Assets", "system:assets")


def sync_agent_inbox_topics():
    """Sync agent inbox topics with current agents.

    Creates inbox topics for new agents under the Agents container,
    archives orphaned ones, and updates names if agents were renamed.
    Also migrates any orphaned user topics under Projects.
    """
    from ..agents.agents import list_agents

    # Ensure system containers exist
    agents_container = get_agents_container()
    projects_container = get_projects_container()
    get_assets_container()  # Create Assets container if it doesn't exist

    agents = list_agents()
    agent_ids = {a["id"] for a in agents}
    agent_names = {a["id"]: a.get("name", a["id"]) for a in agents}

    all_topics = list_topics()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    changes_made = False

    # Get existing agent inbox topics (topics with agent_id set)
    inbox_topics = {j["agent_id"]: j for j in all_topics if j.get("agent_id")}

    # Create inbox topics for agents that don't have one
    for agent in agents:
        agent_id = agent["id"]
        agent_name = agent.get("name", agent_id)

        if agent_id not in inbox_topics:
            # Create new inbox topic under Agents container
            topic_id = f"topic-{uuid.uuid4().hex[:8]}"
            with _transaction() as conn:
                conn.execute('''
                    INSERT INTO topics (id, name, parent_id, status, created_at, updated_at,
                                    created_by, description, tags, agent_id)
                    VALUES (?, ?, ?, 'todo', ?, ?, 'system', ?, ?, ?)
                ''', (
                    topic_id, agent_name, agents_container["id"], now, now,
                    f"Inbox for {agent_name}",
                    json.dumps(["agent-inbox"]),
                    agent_id
                ))
            print(f"Created inbox topic for agent: {agent_id}")
            changes_made = True

        else:
            topic = inbox_topics[agent_id]
            updates_needed = []

            # Check if name changed
            if topic["name"] != agent_name:
                updates_needed.append(("name", agent_name))
                updates_needed.append(("description", f"Inbox for {agent_name}"))

            # Check if needs to be moved under Agents container
            if topic["parent_id"] != agents_container["id"]:
                updates_needed.append(("parent_id", agents_container["id"]))

            if updates_needed:
                set_clauses = ", ".join(f"{k} = ?" for k, v in updates_needed)
                values = [v for k, v in updates_needed] + [now, topic["id"]]
                with _transaction() as conn:
                    conn.execute(
                        f"UPDATE topics SET {set_clauses}, updated_at = ? WHERE id = ?",
                        values
                    )
                print(f"Updated inbox topic for agent: {agent_id}")
                changes_made = True

    # Archive inbox topics for deleted agents
    for agent_id, topic in inbox_topics.items():
        if agent_id not in agent_ids and topic["status"] != "archived":
            with _transaction() as conn:
                conn.execute(
                    "UPDATE topics SET status = 'archived', updated_at = ? WHERE id = ?",
                    (now, topic["id"])
                )
            print(f"Archived inbox topic for deleted agent: {agent_id}")
            changes_made = True

    # Migrate orphaned root topics (user-created, not system) under Projects
    system_tags = {"system:agents", "system:projects", "system:assets"}
    system_container_names = {"Agents", "Projects", "Assets", "System"}
    for topic in all_topics:
        # Skip if not a root topic
        if topic["parent_id"] is not None:
            continue

        # Skip if it's a system container (check by tag)
        if any(tag in system_tags for tag in topic.get("tags", [])):
            continue

        # PROTECTION: Also skip if topic name matches system container names
        # This prevents moving containers with corrupted/missing tags
        if topic["name"] in system_container_names:
            # Log warning about potential tag corruption
            topic_tags = topic.get("tags", [])
            if not any(tag in system_tags for tag in topic_tags):
                print(f"WARNING: System container '{topic['name']}' (id={topic['id']}) has corrupted tags: {topic_tags}")
                print(f"  Expected one of: {system_tags}")
                print(f"  Skipping migration and preserving as root topic")
            continue

        # Skip agent inbox topics (handled above)
        if topic.get("agent_id"):
            continue

        # This is a user root topic - move it under Projects
        with _transaction() as conn:
            conn.execute(
                "UPDATE topics SET parent_id = ?, updated_at = ? WHERE id = ?",
                (projects_container["id"], now, topic["id"])
            )
        print(f"Moved topic '{topic['name']}' under Projects")
        changes_made = True

    if changes_made:
        _emit_topics_update()

    return {"synced": True, "agent_count": len(agents)}


def release_topic(topic_id: str, agent_id: str) -> dict:
    """Release a topic after working on it.

    Resets status from 'working' back to 'todo' so the agent can work on it again later.
    Only topics with 'working' status and matching assignee are affected.

    Args:
        topic_id: The topic to release
        agent_id: The agent releasing the topic
    """
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with _transaction() as conn:
        # Reset status to 'todo' only if currently 'working' and assigned to this agent
        conn.execute(
            "UPDATE topics SET status = 'todo', updated_at = ? WHERE id = ? AND status = 'working' AND assignee = ?",
            (now, topic_id, agent_id)
        )

    # Notify UI clients
    _emit_topics_update()

    return {"released": True, "topic_id": topic_id}


def error_topic(topic_id: str, error_message: str, agent: str = "user") -> Optional[dict]:
    """Mark a topic as failed with an error.

    Args:
        topic_id: The topic to mark as error
        error_message: Description of what went wrong
        agent: Who is marking the error
    """
    topic = _load_topic(topic_id)
    if not topic:
        return {"error": f"Topic not found: {topic_id}"}

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    with _transaction() as conn:
        conn.execute('''
            UPDATE topics SET status = 'error', updated_at = ?
            WHERE id = ?
        ''', (now, topic_id))

        conn.execute('''
            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
            VALUES (?, ?, ?, ?)
        ''', (topic_id, now, agent, f"error: {error_message}"))

    # Emit topic:error to assignee
    assignee = topic.get("assignee")
    if assignee:
        _emit_event("topic:error", scope=assignee, data={"topic_id": topic_id, "name": topic["name"], "error": error_message})

    # Notify UI clients
    _emit_topics_update()

    return _load_topic(topic_id)


# =============================================================================
# AGENT QUERY FUNCTIONS (non-tool helpers for API)
# =============================================================================

def get_topics_completed_by_agent(agent_id: str, limit: int = 20) -> List[dict]:
    """Get topics that were completed by a specific agent.

    Queries the topic_logs table for 'completed' actions by the given agent,
    then loads the full topic records.

    Args:
        agent_id: The agent ID to query
        limit: Maximum number of topics to return (default 20)

    Returns:
        List of topic dicts, most recently completed first
    """
    conn = _get_connection()
    cursor = conn.execute('''
        SELECT DISTINCT tl.topic_id, tl.timestamp
        FROM topic_logs tl
        WHERE tl.agent = ? AND tl.action = 'completed'
        ORDER BY tl.timestamp DESC
        LIMIT ?
    ''', (agent_id, limit))

    topics = []
    for row in cursor:
        topic = _load_topic(row["topic_id"])
        if topic:
            topics.append(topic)

    return topics


# =============================================================================
# SYNC FUNCTIONS - Export/Import for bidirectional sync
# =============================================================================

def export_topics() -> dict:
    """Export all topics and logs for sync.

    Returns a dict with:
    - topics: List of all topic records
    - logs: List of all log entries
    - exported_at: Timestamp of export
    """
    from datetime import datetime, UTC

    conn = _get_connection()

    # Export all topics
    cursor = conn.execute("SELECT * FROM topics ORDER BY created_at")
    topics = []
    for row in cursor:
        topic = dict(row)
        # Convert tags from JSON string to list
        if topic.get("tags"):
            topic["tags"] = json.loads(topic["tags"])
        else:
            topic["tags"] = []
        # Convert someday to bool
        topic["someday"] = bool(topic.get("someday", 0))
        topics.append(topic)

    # Export all logs
    cursor = conn.execute(
        "SELECT topic_id, timestamp, agent, action FROM topic_logs ORDER BY id"
    )
    logs = [dict(row) for row in cursor]

    return {
        "topics": topics,
        "logs": logs,
        "exported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def import_topics(data: dict, merge: bool = True) -> dict:
    """Import topics and logs from sync data.

    Args:
        data: Dict with 'topics' and 'logs' keys from export_topics()
        merge: If True, merge with existing data. If False, replace.

    Returns:
        Dict with import results: created, updated, skipped counts
    """
    topics = data.get("topics", [])
    logs = data.get("logs", [])

    created = 0
    updated = 0
    skipped = 0
    log_count = 0

    conn = _get_connection()

    # Get existing topic IDs and their updated_at timestamps
    existing = {}
    cursor = conn.execute("SELECT id, updated_at FROM topics")
    for row in cursor:
        existing[row["id"]] = row["updated_at"]

    # Import topics (order matters for parent_id relationships)
    # Use topological sort to ensure parents are created before children
    def topological_sort(topics_list):
        """Sort topics so parents come before children."""
        # Build lookup and dependency graph
        by_id = {t["id"]: t for t in topics_list}
        result = []
        visited = set()

        def visit(topic):
            if topic["id"] in visited:
                return
            visited.add(topic["id"])
            # Visit parent first if it's in our import set
            parent_id = topic.get("parent_id")
            if parent_id and parent_id in by_id:
                visit(by_id[parent_id])
            result.append(topic)

        for topic in topics_list:
            visit(topic)
        return result

    sorted_topics = topological_sort(topics)

    for topic in sorted_topics:
        topic_id = topic["id"]
        tags_json = json.dumps(topic.get("tags", []))
        someday_int = int(topic.get("someday", False))

        if topic_id in existing:
            if merge:
                # Compare updated_at to decide if we should update
                local_updated = existing[topic_id]
                remote_updated = topic.get("updated_at", "")

                if remote_updated > local_updated:
                    # Remote is newer, update
                    with _transaction() as conn:
                        conn.execute('''
                            UPDATE topics SET
                                name = ?, parent_id = ?, status = ?, updated_at = ?,
                                created_by = ?, description = ?, due_date = ?,
                                someday = ?, tags = ?, assignee = ?, agent_id = ?,
                                pending_from = ?, completed_at = ?
                            WHERE id = ?
                        ''', (
                            topic["name"], topic.get("parent_id"), topic["status"],
                            topic["updated_at"], topic.get("created_by", "user"),
                            topic.get("description"), topic.get("due_date"),
                            someday_int, tags_json, topic.get("assignee"),
                            topic.get("agent_id"), topic.get("pending_from"),
                            topic.get("completed_at"), topic_id
                        ))
                    updated += 1
                else:
                    skipped += 1
            else:
                skipped += 1
        else:
            # New topic - insert
            with _transaction() as conn:
                conn.execute('''
                    INSERT INTO topics (
                        id, name, parent_id, status, created_at, updated_at,
                        created_by, description, due_date, someday, tags,
                        assignee, agent_id, pending_from, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    topic_id, topic["name"], topic.get("parent_id"), topic["status"],
                    topic["created_at"], topic["updated_at"],
                    topic.get("created_by", "user"), topic.get("description"),
                    topic.get("due_date"), someday_int, tags_json,
                    topic.get("assignee"), topic.get("agent_id"),
                    topic.get("pending_from"), topic.get("completed_at")
                ))
            created += 1

    # Import logs (deduplicate by topic_id + timestamp + agent + action)
    existing_logs = set()
    cursor = conn.execute(
        "SELECT topic_id, timestamp, agent, action FROM topic_logs"
    )
    for row in cursor:
        key = (row["topic_id"], row["timestamp"], row["agent"], row["action"])
        existing_logs.add(key)

    for log in logs:
        key = (log["topic_id"], log["timestamp"], log["agent"], log["action"])
        if key not in existing_logs:
            # Check that topic exists
            if log["topic_id"] in existing or any(t["id"] == log["topic_id"] for t in topics):
                with _transaction() as conn:
                    try:
                        conn.execute('''
                            INSERT INTO topic_logs (topic_id, timestamp, agent, action)
                            VALUES (?, ?, ?, ?)
                        ''', (log["topic_id"], log["timestamp"], log["agent"], log["action"]))
                        log_count += 1
                    except Exception:
                        pass  # Skip if topic doesn't exist

    # Notify UI if changes were made
    if created > 0 or updated > 0:
        _emit_topics_update()

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "logs_imported": log_count,
    }


