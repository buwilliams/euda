"""
Global pytest fixtures for Euno tests.

Provides isolated test environments, mock LLM clients, and test configurations.
"""

import json
import os
import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


# =============================================================================
# Data Directory Fixtures
# =============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create an isolated data directory for tests.

    Sets up the standard Euno data structure:
    - data/agents/
    - data/jobs/
    - data/system/
    """
    data_dir = tmp_path / "data"
    (data_dir / "agents").mkdir(parents=True)
    (data_dir / "jobs").mkdir(parents=True)
    (data_dir / "system").mkdir(parents=True)
    (data_dir / "system" / "token_usage").mkdir(parents=True)

    # Create default system config (without LLM settings)
    config = {
        "metacognition": {
            "token_awareness": {
                "enabled": True,
                "thresholds": {"warning_percent": 80, "pause_percent": 100}
            }
        }
    }
    (data_dir / "system" / "config.json").write_text(json.dumps(config, indent=2))

    # Create default LLM config
    llm_config = {
        "provider": "openai",
        "model": "gpt-4.1",
        "budget": {"limit": 10.0, "period": "monthly"},
        "providers": {
            "openai": {
                "display_name": "ChatGPT",
                "description": "OpenAI's GPT models",
                "models": [
                    {"model": "gpt-4.1", "display_name": "GPT-4.1", "pricing": {"input": 3.0, "cached_input": 0.3, "output": 15.0}}
                ]
            }
        }
    }
    (data_dir / "system" / "llm.json").write_text(json.dumps(llm_config, indent=2))

    return data_dir


@pytest.fixture
def patch_data_dir(temp_data_dir):
    """Patch DATA_DIR in all relevant modules to use temp directory.

    Returns the temp data directory path.
    """
    patches = []

    # Patch jobs module
    try:
        from src.tools.data import jobs
        p1 = patch.object(jobs, 'DATA_DIR', temp_data_dir)
        p1.start()
        patches.append(p1)

        # Also patch derived paths
        patch.object(jobs, 'JOBS_DIR', temp_data_dir / "jobs").start()
        patch.object(jobs, 'DB_PATH', temp_data_dir / "jobs" / "db.sqlite").start()

        # Clear and reinitialize the connection
        jobs._clear_connection()
    except ImportError:
        pass

    # Patch memory module
    try:
        from src.tools.data import memory
        p2 = patch.object(memory, 'DATA_DIR', temp_data_dir)
        p2.start()
        patches.append(p2)
        patch.object(memory, 'AGENTS_DIR', temp_data_dir / "agents").start()
    except ImportError:
        pass

    # Patch tokens module
    try:
        from src.agent.cognition.metacognition.regulation import tokens
        p3 = patch.object(tokens, 'DATA_DIR', temp_data_dir)
        p3.start()
        patches.append(p3)
        patch.object(tokens, 'CONFIG_PATH', temp_data_dir / "system" / "config.json").start()
        patch.object(tokens, 'LLM_CONFIG_PATH', temp_data_dir / "system" / "llm.json").start()
        patch.object(tokens, 'AGENTS_DIR', temp_data_dir / "agents").start()
        patch.object(tokens, 'USAGE_DIR', temp_data_dir / "system" / "token_usage").start()
    except ImportError:
        pass

    # Patch llms.base module
    try:
        from src.llms import base
        patch.object(base, 'LLM_CONFIG_PATH', temp_data_dir / "system" / "llm.json").start()
    except ImportError:
        pass

    yield temp_data_dir

    # Stop all patches
    for p in patches:
        p.stop()


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def test_db(patch_data_dir):
    """Create a fresh test database.

    Returns the database path after initializing schema.
    """
    from src.tools.data import jobs

    db_path = patch_data_dir / "jobs" / "db.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Clear existing connection and reinitialize schema
    jobs._clear_connection()
    jobs._ensure_schema()

    yield db_path

    # Cleanup
    jobs._clear_connection()


# =============================================================================
# Agent Fixtures
# =============================================================================

@pytest.fixture
def test_agent_config():
    """Standard agent configuration for testing."""
    return {
        "id": "test-agent",
        "name": "Test Agent",
        "state": "enabled",
        "tools": ["list_jobs", "get_job", "create_job", "complete_job"],
        "triggers": ["job:assigned"],
        "token_budget": {
            "frequency": "daily",
            "input_ratio": 0.8,
            "output_ratio": 0.2
        }
    }


@pytest.fixture
def create_test_agent(patch_data_dir):
    """Factory fixture to create test agent configurations."""
    def _create(agent_id="test-agent", **overrides):
        config = {
            "id": agent_id,
            "name": agent_id.title().replace("-", " "),
            "state": "enabled",
            "tools": ["list_jobs", "get_job", "create_job", "complete_job"],
            "triggers": ["job:assigned"],
            "token_budget": {
                "frequency": "daily",
                "input_ratio": 0.8,
                "output_ratio": 0.2
            }
        }
        config.update(overrides)

        # Write config to disk
        agent_dir = patch_data_dir / "agents" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))

        # Create identity.md
        (agent_dir / "identity.md").write_text(f"# {config['name']}\n\nTest agent identity.")

        return config

    return _create


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client to avoid API calls in tests."""
    with patch('src.llms.base.get_client') as mock:
        mock_client = MagicMock()
        mock_client.complete.return_value = {
            "content": "Test response",
            "usage": {"input_tokens": 100, "output_tokens": 50}
        }
        mock.return_value = mock_client
        yield mock


@pytest.fixture
def mock_emit_event():
    """Mock event emission to avoid side effects."""
    with patch('src.tools.data.jobs._emit_event') as mock:
        yield mock


@pytest.fixture
def mock_emit_ui_event():
    """Mock UI event emission and jobs update notification."""
    with patch('src.tools.data.jobs._emit_jobs_update') as mock_update:
        with patch('src.tools.data.jobs._notify_agent_has_jobs') as mock_notify:
            yield mock_update, mock_notify


# =============================================================================
# Token Awareness Fixtures
# =============================================================================

@pytest.fixture
def fresh_token_awareness(patch_data_dir):
    """Create a fresh TokenAwareness instance for testing.

    Resets the singleton and returns a new instance.
    """
    from src.agent.cognition.metacognition.regulation import tokens

    # Reset singleton
    tokens._token_awareness = None

    # Get fresh instance
    ta = tokens.get_token_awareness()

    yield ta

    # Reset again for cleanup
    tokens._token_awareness = None


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def today():
    """Get today's date as ISO string."""
    from datetime import date
    return date.today().isoformat()


@pytest.fixture
def yesterday():
    """Get yesterday's date as ISO string."""
    from datetime import date, timedelta
    return (date.today() - timedelta(days=1)).isoformat()


@pytest.fixture
def tomorrow():
    """Get tomorrow's date as ISO string."""
    from datetime import date, timedelta
    return (date.today() + timedelta(days=1)).isoformat()
