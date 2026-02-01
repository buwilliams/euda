from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable

import typer
import shared_router

from src.config import (
    OVERRIDE_CONFIG_FILENAME,
    config_dir,
    data_dir,
    get_value,
    load_config,
    parse_value,
    set_value,
    write_override,
    save_json,
    load_json,
)

app = typer.Typer(help="Euda identity CLI.", invoke_without_command=True)
config_app = typer.Typer(help="Inspect or update config.json overrides and merged defaults.")
schema_app = typer.Typer(help="Manage cognitive traits schemas.")
identity_app = typer.Typer(help="Manage identities.")


@app.callback()
def app_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


app.add_typer(config_app, name="config")
app.add_typer(schema_app, name="schema")
app.add_typer(identity_app, name="identity")


@dataclass(frozen=True)
class SourceItem:
    label: str
    content: str
    metadata: dict


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().isoformat()


def _today_utc() -> date:
    return _utc_now().date()


def _schema_dir() -> Path:
    return data_dir() / "schema"


def _identity_root() -> Path:
    return data_dir() / "identity"


def _identity_dir(schema: str) -> Path:
    return _identity_root() / schema


def _prompt_path(config: dict, key: str) -> Path:
    prompts = config.get("prompts", {}) or {}
    filename = prompts.get(key)
    if not filename:
        raise typer.BadParameter(f"Missing prompts.{key} in config.")
    return data_dir() / filename


def _read_prompt(config: dict, key: str) -> str:
    path = _prompt_path(config, key)
    if not path.exists():
        raise typer.BadParameter(f"Missing prompt template: {path}")
    return path.read_text(encoding="utf-8")


def _read_stdin_if_available() -> str:
    if sys.stdin is None or sys.stdin.isatty():
        return ""
    return typer.get_text_stream("stdin").read()


def _parse_traits_payload(payload: str) -> list[dict]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter("Traits payload must be valid JSON.") from exc
    traits: list[dict] = []
    if isinstance(data, dict):
        for name, instruction in data.items():
            traits.append({"name": str(name), "instruction": str(instruction)})
    elif isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                raise typer.BadParameter("Trait list items must be objects.")
            name = item.get("name")
            instruction = item.get("instruction")
            if not name or not instruction:
                raise typer.BadParameter("Each trait needs name and instruction.")
            traits.append({"name": str(name), "instruction": str(instruction)})
    else:
        raise typer.BadParameter("Traits payload must be a list or object.")
    if not traits:
        raise typer.BadParameter("Traits payload is empty.")
    return traits


def _schema_paths(schema: str) -> list[Path]:
    base = _schema_dir()
    if not base.exists():
        return []
    return sorted(base.glob(f"{schema}-*.json"))


def _schema_version_from_path(path: Path) -> int:
    name = path.stem
    try:
        return int(name.rsplit("-", 1)[-1])
    except ValueError:
        return 0


def _latest_schema_path(schema: str) -> Path | None:
    paths = _schema_paths(schema)
    if not paths:
        return None
    return max(paths, key=_schema_version_from_path)


def _latest_schema(schema: str) -> dict | None:
    path = _latest_schema_path(schema)
    if path is None:
        return None
    return load_json(path)


def _next_schema_version(schema: str) -> int:
    path = _latest_schema_path(schema)
    if path is None:
        return 1
    return _schema_version_from_path(path) + 1


def _schema_id_for(schema: str) -> str:
    latest = _latest_schema(schema)
    if latest and latest.get("schema_id"):
        return str(latest["schema_id"])
    return uuid.uuid4().hex


def _schema_path(schema: str, version: int) -> Path:
    return _schema_dir() / f"{schema}-{version}.json"


def _identity_paths(schema: str, name: str) -> list[Path]:
    base = _identity_dir(schema)
    if not base.exists():
        return []
    return sorted(base.glob(f"{name}-*.json"))


def _identity_version_from_path(path: Path) -> int:
    name = path.stem
    try:
        return int(name.rsplit("-", 1)[-1])
    except ValueError:
        return 0


def _latest_identity_path(schema: str, name: str) -> Path | None:
    paths = _identity_paths(schema, name)
    if not paths:
        return None
    return max(paths, key=_identity_version_from_path)


def _latest_identity(schema: str, name: str) -> dict | None:
    path = _latest_identity_path(schema, name)
    if path is None:
        return None
    return load_json(path)


def _next_identity_version(schema: str, name: str) -> int:
    path = _latest_identity_path(schema, name)
    if path is None:
        return 1
    return _identity_version_from_path(path) + 1


def _identity_path(schema: str, name: str, version: int) -> Path:
    return _identity_dir(schema) / f"{name}-{version}.json"


