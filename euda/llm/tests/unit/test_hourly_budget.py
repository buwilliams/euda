import json
from pathlib import Path

from typer.testing import CliRunner

import main
from src.providers import LLMResponse


def write_default_config(tmp_path: Path, monthly_budget: float) -> None:
    config = {
        "calendar_monthly_budget": monthly_budget,
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


class StubClient:
    def call(self, system_prompt: str, prompt: str) -> LLMResponse:
        return LLMResponse(text="ok", input_tokens=1000000, output_tokens=0)


def test_pause_when_budget_exceeded(tmp_path, monkeypatch):
    write_default_config(tmp_path, monthly_budget=1.0)
    monkeypatch.setattr(main, "_get_llm_client", lambda config: StubClient())

    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}
    result = runner.invoke(main.app, ["call", "sys", "hello"], env=env)
    assert result.exit_code == 1
    assert "Hourly budget reached" in result.stderr

    override = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert override["paused"] is True


def test_reset_hour_unpauses(tmp_path, monkeypatch):
    write_default_config(tmp_path, monthly_budget=1.0)
    monkeypatch.setattr(main, "_get_llm_client", lambda config: StubClient())

    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}
    runner.invoke(main.app, ["call", "sys", "hello"], env=env)

    reset = runner.invoke(main.app, ["config", "reset-hour"], env=env)
    assert reset.exit_code == 0

    override = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert override["paused"] is False
    assert override["hourly_input_tokens"] == 0
    assert override["hourly_output_tokens"] == 0
    assert override["hourly_cost"] == 0.0
