from __future__ import annotations

import difflib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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
)

app = typer.Typer(help="Identity CLI.", invoke_without_command=True)
config_app = typer.Typer(help="Inspect or update config.json overrides and merged defaults.")
guide_app = typer.Typer(help="Manage consolidation guides.")
identity_app = typer.Typer(help="Manage identities.")

app.add_typer(config_app, name="config")
app.add_typer(guide_app, name="guide")
app.add_typer(identity_app, name="identity")


@app.callback()
def app_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@dataclass(frozen=True)
class InputSource:
    label: str
    content: str
    metadata: dict


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().isoformat()


def _guide_dir() -> Path:
    return data_dir() / "guide"


def _identity_dir(name: str) -> Path:
    return data_dir() / "identity" / name


def _normalize_name(name: str) -> str:
    cleaned = re.sub(r"\s+", "-", name.strip().lower())
    cleaned = re.sub(r"[^a-z0-9\-]", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    if not cleaned:
        raise typer.BadParameter("Identity name must include alphanumeric characters.")
    return cleaned


def _read_stdin(allow_tty: bool) -> str:
    if sys.stdin is None:
        return ""
    if sys.stdin.isatty() and not allow_tty:
        return ""
    return typer.get_text_stream("stdin").read()


def _version_from_path(path: Path, prefix: str) -> int:
    stem = path.stem
    try:
        return int(stem.replace(prefix + "-", ""))
    except ValueError:
        return 0


def _latest_version_int(directory: Path, prefix: str) -> int | None:
    if not directory.exists():
        return None
    paths = list(directory.glob(f"{prefix}-*.md"))
    if not paths:
        return None
    return max(paths, key=lambda p: _version_from_path(p, prefix))


def _next_version(directory: Path, prefix: str) -> int:
    latest = _latest_version_int(directory, prefix)
    if latest is None:
        return 1
    return _version_from_path(latest, prefix) + 1


def _markdown_path(directory: Path, prefix: str, version: int) -> Path:
    return directory / f"{prefix}-{version}.md"


def _metadata_path(markdown_path: Path) -> Path:
    return markdown_path.with_suffix(".json")


def _prune_versions(directory: Path, prefix: str, keep: int) -> None:
    if keep <= 0:
        return
    paths = sorted(directory.glob(f"{prefix}-*.md"), key=lambda p: _version_from_path(p, prefix))
    if len(paths) <= keep:
        return
    for path in paths[: len(paths) - keep]:
        meta = _metadata_path(path)
        if path.exists():
            path.unlink()
        if meta.exists():
            meta.unlink()


def _validate_identity_header(content: str, name: str) -> None:
    for line in content.splitlines():
        if not line.strip():
            continue
        if not line.startswith("# "):
            raise typer.BadParameter("Identity must start with a '# name' header.")
        header = line[2:].strip()
        if header != name:
            raise typer.BadParameter(f"Identity header must be '# {name}'.")
        return
    raise typer.BadParameter("Identity is empty.")


def _identity_markdown_from_sources(name: str, content: str) -> str:
    if not content.endswith("\n"):
        content = content + "\n"
    _validate_identity_header(content, name)
    return content


def _render_prompt(template: str, *, identity: str, guide: str, data: str, variance: str) -> str:
    return template.format(
        identity=identity.strip(),
        guide=guide.strip(),
        data=data.strip(),
        variance=variance,
    )


def _call_llm(
    system_prompt: str,
    prompt: str,
    *,
    provider: str | None,
    model: str | None,
    timeout: float | None,
) -> str:
    args = ["call", system_prompt, "-"]
    if provider:
        args.extend(["--provider", provider])
    if model:
        args.extend(["--model", model])
    result = shared_router.run_core("llm", args, input_text=prompt, timeout=timeout)
    return result.stdout


def _change_ratio(before: str, after: str) -> float:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines)
    return 1.0 - matcher.ratio()


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


@guide_app.command("read", help="Read the latest guide (markdown).")
def guide_read(
    version: int | None = typer.Option(None, "--version", help="Guide version (defaults to latest)."),
) -> None:
    directory = _guide_dir()
    prefix = "guide"
    if version is None:
        latest = _latest_version_int(directory, prefix)
        if latest is None:
            typer.echo("Guide not found.", err=True)
            raise typer.Exit(code=1)
        path = latest
    else:
        path = _markdown_path(directory, prefix, version)
    if not path.exists():
        typer.echo("Guide not found.", err=True)
        raise typer.Exit(code=1)
    typer.echo(path.read_text(encoding="utf-8").rstrip("\n"))


