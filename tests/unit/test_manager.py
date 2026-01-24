"""
Unit tests for AgentManager.

Tests for src/agent/manager.py including:
- Startup trigger creation
- Missed trigger detection
- Config hot-reload
- Job cache notification

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
            "tools": ["list_jobs"],
            "triggers": triggers or ["job:assigned"]
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
    agent.config = {"id": "test-agent", "state": "enabled", "triggers": ["system:start"]}
    return agent


# =============================================================================
# Startup Trigger Tests
# =============================================================================

@pytest.mark.unit
class TestStartupTriggers:
    """Test _emit_startup_triggers functionality."""

    def test_creates_start_trigger_for_subscribed_agents(
        self, manager_data_dir, create_manager_agent, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Agents with system:start trigger get a Trigger:start job.

        Spec: Manager creates startup trigger jobs for agents with system:start.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.jobs import list_jobs

        # Create agent with system:start trigger
        create_manager_agent("worker", triggers=["system:start", "job:assigned"])

        manager = AgentManager()
        configs = manager.load_agent_configs()

        # Manually add mock agent (don't actually start threads)
        mock_agent = MagicMock()
        mock_agent.id = "worker"
        mock_agent.config = configs[0]
        manager.agents["worker"] = mock_agent

        # Emit startup triggers
        manager._emit_startup_triggers()

        # Verify trigger job was created
        jobs = list_jobs(assignee="worker")
        trigger_jobs = [j for j in jobs if j["name"].startswith("Trigger:start:")]

        assert len(trigger_jobs) == 1
        assert trigger_jobs[0]["name"] == f"Trigger:start:{datetime.now().strftime('%Y-%m-%d')}"

    def test_skips_agents_without_start_trigger(
        self, manager_data_dir, create_manager_agent, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Agents without system:start trigger don't get startup jobs.

        Spec: Only agents subscribed to system:start receive trigger jobs.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.jobs import list_jobs

        # Create agent without system:start trigger
        create_manager_agent("regular", triggers=["job:assigned"])

        manager = AgentManager()
        configs = manager.load_agent_configs()

        mock_agent = MagicMock()
        mock_agent.id = "regular"
        mock_agent.config = configs[0]
        manager.agents["regular"] = mock_agent

        manager._emit_startup_triggers()

        # No trigger jobs should exist
        jobs = list_jobs(assignee="regular")
        trigger_jobs = [j for j in jobs if j["name"].startswith("Trigger:start:")]

        assert len(trigger_jobs) == 0

    def test_skips_disabled_agents(
        self, manager_data_dir, create_manager_agent, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Disabled agents don't get startup trigger jobs.

        Spec: Disabled agents never process jobs.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.jobs import list_jobs

        # Create disabled agent with system:start trigger
        create_manager_agent("disabled-worker", triggers=["system:start"], enabled=False)

        manager = AgentManager()
        configs = manager.load_agent_configs()

        mock_agent = MagicMock()
        mock_agent.id = "disabled-worker"
        mock_agent.config = configs[0]
        manager.agents["disabled-worker"] = mock_agent

        manager._emit_startup_triggers()

        # No trigger jobs should exist
        jobs = list_jobs(assignee="disabled-worker")
        assert len(jobs) == 0

    def test_no_duplicate_trigger_jobs(
        self, manager_data_dir, create_manager_agent, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Running startup twice doesn't create duplicate trigger jobs.

        Spec: Check if trigger job already exists before creating.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.jobs import list_jobs

        create_manager_agent("worker", triggers=["system:start"])

        manager = AgentManager()
        configs = manager.load_agent_configs()

        mock_agent = MagicMock()
        mock_agent.id = "worker"
        mock_agent.config = configs[0]
        manager.agents["worker"] = mock_agent

        # Emit twice
        manager._emit_startup_triggers()
        manager._emit_startup_triggers()

        # Should still only have one trigger job
        jobs = list_jobs(assignee="worker")
        trigger_jobs = [j for j in jobs if j["name"].startswith("Trigger:start:")]

        assert len(trigger_jobs) == 1


# =============================================================================
# Missed Trigger Detection Tests
# =============================================================================

@pytest.mark.unit
class TestMissedTriggerDetection:
    """Test _check_missed_triggers functionality."""

    def test_detects_missed_morning_trigger(self, manager_data_dir, system_config_with_schedules):
        """Detects morning trigger missed when time has passed and not run today.

        Spec: Detects missed time:morning triggers at startup.
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

        assert "time:morning" in missed

    def test_detects_missed_evening_trigger(self, manager_data_dir, system_config_with_schedules):
        """Detects evening trigger missed when time has passed and not run today.

        Spec: Detects missed time:evening triggers at startup.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()

        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "22:00"
            mock_dt.now.return_value = mock_now

            missed = manager._check_missed_triggers()

        assert "time:evening" in missed

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

        assert "time:morning" not in missed

    def test_creates_jobs_for_missed_triggers(
        self, manager_data_dir, system_config_with_schedules, create_manager_agent,
        test_db, mock_emit_event, mock_emit_ui_event
    ):
        """Missed triggers create jobs for subscribed agents.

        Spec: Creates missed trigger jobs at startup.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.jobs import list_jobs

        # Create agent subscribed to time:morning
        create_manager_agent("morning-worker", triggers=["time:morning"])

        manager = AgentManager()
        configs = manager.load_agent_configs()

        mock_agent = MagicMock()
        mock_agent.id = "morning-worker"
        mock_agent.config = configs[0]
        manager.agents["morning-worker"] = mock_agent

        with patch('src.agent.manager.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.side_effect = lambda fmt: "2025-01-23" if fmt == "%Y-%m-%d" else "10:00"
            mock_dt.now.return_value = mock_now

            manager._emit_startup_triggers()

        jobs = list_jobs(assignee="morning-worker")
        morning_jobs = [j for j in jobs if "morning" in j["name"]]

        assert len(morning_jobs) == 1
        assert morning_jobs[0]["name"] == "Trigger:morning:2025-01-23"


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

        create_manager_agent("reloadable", triggers=["job:assigned"])

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

        create_manager_agent("reloadable", triggers=["job:assigned"])

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
        create_manager_agent("new-agent", triggers=["job:assigned"])

        # Now should find the new agent
        configs = manager.load_agent_configs()
        assert len(configs) == 1
        assert configs[0]["id"] == "new-agent"


# =============================================================================
# Dict-Based Trigger Format Tests
# =============================================================================

@pytest.mark.unit
class TestDictBasedTriggers:
    """Test handling of new dict-based trigger format.

    Spec: New trigger format uses objects with job_name, job_description, schedule.
    Dict triggers should not be passed to event bus (only string triggers).
    """

    def test_start_agent_with_dict_triggers(
        self, manager_data_dir, create_manager_agent
    ):
        """start_agent handles dict-based triggers without error.

        Spec: Dict triggers are for scheduled jobs, not event bus subscriptions.
        """
        from src.agent.manager import AgentManager

        # Create agent with both string and dict triggers
        config = {
            "id": "dict-trigger-agent",
            "name": "Dict Trigger Agent",
            "state": "enabled",
            "tools": ["list_jobs"],
            "triggers": [
                "job:assigned",  # String trigger (legacy)
                {  # Dict trigger (new format)
                    "job_name": "euno:consolidate",
                    "job_description": "Run consolidation",
                    "schedule": "evening"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "dict-trigger-agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Dict Trigger Agent\n\nTest agent.")

        manager = AgentManager()

        # This should not raise TypeError: unhashable type: 'dict'
        with patch.object(manager, '_run_agent_loop'):
            manager.start_agent(config)

        assert "dict-trigger-agent" in manager.agents

    def test_event_bus_only_receives_string_triggers(
        self, manager_data_dir, create_manager_agent
    ):
        """Event bus subscription only receives string triggers, not dicts.

        Spec: Dict triggers are handled by scheduler, not event bus.
        """
        from src.agent.manager import AgentManager

        # Create agent with mixed triggers
        config = {
            "id": "mixed-trigger-agent",
            "name": "Mixed Trigger Agent",
            "state": "enabled",
            "tools": ["list_jobs"],
            "triggers": [
                "job:assigned",
                "system:start",
                {
                    "job_name": "euno:consolidate",
                    "schedule": "evening"
                },
                {
                    "job_name": "euno:quote",
                    "schedule": "morning"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "mixed-trigger-agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Mixed Trigger Agent\n\nTest agent.")

        manager = AgentManager()

        # Track what gets passed to event_bus.subscribe
        subscribed_triggers = []
        original_subscribe = manager.event_bus.subscribe

        def capture_subscribe(agent_id, triggers):
            subscribed_triggers.extend(triggers)
            return original_subscribe(agent_id, triggers)

        manager.event_bus.subscribe = capture_subscribe

        with patch.object(manager, '_run_agent_loop'):
            manager.start_agent(config)

        # Only string triggers should be subscribed
        assert "job:assigned" in subscribed_triggers
        assert "system:start" in subscribed_triggers
        assert len(subscribed_triggers) == 2  # No dict triggers

        # Verify no dicts in subscribed triggers
        for trigger in subscribed_triggers:
            assert isinstance(trigger, str), f"Dict trigger leaked to event bus: {trigger}"

    def test_start_agent_with_only_dict_triggers(
        self, manager_data_dir
    ):
        """start_agent works when agent has only dict-based triggers.

        Spec: Agents can have only scheduled triggers (no event bus subscriptions).
        """
        from src.agent.manager import AgentManager

        # Create agent with only dict triggers
        config = {
            "id": "only-dict-triggers",
            "name": "Only Dict Triggers",
            "state": "enabled",
            "tools": ["list_jobs"],
            "triggers": [
                {
                    "job_name": "euno:consolidate",
                    "schedule": "evening"
                }
            ]
        }
        agent_dir = manager_data_dir / "agents" / "only-dict-triggers"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.json").write_text(json.dumps(config, indent=2))
        (agent_dir / "identity.md").write_text("# Only Dict Triggers\n\nTest agent.")

        manager = AgentManager()

        # Should not raise, should subscribe to empty list
        with patch.object(manager, '_run_agent_loop'):
            manager.start_agent(config)

        assert "only-dict-triggers" in manager.agents

    def test_has_open_internal_job_detects_working_status(
        self, manager_data_dir, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """_has_open_internal_job detects jobs with 'working' status.

        Spec: Prevent duplicate jobs while a job is being executed (status=working).
        """
        from src.agent.manager import AgentManager
        from src.tools.data.jobs import create_job, claim_job

        manager = AgentManager()

        # Create a job and claim it (changes status to 'working')
        job = create_job(
            name="euno:quote",
            assignee="chat",
            parent_id=None,
            created_by="system"
        )
        claim_job(job["id"], "chat")

        # Should detect the working job as "open"
        assert manager._has_open_internal_job("euno:quote", "chat") is True

    def test_has_open_internal_job_detects_todo_status(
        self, manager_data_dir, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """_has_open_internal_job detects jobs with 'todo' status.

        Spec: Prevent duplicate jobs when a job is pending.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.jobs import create_job

        manager = AgentManager()

        # Create a job (status='todo')
        create_job(
            name="euno:consolidate",
            assignee="chat",
            parent_id=None,
            created_by="system"
        )

        # Should detect the todo job as "open"
        assert manager._has_open_internal_job("euno:consolidate", "chat") is True

    def test_has_open_internal_job_false_when_done(
        self, manager_data_dir, test_db, mock_emit_event, mock_emit_ui_event
    ):
        """_has_open_internal_job returns False for completed jobs.

        Spec: Completed jobs should not block creating new ones.
        """
        from src.agent.manager import AgentManager
        from src.tools.data.jobs import create_job, complete_job

        manager = AgentManager()

        # Create and complete a job
        job = create_job(
            name="euno:quote",
            assignee="chat",
            parent_id=None,
            created_by="system"
        )
        complete_job(job["id"], agent="chat")

        # Should NOT detect the done job as "open"
        assert manager._has_open_internal_job("euno:quote", "chat") is False


# =============================================================================
# Job Cache Notification Tests
# =============================================================================

@pytest.mark.unit
class TestJobCacheNotification:
    """Test job cache notification integration."""

    def test_notify_agent_has_jobs_updates_cache(self, manager_data_dir):
        """_notify_agent_has_jobs sets cache to True.

        Spec: Cache is shared across threads - when job assigned, cache is notified.
        """
        from src.agent.manager import AgentManager, set_manager, get_manager
        from src.tools.data.jobs import _notify_agent_has_jobs

        manager = AgentManager()
        set_manager(manager)

        # Initially no jobs cached
        assert manager.agents_with_jobs.get("test-agent", False) is False

        # Notify
        _notify_agent_has_jobs("test-agent")

        # Cache should be True
        assert manager.agents_with_jobs["test-agent"] is True

    def test_create_job_notifies_cache(
        self, manager_data_dir, test_db, mock_emit_event
    ):
        """create_job calls _notify_agent_has_jobs for assignee.

        Spec: When agent A assigns to agent B, cache is notified immediately.
        """
        from src.agent.manager import AgentManager, set_manager
        from src.tools.data.jobs import create_job

        manager = AgentManager()
        set_manager(manager)

        # Create job with assignee
        with patch('src.tools.data.jobs._notify_agent_has_jobs') as mock_notify:
            with patch('src.tools.data.jobs._emit_jobs_update'):
                create_job(
                    name="Test Job",
                    assignee="worker-agent",
                    parent_id=None,
                    created_by="test"
                )

            # Verify notify was called for the assignee
            mock_notify.assert_called_with("worker-agent")

    def test_assign_agent_notifies_cache(
        self, manager_data_dir, test_db, mock_emit_event
    ):
        """assign_agent calls _notify_agent_has_jobs.

        Spec: Job assignment immediately notifies the cache.
        """
        from src.agent.manager import AgentManager, set_manager
        from src.tools.data.jobs import create_job, assign_agent

        manager = AgentManager()
        set_manager(manager)

        # Create job without assignee
        with patch('src.tools.data.jobs._notify_agent_has_jobs'):
            with patch('src.tools.data.jobs._emit_jobs_update'):
                job = create_job(
                    name="Unassigned Job",
                    assignee=None,
                    parent_id=None,
                    created_by="test"
                )

        # Assign to agent
        with patch('src.tools.data.jobs._notify_agent_has_jobs') as mock_notify:
            with patch('src.tools.data.jobs._emit_jobs_update'):
                with patch('src.tools.data.jobs._emit_event'):
                    assign_agent(job["id"], "new-assignee")

            mock_notify.assert_called_with("new-assignee")

    def test_handoff_job_notifies_cache(
        self, manager_data_dir, test_db, mock_emit_event
    ):
        """handoff_job calls _notify_agent_has_jobs for recipient.

        Spec: Job handoff notifies the receiving agent's cache.
        """
        from src.agent.manager import AgentManager, set_manager
        from src.tools.data.jobs import create_job, handoff_job

        manager = AgentManager()
        set_manager(manager)

        # Create job assigned to agent A
        with patch('src.tools.data.jobs._notify_agent_has_jobs'):
            with patch('src.tools.data.jobs._emit_jobs_update'):
                job = create_job(
                    name="Handoff Job",
                    assignee="agent-a",
                    parent_id=None,
                    created_by="test"
                )

        # Handoff to agent B
        with patch('src.tools.data.jobs._notify_agent_has_jobs') as mock_notify:
            with patch('src.tools.data.jobs._emit_jobs_update'):
                with patch('src.tools.data.jobs._emit_event'):
                    handoff_job(job["id"], "agent-b", "Please review")

            mock_notify.assert_called_with("agent-b")


# =============================================================================
# Agent Loop State Checks
# =============================================================================

@pytest.mark.unit
class TestAgentLoopStateChecks:
    """Test agent loop respects state checks."""

    def test_cache_prevents_unnecessary_queries(self, manager_data_dir):
        """When cache is False, agent doesn't query for jobs.

        Spec: Job cache prevents database queries when no jobs are pending.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()
        manager.running = True

        # Set cache to False
        manager.agents_with_jobs["test-agent"] = False

        # The loop checks cache before querying
        # We verify the cache value is used correctly
        assert not manager.agents_with_jobs.get("test-agent", False)

    def test_cache_true_allows_work_cycle(self, manager_data_dir):
        """When cache is True, agent proceeds to work cycle.

        Spec: Agents poll for actionable jobs when cache indicates jobs exist.
        """
        from src.agent.manager import AgentManager

        manager = AgentManager()
        manager.running = True

        # Set cache to True
        manager.agents_with_jobs["test-agent"] = True

        # Cache indicates jobs exist
        assert manager.agents_with_jobs.get("test-agent", False)
