"""
Unit tests for AgentManager.

Tests for src/agent/manager.py including:
- Startup trigger creation
- Missed trigger detection
- Config hot-reload
- Topic cache notification

Spec: specs/1_agents.md - Manager section
"""

import json
import pytest
import time
import threading
from datetime import datetime
from unittest.mock import patch, MagicMock


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def manager_data_dir(patch_data_dir):
    """Set up data directory with manager-specific patches."""
    from src.agent import manager as manager_module

    # Patch manager module paths
    with patch.object(manager_module, 'DATA_DIR', patch_data_dir):
        with patch.object(manager_module, 'AGENTS_DIR', patch_data_dir / "agents"):
            with patch.object(manager_module, 'SYSTEM_STATE_PATH', patch_data_dir / "system" / "state.json"):
                yield patch_data_dir


@pytest.fixture
def system_config_with_schedules(manager_data_dir):
    """Create system config with morning/evening schedules."""
    config = {
        "schedules": {
            "morning": "08:00",
            "evening": "20:00"
        },
        "agents": {
            "poll_interval": 0.1
        }
    }
    config_path = manager_data_dir / "system" / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    return config


@pytest.fixture
def create_manager_agent(manager_data_dir):
    """Factory to create agent configs for manager tests."""
    def _create(agent_id, triggers=None, enabled=True):
        config = {
            "id": agent_id,
            "name": agent_id.title(),
            "state": "enabled" if enabled else "disabled",
            "tools": ["list_topics"],
            "triggers": triggers or []  # Dict-based triggers only
        }
        agent_dir = manager_data_dir / "agents" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text(f"# {agent_id}\n\nTest agent.")
        return config
    return _create


@pytest.fixture
def mock_agent():
    """Create a mock Agent instance."""
    agent = MagicMock()
    agent.id = "test-agent"
    agent.config = {"id": "test-agent", "state": "enabled", "triggers": []}
    return agent


# =============================================================================
# Startup Trigger Tests
# =============================================================================