@guide_app.command("write", help="Write a new guide version.")
def guide_write(
    content: str | None = typer.Argument(
        None, help="Markdown content. Reads stdin if omitted or '-'."
    ),
    from_version: int | None = typer.Option(
        None, "--from-version", help="Copy content from an earlier version."
    ),
    file: Path | None = typer.Option(None, "--file", help="Read markdown from a file."),
) -> None:
    if from_version is not None and (content is not None or file is not None):
        typer.echo("Use --from-version by itself (no content or --file).", err=True)
        raise typer.Exit(code=1)
    directory = _guide_dir()
    prefix = "guide"
    if from_version is not None:
        source_path = _markdown_path(directory, prefix, from_version)
        if not source_path.exists():
            typer.echo("Guide version not found.", err=True)
            raise typer.Exit(code=1)
        content = source_path.read_text(encoding="utf-8")
        source_meta = {"type": "copy", "from_version": from_version}
    elif file is not None:
        if not file.exists():
            typer.echo("File not found.", err=True)
            raise typer.Exit(code=1)
        content = file.read_text(encoding="utf-8")
        source_meta = {"type": "file", "path": str(file)}
    else:
        if content is None or content == "-":
            content = typer.get_text_stream("stdin").read()
        source_meta = {"type": "stdin"}

    if content is None or not content.strip():
        typer.echo("Guide content is empty.", err=True)
        raise typer.Exit(code=1)

    version = _next_version(directory, prefix)
    path = _markdown_path(directory, prefix, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")
    metadata = {
        "version": version,
        "created_at": _utc_iso(),
        "source": source_meta,
    }
    save_json(_metadata_path(path), metadata)

    config, _ = load_config()
    keep = int(get_value(config, "guide.max_versions"))
    _prune_versions(directory, prefix, keep)

    typer.echo(json.dumps(metadata, indent=2, sort_keys=True))


@identity_app.command("create", help="Create a new identity with a # name header.")
def identity_create(
    name: str = typer.Argument(..., help="Identity name."),
    content: str | None = typer.Argument(
        None, help="Optional markdown content. Reads stdin if omitted or '-'."
    ),
    file: Path | None = typer.Option(None, "--file", help="Read markdown from a file."),
) -> None:
    normalized = _normalize_name(name)
    config, _ = load_config()
    max_chars = int(get_value(config, "identity.max_chars"))
    directory = _identity_dir(normalized)
    prefix = "identity"
    if directory.exists() and list(directory.glob(f"{prefix}-*.md")):
        typer.echo("Identity already exists.", err=True)
        raise typer.Exit(code=1)

    if file is not None:
        if not file.exists():
            typer.echo("File not found.", err=True)
            raise typer.Exit(code=1)
        content = file.read_text(encoding="utf-8")
        source_meta = {"type": "file", "path": str(file)}
    elif content is None:
        stdin_text = _read_stdin(allow_tty=False)
        if stdin_text.strip():
            content = stdin_text
            source_meta = {"type": "stdin"}
        else:
            content = f"# {normalized}\n"
            source_meta = {"type": "generated"}
    else:
        if content == "-":
            content = typer.get_text_stream("stdin").read()
            source_meta = {"type": "stdin"}
        else:
            source_meta = {"type": "inline"}

    content = _identity_markdown_from_sources(normalized, content)
    if max_chars > 0 and len(content) > max_chars:
        typer.echo("Identity exceeds maximum size.", err=True)
        raise typer.Exit(code=1)

    version = _next_version(directory, prefix)
    path = _markdown_path(directory, prefix, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    metadata = {
        "name": normalized,
        "version": version,
        "created_at": _utc_iso(),
        "source": source_meta,
    }
    save_json(_metadata_path(path), metadata)

    keep = int(get_value(config, "identity.max_versions"))
    _prune_versions(directory, prefix, keep)

    typer.echo(json.dumps(metadata, indent=2, sort_keys=True))


@identity_app.command("read", help="Read an identity (markdown).")
def identity_read(
    name: str = typer.Argument(..., help="Identity name."),
    version: int | None = typer.Option(None, "--version", help="Identity version (defaults to latest)."),
    metadata: bool = typer.Option(False, "--metadata", help="Print metadata JSON instead of markdown."),
) -> None:
    normalized = _normalize_name(name)
    directory = _identity_dir(normalized)
    prefix = "identity"
    if version is None:
        latest = _latest_version_int(directory, prefix)
        if latest is None:
            typer.echo("Identity not found.", err=True)
            raise typer.Exit(code=1)
        path = latest
    else:
        path = _markdown_path(directory, prefix, version)
    if not path.exists():
        typer.echo("Identity not found.", err=True)
        raise typer.Exit(code=1)
    if metadata:
        meta = _metadata_path(path)
        if not meta.exists():
            typer.echo("Identity metadata not found.", err=True)
            raise typer.Exit(code=1)
        typer.echo(meta.read_text(encoding="utf-8").rstrip("\n"))
        return
    typer.echo(path.read_text(encoding="utf-8").rstrip("\n"))


@identity_app.command("write", help="Write a new identity version.")
def identity_write(
    name: str = typer.Argument(..., help="Identity name."),
    content: str | None = typer.Argument(
        None, help="Markdown content. Reads stdin if omitted or '-'."
    ),
    from_version: int | None = typer.Option(
        None, "--from-version", help="Copy content from an earlier version."
    ),
    file: Path | None = typer.Option(None, "--file", help="Read markdown from a file."),
) -> None:
    normalized = _normalize_name(name)
    config, _ = load_config()
    max_chars = int(get_value(config, "identity.max_chars"))
    directory = _identity_dir(normalized)
    prefix = "identity"

    if from_version is not None and (content is not None or file is not None):
        typer.echo("Use --from-version by itself (no content or --file).", err=True)
        raise typer.Exit(code=1)

    if from_version is not None:
        source_path = _markdown_path(directory, prefix, from_version)
        if not source_path.exists():
            typer.echo("Identity version not found.", err=True)
            raise typer.Exit(code=1)
        content = source_path.read_text(encoding="utf-8")
        source_meta = {"type": "copy", "from_version": from_version}
    elif file is not None:
        if not file.exists():
            typer.echo("File not found.", err=True)
            raise typer.Exit(code=1)
        content = file.read_text(encoding="utf-8")
        source_meta = {"type": "file", "path": str(file)}
    else:
        if content is None or content == "-":
            content = typer.get_text_stream("stdin").read()
            source_meta = {"type": "stdin"}
        else:
            source_meta = {"type": "inline"}

    if content is None or not content.strip():
        typer.echo("Identity content is empty.", err=True)
        raise typer.Exit(code=1)

    content = _identity_markdown_from_sources(normalized, content)
    if max_chars > 0 and len(content) > max_chars:
        typer.echo("Identity exceeds maximum size.", err=True)
        raise typer.Exit(code=1)

    version = _next_version(directory, prefix)
    path = _markdown_path(directory, prefix, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    metadata = {
        "name": normalized,
        "version": version,
        "created_at": _utc_iso(),
        "source": source_meta,
    }
    save_json(_metadata_path(path), metadata)

    keep = int(get_value(config, "identity.max_versions"))
    _prune_versions(directory, prefix, keep)

    typer.echo(json.dumps(metadata, indent=2, sort_keys=True))


@identity_app.command("update", help="Alias for write (creates a new version).")
def identity_update(
    name: str = typer.Argument(..., help="Identity name."),
    content: str | None = typer.Argument(
        None, help="Markdown content. Reads stdin if omitted or '-'."
    ),
    from_version: int | None = typer.Option(
        None, "--from-version", help="Copy content from an earlier version."
    ),
    file: Path | None = typer.Option(None, "--file", help="Read markdown from a file."),
) -> None:
    identity_write(name=name, content=content, from_version=from_version, file=file)


@app.command(help="Consolidate identity with latest cognitive core and input data.")
def consolidate(
    name: str = typer.Argument(..., help="Identity name."),
    input_file: list[Path] = typer.Option(
        None, "--file", help="Input data file (repeatable)."
    ),
    input_text: list[str] = typer.Option(
        None, "--text", help="Inline input text (repeatable)."
    ),
    no_stdin: bool = typer.Option(False, "--no-stdin", help="Disable stdin input."),
    provider: str | None = typer.Option(None, "--provider", help="LLM provider override."),
    model: str | None = typer.Option(None, "--model", help="LLM model override."),
    llm_timeout: float | None = typer.Option(None, "--llm-timeout", help="LLM timeout in seconds."),
) -> None:
    config, _ = load_config()
    normalized = _normalize_name(name)

    identity_directory = _identity_dir(normalized)
    identity_prefix = "identity"
    latest_identity_path = _latest_version_int(identity_directory, identity_prefix)
    if latest_identity_path is None:
        typer.echo("Identity not found.", err=True)
        raise typer.Exit(code=1)
    identity_markdown = latest_identity_path.read_text(encoding="utf-8")

    guide_directory = _guide_dir()
    guide_prefix = "guide"
    latest_guide_path = _latest_version_int(guide_directory, guide_prefix)
    if latest_guide_path is None:
        typer.echo("Guide not found.", err=True)
        raise typer.Exit(code=1)
    guide_markdown = latest_guide_path.read_text(encoding="utf-8")

    sources: list[InputSource] = []
    if not no_stdin:
        if sys.stdin is not None and sys.stdin.isatty() and not input_text and not input_file:
            typer.echo(
                "Consolidate requires data via stdin, --text, or --file.",
                err=True,
            )
            raise typer.Exit(code=1)
        stdin_text = _read_stdin(allow_tty=False)
        if stdin_text.strip():
            sources.append(InputSource(label="stdin", content=stdin_text, metadata={}))
    else:
        stdin_text = ""

    if input_text:
        for text in input_text:
            if text.strip():
                sources.append(InputSource(label="text", content=text, metadata={}))

    if input_file:
        for path in input_file:
            if not path.exists():
                typer.echo(f"Input file not found: {path}", err=True)
                raise typer.Exit(code=1)
            content = path.read_text(encoding="utf-8")
            if content.strip():
                sources.append(
                    InputSource(label="file", content=content, metadata={"path": str(path)})
                )

    if not sources:
        typer.echo("Consolidate requires data via stdin, --text, or --file.", err=True)
        raise typer.Exit(code=1)

    prompts = config.get("prompts", {}) or {}
    template_name = prompts.get("consolidate_user") or "consolidate-prompt.md"
    system_name = prompts.get("consolidate_system") or "consolidate-system-prompt.md"
    template_path = data_dir() / template_name
    system_path = data_dir() / system_name
    if not template_path.exists() or not system_path.exists():
        typer.echo("Missing consolidate prompt templates.", err=True)
        raise typer.Exit(code=1)

    variance = str(get_value(config, "consolidate.variance"))
    max_change_ratio = float(get_value(config, "consolidate.max_change_ratio"))
    max_chars = int(get_value(config, "identity.max_chars"))
    llm_timeout = llm_timeout if llm_timeout is not None else config.get("consolidate", {}).get("llm_timeout")
    provider = provider or config.get("consolidate", {}).get("provider")
    model = model or config.get("consolidate", {}).get("model")

    merged_data = []
    for source in sources:
        header = f"### Source ({source.label})"
        if source.metadata:
            header += f"\nMetadata: {json.dumps(source.metadata, sort_keys=True)}"
        merged_data.append(header + "\n" + source.content.strip())
    data_block = "\n\n".join(merged_data)

    prompt = _render_prompt(
        template_path.read_text(encoding="utf-8"),
        identity=identity_markdown,
        guide="",
        data=data_block,
        variance=variance,
    )

    system_prompt = system_path.read_text(encoding="utf-8").rstrip()
    if system_prompt:
        system_prompt = f"{system_prompt}\n\n{guide_markdown.strip()}\n"
    else:
        system_prompt = guide_markdown.strip() + "\n"

    response = _call_llm(
        system_prompt,
        prompt,
        provider=provider,
        model=model,
        timeout=llm_timeout,
    ).strip()

    if not response:
        typer.echo("LLM returned empty identity.", err=True)
        raise typer.Exit(code=1)

    response = _identity_markdown_from_sources(normalized, response)

    if max_chars > 0 and len(response) > max_chars:
        typer.echo("Identity exceeds maximum size.", err=True)
        raise typer.Exit(code=1)

    change_ratio = _change_ratio(identity_markdown, response)
    if max_change_ratio > 0 and change_ratio > max_change_ratio:
        typer.echo("Identity change exceeds max change ratio.", err=True)
        raise typer.Exit(code=1)

    version = _next_version(identity_directory, identity_prefix)
    new_path = _markdown_path(identity_directory, identity_prefix, version)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text(response, encoding="utf-8")

    metadata = {
        "name": normalized,
        "version": version,
        "created_at": _utc_iso(),
        "source": {
            "stdin": bool(stdin_text.strip()),
            "input_text_count": len([s for s in sources if s.label == "text"]),
            "input_file_count": len([s for s in sources if s.label == "file"]),
        },
        "guide_version": _version_from_path(latest_guide_path, guide_prefix),
        "previous_identity_version": _version_from_path(latest_identity_path, identity_prefix),
        "consolidate": {
            "variance": variance,
            "max_change_ratio": max_change_ratio,
            "change_ratio": round(change_ratio, 4),
            "llm": {"provider": provider, "model": model, "timeout": llm_timeout},
        },
    }
    save_json(_metadata_path(new_path), metadata)

    keep = int(get_value(config, "identity.max_versions"))
    _prune_versions(identity_directory, identity_prefix, keep)

    typer.echo(json.dumps(metadata, indent=2, sort_keys=True))


@app.command(help="Simple health check.")
def ping() -> None:
    typer.echo("pong")


if __name__ == "__main__":
    app()
