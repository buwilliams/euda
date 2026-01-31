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


def _write_default_config(tmp_path: Path) -> None:
    (tmp_path / "config.default.json").write_text("{}", encoding="utf-8")


def test_write_uses_stdin_and_appends_jsonl(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    fixed = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, fixed)
    _write_default_config(tmp_path)

    result = runner.invoke(cli.app, ["write"], input="hello world\n", env={"LOGS_CONFIG_DIR": str(tmp_path)})

    assert result.exit_code == 0
    log_path = tmp_path / "data" / "2026" / "20260131-system-none.jsonl"
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["timestamp"] == fixed.isoformat()
    assert entry["type"] == "system"
    assert entry["id"] == "none"
    assert entry["message"] == "hello world"


def test_read_filters_by_time_type_and_id(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_default_config(tmp_path)

    first_time = datetime(2026, 1, 31, 10, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, first_time)
    runner.invoke(
        cli.app,
        ["write", "first", "--type", "system", "--id", "none"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )

    second_time = datetime(2026, 1, 31, 11, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, second_time)
    runner.invoke(
        cli.app,
        ["write", "second", "--type", "app", "--id", "abc"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )

    result = runner.invoke(
        cli.app,
        [
            "read",
            "--start-date",
            "2026-01-31",
            "--end-date",
            "2026-01-31",
            "--start-time",
            "09:30",
            "--end-time",
            "10:30",
        ],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(output_lines) == 1
    assert json.loads(output_lines[0])["message"] == "first"

    now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, now)
    result = runner.invoke(
        cli.app,
        ["read", "--hours", "2", "--type", "app", "--id", "abc"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(output_lines) == 1
    assert json.loads(output_lines[0])["message"] == "second"


def test_read_skips_malformed_lines(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    fixed = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, fixed)
    _write_default_config(tmp_path)

    runner.invoke(
        cli.app,
        ["write", "good", "--type", "system", "--id", "none"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )
    log_path = tmp_path / "data" / "2026" / "20260131-system-none.jsonl"
    log_path.write_text(log_path.read_text(encoding="utf-8") + "not-json\n", encoding="utf-8")

    result = runner.invoke(
        cli.app,
        ["read", "--start-date", "2026-01-31", "--end-date", "2026-01-31"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(output_lines) == 1
    assert json.loads(output_lines[0])["message"] == "good"


def test_clean_requires_confirmation_and_removes_logs(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, fixed)
    _write_default_config(tmp_path)

    runner.invoke(
        cli.app,
        ["write", "cleanup", "--type", "system", "--id", "none"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )
    data_root = tmp_path / "data"
    assert data_root.exists()

    result = runner.invoke(cli.app, ["clean", "--all"], input="no\n", env={"LOGS_CONFIG_DIR": str(tmp_path)})
    assert result.exit_code == 1
    assert data_root.exists()

    result = runner.invoke(cli.app, ["clean", "--all"], input="yes\n", env={"LOGS_CONFIG_DIR": str(tmp_path)})
    assert result.exit_code == 0
    assert not data_root.exists()


def test_clean_filters_by_time_and_type(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_default_config(tmp_path)
    first_time = datetime(2026, 1, 31, 9, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, first_time)
    runner.invoke(
        cli.app,
        ["write", "keep", "--type", "system", "--id", "none"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )

    second_time = datetime(2026, 1, 31, 11, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, second_time)
    runner.invoke(
        cli.app,
        ["write", "delete", "--type", "app", "--id", "abc"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )

    now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, now)
    result = runner.invoke(
        cli.app,
        ["clean", "--hours", "2", "--type", "app", "--id", "abc", "--yes"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0

    log_path_app = tmp_path / "data" / "2026" / "20260131-app-abc.jsonl"
    assert not log_path_app.exists()
    log_path_system = tmp_path / "data" / "2026" / "20260131-system-none.jsonl"
    assert log_path_system.exists()


def test_tail_outputs_existing_lines_with_filters(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed = datetime(2026, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
    _set_fixed_time(monkeypatch, fixed)
    _write_default_config(tmp_path)

    log_dir = tmp_path / "data" / "2026"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "20260131-app-abc.jsonl"
    entries = [
        {"timestamp": fixed.isoformat(), "type": "app", "id": "abc", "message": "one"},
        {"timestamp": fixed.isoformat(), "type": "app", "id": "abc", "message": "two"},
    ]
    log_path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")

    result = runner.invoke(
        cli.app,
        ["tail", "--type", "app", "--id", "abc", "--_iterations", "1", "--_sleep", "0"],
        env={"LOGS_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(output_lines) == 2
    assert [json.loads(line)["message"] for line in output_lines] == ["one", "two"]
