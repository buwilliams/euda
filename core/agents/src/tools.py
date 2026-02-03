import json
from typing import Any, Dict, List

import shared_router

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "list_apps",
        "description": (
            "List all available euda applications. "
            "Returns the output of 'euda core list' and 'euda skills list' combined."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "app_usage",
        "description": (
            "Show the help/usage text for a specific euda application. "
            "Provide the app path as '<category> <app>', e.g. 'core topics' or 'skills gcal'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "app_path": {
                    "type": "string",
                    "description": "App path in the form '<category> <app>', e.g. 'core topics'.",
                },
            },
            "required": ["app_path"],
        },
    },
    {
        "name": "execute_command",
        "description": (
            "Execute an euda CLI command and return its output. "
            "Provide the command without the leading 'euda' prefix, "
            "e.g. 'core topics list --state todo'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The euda command to run (without the 'euda' prefix).",
                },
            },
            "required": ["command"],
        },
    },
]


def tools_for_openai() -> List[Dict[str, Any]]:
    result = []
    for tool in TOOLS:
        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        })
    return result


def execute_list_apps() -> str:
    try:
        core = shared_router.run_cli(
            ["uv", "run", "euda", "core", "list"],
            timeout=15.0,
        )
        skills = shared_router.run_cli(
            ["uv", "run", "euda", "skills", "list"],
            timeout=15.0,
        )
        parts = []
        if core.stdout.strip():
            parts.append("=== Core Apps ===\n" + core.stdout.strip())
        if skills.stdout.strip():
            parts.append("=== Skills Apps ===\n" + skills.stdout.strip())
        if not parts:
            return "No apps found."
        return "\n\n".join(parts)
    except Exception as exc:
        return f"Error listing apps: {exc}"


def execute_app_usage(app_path: str) -> str:
    try:
        parts = app_path.strip().split()
        if len(parts) != 2:
            return f"Invalid app_path '{app_path}'. Expected '<category> <app>', e.g. 'core topics'."
        category, app_name = parts
        if category not in ("core", "skills"):
            return f"Invalid category '{category}'. Must be 'core' or 'skills'."
        result = shared_router.run_cli(
            ["uv", "run", "euda", category, "help", app_name],
            timeout=15.0,
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else "No usage information available."
    except Exception as exc:
        return f"Error getting usage: {exc}"


def execute_command(command: str, timeout: float = 30.0) -> str:
    try:
        args = command.strip().split()
        if not args:
            return "Error: empty command."
        result = shared_router.run_cli(
            ["uv", "run", "euda", *args],
            timeout=timeout,
        )
        parts = []
        if result.stdout.strip():
            parts.append(result.stdout.strip())
        if result.stderr.strip():
            parts.append(f"[stderr] {result.stderr.strip()}")
        if result.returncode != 0:
            parts.append(f"[exit code: {result.returncode}]")
        return "\n".join(parts) if parts else "(no output)"
    except Exception as exc:
        return f"Error executing command: {exc}"


def dispatch_tool(name: str, tool_input: Dict[str, Any], timeout: float = 30.0) -> str:
    if name == "list_apps":
        return execute_list_apps()
    elif name == "app_usage":
        return execute_app_usage(tool_input.get("app_path", ""))
    elif name == "execute_command":
        return execute_command(tool_input.get("command", ""), timeout=timeout)
    else:
        return f"Unknown tool: {name}"
