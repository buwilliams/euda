import json
import shutil
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator

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

app = typer.Typer(help="Euda memory CLI.", invoke_without_command=True)
config_app = typer.Typer(help="Inspect or update config.json overrides and merged defaults.")


@app.callback()
def app_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


app.add_typer(config_app, name="config")


TERMS = {"short", "long"}


def _validate_term(term: str) -> str:
    normalized = term.strip().lower()
    if normalized not in TERMS:
        raise typer.BadParameter("Term must be 'short' or 'long'.")
    return normalized


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc() -> date:
    return _utc_now().date()


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("Date must be ISO format: YYYY-MM-DD") from exc


def _parse_time(value: str) -> dt_time:
    try:
        return dt_time.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("Time must be ISO format: HH:MM[:SS]") from exc


def _make_range(
    start_date: date,
    end_date: date,
    start_time: dt_time,
    end_time: dt_time,
) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start_date, start_time, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, end_time, tzinfo=timezone.utc)
    return start_dt, end_dt


def _date_span(start_dt: datetime, end_dt: datetime) -> Iterable[date]:
    current = start_dt.date()
    end_date = end_dt.date()
    step = timedelta(days=1)
    while current <= end_date:
        yield current
        current = current + step


def _term_dir(term: str) -> Path:
    return data_dir() / term


def _short_path(day: date, entry_type: str, entry_id: str) -> Path:
    day_token = day.strftime("%Y%m%d")
    year_dir = _term_dir("short") / day.strftime("%Y")
    return year_dir / f"{day_token}-{entry_type}-{entry_id}.jsonl"


def _iter_short_paths(day: date, entry_type: str, entry_id: str) -> Iterator[Path]:
    day_token = day.strftime("%Y%m%d")
    year_dir = _term_dir("short") / day.strftime("%Y")
    if not year_dir.exists():
        return iter(())
    return iter([year_dir / f"{day_token}-{entry_type}-{entry_id}.jsonl"])


def _long_glob(day: date, entry_type: str, entry_id: str) -> list[Path]:
    day_token = day.strftime("%Y%m%d")
    year_dir = _term_dir("long") / day.strftime("%Y")
    if not year_dir.exists():
        return []
    pattern = f"{day_token}-{entry_type}-{entry_id}-*.md"
    return sorted(year_dir.glob(pattern))


def _next_long_index(day: date, entry_type: str, entry_id: str) -> int:
    existing = _long_glob(day, entry_type, entry_id)
    max_index = 0
    for path in existing:
        name = path.stem
        try:
            index = int(name.rsplit("-", 1)[-1])
        except ValueError:
            continue
        if index > max_index:
            max_index = index
    return max_index + 1


def _long_path(day: date, entry_type: str, entry_id: str, index: int) -> Path:
    day_token = day.strftime("%Y%m%d")
    year_dir = _term_dir("long") / day.strftime("%Y")
    return year_dir / f"{day_token}-{entry_type}-{entry_id}-{index}.md"


def _iter_json_lines(paths: Iterable[Path]) -> Iterator[dict]:
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                yield data


def _normalize_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _filter_entries(
    entries: Iterable[dict],
    start_dt: datetime,
    end_dt: datetime,
    entry_type: str,
    entry_id: str,
) -> Iterator[dict]:
    for entry in entries:
        timestamp = _normalize_timestamp(entry.get("timestamp", ""))
        if timestamp is None:
            continue
        if timestamp < start_dt or timestamp > end_dt:
            continue
        if entry.get("type") != entry_type:
            continue
        if entry.get("id") != entry_id:
            continue
        yield entry


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    lines = text.splitlines()
    try:
        end_index = lines[1:].index("---") + 1
    except ValueError:
        return {}, text
    header_lines = lines[1:end_index]
    body = "\n".join(lines[end_index + 1 :])
    meta: dict[str, str] = {}
    for line in header_lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body


def _entry_from_long_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(content)
    body = body.rstrip("\n")
    name = path.stem
    parts = name.split("-")
    day_token = parts[0] if parts else ""
    timestamp = meta.get("timestamp", "")
    if not timestamp and len(day_token) == 8:
        try:
            day = date.fromisoformat(f"{day_token[:4]}-{day_token[4:6]}-{day_token[6:]}")
            timestamp = datetime.combine(day, dt_time(0, 0, 0), tzinfo=timezone.utc).isoformat()
        except ValueError:
            timestamp = ""
    entry_type = meta.get("type", parts[1] if len(parts) > 1 else "")
    entry_id = meta.get("id", parts[2] if len(parts) > 2 else "")
    index_raw = meta.get("index", parts[-1] if parts else "")
    try:
        index = int(index_raw)
    except ValueError:
        index = 0
    return {
        "timestamp": timestamp,
        "type": entry_type,
        "id": entry_id,
        "term": "long",
        "index": index,
        "memory": body,
    }


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


