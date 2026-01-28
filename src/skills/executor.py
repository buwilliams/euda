"""
Skill Executor - Run skill commands via subprocess.

Skills are executed as subprocesses using `uv run` to ensure they run
in the correct Python environment with all dependencies available.
"""

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .context import build_skill_env
from .discovery import get_skill_path, validate_skill
from .exceptions import SkillNotFoundError, SkillExecutionError, SkillTimeoutError


@dataclass
class SkillResult:
    """Result of a skill execution."""
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


def execute_skill(
    name: str,
    command: str,
    timeout: int = 60,
    agent_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> SkillResult:
    """Execute a skill command.

    Args:
        name: Skill name
        command: Command string to pass to the skill CLI
        timeout: Maximum execution time in seconds (default 60)
        agent_id: Current agent ID for context
        topic_id: Current topic ID for context
        session_id: Current session ID for context

    Returns:
        SkillResult with execution details

    Raises:
        SkillNotFoundError: If skill doesn't exist
        SkillTimeoutError: If execution times out
        SkillExecutionError: If subprocess fails to start
    """
    # Validate skill exists
    if not validate_skill(name):
        raise SkillNotFoundError(f"Skill not found or invalid: {name}")

    skill_path = get_skill_path(name)
    cli_path = skill_path / "cli.py"

    # Build environment
    env = build_skill_env(
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
            cwd=str(skill_path)
        )

        return SkillResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            success=result.returncode == 0
        )

    except subprocess.TimeoutExpired as e:
        raise SkillTimeoutError(
            f"Skill {name} timed out after {timeout} seconds"
        )
    except Exception as e:
        raise SkillExecutionError(f"Failed to execute skill {name}: {e}")


def execute_skill_help(name: str) -> str:
    """Get help text for a skill.

    Args:
        name: Skill name

    Returns:
        Help text from --help command
    """
    result = execute_skill(name, "--help", timeout=10)
    return result.output
