"""System management commands for the core skill."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_system_module():
    """Lazy import of system module."""
    from src.core.system.system import (
        get_system_config,
        set_nested_config,
        trigger_config_reload,
    )
    return {
        "get_system_config": get_system_config,
        "set_nested_config": set_nested_config,
        "trigger_config_reload": trigger_config_reload,
    }


@app.command("restart")
def restart_cmd(
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Reason for restart"),
):
    """Restart the Euno server.

    This triggers a graceful restart by calling the restart API endpoint.
    The server must be running with the run-euno.sh wrapper script for
    automatic restart to work.
    """
    import requests

    try:
        response = requests.post(
            "http://localhost:8000/api/system/restart",
            json={"reason": reason} if reason else {},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print("Restart requested successfully")
            if data.get("reason"):
                print(f"Reason: {data['reason']}")
            print("\nServer will restart momentarily...")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            raise typer.Exit(1)

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server at localhost:8000")
        print("Is the server running?")
        raise typer.Exit(1)
    except Exception as e:
        print(f"Error: {e}")
        raise typer.Exit(1)


@app.command("show")
def show_cmd(
    key: Optional[str] = typer.Argument(None, help="Config key to show (dot notation, e.g., 'logging.level')"),
):
    """Show system configuration.

    Without arguments, shows the entire config.
    With a key, shows just that value (supports dot notation).
    """
    import json

    m = _get_system_module()
    config = m["get_system_config"]()

    if key:
        # Navigate to nested key
        parts = key.split(".")
        value = config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                print(f"Key not found: {key}")
                raise typer.Exit(1)
        if isinstance(value, (dict, list)):
            print(json.dumps(value, indent=2))
        else:
            print(value)
    else:
        print(json.dumps(config, indent=2))


@app.command("set")
def set_cmd(
    key: str = typer.Argument(..., help="Config key (dot notation, e.g., 'logging.level')"),
    value: str = typer.Argument(..., help="Value to set (JSON for complex values)"),
):
    """Update a system configuration value.

    Supports dot notation for nested keys (e.g., 'logging.level').
    Complex values should be JSON-encoded.
    """
    import json

    m = _get_system_module()

    # Try to parse value as JSON for complex types
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        # Keep as string if not valid JSON
        parsed_value = value

    result = m["set_nested_config"](key, parsed_value)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Updated: {key} = {parsed_value}")


@app.command("reload")
def reload_cmd():
    """Force reload of all cached configurations.

    This invalidates caches for:
    - System config
    - LLM config
    - Prompt templates
    - Agent configs (via hot reload)
    """
    m = _get_system_module()
    result = m["trigger_config_reload"]()

    print("Configuration caches invalidated:")
    for item in result.get("invalidated", []):
        print(f"  - {item}")


@app.command("llm")
def llm_cmd():
    """Show current LLM configuration."""
    import json
    from src.llms import get_provider, get_model
    from src.llms.base import _load_config

    config = _load_config()

    print("LLM Configuration:")
    print(f"  Provider: {get_provider()}")
    print(f"  Model: {get_model()}")

    budget = config.get("budget", {})
    if budget:
        print(f"\nBudget:")
        print(f"  Limit: ${budget.get('limit', 'unlimited')}")
        print(f"  Period: {budget.get('period', 'monthly')}")
