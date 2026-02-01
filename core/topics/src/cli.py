import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import secrets

import typer

from src.config import (
    OVERRIDE_CONFIG_FILENAME,
    config_dir,
    data_dir,
    get_value,
    load_config,
    parse_value,
    set_value,
    write_override,
)

app = typer.Typer(help="Euda topics CLI.", invoke_without_command=True)
config_app = typer.Typer(help="Inspect or update config.json overrides and merged defaults.")


@app.callback()
def app_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


app.add_typer(config_app, name="config")


STATES = {"todo", "working", "done", "error", "archived"}


@dataclass(frozen=True)
class Topic:
    id: str
    name: str
    description: str | None
    state: str
    assignee: str
    tags: list[str]
    parent_id: str | None
    created_at: str
    updated_at: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().isoformat()


def _validate_state(state: str) -> str:
    normalized = state.strip().lower()
    if normalized not in STATES:
        raise typer.BadParameter("State must be one of: todo, working, done, error, archived.")
    return normalized


def _ulid() -> str:
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    timestamp_ms = int(_utc_now().timestamp() * 1000)
    rand = int.from_bytes(secrets.token_bytes(10), "big")
    value = (timestamp_ms << 80) | rand
    chars = []
    for _ in range(26):
        value, index = divmod(value, 32)
        chars.append(alphabet[index])
    return "".join(reversed(chars))


def _db_path() -> Path:
    return data_dir() / "db.sqlite"


def _assets_dir(topic_id: str) -> Path:
    return data_dir() / "assets" / topic_id


