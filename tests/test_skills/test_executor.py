"""
Skill Executor Tests.

Tests for skill execution, timeouts, and error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess


class TestSkillExecution:
    """Test skill execution functionality."""

    def test_execute_skill_runs_command(self):
        """Should execute skill command and return result."""
        from src.skills import execute_skill

        result = execute_skill("core", "dates current")

        assert result.success
        assert result.exit_code == 0
        assert "Date:" in result.stdout

    def test_execute_skill_returns_result_object(self):
        """Should return SkillResult with all fields."""
        from src.skills import execute_skill, SkillResult

        result = execute_skill("core", "--help")

        assert isinstance(result, SkillResult)
        assert hasattr(result, 'exit_code')
        assert hasattr(result, 'stdout')
        assert hasattr(result, 'stderr')
        assert hasattr(result, 'success')

    def test_execute_skill_help_returns_usage(self):
        """Should return help text for --help command."""
        from src.skills import execute_skill

        result = execute_skill("core", "--help")

        assert result.success
        assert "topics" in result.stdout.lower()
        assert "memory" in result.stdout.lower()

    def test_execute_skill_subcommand_help(self):
        """Should return subcommand help."""
        from src.skills import execute_skill

        result = execute_skill("core", "topics --help")

        assert result.success
        assert "list" in result.stdout.lower()
        assert "create" in result.stdout.lower()

    def test_execute_skill_handles_invalid_command(self):
        """Should handle invalid commands gracefully."""
        from src.skills import execute_skill

        result = execute_skill("core", "nonexistent_command_xyz")

        assert not result.success
        assert result.exit_code != 0


class TestSkillNotFound:
    """Test handling of nonexistent skills."""

    def test_execute_skill_raises_for_nonexistent(self):
        """Should raise SkillNotFoundError for nonexistent skill."""
        from src.skills import execute_skill, SkillNotFoundError

        with pytest.raises(SkillNotFoundError):
            execute_skill("nonexistent_skill_xyz", "command")

    def test_execute_skill_raises_for_invalid(self, tmp_path):
        """Should raise SkillNotFoundError for invalid skill."""
        from src.skills.executor import execute_skill
        from src.skills import SkillNotFoundError
        from src.skills.discovery import invalidate_cache

        # Create invalid skill directory (no cli.py)
        skill_dir = tmp_path / "skills" / "invalid"
        skill_dir.mkdir(parents=True)

        with patch('src.skills.discovery.SKILLS_DIR', tmp_path / "skills"):
            invalidate_cache()
            with pytest.raises(SkillNotFoundError):
                execute_skill("invalid", "command")


class TestSkillTimeout:
    """Test skill execution timeout handling."""

    def test_execute_skill_respects_timeout(self):
        """Should timeout for long-running commands."""
        from src.skills import SkillTimeoutError
        from src.skills.executor import execute_skill

        # Mock subprocess to simulate timeout
        with patch('src.skills.executor.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)

            with pytest.raises(SkillTimeoutError):
                execute_skill("core", "dates current", timeout=1)

    def test_execute_skill_default_timeout(self):
        """Should use default timeout of 60 seconds."""
        from src.skills.executor import execute_skill

        # This should complete within default timeout
        result = execute_skill("core", "dates current")
        assert result.success


class TestSkillResult:
    """Test SkillResult dataclass behavior."""

    def test_skill_result_output_on_success(self):
        """Should return stdout on success."""
        from src.skills import SkillResult

        result = SkillResult(
            exit_code=0,
            stdout="Success output",
            stderr="",
            success=True
        )

        assert result.output == "Success output"

    def test_skill_result_output_on_failure(self):
        """Should return formatted error on failure."""
        from src.skills import SkillResult

        result = SkillResult(
            exit_code=1,
            stdout="",
            stderr="Error message",
            success=False
        )

        assert "Error" in result.output
        assert "1" in result.output
        assert "Error message" in result.output

    def test_skill_result_output_uses_stdout_if_no_stderr(self):
        """Should use stdout for error if stderr is empty."""
        from src.skills import SkillResult

        result = SkillResult(
            exit_code=1,
            stdout="Error in stdout",
            stderr="",
            success=False
        )

        assert "Error in stdout" in result.output


class TestSkillExecutionWithContext:
    """Test skill execution with agent context."""

    def test_execute_skill_passes_agent_id(self):
        """Should pass agent_id to skill via environment."""
        from src.skills.executor import execute_skill
        from unittest.mock import ANY

        with patch('src.skills.executor.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr=""
            )

            execute_skill("core", "dates current", agent_id="test-agent")

            # Check that env was passed with EUNO_AGENT_ID
            call_kwargs = mock_run.call_args[1]
            assert "env" in call_kwargs
            assert call_kwargs["env"].get("EUNO_AGENT_ID") == "test-agent"

    def test_execute_skill_passes_topic_id(self):
        """Should pass topic_id to skill via environment."""
        from src.skills.executor import execute_skill

        with patch('src.skills.executor.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr=""
            )

            execute_skill("core", "dates current", topic_id="topic-123")

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["env"].get("EUNO_TOPIC_ID") == "topic-123"

    def test_execute_skill_passes_session_id(self):
        """Should pass session_id to skill via environment."""
        from src.skills.executor import execute_skill

        with patch('src.skills.executor.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr=""
            )

            execute_skill("core", "dates current", session_id="session-456")

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["env"].get("EUNO_SESSION_ID") == "session-456"
