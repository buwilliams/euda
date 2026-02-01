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


def test_list_and_get_with_filters(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    first = runner.invoke(
        cli.app,
        ["create", "Parent", "--state", "working", "--assignee", "agent", "--tag", "alpha"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    parent_id = json.loads(first.stdout)["id"]
    second = runner.invoke(
        cli.app,
        ["create", "Child", "--parent-id", parent_id, "--tag", "beta"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    child_id = json.loads(second.stdout)["id"]

    result = runner.invoke(
        cli.app,
        ["list", "--state", "working", "--assignee", "agent", "--tag", "alpha"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == parent_id

    result = runner.invoke(
        cli.app,
        ["list", "--parent-id", parent_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == child_id

    result = runner.invoke(
        cli.app,
        ["get", child_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["name"] == "Child"


def test_state_validation_and_parent_validation(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    result = runner.invoke(
        cli.app,
        ["create", "Bad", "--state", "invalid"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code != 0

    result = runner.invoke(
        cli.app,
        ["create", "Child", "--parent-id", "unknown"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code != 0


def test_update_tags_and_parent_controls(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    parent = runner.invoke(
        cli.app,
        ["create", "Parent"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    parent_id = json.loads(parent.stdout)["id"]
    child = runner.invoke(
        cli.app,
        ["create", "Child", "--tag", "alpha", "--parent-id", parent_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    child_id = json.loads(child.stdout)["id"]

    result = runner.invoke(
        cli.app,
        ["update", child_id, "--clear-tags"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    payload = json.loads(result.stdout)
    assert payload["tags"] == []

    result = runner.invoke(
        cli.app,
        ["update", child_id, "--clear-parent"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    payload = json.loads(result.stdout)
    assert payload["parent_id"] is None

    result = runner.invoke(
        cli.app,
        ["update", child_id, "--tag", "alpha", "--clear-tags"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code != 0

    result = runner.invoke(
        cli.app,
        ["update", child_id, "--parent-id", parent_id, "--clear-parent"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code != 0


def test_update_changes_updated_at(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    created = runner.invoke(
        cli.app,
        ["create", "Task"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    topic_id = json.loads(created.stdout)["id"]

    fetched = runner.invoke(
        cli.app,
        ["get", topic_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    before = json.loads(fetched.stdout)["updated_at"]

    updated = runner.invoke(
        cli.app,
        ["update", topic_id, "--name", "Task Updated"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    after = json.loads(updated.stdout)["updated_at"]
    assert after >= before


def test_delete_requires_confirmation(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    created = runner.invoke(
        cli.app,
        ["create", "Task"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    topic_id = json.loads(created.stdout)["id"]

    result = runner.invoke(
        cli.app,
        ["delete", topic_id],
        input="no\n",
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code != 0
    assert _fetch_all(tmp_path)
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


def test_children_ancestors_descendants_and_path(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    root = runner.invoke(
        cli.app,
        ["create", "Root"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    root_id = json.loads(root.stdout)["id"]
    child = runner.invoke(
        cli.app,
        ["create", "Child", "--parent-id", root_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    child_id = json.loads(child.stdout)["id"]
    grand = runner.invoke(
        cli.app,
        ["create", "Grand", "--parent-id", child_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    grand_id = json.loads(grand.stdout)["id"]

    result = runner.invoke(
        cli.app,
        ["children", root_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == child_id

    result = runner.invoke(
        cli.app,
        ["ancestors", grand_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    names = [json.loads(line)["name"] for line in lines]
    assert names == ["Child", "Root"]

    result = runner.invoke(
        cli.app,
        ["descendants", root_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    ids = [json.loads(line)["id"] for line in lines]
    assert ids == [child_id, grand_id]

    result = runner.invoke(
        cli.app,
        ["path", grand_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.stdout.strip() == "Root/Child/Grand"

    result = runner.invoke(
        cli.app,
        ["find", "--path", "Root/Child/Grand"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert json.loads(result.stdout)["id"] == grand_id


def test_move_and_parent_clear_and_archive_tree(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    root = runner.invoke(
        cli.app,
        ["create", "Root"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    root_id = json.loads(root.stdout)["id"]
    other = runner.invoke(
        cli.app,
        ["create", "Other"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    other_id = json.loads(other.stdout)["id"]
    child = runner.invoke(
        cli.app,
        ["create", "Child", "--parent-id", root_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    child_id = json.loads(child.stdout)["id"]

    moved = runner.invoke(
        cli.app,
        ["move", child_id, other_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert json.loads(moved.stdout)["parent_id"] == other_id

    cleared = runner.invoke(
        cli.app,
        ["parent-clear", child_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert json.loads(cleared.stdout)["parent_id"] is None

    runner.invoke(
        cli.app,
        ["move", child_id, root_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )

    result = runner.invoke(
        cli.app,
        ["archive-tree", root_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0

    listed = runner.invoke(
        cli.app,
        ["list", "--parent-id", root_id],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    payload = json.loads(listed.stdout.strip())
    assert payload["state"] == "archived"


def test_include_descendants_filters(tmp_path: Path, runner: CliRunner) -> None:
    _write_default_config(tmp_path)

    root = runner.invoke(
        cli.app,
        ["create", "Root", "--assignee", "agent"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    root_id = json.loads(root.stdout)["id"]
    child = runner.invoke(
        cli.app,
        ["create", "Child", "--parent-id", root_id, "--assignee", "agent"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    child_id = json.loads(child.stdout)["id"]

    result = runner.invoke(
        cli.app,
        ["list", "--parent-id", root_id, "--include-descendants"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    ids = [json.loads(line)["id"] for line in lines]
    assert ids == [child_id]

    result = runner.invoke(
        cli.app,
        ["search", "--query", "child", "--parent-id", root_id, "--include-descendants"],
        env={"TOPICS_CONFIG_DIR": str(tmp_path)},
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == child_id