@app.command(help="Simple health check.")
def ping() -> None:
    typer.echo("pong")


@app.command(help="Write a memory entry.")
def write(
    payload: str | None = typer.Argument(None, help="Payload to store. Reads stdin when omitted or '-'."),
    term: str = typer.Option(..., "--term", help="Memory term (short or long)."),
    entry_type: str = typer.Option(..., "--type", help="Memory type."),
    entry_id: str = typer.Option(..., "--id", help="Memory id."),
) -> None:
    if payload is None or payload == "-":
        payload = typer.get_text_stream("stdin").read()
    payload = payload.rstrip("\n")
    term = _validate_term(term)
    timestamp = _utc_now().isoformat()

    if term == "short":
        try:
            memory_payload = json.loads(payload)
        except json.JSONDecodeError:
            typer.echo("Short-term memory payload must be valid JSON.", err=True)
            raise typer.Exit(code=1)
        entry = {
            "timestamp": timestamp,
            "type": entry_type,
            "id": entry_id,
            "term": "short",
            "memory": memory_payload,
        }
        path = _short_path(_today_utc(), entry_type, entry_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return

    index = _next_long_index(_today_utc(), entry_type, entry_id)
    path = _long_path(_today_utc(), entry_type, entry_id, index)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "---",
        f"timestamp: {timestamp}",
        f"type: {entry_type}",
        f"id: {entry_id}",
        f"index: {index}",
        "---",
        "",
    ]
    content = "\n".join(header) + payload + "\n"
    path.write_text(content, encoding="utf-8")


@app.command(help="Read memory entries within a time range.")
def read(
    term: str = typer.Option(..., "--term", help="Memory term (short or long)."),
    entry_type: str = typer.Option(..., "--type", help="Memory type."),
    entry_id: str = typer.Option(..., "--id", help="Memory id."),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (UTC, YYYY-MM-DD)."),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (UTC, YYYY-MM-DD)."),
    start_time: str | None = typer.Option(None, "--start-time", help="Start time (UTC, HH:MM[:SS])."),
    end_time: str | None = typer.Option(None, "--end-time", help="End time (UTC, HH:MM[:SS])."),
    hours: int | None = typer.Option(None, "--hours", help="Hours backwards from now (UTC)."),
    days: int | None = typer.Option(None, "--days", help="Days backwards from now (UTC)."),
    minutes: int | None = typer.Option(None, "--minutes", help="Minutes backwards from now (UTC)."),
) -> None:
    term = _validate_term(term)
    now = _utc_now()
    if hours is not None or days is not None or minutes is not None:
        delta = timedelta(hours=hours or 0, days=days or 0, minutes=minutes or 0)
        start_dt = now - delta
        end_dt = now
    else:
        today = _today_utc()
        start_day = _parse_date(start_date) if start_date else today
        end_day = _parse_date(end_date) if end_date else today
        start_clock = _parse_time(start_time) if start_time else dt_time(0, 0, 0)
        end_clock = _parse_time(end_time) if end_time else dt_time(23, 59, 59, 999999)
        start_dt, end_dt = _make_range(start_day, end_day, start_clock, end_clock)

    if term == "short":
        all_paths = []
        for day in _date_span(start_dt, end_dt):
            all_paths.extend(list(_iter_short_paths(day, entry_type, entry_id)))
        entries = _iter_json_lines(all_paths)
        filtered = _filter_entries(entries, start_dt, end_dt, entry_type, entry_id)
        for entry in filtered:
            entry.setdefault("term", "short")
            typer.echo(json.dumps(entry, sort_keys=True))
        return

    entries: list[dict] = []
    for day in _date_span(start_dt, end_dt):
        for path in _long_glob(day, entry_type, entry_id):
            entry = _entry_from_long_file(path)
            if entry is None:
                continue
            entries.append(entry)
    filtered = _filter_entries(entries, start_dt, end_dt, entry_type, entry_id)
    for entry in filtered:
        typer.echo(json.dumps(entry, sort_keys=True))


