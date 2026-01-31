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

app = typer.Typer(help="Euda logs CLI.")
config_app = typer.Typer(help="Inspect or update config.json overrides and merged defaults.")
app.add_typer(config_app, name="config")


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


def _log_path(day: date, entry_type: str, entry_id: str) -> Path:
    day_token = day.strftime("%Y%m%d")
    year_dir = data_dir() / day.strftime("%Y")
    return year_dir / f"{day_token}-{entry_type}-{entry_id}.jsonl"


def _iter_log_paths(day: date, entry_type: str | None, entry_id: str | None) -> Iterator[Path]:
    day_token = day.strftime("%Y%m%d")
    year_dir = data_dir() / day.strftime("%Y")
    if not year_dir.exists():
        return iter(())
    if entry_type is not None and entry_id is not None:
        return iter([year_dir / f"{day_token}-{entry_type}-{entry_id}.jsonl"])
    if entry_type is not None:
        return iter(year_dir.glob(f"{day_token}-{entry_type}-*.jsonl"))
    if entry_id is not None:
        return iter(year_dir.glob(f"{day_token}-*-{entry_id}.jsonl"))
    return iter(year_dir.glob(f"{day_token}-*.jsonl"))


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


def _filter_entries(
    entries: Iterable[dict],
    start_dt: datetime,
    end_dt: datetime,
    entry_type: str | None,
    entry_id: str | None,
) -> Iterator[dict]:
    for entry in entries:
        try:
            timestamp_raw = entry.get("timestamp", "")
            timestamp = datetime.fromisoformat(timestamp_raw)
        except (TypeError, ValueError):
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        if timestamp < start_dt or timestamp > end_dt:
            continue
        if entry_type is not None and entry.get("type") != entry_type:
            continue
        if entry_id is not None and entry.get("id") != entry_id:
            continue
        yield entry


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


@app.command(help="Write a log entry.")
def write(
    message: str | None = typer.Argument(None, help="Message to log. Reads stdin when omitted or '-'."),
    entry_type: str = typer.Option("system", "--type", help="Log type."),
    entry_id: str = typer.Option("none", "--id", help="Log id."),
) -> None:
    if message is None or message == "-":
        message = typer.get_text_stream("stdin").read()
    message = message.rstrip("\n")
    entry = {
        "timestamp": _utc_now().isoformat(),
        "type": entry_type,
        "id": entry_id,
        "message": message,
    }
    path = _log_path(_today_utc(), entry_type, entry_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


@app.command(help="Read log entries within a time range.")
def read(
    entry_type: str = typer.Option("system", "--type", help="Log type."),
    entry_id: str = typer.Option("none", "--id", help="Log id."),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (UTC, YYYY-MM-DD)."),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (UTC, YYYY-MM-DD)."),
    start_time: str | None = typer.Option(None, "--start-time", help="Start time (UTC, HH:MM[:SS])."),
    end_time: str | None = typer.Option(None, "--end-time", help="End time (UTC, HH:MM[:SS])."),
    hours: int | None = typer.Option(None, "--hours", help="Hours backwards from now (UTC)."),
    days: int | None = typer.Option(None, "--days", help="Days backwards from now (UTC)."),
    minutes: int | None = typer.Option(None, "--minutes", help="Minutes backwards from now (UTC)."),
) -> None:
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

    all_paths = []
    for day in _date_span(start_dt, end_dt):
        all_paths.extend(list(_iter_log_paths(day, entry_type, entry_id)))
    entries = _iter_json_lines(all_paths)
    filtered = _filter_entries(entries, start_dt, end_dt, entry_type, entry_id)
    for entry in filtered:
        typer.echo(json.dumps(entry, sort_keys=True))


@app.command(help="Tail log files in real time.")
def tail(
    entry_type: str | None = typer.Option(None, "--type", help="Log type filter."),
    entry_id: str | None = typer.Option(None, "--id", help="Log id filter."),
    iterations: int | None = typer.Option(
        None, "--_iterations", hidden=True, help="Limit loop iterations (tests only)."
    ),
    sleep_seconds: float = typer.Option(0.5, "--_sleep", hidden=True, help="Sleep seconds (tests only)."),
) -> None:
    current_day = _today_utc()
    seen: set[Path] = set()
    last_output: dict[Path, int] = {}

    def emit_existing(path: Path) -> None:
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines[-10:]:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry_type is not None and data.get("type") != entry_type:
                continue
            if entry_id is not None and data.get("id") != entry_id:
                continue
            typer.echo(json.dumps(data, sort_keys=True))
        last_output[path] = len(lines)

    remaining = iterations
    while True:
        new_day = _today_utc()
        if new_day != current_day:
            current_day = new_day
            seen.clear()
            last_output.clear()
        if not data_dir().exists():
            seen.clear()
            last_output.clear()
            time.sleep(sleep_seconds)
            if remaining is not None:
                remaining -= 1
                if remaining <= 0:
                    break
            continue
        for path in _iter_log_paths(current_day, entry_type, entry_id):
            if path not in seen:
                seen.add(path)
                emit_existing(path)
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
                if entry_type is not None and data.get("type") != entry_type:
                    continue
                if entry_id is not None and data.get("id") != entry_id:
                    continue
                typer.echo(json.dumps(data, sort_keys=True))
            last_output[path] = len(lines)
        time.sleep(sleep_seconds)
        if remaining is not None:
            remaining -= 1
            if remaining <= 0:
                break


@app.command(help="Remove all log files.")
def clean(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
    entry_type: str | None = typer.Option(None, "--type", help="Log type filter."),
    entry_id: str | None = typer.Option(None, "--id", help="Log id filter."),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (UTC, YYYY-MM-DD)."),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (UTC, YYYY-MM-DD)."),
    start_time: str | None = typer.Option(None, "--start-time", help="Start time (UTC, HH:MM[:SS])."),
    end_time: str | None = typer.Option(None, "--end-time", help="End time (UTC, HH:MM[:SS])."),
    hours: int | None = typer.Option(None, "--hours", help="Hours backwards from now (UTC)."),
    days: int | None = typer.Option(None, "--days", help="Days backwards from now (UTC)."),
    minutes: int | None = typer.Option(None, "--minutes", help="Minutes backwards from now (UTC)."),
    all_logs: bool = typer.Option(False, "--all", help="Remove all logs (ignores filters)."),
) -> None:
    if not yes:
        confirmation = typer.prompt("Type 'yes' to confirm", default="", show_default=False)
        if confirmation.strip().lower() != "yes":
            typer.echo("Aborted.")
            raise typer.Exit(code=1)
    target = data_dir()
    if all_logs:
        if target.exists():
            shutil.rmtree(target)
        typer.echo("Logs removed.")
        return

    if not target.exists():
        typer.echo("Logs removed.")
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

    for day in _date_span(start_dt, end_dt):
        for path in _iter_log_paths(day, entry_type, entry_id):
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
                timestamp_raw = data.get("timestamp", "")
                try:
                    timestamp = datetime.fromisoformat(timestamp_raw)
                except (TypeError, ValueError):
                    kept.append(line)
                    continue
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                timestamp = timestamp.astimezone(timezone.utc)
                matches_time = start_dt <= timestamp <= end_dt
                matches_type = entry_type is None or data.get("type") == entry_type
                matches_id = entry_id is None or data.get("id") == entry_id
                if matches_time and matches_type and matches_id:
                    continue
                kept.append(line)
            if kept:
                path.write_text("\n".join(kept) + "\n", encoding="utf-8")
            else:
                path.unlink()
    typer.echo("Logs removed.")


if __name__ == "__main__":
    app()