def _working_identity_path(schema: str, name: str, run_id: str) -> Path:
    return _identity_dir(schema) / f"{name}-working-{run_id}.json"


def _latest_working_path(schema: str, name: str) -> Path | None:
    base = _identity_dir(schema)
    if not base.exists():
        return None
    candidates = list(base.glob(f"{name}-working-*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _write_working_identity(
    *,
    schema: str,
    name: str,
    run_id: str,
    current_identity: str,
    schema_data: dict,
    metadata: dict,
) -> None:
    working_payload = {
        "name": name,
        "schema": schema,
        "schema_id": schema_data.get("schema_id"),
        "schema_version": schema_data.get("version"),
        "version": None,
        "created_at": None,
        "updated_at": _utc_iso(),
        "content": current_identity.strip() + "\n",
        "metadata": {"working": True, "run_id": run_id, **metadata},
    }
    working_path = _working_identity_path(schema, name, run_id)
    working_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(working_path, working_payload)


def _empty_identity_markdown(traits: Iterable[dict]) -> str:
    lines = []
    for trait in traits:
        lines.append(f"## {trait['name']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _traits_markdown(traits: Iterable[dict]) -> str:
    lines = []
    for trait in traits:
        lines.append(f"- {trait['name']}: {trait['instruction']}")
    return "\n".join(lines)


def _render_prompt(
    template: str,
    *,
    schema: dict,
    current_identity: str,
    source: SourceItem,
) -> str:
    return template.format(
        schema_name=schema.get("schema"),
        schema_version=schema.get("version"),
        schema_id=schema.get("schema_id"),
        traits_markdown=_traits_markdown(schema.get("traits", [])),
        current_identity=current_identity.strip() or "(empty)",
        source_label=source.label,
        source_metadata=json.dumps(source.metadata, sort_keys=True),
        source_content=source.content.strip() or "(empty)",
    )


def _call_llm(
    system_prompt: str,
    prompt: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    retries: int = 0,
    retry_wait: float = 2.0,
    timeout: float | None = 30.0,
) -> str:
    args = ["call", system_prompt, "-"]
    if provider:
        args.extend(["--provider", provider])
    if model:
        args.extend(["--model", model])
    attempt = 0
    while True:
        try:
            _log_event(
                "llm_call_started",
                {
                    "provider": provider,
                    "model": model,
                    "prompt_chars": len(prompt),
                    "system_chars": len(system_prompt),
                    "timeout": timeout,
                },
            )
            result = shared_router.run_core(
                "llm",
                args,
                input_text=prompt,
                timeout=timeout,
            )
            _log_event(
                "llm_call_completed",
                {"provider": provider, "model": model, "response_chars": len(result.stdout)},
            )
            return result.stdout
        except Exception as exc:
            message = str(exc)
            lower = message.lower()
            transient = (
                "temporarily unavailable" in lower
                or "unavailable" in lower
                or "timed out" in lower
                or "time out" in lower
            )
            if attempt >= retries or not transient:
                _log_event(
                    "llm_call_failed",
                    {"provider": provider, "model": model, "error": message},
                )
                raise
            attempt += 1
            _log_event(
                "llm_retry",
                {"attempt": attempt, "error": message, "wait_seconds": retry_wait},
            )
            time.sleep(retry_wait)


def _log_event(event: str, payload: dict) -> None:
    message = json.dumps({"event": event, **payload}, sort_keys=True)
    try:
        shared_router.run_core(
            "logs",
            ["write", message, "--type", "system", "--id", "identity"],
        )
    except Exception:
        return


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _range_from_filters(
    years: int | None,
    days: int | None,
    hours: int | None,
) -> tuple[datetime, datetime] | None:
    if years is None and days is None and hours is None:
        return None
    total_days = (years or 0) * 365 + (days or 0)
    delta = timedelta(days=total_days, hours=hours or 0)
    end_dt = _utc_now()
    start_dt = end_dt - delta
    return start_dt, end_dt


def _in_range(timestamp: datetime | None, window: tuple[datetime, datetime] | None) -> bool:
    if timestamp is None:
        return False
    if window is None:
        return True
    start_dt, end_dt = window
    return start_dt <= timestamp <= end_dt


def _fetch_memory_entries(
    *,
    term: str,
    entry_type: str,
    entry_id: str,
    window: tuple[datetime, datetime] | None,
    years: int | None,
    days: int | None,
    hours: int | None,
) -> list[dict]:
    args = [
        "read",
        "--term",
        term,
        "--type",
        entry_type,
        "--id",
        entry_id,
    ]
    total_days = (years or 0) * 365 + (days or 0)
    if window is not None:
        if hours is not None:
            args.extend(["--hours", str(hours)])
        if total_days:
            args.extend(["--days", str(total_days)])
    else:
        args.extend(["--start-date", "1970-01-01", "--end-date", _today_utc().isoformat()])
    result = shared_router.run_core("memory", args)
    entries: list[dict] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            entries.append(data)
    if window is None:
        return entries
    filtered: list[dict] = []
    for entry in entries:
        ts = _parse_iso_timestamp(entry.get("timestamp"))
        if _in_range(ts, window):
            filtered.append(entry)
    return filtered


def _format_memory_entry(entry: dict) -> SourceItem:
    metadata = {
        "timestamp": entry.get("timestamp"),
        "type": entry.get("type"),
        "id": entry.get("id"),
        "term": entry.get("term"),
        "index": entry.get("index"),
    }
    if "memory" in entry:
        content = entry.get("memory") or ""
    else:
        content = json.dumps(entry, sort_keys=True)
    return SourceItem(label="memory", content=str(content), metadata=metadata)


def _fetch_topics(window: tuple[datetime, datetime] | None) -> list[dict]:
    result = shared_router.run_core("topics", ["list"])
    entries: list[dict] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            entries.append(data)
    if window is None:
        return entries
    filtered: list[dict] = []
    for entry in entries:
        ts = _parse_iso_timestamp(entry.get("updated_at"))
        if _in_range(ts, window):
            filtered.append(entry)
    return filtered


def _format_topic(entry: dict) -> SourceItem:
    metadata = {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "state": entry.get("state"),
        "assignee": entry.get("assignee"),
        "updated_at": entry.get("updated_at"),
    }
    content = json.dumps(entry, sort_keys=True)
    return SourceItem(label="topic", content=content, metadata=metadata)


def _split_by_chars(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks


def _summarize_text(
    config: dict,
    source: SourceItem,
    *,
    max_chars: int,
    provider: str | None,
    model: str | None,
    retries: int,
    retry_wait: float,
    timeout: float | None,
) -> str:
    _log_event(
        "summary_started",
        {
            "label": source.label,
            "metadata": source.metadata,
            "content_chars": len(source.content),
            "max_chars": max_chars,
        },
    )
    system_prompt = _read_prompt(config, "summary_system")
    user_template = _read_prompt(config, "summary_user")
    chunks = _split_by_chars(source.content, max_chars)
    summaries: list[str] = []
    _log_event(
        "summary_chunks_ready",
        {"label": source.label, "chunk_count": len(chunks)},
    )
    for chunk in chunks:
        _log_event(
            "summary_chunk_started",
            {"label": source.label, "chunk_chars": len(chunk)},
        )
        prompt = user_template.format(
            source_label=source.label,
            source_metadata=json.dumps(source.metadata, sort_keys=True),
            source_content=chunk,
        )
        summary = _call_llm(
            system_prompt,
            prompt,
            provider=provider,
            model=model,
            retries=retries,
            retry_wait=retry_wait,
            timeout=timeout,
        ).strip()
        if summary:
            summaries.append(summary)
        _log_event(
            "summary_chunk_completed",
            {"label": source.label, "summary_chars": len(summary)},
        )
    if not summaries:
        _log_event(
            "summary_completed",
            {"label": source.label, "summary_chars": 0},
        )
        return ""
    if len(summaries) == 1:
        _log_event(
            "summary_completed",
            {"label": source.label, "summary_chars": len(summaries[0])},
        )
        return summaries[0]
    combined = "\n\n".join(summaries)
    _log_event(
        "summary_merge_started",
        {"label": source.label, "combined_chars": len(combined)},
    )
    prompt = user_template.format(
        source_label=source.label,
        source_metadata=json.dumps({**source.metadata, "summary_stage": "merge"}, sort_keys=True),
        source_content=combined,
    )
    merged = _call_llm(
        system_prompt,
        prompt,
        provider=provider,
        model=model,
        retries=retries,
        retry_wait=retry_wait,
        timeout=timeout,
    ).strip()
    _log_event(
        "summary_completed",
        {"label": source.label, "summary_chars": len(merged)},
    )
    return merged


def _batch_sources_by_chars(sources: list[SourceItem], max_chars: int) -> list[SourceItem]:
    if max_chars <= 0:
        return sources
    batches: list[SourceItem] = []
    current_parts: list[str] = []
    current_meta: list[dict] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_parts, current_meta, current_len
        if not current_parts:
            return
        content = "\n\n".join(current_parts)
        batches.append(SourceItem(label="batch", content=content, metadata={"items": current_meta}))
        current_parts = []
        current_meta = []
        current_len = 0

    for source in sources:
        header = f"### Source\\nLabel: {source.label}\\nMetadata: {json.dumps(source.metadata, sort_keys=True)}\\n\\n"
        block = header + source.content
        block_len = len(block)
        if current_len + block_len > max_chars and current_parts:
            flush()
        current_parts.append(block)
        current_meta.append({"label": source.label, "metadata": source.metadata})
        current_len += block_len

    flush()
    _log_event(
        "batching_completed",
        {"batch_count": len(batches), "max_chars": max_chars},
    )
    return batches


def _identity_versions(schema: str, name: str) -> list[dict]:
    paths = _identity_paths(schema, name)
    entries: list[dict] = []
    for path in sorted(paths, key=_identity_version_from_path):
        data = load_json(path)
        if data:
            entries.append(data)
    return entries


def _previous_identity_for_range(
    schema: str,
    name: str,
    window: tuple[datetime, datetime] | None,
) -> dict | None:
    latest = _latest_identity(schema, name)
    if latest is None:
        return None
    return latest


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


@schema_app.command("create", help="Create a cognitive traits schema.")
def schema_create(
    schema: str = typer.Argument(..., help="Schema name."),
    traits: str | None = typer.Argument(
        None,
        help="JSON traits payload (list or object). Reads stdin if omitted or '-'.",
    ),
) -> None:
    if traits is None or traits == "-":
        traits = typer.get_text_stream("stdin").read()
    parsed_traits = _parse_traits_payload(traits)
    version = _next_schema_version(schema)
    schema_id = _schema_id_for(schema)
    payload = {
        "schema": schema,
        "schema_id": schema_id,
        "version": version,
        "created_at": _utc_iso(),
        "traits": parsed_traits,
    }
    path = _schema_path(schema, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_json(path, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@schema_app.command("get", help="Get a schema by name and version.")
def schema_get(
    schema: str = typer.Argument(..., help="Schema name."),
    version: int | None = typer.Option(None, "--version", help="Schema version. Defaults to latest."),
) -> None:
    if version is None:
        data = _latest_schema(schema)
        if data is None:
            typer.echo("Schema not found.", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(data, indent=2, sort_keys=True))
        return
    path = _schema_path(schema, version)
    if not path.exists():
        typer.echo("Schema not found.", err=True)
        raise typer.Exit(code=1)
    data = load_json(path)
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


@schema_app.command("latest", help="Get the latest schema version.")
def schema_latest(
    schema: str = typer.Argument(..., help="Schema name."),
) -> None:
    data = _latest_schema(schema)
    if data is None:
        typer.echo("Schema not found.", err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


@schema_app.command("list", help="List schemas and versions.")
def schema_list() -> None:
    base = _schema_dir()
    if not base.exists():
        return
    for path in sorted(base.glob("*.json"), key=_schema_version_from_path):
        data = load_json(path)
        if data:
            typer.echo(json.dumps(data, sort_keys=True))


@identity_app.command("create", help="Create a new identity version.")
def identity_create(
    name: str = typer.Argument(..., help="Identity name."),
    content: str | None = typer.Argument(
        None,
        help="Identity markdown content. Reads stdin if omitted or '-'.",
    ),
    schema: str | None = typer.Option(None, "--schema", help="Schema name (defaults to config)."),
    schema_version: int | None = typer.Option(
        None, "--schema-version", help="Schema version (defaults to latest)."
    ),
) -> None:
    config, _ = load_config()
    if schema is None:
        schema = config.get("default_schema")
    if not schema:
        typer.echo("Missing schema (set default_schema in config or pass --schema).", err=True)
        raise typer.Exit(code=1)
    if schema_version is None:
        schema_data = _latest_schema(schema)
    else:
        schema_data = load_json(_schema_path(schema, schema_version))
    if not schema_data:
        typer.echo("Schema not found.", err=True)
        raise typer.Exit(code=1)
    if content is None or content == "-":
        content = typer.get_text_stream("stdin").read()
    if not content.strip():
        typer.echo("Identity content is empty.", err=True)
        raise typer.Exit(code=1)
    version = _next_identity_version(schema, name)
    now = _utc_iso()
    payload = {
        "name": name,
        "schema": schema,
        "schema_id": schema_data.get("schema_id"),
        "schema_version": schema_data.get("version"),
        "version": version,
        "created_at": now,
        "updated_at": now,
        "content": content,
        "metadata": {},
    }
    path = _identity_path(schema, name, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_json(path, payload)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@identity_app.command("get", help="Get an identity by name and version.")
def identity_get(
    name: str = typer.Argument(..., help="Identity name."),
    schema: str | None = typer.Option(None, "--schema", help="Schema name (defaults to config)."),
    version: int | None = typer.Option(None, "--version", help="Identity version (defaults to latest)."),
) -> None:
    config, _ = load_config()
    if schema is None:
        schema = config.get("default_schema")
    if not schema:
        typer.echo("Missing schema (set default_schema in config or pass --schema).", err=True)
        raise typer.Exit(code=1)
    if version is None:
        data = _latest_identity(schema, name)
        if data is None:
            typer.echo("Identity not found.", err=True)
            raise typer.Exit(code=1)
        typer.echo(json.dumps(data, indent=2, sort_keys=True))
        return
    path = _identity_path(schema, name, version)
    if not path.exists():
        typer.echo("Identity not found.", err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps(load_json(path), indent=2, sort_keys=True))


@identity_app.command("latest", help="Get the latest identity version.")
def identity_latest(
    name: str = typer.Argument(..., help="Identity name."),
    schema: str | None = typer.Option(None, "--schema", help="Schema name (defaults to config)."),
) -> None:
    config, _ = load_config()
    if schema is None:
        schema = config.get("default_schema")
    if not schema:
        typer.echo("Missing schema (set default_schema in config or pass --schema).", err=True)
        raise typer.Exit(code=1)
    data = _latest_identity(schema, name)
    if data is None:
        typer.echo("Identity not found.", err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


@identity_app.command("list", help="List identity versions for a schema.")
def identity_list(
    schema: str | None = typer.Option(None, "--schema", help="Schema name (defaults to config)."),
) -> None:
    config, _ = load_config()
    if schema is None:
        schema = config.get("default_schema")
    if not schema:
        typer.echo("Missing schema (set default_schema in config or pass --schema).", err=True)
        raise typer.Exit(code=1)
    base = _identity_dir(schema)
    if not base.exists():
        return
    for path in sorted(base.glob("*.json"), key=_identity_version_from_path):
        data = load_json(path)
        if data:
            typer.echo(json.dumps(data, sort_keys=True))


@identity_app.command("tail-working", help="Tail the working identity file in real time.")
def identity_tail_working(
    name: str = typer.Argument(..., help="Identity name."),
    schema: str | None = typer.Option(None, "--schema", help="Schema name (defaults to config)."),
    run_id: str | None = typer.Option(None, "--run-id", help="Specific consolidate run id."),
    sleep_seconds: float = typer.Option(1.0, "--sleep", help="Sleep seconds between checks."),
    iterations: int | None = typer.Option(
        None, "--_iterations", hidden=True, help="Limit loop iterations (tests only)."
    ),
) -> None:
    config, _ = load_config()
    if schema is None:
        schema = config.get("default_schema")
    if not schema:
        typer.echo("Missing schema (set default_schema in config or pass --schema).", err=True)
        raise typer.Exit(code=1)
    path = _working_identity_path(schema, name, run_id) if run_id else None
    last_mtime: float | None = None
    remaining = iterations
    while True:
        if path is None:
            path = _latest_working_path(schema, name)
        if path is not None and path.exists():
            mtime = path.stat().st_mtime
            if last_mtime is None or mtime > last_mtime:
                data = load_json(path)
                if data:
                    typer.echo(json.dumps(data, sort_keys=True))
                last_mtime = mtime
        time.sleep(sleep_seconds)
        if remaining is not None:
            remaining -= 1
            if remaining <= 0:
                break


@app.command(help="Consolidate identity by extracting schema traits from data sources.")
def consolidate(
    name: str = typer.Argument(..., help="Identity name."),
    schema: str | None = typer.Option(None, "--schema", help="Schema name (defaults to config)."),
    schema_version: int | None = typer.Option(
        None, "--schema-version", help="Schema version (defaults to latest)."
    ),
    memory_term: str | None = typer.Option(None, "--memory-term", help="Memory term (short or long)."),
    memory_type: str | None = typer.Option(None, "--memory-type", help="Memory type."),
    memory_id: str | None = typer.Option(None, "--memory-id", help="Memory id."),
    input_text: list[str] = typer.Option(None, "--input", help="Inline text input (repeatable)."),
    no_stdin: bool = typer.Option(False, "--no-stdin", help="Disable stdin input."),
    no_memory: bool = typer.Option(False, "--no-memory", help="Disable memory input."),
    no_topics: bool = typer.Option(False, "--no-topics", help="Disable topics input."),
    no_input: bool = typer.Option(False, "--no-input", help="Disable inline input."),
    no_previous: bool = typer.Option(False, "--no-previous", help="Disable previous identity input."),
    years: int | None = typer.Option(None, "--years", help="Years backwards from now (UTC)."),
    days: int | None = typer.Option(None, "--days", help="Days backwards from now (UTC)."),
    hours: int | None = typer.Option(None, "--hours", help="Hours backwards from now (UTC)."),
    max_chars: int = typer.Option(200000, "--max-chars", help="Max chars per source batch."),
    summary_max_chars: int = typer.Option(
        20000, "--summary-max-chars", help="Max chars per summary chunk."
    ),
    provider: str | None = typer.Option(None, "--provider", help="LLM provider override."),
    model: str | None = typer.Option(None, "--model", help="LLM model override."),
    retries: int = typer.Option(2, "--retries", help="Retries on transient LLM errors."),
    retry_wait: float = typer.Option(2.0, "--retry-wait", help="Seconds to wait between retries."),
    llm_timeout: float | None = typer.Option(
        60.0, "--llm-timeout", help="Timeout in seconds for each LLM call."
    ),
) -> None:
    config, _ = load_config()
    if schema is None:
        schema = config.get("default_schema")
    if not schema:
        typer.echo("Missing schema (set default_schema in config or pass --schema).", err=True)
        raise typer.Exit(code=1)
    if schema_version is None:
        schema_data = _latest_schema(schema)
    else:
        schema_data = load_json(_schema_path(schema, schema_version))
    if not schema_data:
        typer.echo("Schema not found.", err=True)
        raise typer.Exit(code=1)

    window = _range_from_filters(years, days, hours)

    sources: list[SourceItem] = []
    stdin_text = ""
    if not no_stdin:
        stdin_text = _read_stdin_if_available()
        if stdin_text.strip():
            sources.append(SourceItem(label="stdin", content=stdin_text, metadata={}))

    if not no_input and input_text:
        for value in input_text:
            if value.strip():
                sources.append(SourceItem(label="input", content=value, metadata={}))

    memory_total = 0
    memory_done = 0
    if not no_memory and (memory_term or memory_type or memory_id):
        if not memory_term or not memory_type or not memory_id:
            typer.echo("Memory input requires --memory-term, --memory-type, and --memory-id.", err=True)
            raise typer.Exit(code=1)
        memory_entries = _fetch_memory_entries(
            term=memory_term,
            entry_type=memory_type,
            entry_id=memory_id,
            window=window,
            years=years,
            days=days,
            hours=hours,
        )
        memory_total = len(memory_entries)
        for entry in memory_entries:
            raw = _format_memory_entry(entry)
            summary = _summarize_text(
                config,
                raw,
                max_chars=summary_max_chars,
                provider=provider,
                model=model,
                retries=retries,
                retry_wait=retry_wait,
                timeout=llm_timeout,
            )
            if summary:
                sources.append(
                    SourceItem(
                        label="memory-summary",
                        content=summary,
                        metadata={**raw.metadata, "summary": True},
                    )
                )
            memory_done += 1
            _write_working_identity(
                schema=schema,
                name=name,
                run_id=run_id,
                current_identity=current_identity,
                schema_data=schema_data,
                metadata={
                    "stage": "summary",
                    "memory_progress": {"done": memory_done, "total": memory_total},
                    "time_filter": {"years": years, "days": days, "hours": hours},
                },
            )

    if not no_topics:
        topic_entries = _fetch_topics(window)
        for entry in topic_entries:
            sources.append(_format_topic(entry))

    previous_identity = None
    if not no_previous:
        previous_identity = _previous_identity_for_range(schema, name, window)

    system_prompt = _read_prompt(config, "system")
    user_template = _read_prompt(config, "user")

    if previous_identity is not None:
        current_identity = str(previous_identity.get("content") or "")
    else:
        current_identity = ""

    if not current_identity.strip():
        current_identity = _empty_identity_markdown(schema_data.get("traits", []))

    run_id = uuid.uuid4().hex
    _log_event(
        "consolidate_started",
        {
            "name": name,
            "schema": schema,
            "schema_version": schema_data.get("version"),
            "source_count": len(sources),
            "run_id": run_id,
            "time_filter": {"years": years, "days": days, "hours": hours},
        },
    )

    batched_sources = _batch_sources_by_chars(sources, max_chars)

    total_batches = len(batched_sources)
    for idx, source in enumerate(batched_sources, start=1):
        _log_event(
            "consolidate_source_started",
            {
                "name": name,
                "schema": schema,
                "label": source.label,
                "metadata": source.metadata,
                "batch_index": idx,
                "batch_count": total_batches,
                "run_id": run_id,
            },
        )
        prompt = _render_prompt(
            user_template,
            schema=schema_data,
            current_identity=current_identity,
            source=source,
        )
        current_identity = _call_llm(
            system_prompt,
            prompt,
            provider=provider,
            model=model,
            retries=retries,
            retry_wait=retry_wait,
            timeout=llm_timeout,
        ).strip()
        _log_event(
            "consolidate_source_completed",
            {
                "name": name,
                "schema": schema,
                "label": source.label,
                "metadata": source.metadata,
                "batch_index": idx,
                "batch_count": total_batches,
                "run_id": run_id,
                "content_chars": len(current_identity),
            },
        )
        _write_working_identity(
            schema=schema,
            name=name,
            run_id=run_id,
            current_identity=current_identity,
            schema_data=schema_data,
            metadata={
                "stage": "consolidate",
                "batch_index": idx,
                "batch_count": total_batches,
                "time_filter": {"years": years, "days": days, "hours": hours},
            },
        )

    now = _utc_iso()
    version = _next_identity_version(schema, name)
    payload = {
        "name": name,
        "schema": schema,
        "schema_id": schema_data.get("schema_id"),
        "schema_version": schema_data.get("version"),
        "version": version,
        "created_at": now,
        "updated_at": now,
        "content": current_identity.strip() + "\n",
        "metadata": {
            "consolidation": {
                "run_id": run_id,
                "sources": {
                    "stdin": bool(stdin_text.strip()),
                    "input_count": len(input_text or []),
                    "memory": None if no_memory else {
                        "term": memory_term,
                        "type": memory_type,
                        "id": memory_id,
                    },
                    "topics": not no_topics,
                    "previous_identity_version": previous_identity.get("version") if previous_identity else None,
                },
                "time_filter": {
                    "years": years,
                    "days": days,
                    "hours": hours,
                },
                "source_count": len(sources),
                "batch_count": len(batched_sources),
                "max_chars": max_chars,
                "summary_max_chars": summary_max_chars,
                "llm": {"provider": provider, "model": model, "timeout": llm_timeout},
            }
        },
    }
    path = _identity_path(schema, name, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_json(path, payload)
    working_path = _working_identity_path(schema, name, run_id)
    if working_path.exists():
        working_path.unlink()
    _log_event(
        "consolidate_completed",
        {
            "name": name,
            "schema": schema,
            "version": version,
            "source_count": len(sources),
            "run_id": run_id,
        },
    )
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command(help="Incrementally update the latest identity without creating a new version.")
def update(
    name: str = typer.Argument(..., help="Identity name."),
    schema: str | None = typer.Option(None, "--schema", help="Schema name (defaults to config)."),
    memory_term: str | None = typer.Option(None, "--memory-term", help="Memory term (short or long)."),
    memory_type: str | None = typer.Option(None, "--memory-type", help="Memory type."),
    memory_id: str | None = typer.Option(None, "--memory-id", help="Memory id."),
    input_text: list[str] = typer.Option(None, "--input", help="Inline text input (repeatable)."),
    no_stdin: bool = typer.Option(False, "--no-stdin", help="Disable stdin input."),
    no_memory: bool = typer.Option(False, "--no-memory", help="Disable memory input."),
    no_topics: bool = typer.Option(False, "--no-topics", help="Disable topics input."),
    no_input: bool = typer.Option(False, "--no-input", help="Disable inline input."),
    include_history: bool = typer.Option(
        False, "--include-history", help="Include prior identity versions as data sources."
    ),
    years: int | None = typer.Option(None, "--years", help="Years backwards from now (UTC)."),
    days: int | None = typer.Option(None, "--days", help="Days backwards from now (UTC)."),
    hours: int | None = typer.Option(None, "--hours", help="Hours backwards from now (UTC)."),
    max_chars: int = typer.Option(200000, "--max-chars", help="Max chars per source batch."),
    summary_max_chars: int = typer.Option(
        20000, "--summary-max-chars", help="Max chars per summary chunk."
    ),
    provider: str | None = typer.Option(None, "--provider", help="LLM provider override."),
    model: str | None = typer.Option(None, "--model", help="LLM model override."),
    retries: int = typer.Option(2, "--retries", help="Retries on transient LLM errors."),
    retry_wait: float = typer.Option(2.0, "--retry-wait", help="Seconds to wait between retries."),
    llm_timeout: float | None = typer.Option(
        60.0, "--llm-timeout", help="Timeout in seconds for each LLM call."
    ),
) -> None:
    config, _ = load_config()
    if schema is None:
        schema = config.get("default_schema")
    if not schema:
        typer.echo("Missing schema (set default_schema in config or pass --schema).", err=True)
        raise typer.Exit(code=1)

    latest_path = _latest_identity_path(schema, name)
    if latest_path is None:
        typer.echo("Identity not found.", err=True)
        raise typer.Exit(code=1)
    identity = load_json(latest_path)
    schema_data = None
    schema_version = identity.get("schema_version")
    if schema_version:
        schema_data = load_json(_schema_path(schema, int(schema_version)))
    if not schema_data:
        schema_data = _latest_schema(schema)
    if not schema_data:
        typer.echo("Schema not found.", err=True)
        raise typer.Exit(code=1)

    window = _range_from_filters(years, days, hours)

    sources: list[SourceItem] = []
    stdin_text = ""
    if not no_stdin:
        stdin_text = _read_stdin_if_available()
        if stdin_text.strip():
            sources.append(SourceItem(label="stdin", content=stdin_text, metadata={}))

    if not no_input and input_text:
        for value in input_text:
            if value.strip():
                sources.append(SourceItem(label="input", content=value, metadata={}))

    if not no_memory and (memory_term or memory_type or memory_id):
        if not memory_term or not memory_type or not memory_id:
            typer.echo("Memory input requires --memory-term, --memory-type, and --memory-id.", err=True)
            raise typer.Exit(code=1)
        memory_entries = _fetch_memory_entries(
            term=memory_term,
            entry_type=memory_type,
            entry_id=memory_id,
            window=window,
            years=years,
            days=days,
            hours=hours,
        )
        for entry in memory_entries:
            raw = _format_memory_entry(entry)
            summary = _summarize_text(
                config,
                raw,
                max_chars=summary_max_chars,
                provider=provider,
                model=model,
                retries=retries,
                retry_wait=retry_wait,
                timeout=llm_timeout,
            )
            if summary:
                sources.append(
                    SourceItem(
                        label="memory-summary",
                        content=summary,
                        metadata={**raw.metadata, "summary": True},
                    )
                )

    if not no_topics:
        topic_entries = _fetch_topics(window)
        for entry in topic_entries:
            sources.append(_format_topic(entry))

    if include_history:
        history = _identity_versions(schema, name)
        for item in history[:-1]:
            created_at = _parse_iso_timestamp(item.get("created_at"))
            if window is not None and not _in_range(created_at, window):
                continue
            sources.append(
                SourceItem(
                    label="identity-history",
                    content=str(item.get("content") or ""),
                    metadata={"version": item.get("version"), "created_at": item.get("created_at")},
                )
            )

    system_prompt = _read_prompt(config, "system")
    user_template = _read_prompt(config, "user")

    current_identity = str(identity.get("content") or "")
    if not current_identity.strip():
        current_identity = _empty_identity_markdown(schema_data.get("traits", []))

    run_id = uuid.uuid4().hex
    _log_event(
        "update_started",
        {
            "name": name,
            "schema": schema,
            "version": identity.get("version"),
            "source_count": len(sources),
            "run_id": run_id,
            "time_filter": {"years": years, "days": days, "hours": hours},
        },
    )

    batched_sources = _batch_sources_by_chars(sources, max_chars)

    for source in batched_sources:
        _log_event(
            "update_source_started",
            {
                "name": name,
                "schema": schema,
                "label": source.label,
                "metadata": source.metadata,
                "run_id": run_id,
            },
        )
        prompt = _render_prompt(
            user_template,
            schema=schema_data,
            current_identity=current_identity,
            source=source,
        )
        current_identity = _call_llm(
            system_prompt,
            prompt,
            provider=provider,
            model=model,
            retries=retries,
            retry_wait=retry_wait,
            timeout=llm_timeout,
        ).strip()
        _log_event(
            "update_source_completed",
            {
                "name": name,
                "schema": schema,
                "label": source.label,
                "metadata": source.metadata,
                "run_id": run_id,
                "content_chars": len(current_identity),
            },
        )

    now = _utc_iso()
    identity["content"] = current_identity.strip() + "\n"
    identity["updated_at"] = now
    identity["run_id"] = run_id
    metadata = identity.get("metadata") or {}
    updates = metadata.get("updates") or []
    updates.append(
        {
            "updated_at": now,
            "source_count": len(sources),
            "time_filter": {"years": years, "days": days, "hours": hours},
            "sources": {
                "stdin": bool(stdin_text.strip()),
                "input_count": len(input_text or []),
                "memory": None if no_memory else {
                    "term": memory_term,
                    "type": memory_type,
                    "id": memory_id,
                },
                "topics": not no_topics,
                "included_history": include_history,
            },
            "batch_count": len(batched_sources),
            "max_chars": max_chars,
            "summary_max_chars": summary_max_chars,
            "llm": {"provider": provider, "model": model, "timeout": llm_timeout},
            "run_id": run_id,
        }
    )
    metadata["updates"] = updates
    identity["metadata"] = metadata
    save_json(latest_path, identity)
    _log_event(
        "update_completed",
        {
            "name": name,
            "schema": schema,
            "version": identity.get("version"),
            "source_count": len(sources),
            "run_id": run_id,
        },
    )
    typer.echo(json.dumps(identity, indent=2, sort_keys=True))


@app.command(help="Simple health check.")
def ping() -> None:
    typer.echo("pong")


if __name__ == "__main__":
    app()
