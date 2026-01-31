import json
from pathlib import Path

from typer.testing import CliRunner

import main


def write_default_config(tmp_path: Path) -> None:
    config = {
        "calendar_monthly_budget": 10.0,
        "hourly_input_tokens": 0,
        "hourly_output_tokens": 0,
        "hourly_cost": 0.0,
        "hour_window_start_utc": "",
        "paused": False,
        "provider": "openai",
        "model": "gpt-4o-mini",
        "providers": {
            "openai": {
                "models": {
                    "gpt-4o-mini": {
                        "price_input_per_million": 1.0,
                        "price_output_per_million": 2.0,
                    }
                }
            }
        },
    }
    (tmp_path / "config.default.json").write_text(json.dumps(config), encoding="utf-8")


def test_unknown_provider_error(tmp_path):
    write_default_config(tmp_path)
    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}
    result = runner.invoke(main.app, ["call", "sys", "hello", "--provider", "bad"], env=env)
    assert result.exit_code == 1
    assert "Unknown provider" in result.stderr


def test_unknown_model_error(tmp_path):
    write_default_config(tmp_path)
    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}
    result = runner.invoke(main.app, ["call", "sys", "hello", "--model", "nope"], env=env)
    assert result.exit_code == 1
    assert "Unknown model" in result.stderr