def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS topics (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            state TEXT NOT NULL,
            assignee TEXT NOT NULL,
            tags TEXT NOT NULL,
            parent_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_parent ON topics(parent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_state ON topics(state)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_assignee ON topics(assignee)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_updated ON topics(updated_at)")
    conn.commit()
    return conn


def _row_to_topic(row: sqlite3.Row) -> Topic:
    return Topic(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        state=row["state"],
        assignee=row["assignee"],
        tags=json.loads(row["tags"]),
        parent_id=row["parent_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _topic_to_dict(topic: Topic) -> dict:
    return {
        "id": topic.id,
        "name": topic.name,
        "description": topic.description,
        "state": topic.state,
        "assignee": topic.assignee,
        "tags": topic.tags,
        "parent_id": topic.parent_id,
        "created_at": topic.created_at,
        "updated_at": topic.updated_at,
    }


def _fetch_topic(conn: sqlite3.Connection, topic_id: str) -> Topic | None:
    row = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
    if row is None:
        return None
    return _row_to_topic(row)


def _ensure_parent(conn: sqlite3.Connection, parent_id: str | None) -> None:
    if not parent_id:
        return
    row = conn.execute("SELECT 1 FROM topics WHERE id = ?", (parent_id,)).fetchone()
    if row is None:
        raise typer.BadParameter(f"Unknown parent id: {parent_id}")


def _normalize_assignee(value: str | None) -> str:
    if value is None:
        return "none"
    stripped = value.strip()
    return stripped if stripped else "none"


def _parse_tags(tags: Iterable[str] | None) -> list[str]:
    if not tags:
        return []
    cleaned = [tag.strip() for tag in tags if tag.strip()]
    return cleaned


def _query_with_filters(
    conn: sqlite3.Connection,
    *,
    query: str | None,
    state: str | None,
    assignee: str | None,
    parent_id: str | None,
) -> list[sqlite3.Row]:
    clauses: list[str] = []
    params: list[str] = []
    if state is not None:
        clauses.append("state = ?")
        params.append(state)
    if assignee is not None:
        clauses.append("assignee = ?")
        params.append(assignee)
    if parent_id is not None:
        clauses.append("parent_id = ?")
        params.append(parent_id)

    if query:
        tokens = [token for token in query.lower().split() if token.strip()]
        for token in tokens:
            clauses.append(
                "(" + " OR ".join(
                    [
                        "lower(id) LIKE ?",
                        "lower(name) LIKE ?",
                        "lower(description) LIKE ?",
                        "lower(state) LIKE ?",
                        "lower(assignee) LIKE ?",
                        "lower(tags) LIKE ?",
                        "lower(parent_id) LIKE ?",
                    ]
                ) + ")"
            )
            pattern = f"%{token}%"
            params.extend([pattern] * 7)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM topics {where} ORDER BY created_at DESC", params
    ).fetchall()
    return rows


def _filter_tags(rows: list[sqlite3.Row], tag: str | None) -> list[sqlite3.Row]:
    if not tag:
        return rows
    tag_lower = tag.strip().lower()
    filtered = []
    for row in rows:
        tags = json.loads(row["tags"])
        if any(existing.lower() == tag_lower for existing in tags):
            filtered.append(row)
    return filtered


def _descendant_ids(conn: sqlite3.Connection, topic_id: str) -> list[str]:
    rows = conn.execute(
        """
        WITH RECURSIVE descendants(id) AS (
            SELECT id FROM topics WHERE id = ?
            UNION ALL
            SELECT topics.id FROM topics
            JOIN descendants ON topics.parent_id = descendants.id
        )
        SELECT id FROM descendants
        """,
        (topic_id,),
    ).fetchall()
    return [row["id"] for row in rows]


@config_app.command("get", help="Get a merged config value (defaults + overrides).")
def config_get(key: str = typer.Argument(..., help="Config key, supports dot paths.")) -> None:
    config, _ = load_config()
    try:
        value = get_value(config, key)
    except KeyError:
        typer.echo(f"Missing key: {key}", err=True)
        raise typer.Exit(code=1)
    if isinstance(value, (dict, list)):
        typer.echo(json.dumps(value, indent=2, sort_keys=True))
    else:
        typer.echo(value)


@config_app.command("set", help="Set a config.json override (dot path).")
def config_set(
    key: str = typer.Argument(..., help="Config key, supports dot paths."),
    value: str = typer.Argument(..., help="JSON value or raw string."),
) -> None:
    _, override = load_config()
    parsed = parse_value(value)
    set_value(override, key, parsed)
    write_override(override)
    if isinstance(parsed, (dict, list)):
        typer.echo(json.dumps(parsed, indent=2, sort_keys=True))
    else:
        typer.echo(parsed)


@config_app.command("cat", help="Print raw config.json (overrides only).")
def config_cat() -> None:
    path = config_dir() / OVERRIDE_CONFIG_FILENAME
    if not path.exists():
        return
    typer.echo(path.read_text(encoding="utf-8").rstrip("\n"))


@config_app.command("cat-full", help="Print the merged config (defaults + overrides).")
def config_cat_full() -> None:
    config, _ = load_config()
    typer.echo(json.dumps(config, indent=2, sort_keys=True))


@config_app.command("write", help="Replace config.json with a full JSON object.")
def config_write(
    payload: str | None = typer.Argument(
        None, help="Full JSON object to write to config.json. Reads stdin if omitted or '-'."
    ),
) -> None:
    if payload is None or payload == "-":
        payload = typer.get_text_stream("stdin").read()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        typer.echo("Payload must be valid JSON.", err=True)
        raise typer.Exit(code=1)
    if not isinstance(data, dict):
        typer.echo("Payload must be a JSON object.", err=True)
        raise typer.Exit(code=1)
    write_override(data)
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


@app.command(help="Create a topic.")
def create(
    name: str = typer.Argument(..., help="Topic name."),
    description: str | None = typer.Argument(
        None, help="Topic description. Reads stdin when omitted or '-'."
    ),
    state: str = typer.Option("todo", "--state", help="Topic state."),
    assignee: str | None = typer.Option(None, "--assignee", help="Assigned agent."),
    tag: list[str] | None = typer.Option(None, "--tag", help="Tag (repeatable)."),
    parent_id: str | None = typer.Option(None, "--parent-id", help="Parent topic id."),
) -> None:
    if description is None or description == "-":
        description = typer.get_text_stream("stdin").read().rstrip("\n")
    state = _validate_state(state)
    assignee_value = _normalize_assignee(assignee)
    tags = _parse_tags(tag)
    now = _utc_iso()

    conn = _connect()
    _ensure_parent(conn, parent_id)
    topic_id = _ulid()
    conn.execute(
        """
        INSERT INTO topics
        (id, name, description, state, assignee, tags, parent_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            topic_id,
            name,
            description if description else None,
            state,
            assignee_value,
            json.dumps(tags),
            parent_id,
            now,
            now,
        ),
    )
    conn.commit()
    topic = _fetch_topic(conn, topic_id)
    if topic is None:
        raise typer.Exit(code=1)
    typer.echo(json.dumps(_topic_to_dict(topic), sort_keys=True))


@app.command(help="Get a topic by id.")
def get(
    topic_id: str = typer.Argument(..., help="Topic id."),
) -> None:
    conn = _connect()
    topic = _fetch_topic(conn, topic_id)
    if topic is None:
        typer.echo("Topic not found.", err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps(_topic_to_dict(topic), sort_keys=True))


@app.command(help="List topics.")
def list(
    state: str | None = typer.Option(None, "--state", help="Filter by state."),
    assignee: str | None = typer.Option(None, "--assignee", help="Filter by assignee."),
    parent_id: str | None = typer.Option(None, "--parent-id", help="Filter by parent id."),
    tag: str | None = typer.Option(None, "--tag", help="Filter by tag."),
) -> None:
    if state is not None:
        state = _validate_state(state)
    conn = _connect()
    rows = _query_with_filters(conn, query=None, state=state, assignee=assignee, parent_id=parent_id)
    rows = _filter_tags(rows, tag)
    for row in rows:
        topic = _row_to_topic(row)
        typer.echo(json.dumps(_topic_to_dict(topic), sort_keys=True))


@app.command(help="Search topics by keyword.")
def search(
    query: str = typer.Option(..., "--query", help="Search query."),
    state: str | None = typer.Option(None, "--state", help="Filter by state."),
    assignee: str | None = typer.Option(None, "--assignee", help="Filter by assignee."),
    parent_id: str | None = typer.Option(None, "--parent-id", help="Filter by parent id."),
    tag: str | None = typer.Option(None, "--tag", help="Filter by tag."),
) -> None:
    if state is not None:
        state = _validate_state(state)
    conn = _connect()
    rows = _query_with_filters(conn, query=query, state=state, assignee=assignee, parent_id=parent_id)
    rows = _filter_tags(rows, tag)
    for row in rows:
        topic = _row_to_topic(row)
        typer.echo(json.dumps(_topic_to_dict(topic), sort_keys=True))


@app.command(help="Update a topic.")
def update(
    topic_id: str = typer.Argument(..., help="Topic id."),
    name: str | None = typer.Option(None, "--name", help="Update name."),
    description: str | None = typer.Option(None, "--description", help="Update description."),
    state: str | None = typer.Option(None, "--state", help="Update state."),
    assignee: str | None = typer.Option(None, "--assignee", help="Update assignee."),
    tag: list[str] | None = typer.Option(None, "--tag", help="Replace tags (repeatable)."),
    clear_tags: bool = typer.Option(False, "--clear-tags", help="Clear tags."),
    parent_id: str | None = typer.Option(None, "--parent-id", help="Update parent id."),
    clear_parent: bool = typer.Option(False, "--clear-parent", help="Clear parent."),
) -> None:
    conn = _connect()
    topic = _fetch_topic(conn, topic_id)
    if topic is None:
        typer.echo("Topic not found.", err=True)
        raise typer.Exit(code=1)

    updates: dict[str, object] = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        if description == "-":
            description = typer.get_text_stream("stdin").read().rstrip("\n")
        updates["description"] = description if description else None
    if state is not None:
        updates["state"] = _validate_state(state)
    if assignee is not None:
        updates["assignee"] = _normalize_assignee(assignee)
    if clear_tags and tag:
        typer.echo("Use either --tag or --clear-tags, not both.", err=True)
        raise typer.Exit(code=1)
    if clear_tags:
        updates["tags"] = json.dumps([])
    elif tag is not None:
        updates["tags"] = json.dumps(_parse_tags(tag))
    if clear_parent and parent_id:
        typer.echo("Use either --parent-id or --clear-parent, not both.", err=True)
        raise typer.Exit(code=1)
    if clear_parent:
        updates["parent_id"] = None
    elif parent_id is not None:
        _ensure_parent(conn, parent_id)
        updates["parent_id"] = parent_id

    if not updates:
        typer.echo(json.dumps(_topic_to_dict(topic), sort_keys=True))
        return

    updates["updated_at"] = _utc_iso()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [topic_id]
    conn.execute(f"UPDATE topics SET {assignments} WHERE id = ?", values)
    conn.commit()
    updated = _fetch_topic(conn, topic_id)
    if updated is None:
        raise typer.Exit(code=1)
    typer.echo(json.dumps(_topic_to_dict(updated), sort_keys=True))


@app.command(help="Delete a topic and its descendants.")
def delete(
    topic_id: str = typer.Argument(..., help="Topic id."),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
) -> None:
    conn = _connect()
    topic = _fetch_topic(conn, topic_id)
    if topic is None:
        typer.echo("Topic not found.", err=True)
        raise typer.Exit(code=1)
    if not yes:
        confirmation = typer.prompt("Type 'yes' to confirm", default="", show_default=False)
        if confirmation.strip().lower() != "yes":
            typer.echo("Aborted.")
            raise typer.Exit(code=1)

    ids = _descendant_ids(conn, topic_id)
    conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
    conn.commit()
    for item_id in ids:
        assets_path = _assets_dir(item_id)
        if assets_path.exists():
            shutil.rmtree(assets_path)
    typer.echo(json.dumps({"id": topic_id, "deleted": True}, sort_keys=True))


if __name__ == "__main__":
    app()
