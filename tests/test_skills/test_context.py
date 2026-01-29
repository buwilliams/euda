"""
Skill Context Tests.

Tests for environment variable building and context passing.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch


class TestBuildSkillEnv:
    """Test environment variable building for skill execution."""

    def test_build_skill_env_includes_data_dir(self):
        """Should always include EUNO_DATA_DIR."""
        from src.skills import build_skill_env

        env = build_skill_env()

        assert "EUNO_DATA_DIR" in env
        assert Path(env["EUNO_DATA_DIR"]).is_dir()

    def test_build_skill_env_includes_current_env(self):
        """Should include current environment variables."""
        from src.skills import build_skill_env

        env = build_skill_env()

        # Should have PATH and other system vars
        assert "PATH" in env

    def test_build_skill_env_adds_agent_id(self):
        """Should add EUNO_AGENT_ID when provided."""
        from src.skills import build_skill_env

        env = build_skill_env(agent_id="test-agent")

        assert env.get("EUNO_AGENT_ID") == "test-agent"

    def test_build_skill_env_omits_agent_id_when_none(self):
        """Should not add EUNO_AGENT_ID when not provided."""
        from src.skills import build_skill_env

        env = build_skill_env(agent_id=None)

        assert "EUNO_AGENT_ID" not in env or env.get("EUNO_AGENT_ID") is None

    def test_build_skill_env_adds_topic_id(self):
        """Should add EUNO_TOPIC_ID when provided."""
        from src.skills import build_skill_env

        env = build_skill_env(topic_id="topic-123")

        assert env.get("EUNO_TOPIC_ID") == "topic-123"

    def test_build_skill_env_omits_topic_id_when_none(self):
        """Should not add EUNO_TOPIC_ID when not provided."""
        from src.skills import build_skill_env

        env = build_skill_env(topic_id=None)

        assert "EUNO_TOPIC_ID" not in env or env.get("EUNO_TOPIC_ID") is None

    def test_build_skill_env_adds_session_id(self):
        """Should add EUNO_SESSION_ID when provided."""
        from src.skills import build_skill_env

        env = build_skill_env(session_id="session-456")

        assert env.get("EUNO_SESSION_ID") == "session-456"

    def test_build_skill_env_omits_session_id_when_none(self):
        """Should not add EUNO_SESSION_ID when not provided."""
        from src.skills import build_skill_env

        env = build_skill_env(session_id=None)

        assert "EUNO_SESSION_ID" not in env or env.get("EUNO_SESSION_ID") is None

    def test_build_skill_env_all_context(self):
        """Should add all context when provided."""
        from src.skills import build_skill_env

        env = build_skill_env(
            agent_id="agent-1",
            topic_id="topic-2",
            session_id="session-3"
        )

        assert env.get("EUNO_AGENT_ID") == "agent-1"
        assert env.get("EUNO_TOPIC_ID") == "topic-2"
        assert env.get("EUNO_SESSION_ID") == "session-3"
        assert "EUNO_DATA_DIR" in env


class TestGetContextFromEnv:
    """Test retrieving context from environment variables."""

    def test_get_data_dir_from_env_default(self):
        """Should return default data dir when env not set."""
        from src.skills.context import get_data_dir_from_env, DATA_DIR

        with patch.dict(os.environ, {}, clear=False):
            # Remove EUNO_DATA_DIR if present
            os.environ.pop("EUNO_DATA_DIR", None)
            result = get_data_dir_from_env()

        assert result == DATA_DIR

    def test_get_data_dir_from_env_uses_env(self):
        """Should use EUNO_DATA_DIR from environment."""
        from src.skills.context import get_data_dir_from_env

        with patch.dict(os.environ, {"EUNO_DATA_DIR": "/custom/path"}):
            result = get_data_dir_from_env()

        assert result == Path("/custom/path")

    def test_get_agent_id_from_env(self):
        """Should return agent ID from environment."""
        from src.skills.context import get_agent_id_from_env

        with patch.dict(os.environ, {"EUNO_AGENT_ID": "my-agent"}):
            result = get_agent_id_from_env()

        assert result == "my-agent"

    def test_get_agent_id_from_env_none(self):
        """Should return None when not set."""
        from src.skills.context import get_agent_id_from_env

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EUNO_AGENT_ID", None)
            result = get_agent_id_from_env()

        assert result is None

    def test_get_topic_id_from_env(self):
        """Should return topic ID from environment."""
        from src.skills.context import get_topic_id_from_env

        with patch.dict(os.environ, {"EUNO_TOPIC_ID": "topic-abc"}):
            result = get_topic_id_from_env()

        assert result == "topic-abc"

    def test_get_topic_id_from_env_none(self):
        """Should return None when not set."""
        from src.skills.context import get_topic_id_from_env

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EUNO_TOPIC_ID", None)
            result = get_topic_id_from_env()

        assert result is None

    def test_get_session_id_from_env(self):
        """Should return session ID from environment."""
        from src.skills.context import get_session_id_from_env

        with patch.dict(os.environ, {"EUNO_SESSION_ID": "sess-xyz"}):
            result = get_session_id_from_env()

        assert result == "sess-xyz"

    def test_get_session_id_from_env_none(self):
        """Should return None when not set."""
        from src.skills.context import get_session_id_from_env

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EUNO_SESSION_ID", None)
            result = get_session_id_from_env()

        assert result is None


class TestDataDirResolution:
    """Test data directory path resolution."""

    def test_data_dir_is_absolute(self):
        """Should resolve to absolute path."""
        from src.skills.context import DATA_DIR

        assert DATA_DIR.is_absolute()

    def test_data_dir_exists(self):
        """Should point to existing directory."""
        from src.skills.context import DATA_DIR

        assert DATA_DIR.exists()
        assert DATA_DIR.is_dir()

    def test_data_dir_contains_agents(self):
        """Should contain agents subdirectory."""
        from src.skills.context import DATA_DIR

        assert (DATA_DIR / "agents").is_dir()
