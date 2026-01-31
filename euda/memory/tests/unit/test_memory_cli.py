import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

import src.cli as cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _set_fixed_time(monkeypatch: pytest.MonkeyPatch, fixed: datetime) -> None:
    monkeypatch.setattr(cli, "_utc_now", lambda: fixed)
    monkeypatch.setattr(cli, "_today_utc", lambda: fixed.date())


def test_write_short_uses_stdin_and_appends_jsonl(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, fixed)

    result = runner.invoke(
        cli.app,
        ["write", "--term", "short", "--type", "system", "--id", "none"],
        input='{"foo": "bar"}\n',
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    memory_path = tmp_path / "data" / "short" / "2026" / "20260131-system-none.jsonl"
    assert memory_path.exists()
    lines = memory_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["timestamp"] == fixed.isoformat()
    assert entry["type"] == "system"
    assert entry["id"] == "none"
    assert entry["term"] == "short"
    assert entry["memory"] == {"foo": "bar"}


def test_write_long_creates_indexed_markdown(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, fixed)

    runner.invoke(
        cli.app,
        ["write", "first", "--term", "long", "--type", "note", "--id", "alpha"],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )
    runner.invoke(
        cli.app,
        ["write", "second", "--term", "long", "--type", "note", "--id", "alpha"],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    base_dir = tmp_path / "data" / "long" / "2026"
    first_path = base_dir / "20260131-note-alpha-1.md"
    second_path = base_dir / "20260131-note-alpha-2.md"
    assert first_path.exists()
    assert second_path.exists()

    entry = cli._entry_from_long_file(first_path)
    assert entry is not None
    assert entry["timestamp"] == fixed.isoformat()
    assert entry["type"] == "note"
    assert entry["id"] == "alpha"
    assert entry["term"] == "long"
    assert entry["index"] == 1
    assert entry["memory"] == "first"


def test_read_short_filters_by_time_type_and_id(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_time = datetime(2026, 1, 31, 10, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, first_time)
    runner.invoke(
        cli.app,
        ["write", '"first"', "--term", "short", "--type", "app", "--id", "abc"],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    second_time = datetime(2026, 1, 31, 11, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, second_time)
    runner.invoke(
        cli.app,
        ["write", '"second"', "--term", "short", "--type", "app", "--id", "abc"],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    result = runner.invoke(
        cli.app,
        [
            "read",
            "--term",
            "short",
            "--type",
            "app",
            "--id",
            "abc",
            "--start-date",
            "2026-01-31",
            "--end-date",
            "2026-01-31",
            "--start-time",
            "09:30",
            "--end-time",
            "10:30",
        ],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(output_lines) == 1
    assert json.loads(output_lines[0])["memory"] == "first"


def test_read_long_filters_by_hours(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_time = datetime(2026, 1, 31, 9, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, first_time)
    runner.invoke(
        cli.app,
        ["write", "old", "--term", "long", "--type", "note", "--id", "x"],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    second_time = datetime(2026, 1, 31, 11, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, second_time)
    runner.invoke(
        cli.app,
        ["write", "new", "--term", "long", "--type", "note", "--id", "x"],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, now)
    result = runner.invoke(
        cli.app,
        ["read", "--term", "long", "--type", "note", "--id", "x", "--hours", "2"],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(output_lines) == 1
    assert json.loads(output_lines[0])["memory"] == "new"


def test_tail_long_ignores_existing_files(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, fixed)

    runner.invoke(
        cli.app,
        ["write", "existing", "--term", "long", "--type", "note", "--id", "x"],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    result = runner.invoke(
        cli.app,
        [
            "tail",
            "--term",
            "long",
            "--type",
            "note",
            "--id",
            "x",
            "--_iterations",
            "1",
            "--_sleep",
            "0",
        ],
        env={"MEMORY_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert output_lines == []
