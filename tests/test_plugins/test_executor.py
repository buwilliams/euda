"""
Plugin Executor Tests.

Tests for plugin execution, timeouts, and error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess


class TestPluginExecution:
    """Test plugin execution functionality."""

    def test_execute_plugin_runs_command(self):
        """Should execute plugin command and return result."""
        from src.plugins import execute_plugin

        result = execute_plugin("core", "dates current")

        assert result.success
        assert result.exit_code == 0
        assert "Date:" in result.stdout

    def test_execute_plugin_returns_result_object(self):
        """Should return PluginResult with all fields."""
        from src.plugins import execute_plugin, PluginResult

        result = execute_plugin("core", "--help")

        assert isinstance(result, PluginResult)
        assert hasattr(result, 'exit_code')
        assert hasattr(result, 'stdout')
        assert hasattr(result, 'stderr')
        assert hasattr(result, 'success')

    def test_execute_plugin_help_returns_usage(self):
        """Should return help text for --help command."""
        from src.plugins import execute_plugin

        result = execute_plugin("core", "--help")

        assert result.success
        assert "topics" in result.stdout.lower()
        assert "memory" in result.stdout.lower()

    def test_execute_plugin_subcommand_help(self):
        """Should return subcommand help."""
        from src.plugins import execute_plugin

        result = execute_plugin("core", "topics --help")

        assert result.success
        assert "list" in result.stdout.lower()
        assert "create" in result.stdout.lower()

    def test_execute_plugin_handles_invalid_command(self):
        """Should handle invalid commands gracefully."""
        from src.plugins import execute_plugin

        result = execute_plugin("core", "nonexistent_command_xyz")

        assert not result.success
        assert result.exit_code != 0


class TestPluginNotFound:
    """Test handling of nonexistent plugins."""

    def test_execute_plugin_raises_for_nonexistent(self):
        """Should raise PluginNotFoundError for nonexistent plugin."""
        from src.plugins import execute_plugin, PluginNotFoundError

        with pytest.raises(PluginNotFoundError):
            execute_plugin("nonexistent_plugin_xyz", "command")

    def test_execute_plugin_raises_for_invalid(self, tmp_path):
        """Should raise PluginNotFoundError for invalid plugin."""
        from src.plugins.executor import execute_plugin
        from src.plugins import PluginNotFoundError
        from src.plugins.discovery import invalidate_cache

        # Create invalid plugin directory (no cli.py)
        plugin_dir = tmp_path / "plugins" / "invalid"
        plugin_dir.mkdir(parents=True)

        with patch('src.plugins.discovery.PLUGINS_DIR', tmp_path / "plugins"):
            invalidate_cache()
            with pytest.raises(PluginNotFoundError):
                execute_plugin("invalid", "command")


class TestPluginTimeout:
    """Test plugin execution timeout handling."""

    def test_execute_plugin_respects_timeout(self):
        """Should timeout for long-running commands."""
        from src.plugins import PluginTimeoutError
        from src.plugins.executor import execute_plugin

        # Mock subprocess to simulate timeout
        with patch('src.plugins.executor.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)

            with pytest.raises(PluginTimeoutError):
                execute_plugin("core", "dates current", timeout=1)

    def test_execute_plugin_default_timeout(self):
        """Should use default timeout of 60 seconds."""
        from src.plugins.executor import execute_plugin

        # This should complete within default timeout
        result = execute_plugin("core", "dates current")
        assert result.success


class TestPluginResult:
    """Test PluginResult dataclass behavior."""

    def test_plugin_result_output_on_success(self):
        """Should return stdout on success."""
        from src.plugins import PluginResult

        result = PluginResult(
            exit_code=0,
            stdout="Success output",
            stderr="",
            success=True
        )

        assert result.output == "Success output"

    def test_plugin_result_output_on_failure(self):
        """Should return formatted error on failure."""
        from src.plugins import PluginResult

        result = PluginResult(
            exit_code=1,
            stdout="",
            stderr="Error message",
            success=False
        )

        assert "Error" in result.output
        assert "1" in result.output
        assert "Error message" in result.output

    def test_plugin_result_output_uses_stdout_if_no_stderr(self):
        """Should use stdout for error if stderr is empty."""
        from src.plugins import PluginResult

        result = PluginResult(
            exit_code=1,
            stdout="Error in stdout",
            stderr="",
            success=False
        )

        assert "Error in stdout" in result.output


class TestPluginExecutionWithContext:
    """Test plugin execution with agent context."""

    def test_execute_plugin_passes_agent_id(self):
        """Should pass agent_id to plugin via environment."""
        from src.plugins.executor import execute_plugin
        from unittest.mock import ANY

        with patch('src.plugins.executor.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr=""
            )

            execute_plugin("core", "dates current", agent_id="test-agent")

            # Check that env was passed with EUNO_AGENT_ID
            call_kwargs = mock_run.call_args[1]
            assert "env" in call_kwargs
            assert call_kwargs["env"].get("EUNO_AGENT_ID") == "test-agent"

    def test_execute_plugin_passes_topic_id(self):
        """Should pass topic_id to plugin via environment."""
        from src.plugins.executor import execute_plugin

        with patch('src.plugins.executor.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr=""
            )

            execute_plugin("core", "dates current", topic_id="topic-123")

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["env"].get("EUNO_TOPIC_ID") == "topic-123"

    def test_execute_plugin_passes_session_id(self):
        """Should pass session_id to plugin via environment."""
        from src.plugins.executor import execute_plugin

        with patch('src.plugins.executor.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr=""
            )

            execute_plugin("core", "dates current", session_id="session-456")

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["env"].get("EUNO_SESSION_ID") == "session-456"
