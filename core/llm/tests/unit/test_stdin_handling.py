import json
from pathlib import Path

from typer.testing import CliRunner

import main
import src.cli as cli
from src.providers import LLMResponse


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


class StubClient:
    def call(self, system_prompt: str, prompt: str) -> LLMResponse:
        return LLMResponse(text=f"{system_prompt}::{prompt}")


def test_call_reads_stdin_prompt(tmp_path, monkeypatch):
    write_default_config(tmp_path)
    monkeypatch.setattr(cli, "_get_llm_client", lambda config: StubClient())

    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}
    result = runner.invoke(
        main.app,
        ["call", "sys"],
        env=env,
        input="from-stdin",
    )
    assert result.exit_code == 0
    assert result.stdout.strip() == "sys::from-stdin"


def test_call_defaults_empty_system_prompt(tmp_path, monkeypatch):
    write_default_config(tmp_path)
    monkeypatch.setattr(cli, "_get_llm_client", lambda config: StubClient())

    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}
    result = runner.invoke(main.app, ["call", "hello"], env=env)
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello::"


def test_config_write_reads_stdin(tmp_path):
    write_default_config(tmp_path)

    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}
    payload = '{"provider":"xai"}'
    result = runner.invoke(main.app, ["config", "write"], env=env, input=payload)
    assert result.exit_code == 0

    override = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert override["provider"] == "xai"