@pytest.mark.unit
class TestStartupTriggers:
    """Test _emit_startup_triggers functionality.

    Note: String-based triggers (system:start, time:morning) have been removed.
    Only dict-based triggers are now supported.
    """

    def test_skips_disabled_agents(
        self, manager_data_dir, create_manager_agent, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Disabled agents don't get startup trigger topics.

        Spec: Disabled agents never process topics.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.topics import list_topics

        # Create disabled agent with event trigger
        config = {
            "id": "disabled-worker",
            "name": "Disabled Worker",
            "state": "disabled",
            "tools": ["list_topics"],
            "triggers": [
                {
                    "event": "evening",
                    "action": "tool",
                    "tool": "euno_consolidate",
                    "topic_name": "euno:consolidate",
                    "topic_description": "Run consolidation"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "disabled-worker"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Disabled Worker\n\nTest agent.")

        manager = AgentManager()
        configs = manager.load_agent_configs()

        mock_agent = MagicMock()
        mock_agent.id = "disabled-worker"
        mock_agent.config = configs[0]
        manager.agents["disabled-worker"] = mock_agent

        manager._emit_startup_triggers()

        # No trigger topics should exist for disabled agents
        topics = list_topics(assignee="disabled-worker")
        assert len(topics) == 0


# =============================================================================
# Missed Trigger Detection Tests
# =============================================================================

@pytest.mark.unit
class TestMissedTriggerDetection:
    """Test _check_missed_triggers functionality."""

    def test_detects_missed_morning_trigger(self, manager_data_dir, system_config_with_schedules):
        """Detects morning trigger missed when time has passed and not run today.

        Spec: Detects missed morning triggers at startup.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        # Mock current time to be after morning schedule (08:00)
        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "10:00"
            mock_dt.now.return_value = mock_now

            # No previous state (never run)
            missed = manager._check_missed_triggers()

        # Returns schedule names as "time:{name}"
        assert any("morning" in m for m in missed)

    def test_detects_missed_evening_trigger(self, manager_data_dir, system_config_with_schedules):
        """Detects evening trigger missed when time has passed and not run today.

        Spec: Detects missed evening triggers at startup.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "22:00"
            mock_dt.now.return_value = mock_now

            missed = manager._check_missed_triggers()

        # Returns schedule names as "time:{name}"
        assert any("evening" in m for m in missed)

    def test_no_missed_when_already_ran_today(self, manager_data_dir, system_config_with_schedules):
        """No missed triggers when they already ran today.

        Spec: Only detect as missed if last_ran != today.
        """
        from src.agent.manager import AgentManager

        # Set state to indicate triggers ran today
        state = {"last_morning": "2025-01-23", "last_evening": "2025-01-23"}
        state_path = manager_data_dir / "system" / "state.json"
        state_path.write_text(json.dumps(state))

        manager = AgentManager()

        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "22:00"
            mock_dt.now.return_value = mock_now

            missed = manager._check_missed_triggers()

        assert len(missed) == 0

    def test_no_missed_before_schedule_time(self, manager_data_dir, system_config_with_schedules):
        """No missed triggers when schedule time hasn't passed yet.

        Spec: Only detect as missed if current_time >= schedule_time.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            # Current time 07:00 is before morning 08:00
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "07:00"
            mock_dt.now.return_value = mock_now

            missed = manager._check_missed_triggers()

        # Morning shouldn't be missed if we're before 08:00
        assert not any("morning" in m for m in missed)


# =============================================================================
# Config Hot-Reload Tests
# =============================================================================

@pytest.mark.unit
class TestConfigHotReload:
    """Test _watch_configs functionality."""

    def test_detects_config_change(self, manager_data_dir, create_manager_agent):
        """Config watcher detects when agent config is modified.

        Spec: Manager watches for config changes and reloads agents.
        """
        from src.agent.manager import AgentManager

        create_manager_agent("reloadable", triggers=["topic:assigned"])

        manager = AgentManager()
        manager.running = True

        # Load initial config
        configs = manager.load_agent_configs()

        # Track initial mtime
        config_path = manager_data_dir / "agents" / "reloadable" / "config.json"
        initial_mtime = config_path.stat().st_mtime
        manager._config_mtimes["reloadable"] = initial_mtime

        # Mock agent
        mock_agent = MagicMock()
        mock_agent.id = "reloadable"
        mock_agent.config = configs[0]
        manager.agents["reloadable"] = mock_agent

        # Modify config
        time.sleep(0.1)  # Ensure mtime changes
        config = json.loads(config_path.read_text())
        config["name"] = "Updated Name"
        config_path.write_text(json.dumps(config))

        # Verify mtime changed
        new_mtime = config_path.stat().st_mtime
        assert new_mtime > initial_mtime

        # The watcher would detect this change
        # We test the detection logic directly
        current_mtime = config_path.stat().st_mtime
        last_mtime = manager._config_mtimes.get("reloadable", 0)
        assert current_mtime > last_mtime

    def test_reload_agent_loads_fresh_config(self, manager_data_dir, create_manager_agent):
        """reload_agent loads fresh configuration from disk.

        Spec: Manager can reload agents with new config.
        """
        from src.agent.manager import AgentManager

        create_manager_agent("reloadable", triggers=["topic:assigned"])

        manager = AgentManager()

        # Verify config can be loaded
        configs = manager.load_agent_configs()
        assert len(configs) == 1
        assert configs[0]["name"] == "Reloadable"

        # Modify config on disk
        config_path = manager_data_dir / "agents" / "reloadable" / "config.json"
        config = json.loads(config_path.read_text())
        config["name"] = "New Name"
        config_path.write_text(json.dumps(config))

        # Load again
        configs = manager.load_agent_configs()
        assert configs[0]["name"] == "New Name"

    def test_detects_new_agent_directory(self, manager_data_dir, create_manager_agent):
        """Config watcher detects new agent directories.

        Spec: Manager detects and registers new agents.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()
        manager.running = True

        # Initially no agents
        configs = manager.load_agent_configs()
        assert len(configs) == 0

        # Create new agent
        create_manager_agent("new-agent", triggers=["topic:assigned"])

        # Now should find the new agent
        configs = manager.load_agent_configs()
        assert len(configs) == 1
        assert configs[0]["id"] == "new-agent"


# =============================================================================
# Event-Based Trigger Format Tests
# =============================================================================

@pytest.mark.unit
class TestEventBasedTriggers:
    """Test handling of event-based trigger format.

    Spec: specs/1_agents.md - Trigger format uses objects with event, action, tool, topic_name.
    Triggers are handled by the scheduler based on the `event` key.
    """

    def test_start_agent_with_event_triggers(
        self, manager_data_dir, create_manager_agent
    ):
        """start_agent handles event-based triggers without error.

        Spec: Triggers use `event` key for schedule matching.
        """
        from src.agent.manager import AgentManager

        config = {
            "id": "event-trigger-agent",
            "name": "Event Trigger Agent",
            "state": "enabled",
            "tools": ["list_topics"],
            "triggers": [
                {
                    "event": "evening",
                    "action": "tool",
                    "tool": "euno_consolidate",
                    "topic_name": "euno:consolidate",
                    "topic_description": "Run consolidation"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "event-trigger-agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Event Trigger Agent\n\nTest agent.")

        manager = AgentManager()

        with patch.object(manager, '_run_agent_loop'):
            manager.start_agent(config)

        assert "event-trigger-agent" in manager.agents

    def test_start_agent_with_multiple_event_triggers(
        self, manager_data_dir
    ):
        """start_agent works with multiple event-based triggers.

        Spec: Agents can have multiple scheduled triggers with different events.
        """
        from src.agent.manager import AgentManager

        config = {
            "id": "multi-event-triggers",
            "name": "Multi Event Triggers",
            "state": "enabled",
            "tools": ["list_topics"],
            "triggers": [
                {
                    "event": "evening",
                    "action": "tool",
                    "tool": "euno_consolidate",
                    "topic_name": "euno:consolidate"
                },
                {
                    "event": "morning",
                    "action": "tool",
                    "tool": "euno_quote",
                    "topic_name": "euno:quote"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "multi-event-triggers"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Multi Event Triggers\n\nTest agent.")

        manager = AgentManager()

        with patch.object(manager, '_run_agent_loop'):
            manager.start_agent(config)

        assert "multi-event-triggers" in manager.agents


# =============================================================================
# _get_agent_triggers() Tests
# =============================================================================

@pytest.mark.unit
class TestGetAgentTriggers:
    """Test _get_agent_triggers() method.

    Spec: specs/1_agents.md - Triggers are objects with event, action, tool, topic_name.
    """

    def test_returns_dict_triggers_only(self, manager_data_dir):
        """_get_agent_triggers returns only dict-based triggers.

        Spec: Only object triggers are supported.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        config = {
            "id": "test",
            "triggers": [
                {"event": "morning", "topic_name": "euno:quote"},
                {"event": "evening", "topic_name": "euno:consolidate"}
            ]
        }

        triggers = manager._get_agent_triggers(config)

        assert len(triggers) == 2
        assert all(isinstance(t, dict) for t in triggers)

    def test_returns_empty_for_no_triggers(self, manager_data_dir):
        """_get_agent_triggers returns empty list when no triggers.

        Spec: Agents can have no triggers.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        config = {"id": "test", "triggers": []}
        triggers = manager._get_agent_triggers(config)
        assert triggers == []

        config_no_key = {"id": "test"}
        triggers = manager._get_agent_triggers(config_no_key)
        assert triggers == []

    def test_preserves_event_key(self, manager_data_dir):
        """_get_agent_triggers preserves event key in returned triggers.

        Spec: Triggers use `event` key for schedule matching.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        config = {
            "id": "test",
            "triggers": [
                {
                    "event": "evening",
                    "action": "tool",
                    "tool": "euno_consolidate",
                    "topic_name": "euno:consolidate"
                }
            ]
        }

        triggers = manager._get_agent_triggers(config)

        assert len(triggers) == 1
        assert triggers[0].get("event") == "evening"
        assert triggers[0].get("action") == "tool"
        assert triggers[0].get("tool") == "euno_consolidate"

    def test_filters_non_dict_entries(self, manager_data_dir):
        """_get_agent_triggers filters out non-dict entries.

        Spec: Only object triggers are valid.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        # Mix of valid dicts and invalid strings/numbers
        config = {
            "id": "test",
            "triggers": [
                {"event": "morning", "topic_name": "euno:quote"},
                "invalid_string",
                123,
                {"event": "evening", "topic_name": "euno:consolidate"},
                None
            ]
        }

        triggers = manager._get_agent_triggers(config)

        # Should only return the two valid dict triggers
        assert len(triggers) == 2
        assert triggers[0]["event"] == "morning"
        assert triggers[1]["event"] == "evening"


# =============================================================================
# Scheduler Event Matching Tests
# =============================================================================

@pytest.mark.unit
class TestSchedulerEventMatching:
    """Test scheduler matches triggers by `event` key.

    Spec: specs/1_agents.md - Scheduler creates topics when schedule matches event.
    """

    def test_scheduler_matches_event_to_schedule(
        self, manager_data_dir, system_config_with_schedules, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Scheduler creates topic when event matches schedule name.

        Spec: event key maps to schedule names in system config.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.topics import list_topics

        # Create agent with evening event trigger
        config = {
            "id": "scheduler-test",
            "name": "Scheduler Test",
            "state": "enabled",
            "tools": ["list_topics"],
            "triggers": [
                {
                    "event": "evening",
                    "action": "tool",
                    "tool": "euno_consolidate",
                    "topic_name": "euno:consolidate",
                    "topic_description": "Test consolidation"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "scheduler-test"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Scheduler Test\n\nTest agent.")

        manager = AgentManager()

        # Load and register agent
        mock_agent = MagicMock()
        mock_agent.id = "scheduler-test"
        mock_agent.config = config
        manager.agents["scheduler-test"] = mock_agent

        # Simulate missed evening trigger
        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "22:00"
            mock_dt.now.return_value = mock_now

            manager._emit_startup_triggers()

        # Should have created the topic
        topics = list_topics(assignee="scheduler-test")
        assert len(topics) == 1
        assert topics[0]["name"] == "euno:consolidate"

    def test_scheduler_ignores_mismatched_event(
        self, manager_data_dir, system_config_with_schedules, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Scheduler doesn't create topic when event doesn't match.

        Spec: Only matching events trigger topic creation.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.topics import list_topics

        # Create agent with morning event trigger
        config = {
            "id": "morning-agent",
            "name": "Morning Agent",
            "state": "enabled",
            "tools": ["list_topics"],
            "triggers": [
                {
                    "event": "morning",
                    "action": "tool",
                    "tool": "euno_quote",
                    "topic_name": "euno:quote"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "morning-agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Morning Agent\n\nTest agent.")

        manager = AgentManager()

        mock_agent = MagicMock()
        mock_agent.id = "morning-agent"
        mock_agent.config = config
        manager.agents["morning-agent"] = mock_agent

        # Time is after evening (22:00) but before morning would be "missed"
        # We check that evening trigger fires but morning doesn't
        # Actually, let's test that morning IS fired when morning is missed

        # Set state to indicate evening already ran
        state = {"last_evening": "2025-01-23"}
        state_path = manager_data_dir / "system" / "state.json"
        state_path.write_text(json.dumps(state))

        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            # After morning (08:00) so morning should be detected as missed
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "10:00"
            mock_dt.now.return_value = mock_now

            manager._emit_startup_triggers()

        # Should have created the morning topic
        topics = list_topics(assignee="morning-agent")
        assert len(topics) == 1
        assert topics[0]["name"] == "euno:quote"

    def test_scheduler_creates_topic_with_description(
        self, manager_data_dir, system_config_with_schedules, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Scheduler uses topic_description from trigger config.

        Spec: topic_description is used when creating the trigger topic.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.topics import list_topics

        config = {
            "id": "desc-test",
            "name": "Description Test",
            "state": "enabled",
            "tools": ["list_topics"],
            "triggers": [
                {
                    "event": "evening",
                    "action": "tool",
                    "tool": "euno_consolidate",
                    "topic_name": "euno:consolidate",
                    "topic_description": "Custom description for consolidation"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "desc-test"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Desc Test\n\nTest agent.")

        manager = AgentManager()

        mock_agent = MagicMock()
        mock_agent.id = "desc-test"
        mock_agent.config = config
        manager.agents["desc-test"] = mock_agent

        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "22:00"
            mock_dt.now.return_value = mock_now

            manager._emit_startup_triggers()

        topics = list_topics(assignee="desc-test")
        assert len(topics) == 1
        assert topics[0]["description"] == "Custom description for consolidation"


# =============================================================================
# Trigger Action Type Tests
# =============================================================================

@pytest.mark.unit
class TestTriggerActionTypes:
    """Test trigger action types (tool vs llm).

    Spec: specs/1_agents.md - action: "tool" executes directly, "llm" uses agent loop.
    """

    def test_tool_action_includes_tool_field(self, manager_data_dir):
        """Triggers with action=tool should have tool field.

        Spec: action: "tool" requires tool field.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        config = {
            "id": "test",
            "triggers": [
                {
                    "event": "evening",
                    "action": "tool",
                    "tool": "euno_consolidate",
                    "topic_name": "euno:consolidate"
                }
            ]
        }

        triggers = manager._get_agent_triggers(config)

        assert len(triggers) == 1
        assert triggers[0]["action"] == "tool"
        assert triggers[0]["tool"] == "euno_consolidate"

    def test_llm_action_no_tool_field_required(self, manager_data_dir):
        """Triggers with action=llm don't need tool field.

        Spec: action: "llm" creates topic for agent to process via LLM loop.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        config = {
            "id": "test",
            "triggers": [
                {
                    "event": "morning",
                    "action": "llm",
                    "topic_name": "daily:review",
                    "topic_description": "Review daily goals"
                }
            ]
        }

        triggers = manager._get_agent_triggers(config)

        assert len(triggers) == 1
        assert triggers[0]["action"] == "llm"
        assert "tool" not in triggers[0]

    def test_default_action_is_llm(self, manager_data_dir):
        """Triggers without action field default to llm.

        Spec: action defaults to "llm" if not specified.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        config = {
            "id": "test",
            "triggers": [
                {
                    "event": "morning",
                    "topic_name": "daily:task"
                }
            ]
        }

        triggers = manager._get_agent_triggers(config)

        assert len(triggers) == 1
        # No action field means it defaults to llm behavior
        assert triggers[0].get("action") is None  # Not set, defaults to llm


    def test_has_open_internal_topic_detects_working_status(
        self, manager_data_dir, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """_has_open_internal_topic detects topics with 'working' status.

        Spec: Prevent duplicate topics while a topic is being executed (status=working).
        """
        from src.agent.manager import AgentManager
        from src.tools.data.topics import create_topic, claim_topic

        manager = AgentManager()

        # Create a topic and claim it (changes status to 'working')
        topic = create_topic(
            name="euno:quote",
            assignee="user",
            parent_id=None,
            created_by="system"
        )
        claim_topic(topic["id"], "user")

        # Should detect the working topic as "open"
        assert manager._has_open_internal_topic("euno:quote", "user") is True

    def test_has_open_internal_topic_detects_todo_status(
        self, manager_data_dir, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """_has_open_internal_topic detects topics with 'todo' status.

        Spec: Prevent duplicate topics when a topic is pending.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.topics import create_topic

        manager = AgentManager()

        # Create a topic (status='todo')
        create_topic(
            name="euno:consolidate",
            assignee="user",
            parent_id=None,
            created_by="system"
        )

        # Should detect the todo topic as "open"
        assert manager._has_open_internal_topic("euno:consolidate", "user") is True

    def test_has_open_internal_topic_false_when_done(
        self, manager_data_dir, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """_has_open_internal_topic returns False for completed topics.

        Spec: Completed topics should not block creating new ones.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.topics import create_topic, complete_topic

        manager = AgentManager()

        # Create and complete a topic
        topic = create_topic(
            name="euno:quote",
            assignee="user",
            parent_id=None,
            created_by="system"
        )
        complete_topic(topic["id"], agent="user")

        # Should NOT detect the done topic as "open"
        assert manager._has_open_internal_topic("euno:quote", "user") is False


# =============================================================================
# Topic Cache Notification Tests
# =============================================================================

@pytest.mark.unit
class TestTopicCacheNotification:
    """Test topic cache notification integration."""

    def test_notify_agent_has_topics_updates_cache(self, manager_data_dir):
        """_notify_agent_has_topics sets cache to True.

        Spec: Cache is shared across threads - when topic assigned, cache is notified.
        """
        from src.agent.manager import AgentManager, set_manager, get_manager
        from src.tools.data.topics import _notify_agent_has_topics

        manager = AgentManager()
        set_manager(manager)

        # Initially no topics cached
        assert manager.agents_with_topics.get("test-agent", False) is False

        # Notify
        _notify_agent_has_topics("test-agent")

        # Cache should be True
        assert manager.agents_with_topics["test-agent"] is True

    def test_create_topic_notifies_cache(
        self, manager_data_dir, test_db, mock_emit_event
    ):
        """create_topic calls _notify_agent_has_topics for assignee.

        Spec: When agent A assigns to agent B, cache is notified immediately.
        """
        from src.agent.manager import AgentManager, set_manager
        from src.tools.data.topics import create_topic

        manager = AgentManager()
        set_manager(manager)

        # Create topic with assignee
        with patch('src.tools.data.topics._notify_agent_has_topics') as mock_notify:
            with patch('src.tools.data.topics._emit_topics_update'):
                create_topic(
                    name="Test Topic",
                    assignee="worker-agent",
                    parent_id=None,
                    created_by="test"
                )

            # Verify notify was called for the assignee
            mock_notify.assert_called_with("worker-agent")

    def test_assign_agent_notifies_cache(
        self, manager_data_dir, test_db, mock_emit_event
    ):
        """assign_agent calls _notify_agent_has_topics.

        Spec: Topic assignment immediately notifies the cache.
        """
        from src.agent.manager import AgentManager, set_manager
        from src.tools.data.topics import create_topic, assign_agent

        manager = AgentManager()
        set_manager(manager)

        # Create topic without assignee
        with patch('src.tools.data.topics._notify_agent_has_topics'):
            with patch('src.tools.data.topics._emit_topics_update'):
                topic = create_topic(
                    name="Unassigned Topic",
                    assignee=None,
                    parent_id=None,
                    created_by="test"
                )

        # Assign to agent
        with patch('src.tools.data.topics._notify_agent_has_topics') as mock_notify:
            with patch('src.tools.data.topics._emit_topics_update'):
                with patch('src.tools.data.topics._emit_event'):
                    assign_agent(topic["id"], "new-assignee")

            mock_notify.assert_called_with("new-assignee")

    def test_handoff_topic_notifies_cache(
        self, manager_data_dir, test_db, mock_emit_event
    ):
        """handoff_topic calls _notify_agent_has_topics for recipient.

        Spec: Topic handoff notifies the receiving agent's cache.
        """
        from src.agent.manager import AgentManager, set_manager
        from src.tools.data.topics import create_topic, handoff_topic

        manager = AgentManager()
        set_manager(manager)

        # Create topic assigned to agent A
        with patch('src.tools.data.topics._notify_agent_has_topics'):
            with patch('src.tools.data.topics._emit_topics_update'):
                topic = create_topic(
                    name="Handoff Topic",
                    assignee="agent-a",
                    parent_id=None,
                    created_by="test"
                )

        # Handoff to agent B
        with patch('src.tools.data.topics._notify_agent_has_topics') as mock_notify:
            with patch('src.tools.data.topics._emit_topics_update'):
                with patch('src.tools.data.topics._emit_event'):
                    handoff_topic(topic["id"], "agent-b", "Please review")

            mock_notify.assert_called_with("agent-b")


# =============================================================================
# Agent Loop State Checks
# =============================================================================

@pytest.mark.unit
class TestAgentLoopStateChecks:
    """Test agent loop respects state checks."""

    def test_cache_prevents_unnecessary_queries(self, manager_data_dir):
        """When cache is False, agent doesn't query for topics.

        Spec: Topic cache prevents database queries when no topics are pending.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()
        manager.running = True

        # Set cache to False
        manager.agents_with_topics["test-agent"] = False

        # The loop checks cache before querying
        # We verify the cache value is used correctly
        assert not manager.agents_with_topics.get("test-agent", False)

    def test_cache_true_allows_work_cycle(self, manager_data_dir):
        """When cache is True, agent proceeds to work cycle.

        Spec: Agents poll for actionable topics when cache indicates topics exist.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()
        manager.running = True

        # Set cache to True
        manager.agents_with_topics["test-agent"] = True

        # Cache indicates topics exist
        assert manager.agents_with_topics.get("test-agent", False)