@app.command(help="Tail memory entries in real time.")
def tail(
    term: str = typer.Option(..., "--term", help="Memory term (short or long)."),
    entry_type: str = typer.Option(..., "--type", help="Memory type."),
    entry_id: str = typer.Option(..., "--id", help="Memory id."),
    iterations: int | None = typer.Option(
        None, "--_iterations", hidden=True, help="Limit loop iterations (tests only)."
    ),
    sleep_seconds: float = typer.Option(0.5, "--_sleep", hidden=True, help="Sleep seconds (tests only)."),
) -> None:
    term = _validate_term(term)
    current_day = _today_utc()
    seen: set[Path] = set()
    last_output: dict[Path, int] = {}
    initialized_long = False

    def track_existing_short(path: Path) -> None:
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        last_output[path] = len(lines)

    remaining = iterations
    while True:
        new_day = _today_utc()
        if new_day != current_day:
            current_day = new_day
            seen.clear()
            last_output.clear()
            initialized_long = False

        if term == "short":
            if not _term_dir("short").exists():
                seen.clear()
                last_output.clear()
                time.sleep(sleep_seconds)
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        break
                continue
            for path in _iter_short_paths(current_day, entry_type, entry_id):
                if path not in seen:
                    seen.add(path)
                    track_existing_short(path)
                if not path.exists():
                    seen.discard(path)
                    last_output.pop(path, None)
                    continue
                lines = path.read_text(encoding="utf-8").splitlines()
                start_at = last_output.get(path, 0)
                for line in lines[start_at:]:
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") != entry_type:
                        continue
                    if data.get("id") != entry_id:
                        continue
                    if "term" not in data:
                        data["term"] = "short"
                    typer.echo(json.dumps(data, sort_keys=True))
                last_output[path] = len(lines)
            time.sleep(sleep_seconds)
        else:
            if not _term_dir("long").exists():
                seen.clear()
                initialized_long = False
                time.sleep(sleep_seconds)
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        break
                continue
            paths = _long_glob(current_day, entry_type, entry_id)
            if not initialized_long:
                seen.update(paths)
                initialized_long = True
            else:
                for path in paths:
                    if path in seen:
                        continue
                    seen.add(path)
                    entry = _entry_from_long_file(path)
                    if entry is None:
                        continue
                    typer.echo(json.dumps(entry, sort_keys=True))
            time.sleep(sleep_seconds)

        if remaining is not None:
            remaining -= 1
            if remaining <= 0:
                break


@app.command(help="Remove memory entries.")
def clean(
    term: str = typer.Option(..., "--term", help="Memory term (short or long)."),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
    entry_type: str = typer.Option(..., "--type", help="Memory type."),
    entry_id: str = typer.Option(..., "--id", help="Memory id."),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (UTC, YYYY-MM-DD)."),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (UTC, YYYY-MM-DD)."),
    start_time: str | None = typer.Option(None, "--start-time", help="Start time (UTC, HH:MM[:SS])."),
    end_time: str | None = typer.Option(None, "--end-time", help="End time (UTC, HH:MM[:SS])."),
    hours: int | None = typer.Option(None, "--hours", help="Hours backwards from now (UTC)."),
    days: int | None = typer.Option(None, "--days", help="Days backwards from now (UTC)."),
    minutes: int | None = typer.Option(None, "--minutes", help="Minutes backwards from now (UTC)."),
    all_entries: bool = typer.Option(False, "--all", help="Remove all memories for the term (ignores filters)."),
) -> None:
    term = _validate_term(term)
    if not yes:
        confirmation = typer.prompt("Type 'yes' to confirm", default="", show_default=False)
        if confirmation.strip().lower() != "yes":
            typer.echo("Aborted.")
            raise typer.Exit(code=1)

    target = _term_dir(term)
    if all_entries:
        if target.exists():
            shutil.rmtree(target)
        typer.echo("Memories removed.")
        return

    if not target.exists():
        typer.echo("Memories removed.")
        return

    now = _utc_now()
    if hours is not None or days is not None or minutes is not None:
        delta = timedelta(hours=hours or 0, days=days or 0, minutes=minutes or 0)
        start_dt = now - delta
        end_dt = now
    else:
        today = _today_utc()
        start_day = _parse_date(start_date) if start_date else today
        end_day = _parse_date(end_date) if end_date else today
        start_clock = _parse_time(start_time) if start_time else dt_time(0, 0, 0)
        end_clock = _parse_time(end_time) if end_time else dt_time(23, 59, 59, 999999)
        start_dt, end_dt = _make_range(start_day, end_day, start_clock, end_clock)

    if term == "short":
        for day in _date_span(start_dt, end_dt):
            for path in _iter_short_paths(day, entry_type, entry_id):
                if not path.exists():
                    continue
                kept: list[str] = []
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    timestamp = _normalize_timestamp(data.get("timestamp", ""))
                    if timestamp is None:
                        kept.append(line)
                        continue
                    matches_time = start_dt <= timestamp <= end_dt
                    matches_type = data.get("type") == entry_type
                    matches_id = data.get("id") == entry_id
                    if matches_time and matches_type and matches_id:
                        continue
                    kept.append(line)
                if kept:
                    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
                else:
                    path.unlink()
        typer.echo("Memories removed.")
        return

    for day in _date_span(start_dt, end_dt):
        for path in _long_glob(day, entry_type, entry_id):
            entry = _entry_from_long_file(path)
            if entry is None:
                continue
            timestamp = _normalize_timestamp(entry.get("timestamp", ""))
            if timestamp is None:
                continue
            if not (start_dt <= timestamp <= end_dt):
                continue
            if entry.get("type") != entry_type:
                continue
            if entry.get("id") != entry_id:
                continue
            path.unlink()
    typer.echo("Memories removed.")


if __name__ == "__main__":
    app()
