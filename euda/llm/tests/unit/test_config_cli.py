import json
from pathlib import Path

from typer.testing import CliRunner

from main import app


def write_default_config(tmp_path: Path) -> None:
    config = {
        "calendar_monthly_budget": 10.0,
        "hourly_token_count": 0,
        "paused": False,
        "provider": "openai",
        "model": "gpt-4o-mini",
        "providers": {"openai": {"models": {"gpt-4o-mini": {}}}},
    }
    (tmp_path / "config.default.json").write_text(json.dumps(config), encoding="utf-8")


def test_config_get_set(tmp_path):
    write_default_config(tmp_path)
    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}

    result = runner.invoke(app, ["config", "get", "provider"], env=env)
    assert result.exit_code == 0
    assert result.stdout.strip() == "openai"

    result = runner.invoke(app, ["config", "set", "provider", "xai"], env=env)
    assert result.exit_code == 0
    assert result.stdout.strip() == "xai"

    result = runner.invoke(app, ["config", "get", "provider"], env=env)
    assert result.exit_code == 0
    assert result.stdout.strip() == "xai"

    override_path = tmp_path / "config.json"
    assert override_path.exists()
    override = json.loads(override_path.read_text(encoding="utf-8"))
    assert override["provider"] == "xai"


def test_config_set_rounds_hourly_cost(tmp_path):
    write_default_config(tmp_path)
    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}

    result = runner.invoke(app, ["config", "set", "hourly_cost", "0.1234"], env=env)
    assert result.exit_code == 0

    override = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert override["hourly_cost"] == 0.12
