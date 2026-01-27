"""
Plugin Executor - Run plugin commands via subprocess.

Plugins are executed as subprocesses using `uv run` to ensure they run
in the correct Python environment with all dependencies available.
"""

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .context import build_plugin_env
from .discovery import get_plugin_path, validate_plugin
from .exceptions import PluginNotFoundError, PluginExecutionError, PluginTimeoutError


@dataclass
class PluginResult:
    """Result of a plugin execution."""
    exit_code: int
    stdout: str
    stderr: str
    success: bool

    @property
    def output(self) -> str:
        """Get the output to return to the caller.

        Returns stdout for success, formatted error for failure.
        """
        if self.success:
            return self.stdout.strip()
        error_msg = self.stderr.strip() or self.stdout.strip()
        return f"Error (exit {self.exit_code}): {error_msg}"


def execute_plugin(
    name: str,
    command: str,
    timeout: int = 60,
    agent_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> PluginResult:
    """Execute a plugin command.

    Args:
        name: Plugin name
        command: Command string to pass to the plugin CLI
        timeout: Maximum execution time in seconds (default 60)
        agent_id: Current agent ID for context
        topic_id: Current topic ID for context
        session_id: Current session ID for context

    Returns:
        PluginResult with execution details

    Raises:
        PluginNotFoundError: If plugin doesn't exist
        PluginTimeoutError: If execution times out
        PluginExecutionError: If subprocess fails to start
    """
    # Validate plugin exists
    if not validate_plugin(name):
        raise PluginNotFoundError(f"Plugin not found or invalid: {name}")

    plugin_path = get_plugin_path(name)
    cli_path = plugin_path / "cli.py"

    # Build environment
    env = build_plugin_env(
        agent_id=agent_id,
        topic_id=topic_id,
        session_id=session_id
    )

    # Build command - use uv run to ensure correct environment
    # Parse the command string safely
    if command:
        cmd_parts = shlex.split(command)
    else:
        cmd_parts = []

    full_cmd = [sys.executable, str(cli_path)] + cmd_parts

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(plugin_path)
        )

        return PluginResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            success=result.returncode == 0
        )

    except subprocess.TimeoutExpired as e:
        raise PluginTimeoutError(
            f"Plugin {name} timed out after {timeout} seconds"
        )
    except Exception as e:
        raise PluginExecutionError(f"Failed to execute plugin {name}: {e}")


def execute_plugin_help(name: str) -> str:
    """Get help text for a plugin.

    Args:
        name: Plugin name

    Returns:
        Help text from --help command
    """
    result = execute_plugin(name, "--help", timeout=10)
    return result.output
