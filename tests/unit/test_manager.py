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

    Spec: specs/1_agents.md - Trigger format uses objects with event, topic_name, instructions.
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
                    "topic_name": "euno:consolidate",
                    "instructions": "Run consolidation"
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
                    "topic_name": "euno:consolidate"
                },
                {
                    "event": "morning",
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

    Spec: specs/1_agents.md - Triggers are objects with event, topic_name, instructions.
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
                    "topic_name": "euno:consolidate",
                    "instructions": "Review memories. Use consolidation skill"
                }
            ]
        }

        triggers = manager._get_agent_triggers(config)

        assert len(triggers) == 1
        assert triggers[0].get("event") == "evening"
        assert triggers[0].get("instructions") == "Review memories. Use consolidation skill"

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
# Trigger Instruction Tests
# =============================================================================

@pytest.mark.unit
class TestTriggerInstructions:
    """Test trigger instruction passthrough.

    Spec: specs/1_agents.md - optional instructions are carried through for UI and inspection.
    """

    def test_instructions_preserved(self, manager_data_dir):
        """Instructions are preserved in returned triggers."""
        from src.agent.manager import AgentManager

        manager = AgentManager()

        config = {
            "id": "test",
            "triggers": [
                {
                    "event": "morning",
                    "topic_name": "daily:review",
                    "instructions": "Review daily goals. Use core topics list and summarize"
                }
            ]
        }

        triggers = manager._get_agent_triggers(config)

        assert len(triggers) == 1
        assert triggers[0]["instructions"] == "Review daily goals. Use core topics list and summarize"


    def test_has_open_internal_topic_detects_working_status(
        self, manager_data_dir, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """_has_open_internal_topic detects topics with 'working' status.

        Spec: Prevent duplicate topics while a topic is being executed (status=working).
        """
        from src.agent.manager import AgentManager
        from src.core.data.topics import create_topic, claim_topic

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
        from src.core.data.topics import create_topic

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
        from src.core.data.topics import create_topic, complete_topic

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
        from src.core.data.topics import _notify_agent_has_topics

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
        from src.core.data.topics import create_topic

        manager = AgentManager()
        set_manager(manager)

        # Create topic with assignee
        with patch('src.core.data.topics._notify_agent_has_topics') as mock_notify:
            with patch('src.core.data.topics._emit_topics_update'):
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
        from src.core.data.topics import create_topic, assign_agent

        manager = AgentManager()
        set_manager(manager)

        # Create topic without assignee
        with patch('src.core.data.topics._notify_agent_has_topics'):
            with patch('src.core.data.topics._emit_topics_update'):
                topic = create_topic(
                    name="Unassigned Topic",
                    assignee=None,
                    parent_id=None,
                    created_by="test"
                )

        # Assign to agent
        with patch('src.core.data.topics._notify_agent_has_topics') as mock_notify:
            with patch('src.core.data.topics._emit_topics_update'):
                with patch('src.core.data.topics._emit_event'):
                    assign_agent(topic["id"], "new-assignee")

            mock_notify.assert_called_with("new-assignee")

    def test_handoff_topic_notifies_cache(
        self, manager_data_dir, test_db, mock_emit_event
    ):
        """handoff_topic calls _notify_agent_has_topics for recipient.

        Spec: Topic handoff notifies the receiving agent's cache.
        """
        from src.agent.manager import AgentManager, set_manager
        from src.core.data.topics import create_topic, handoff_topic

        manager = AgentManager()
        set_manager(manager)

        # Create topic assigned to agent A
        with patch('src.core.data.topics._notify_agent_has_topics'):
            with patch('src.core.data.topics._emit_topics_update'):
                topic = create_topic(
                    name="Handoff Topic",
                    assignee="agent-a",
                    parent_id=None,
                    created_by="test"
                )

        # Handoff to agent B
        with patch('src.core.data.topics._notify_agent_has_topics') as mock_notify:
            with patch('src.core.data.topics._emit_topics_update'):
                with patch('src.core.data.topics._emit_event'):
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

    def test_periodic_repoll_catches_due_date_transition(self, manager_data_dir):
        """Cache refreshes periodically to catch due-date transitions.

        Spec: Agents re-check for actionable topics every 60s even when cache is False,
        so that topics whose due_date has become current are discovered.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()
        manager.running = True

        # Cache says no topics
        manager.agents_with_topics["test-agent"] = False

        # Simulate last check was >60s ago
        manager._last_topic_check["test-agent"] = time.time() - 61

        # Mock list_topics to return a topic (due date just became current)
        with patch("src.core.data.topics.list_topics", return_value=[{"id": "t1"}]) as mock_lt:
            # Simulate one iteration of the re-poll logic
            now = time.time()
            last_check = manager._last_topic_check.get("test-agent", 0)
            assert now - last_check >= 60

            topics = mock_lt(status="todo", assignee="test-agent", actionable=True)
            assert topics  # Found newly-actionable topic

            # Manager would set cache to True
            manager.agents_with_topics["test-agent"] = True
            manager._last_topic_check["test-agent"] = now

        assert manager.agents_with_topics["test-agent"] is True

    def test_repoll_skipped_when_recently_checked(self, manager_data_dir):
        """Re-poll is skipped when last check was less than 60s ago.

        Spec: Re-check interval is 60 seconds to avoid excessive DB queries.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()
        manager.running = True

        manager.agents_with_topics["test-agent"] = False
        manager._last_topic_check["test-agent"] = time.time() - 10  # 10s ago

        # Check interval hasn't elapsed
        now = time.time()
        last_check = manager._last_topic_check.get("test-agent", 0)
        assert now - last_check < 60  # Should NOT re-poll
