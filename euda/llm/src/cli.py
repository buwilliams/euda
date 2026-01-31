import calendar
import json
from datetime import datetime, timezone
import typer

from src.config import (
    OVERRIDE_CONFIG_FILENAME,
    config_dir,
    get_value,
    load_config,
    parse_value,
    set_value,
    write_override,
)
from src.llm import get_llm_client
from src.providers import LLMClientError

app = typer.Typer(help="LLM CLI.")
config_app = typer.Typer(help="Inspect or update config.json overrides and merged defaults.")
app.add_typer(config_app, name="config")


def _get_llm_client(config):
    return get_llm_client(config)


@config_app.command("get", help="Get a merged config value (defaults + overrides).")
def config_get(key: str = typer.Argument(..., help="Config key, supports dot paths.")) -> None:
    config, _ = load_config()
    try:
        value = get_value(config, key)
    except KeyError:
        typer.echo(f"Missing key: {key}", err=True)
        raise typer.Exit(code=1)
    if isinstance(value, (dict, list)):
        typer.echo(json.dumps(value, indent=2, sort_keys=True))
    else:
        typer.echo(value)


@config_app.command("set", help="Set a config.json override (dot path).")
def config_set(
    key: str = typer.Argument(..., help="Config key, supports dot paths."),
    value: str = typer.Argument(..., help="JSON value or raw string."),
) -> None:
    _, override = load_config()
    parsed = parse_value(value)
    if key.endswith("hourly_cost") and isinstance(parsed, (int, float, str)):
        parsed = round(float(parsed), 2)
    set_value(override, key, parsed)
    write_override(override)
    if isinstance(parsed, (dict, list)):
        typer.echo(json.dumps(parsed, indent=2, sort_keys=True))
    else:
        typer.echo(parsed)


@config_app.command("cat", help="Print raw config.json (overrides only).")
def config_cat() -> None:
    path = config_dir() / OVERRIDE_CONFIG_FILENAME
    if not path.exists():
        return
    typer.echo(path.read_text(encoding="utf-8").rstrip("\n"))


@config_app.command("cat-full", help="Print the merged config (defaults + overrides).")
def config_cat_full() -> None:
    config, _ = load_config()
    typer.echo(json.dumps(config, indent=2, sort_keys=True))


@config_app.command("reset-hour", help="Reset the hourly counters and unpause.")
def config_reset_hour() -> None:
    config, override = load_config()
    _reset_hourly_state(config, override)
    write_override(override)
    typer.echo("Hourly counters reset.")


@config_app.command("write", help="Replace config.json with a full JSON object.")
def config_write(
    payload: str | None = typer.Argument(
        None, help="Full JSON object to write to config.json. Reads stdin if omitted or '-'."
    ),
) -> None:
    if payload is None or payload == "-":
        payload = typer.get_text_stream("stdin").read()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        typer.echo("Payload must be valid JSON.", err=True)
        raise typer.Exit(code=1)
    if not isinstance(data, dict):
        typer.echo("Payload must be a JSON object.", err=True)
        raise typer.Exit(code=1)
    write_override(data)
    typer.echo(json.dumps(data, indent=2, sort_keys=True))


def _current_hour_start_utc() -> str:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def _reset_hourly_state(config: dict, override: dict) -> None:
    current = _current_hour_start_utc()
    set_value(override, "hour_window_start_utc", current)
    set_value(override, "hourly_input_tokens", 0)
    set_value(override, "hourly_output_tokens", 0)
    set_value(override, "hourly_cost", 0.0)
    set_value(override, "paused", False)
    config["hour_window_start_utc"] = current
    config["hourly_input_tokens"] = 0
    config["hourly_output_tokens"] = 0
    config["hourly_cost"] = 0.0
    config["paused"] = False


def _hourly_budget(config: dict) -> float:
    now = datetime.now(timezone.utc)
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    monthly = config.get("calendar_monthly_budget", 0.0) or 0.0
    return monthly / (days_in_month * 24)


def _model_pricing(config: dict) -> tuple[float, float]:
    provider = config.get("provider")
    model = config.get("model")
    models = (config.get("providers") or {}).get(provider, {}).get("models", {})
    pricing = models.get(model, {})
    return (
        float(pricing.get("price_input_per_million", 0.0) or 0.0),
        float(pricing.get("price_output_per_million", 0.0) or 0.0),
    )


@app.command(help="Send a system prompt and user prompt to the selected model.")
def call(
    system_prompt: str | None = typer.Argument(
        None, help="System prompt, or '-' to read the system prompt from stdin."
    ),
    prompt: str | None = typer.Argument(
        None, help="User prompt. Reads stdin if omitted or '-'."
    ),
    provider: str | None = typer.Option(None, "--provider", help="Override provider for this call."),
    model: str | None = typer.Option(None, "--model", help="Override model for this call."),
) -> None:
    config, override = load_config()
    current_hour = _current_hour_start_utc()
    if config.get("hour_window_start_utc") != current_hour:
        _reset_hourly_state(config, override)
        write_override(override)
    if system_prompt is None:
        system_prompt = ""
    elif system_prompt == "-":
        system_prompt = typer.get_text_stream("stdin").read()
    if prompt is None or prompt == "-":
        prompt = typer.get_text_stream("stdin").read()
    if provider:
        config["provider"] = provider
    if model:
        config["model"] = model
    if config.get("paused"):
        typer.echo("Hourly budget reached. Try again next hour.", err=True)
        raise typer.Exit(code=1)
    try:
        client = _get_llm_client(config)
        response = client.call(system_prompt, prompt)
    except LLMClientError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    typer.echo(response.text)
    input_tokens = response.input_tokens or 0
    output_tokens = response.output_tokens or 0
    total_tokens = response.total_tokens
    if total_tokens is None:
        total_tokens = input_tokens + output_tokens
    input_rate, output_rate = _model_pricing(config)
    hourly_cost = config.get("hourly_cost", 0.0) or 0.0
    hourly_cost += (input_tokens / 1_000_000) * input_rate
    hourly_cost += (output_tokens / 1_000_000) * output_rate
    hourly_cost = round(hourly_cost, 2)
    set_value(override, "hourly_input_tokens", (config.get("hourly_input_tokens", 0) or 0) + input_tokens)
    set_value(override, "hourly_output_tokens", (config.get("hourly_output_tokens", 0) or 0) + output_tokens)
    set_value(override, "hourly_cost", hourly_cost)
    set_value(override, "hourly_token_count", (config.get("hourly_token_count", 0) or 0) + total_tokens)
    budget = _hourly_budget(config)
    if hourly_cost >= budget and budget > 0:
        set_value(override, "paused", True)
        write_override(override)
        typer.echo("Hourly budget reached. Pausing until next hour.", err=True)
        raise typer.Exit(code=1)
    write_override(override)


if __name__ == "__main__":
    app()
