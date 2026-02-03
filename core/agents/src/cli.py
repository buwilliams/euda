import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import typer

from src.config import (
    OVERRIDE_CONFIG_FILENAME,
    config_dir,
    data_dir,
    get_value,
    load_config,
    load_json,
    parse_value,
    save_json,
    set_value,
    write_override,
)

app = typer.Typer(help="Euda agents CLI.", invoke_without_command=True)
config_app = typer.Typer(help="Inspect or update config.json overrides and merged defaults.")


@app.callback()
def app_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()

app.add_typer(config_app, name="config")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", name.lower().strip())


def _agents_dir() -> Path:
    return data_dir() / "agents"


def _agent_path(name: str) -> Path:
    return _agents_dir() / name / "agent.json"


def _load_agent(name: str) -> Optional[Dict]:
    path = _agent_path(name)
    if not path.exists():
        return None
    return load_json(path)


def _save_agent(agent: Dict) -> None:
    path = _agent_path(agent["name"])
    path.parent.mkdir(parents=True, exist_ok=True)
    save_json(path, agent)


def _validate_type(t: str) -> str:
    config, _ = load_config()
    valid = config.get("types", [])
    if t not in valid:
        typer.echo(f"Invalid type: {t}. Must be one of: {', '.join(valid)}", err=True)
        raise typer.Exit(code=1)
    return t


def _validate_state(s: str) -> str:
    config, _ = load_config()
    valid = config.get("states", [])
    if s not in valid:
        typer.echo(f"Invalid state: {s}. Must be one of: {', '.join(valid)}", err=True)
        raise typer.Exit(code=1)
    return s


def _list_agent_names() -> List[str]:
    agents = _agents_dir()
    if not agents.exists():
        return []
    return sorted(
        d.name for d in agents.iterdir()
        if d.is_dir() and (d / "agent.json").exists()
    )


# ---------------------------------------------------------------------------
# Config subcommands (unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Agent CRUD commands
# ---------------------------------------------------------------------------

@app.command(help="Create a new agent.")
def create(
    name: str = typer.Argument(..., help="Agent name (lowercase alphanumeric + hyphens)."),
    type: str = typer.Option("autonomous", "--type", help="Agent type."),
    identity: str = typer.Option("", "--identity", help="Identity name to link."),
    state: str = typer.Option("enabled", "--state", help="Initial agent state."),
) -> None:
    norm = _normalize_name(name)
    if not norm:
        typer.echo("Invalid name: must contain at least one alphanumeric character.", err=True)
        raise typer.Exit(code=1)
    _validate_type(type)
    _validate_state(state)
    if _load_agent(norm) is not None:
        typer.echo(f"Agent already exists: {norm}", err=True)
        raise typer.Exit(code=1)
    now = _utc_iso()
    agent = {
        "name": norm,
        "type": type,
        "state": state,
        "identity": identity,
        "created_at": now,
        "updated_at": now,
    }
    _save_agent(agent)
    typer.echo(json.dumps(agent, sort_keys=True))


@app.command(help="Get an agent by name.")
def get(
    name: str = typer.Argument(..., help="Agent name."),
) -> None:
    norm = _normalize_name(name)
    agent = _load_agent(norm)
    if agent is None:
        typer.echo(f"Agent not found: {norm}", err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps(agent, sort_keys=True))


@app.command("list", help="List all agents.")
def list_agents(
    type: Optional[str] = typer.Option(None, "--type", help="Filter by type."),
    state: Optional[str] = typer.Option(None, "--state", help="Filter by state."),
) -> None:
    for agent_name in _list_agent_names():
        agent = _load_agent(agent_name)
        if agent is None:
            continue
        if type is not None and agent.get("type") != type:
            continue
        if state is not None and agent.get("state") != state:
            continue
        typer.echo(json.dumps(agent, sort_keys=True))


@app.command(help="Update an existing agent.")
def update(
    name: str = typer.Argument(..., help="Agent name."),
    state: Optional[str] = typer.Option(None, "--state", help="New state."),
    type: Optional[str] = typer.Option(None, "--type", help="New type."),
    identity: Optional[str] = typer.Option(None, "--identity", help="New identity link."),
) -> None:
    norm = _normalize_name(name)
    agent = _load_agent(norm)
    if agent is None:
        typer.echo(f"Agent not found: {norm}", err=True)
        raise typer.Exit(code=1)
    if state is None and type is None and identity is None:
        typer.echo("Nothing to update. Provide at least one of --state, --type, --identity.", err=True)
        raise typer.Exit(code=1)
    if type is not None:
        _validate_type(type)
        agent["type"] = type
    if state is not None:
        _validate_state(state)
        agent["state"] = state
    if identity is not None:
        agent["identity"] = identity
    agent["updated_at"] = _utc_iso()
    _save_agent(agent)
    typer.echo(json.dumps(agent, sort_keys=True))


@app.command(help="Delete an agent and its data directory.")
def delete(
    name: str = typer.Argument(..., help="Agent name."),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation."),
) -> None:
    norm = _normalize_name(name)
    agent = _load_agent(norm)
    if agent is None:
        typer.echo(f"Agent not found: {norm}", err=True)
        raise typer.Exit(code=1)
    if not yes:
        confirm = typer.confirm(f"Delete agent '{norm}' and all its data?")
        if not confirm:
            raise typer.Abort()
    import shutil
    agent_dir = _agents_dir() / norm
    shutil.rmtree(agent_dir)
    typer.echo(json.dumps({"name": norm, "deleted": True}, sort_keys=True))


@app.command(help="Start an interactive conversation with a user agent.")
def run(
    name: str = typer.Argument(..., help="Agent name."),
    provider: Optional[str] = typer.Option(None, "--provider", help="Override LLM provider."),
    model: Optional[str] = typer.Option(None, "--model", help="Override LLM model."),
) -> None:
    norm = _normalize_name(name)
    agent = _load_agent(norm)
    if agent is None:
        typer.echo(f"Agent not found: {norm}", err=True)
        raise typer.Exit(code=1)
    if agent.get("type") != "user":
        typer.echo(f"Only user-type agents can be run interactively. Agent '{norm}' has type '{agent.get('type')}'.", err=True)
        raise typer.Exit(code=1)
    if agent.get("state") != "enabled":
        typer.echo(f"Agent '{norm}' is not enabled (state: {agent.get('state')}).", err=True)
        raise typer.Exit(code=1)
    if not agent.get("identity"):
        typer.echo(f"Agent '{norm}' has no identity linked. Use 'agents update {norm} --identity <name>'.", err=True)
        raise typer.Exit(code=1)

    from src.runner import run_agent
    run_agent(agent, provider_override=provider, model_override=model)


@app.command(help="Simple health check.")
def ping() -> None:
    typer.echo("pong")


if __name__ == "__main__":
    app()
