import json
from dataclasses import dataclass

from typer.testing import CliRunner

from src.cli import app, shared_router
from conftest import write_schema


@dataclass
class StubResult:
    stdout: str
    stderr: str = ""
    returncode: int = 0


runner = CliRunner()


def test_cli_consolidate_defaults(identity_env, monkeypatch):
    data_dir = identity_env / "data"
    write_schema(data_dir)

    def stub_run_core(app_name, args, input_text=None, **kwargs):
        if app_name == "llm":
            return StubResult(stdout="## Purpose\nUpdated\n")
        if app_name == "topics":
            return StubResult(stdout="")
        if app_name == "memory":
            return StubResult(stdout="")
        raise AssertionError(f"unexpected app: {app_name}")

    monkeypatch.setattr(shared_router, "run_core", stub_run_core)

    result = runner.invoke(
        app,
        [
            "consolidate",
            "neo",
            "--schema",
            "cognitive-core",
            "--no-topics",
            "--no-memory",
            "--no-stdin",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "neo"
    assert payload["schema"] == "cognitive-core"
    assert payload["version"] == 1
    assert "content" in payload
