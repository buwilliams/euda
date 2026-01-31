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
                        "price_output_per_million": 2.0
                    }
                }
            }
        },
    }
    (tmp_path / "config.default.json").write_text(json.dumps(config), encoding="utf-8")


class StubClient:
    def call(self, system_prompt: str, prompt: str) -> LLMResponse:
        return LLMResponse(text=f"{system_prompt}::{prompt}", input_tokens=2, output_tokens=1)


def test_call_updates_usage(tmp_path, monkeypatch):
    write_default_config(tmp_path)
    monkeypatch.setattr(cli, "_get_llm_client", lambda config: StubClient())

    runner = CliRunner()
    env = {"LLM_CONFIG_DIR": str(tmp_path)}
    result = runner.invoke(main.app, ["call", "sys", "hello"], env=env)
    assert result.exit_code == 0
    assert result.stdout.strip() == "sys::hello"

    override_path = tmp_path / "config.json"
    override = json.loads(override_path.read_text(encoding="utf-8"))
    assert override["hourly_input_tokens"] == 2
    assert override["hourly_output_tokens"] == 1
