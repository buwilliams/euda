import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

import src.cli as cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _write_default_config(tmp_path: Path) -> None:
    (tmp_path / "config.default.json").write_text("{}", encoding="utf-8")


def _db_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "db.sqlite"


def _fetch_all(tmp_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(_db_path(tmp_path))
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM topics").fetchall()


def test_create_reads_stdin_and_sets_defaults(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    result = runner.invoke(
        cli.app,
        ["create", "My Topic"],
        input="hello world\n",
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "My Topic"
    assert payload["description"] == "hello world"
    assert payload["state"] == "todo"
    assert payload["assignee"] == "none"
    assert payload["tags"] == []

    rows = _fetch_all(tmp_path)
    assert len(rows) == 1


def test_update_allows_partial_changes(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    result = runner.invoke(
        cli.app,
        ["create", "Task", "--tag", "alpha"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    topic_id = json.loads(result.stdout)["id"]

    result = runner.invoke(
        cli.app,
        [
            "update",
            topic_id,
            "--state",
            "working",
            "--description",
            "-",
            "--tag",
            "beta",
        ],
        input="new description\n",
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["state"] == "working"
    assert payload["description"] == "new description"
    assert payload["tags"] == ["beta"]


def test_search_filters_by_query_and_tag(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    first = runner.invoke(
        cli.app,
        ["create", "Alpha topic", "--tag", "alpha"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    second = runner.invoke(
        cli.app,
        ["create", "Beta topic", "--tag", "beta"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert first.exit_code == 0
    assert second.exit_code == 0

    result = runner.invoke(
        cli.app,
        ["search", "--query", "alpha", "--tag", "alpha"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["name"] == "Alpha topic"


def test_delete_removes_descendants_and_assets(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    parent = runner.invoke(
        cli.app,
        ["create", "Parent"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    parent_id = json.loads(parent.stdout)["id"]

    child = runner.invoke(
        cli.app,
        ["create", "Child", "--parent-id", parent_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    child_id = json.loads(child.stdout)["id"]

    (tmp_path / "data" / "assets" / parent_id).mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "assets" / child_id).mkdir(parents=True, exist_ok=True)

    result = runner.invoke(
        cli.app,
        ["delete", parent_id, "--yes"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    assert _fetch_all(tmp_path) == []
    assert not (tmp_path / "data" / "assets" / parent_id).exists()
    assert not (tmp_path / "data" / "assets" / child_id).exists()
