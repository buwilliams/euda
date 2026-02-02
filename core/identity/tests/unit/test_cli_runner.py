import json
from dataclasses import dataclass

from typer.testing import CliRunner

from src.cli import app, shared_router
from tests.unit.conftest import write_guide, write_identity


@dataclass
class StubResult:
    stdout: str
    stderr: str = ""
    returncode: int = 0


runner = CliRunner()


def test_cli_consolidate_defaults(identity_env, monkeypatch):
    data_dir = identity_env / "data"
    write_guide(data_dir)
    write_identity(data_dir, name="neo")

    def stub_run_core(app_name, args, input_text=None, **kwargs):
        assert app_name == "llm"
        return StubResult(stdout="# neo\n\n## Purpose\nUpdated\n")

    monkeypatch.setattr(shared_router, "run_core", stub_run_core)

    result = runner.invoke(
        app,
        ["consolidate", "neo", "--text", "signal"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "neo"
    assert payload["version"] == 2
