"""
Agent Manager - Manages lifecycle of all agents.

Responsibilities:
- Load agent configurations
- Start all enabled agents (each in its own thread)
- Initialize event bus and subscribe agents to triggers
- Run time scheduler for time-based events
- Handle graceful shutdown
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .agent import Agent
from .cognition.metacognition import (
    AgentPausedError,
    get_token_awareness,
    AgentState,
)
from ..events import EventBus, set_event_bus, get_event_bus, emit_system_event


DATA_DIR = Path(__file__).parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"
SYSTEM_STATE_PATH = DATA_DIR / "system" / "state.json"

# Interval durations for interval-based triggers
INTERVAL_DURATIONS = {
    "minute": timedelta(minutes=1),
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "biweekly": timedelta(days=14),
    "monthly": timedelta(days=30),
    "bimonthly": timedelta(days=60),
    "quarterly": timedelta(days=90),
    "semiannually": timedelta(days=180),
    "annually": timedelta(days=365),
    "biennially": timedelta(days=730),
    "decadal": timedelta(days=3650),
    "generational": timedelta(days=9125),  # 25 years
    "centennial": timedelta(days=36500),
    "millennial": timedelta(days=365000),
}

# Global manager instance for tools to access
_manager_instance: 'AgentManager' = None


def get_manager() -> Optional['AgentManager']:
    """Get the global AgentManager instance."""
    return _manager_instance


def set_manager(manager: 'AgentManager'):
    """Set the global AgentManager instance."""
    global _manager_instance
    _manager_instance = manager


def _get_config_mtime(agent_dir: Path) -> float:
    """Get the latest mtime of config files for an agent.

    Checks both config.defaults.json and config.json, returns the latest.
    Returns 0 if neither file exists.
    """
    defaults_path = agent_dir / "config.defaults.json"
    overrides_path = agent_dir / "config.json"

    mtime = 0.0
    if defaults_path.exists():
        mtime = max(mtime, defaults_path.stat().st_mtime)
    if overrides_path.exists():
        mtime = max(mtime, overrides_path.stat().st_mtime)

    return mtime


def _has_config(agent_dir: Path) -> bool:
    """Check if an agent directory has config files."""
    return (agent_dir / "config.defaults.json").exists() or (agent_dir / "config.json").exists()


class AgentManager:
    """Manages the lifecycle of all agents."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.running = False
        self.agents_with_topics: Dict[str, bool] = {}  # Cache: agent_id -> has_topics
        self._last_topic_check: Dict[str, float] = {}  # agent_id -> last re-poll timestamp
        self.event_bus = EventBus()
        # Config watching
        self._config_mtimes: Dict[str, float] = {}  # agent_id -> last mtime
        self._agent_stop_events: Dict[str, threading.Event] = {}  # Signal agents to stop
        self._config_watch_thread: Optional[threading.Thread] = None
        # Startup synchronization
        self._startup_complete = threading.Event()

    def wait_for_startup(self, timeout: float = 30.0) -> bool:
        """Wait for the manager to complete startup.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if startup completed, False if timeout
        """
        return self._startup_complete.wait(timeout=timeout)

    def load_agent_configs(self) -> List[dict]:
        """Load all agent configurations from data/agents/*/.

        Uses layered config: config.defaults.json (base) + config.json (overrides).
        """
        from src.core.config import load_layered_config

        configs = []
        if not AGENTS_DIR.exists():
            return configs

        for agent_dir in AGENTS_DIR.iterdir():
            if agent_dir.is_dir():
                # Check if either config file exists
                defaults_path = agent_dir / "config.defaults.json"
                overrides_path = agent_dir / "config.json"

                if defaults_path.exists() or overrides_path.exists():
                    config = load_layered_config(agent_dir)
                    if config:
                        config["_dir"] = str(agent_dir)
                        configs.append(config)

        return configs

    def start_agent(self, config: dict):
        """Start a single agent in its own thread."""
        agent_id = config["id"]
        triggers = config.get("triggers", ["topic:assigned"])

        print(f"Starting agent: {agent_id} (triggers: {triggers})")

        agent = Agent(agent_id, config)
        self.agents[agent_id] = agent

        # Track config modification time for reload detection
        agent_dir = AGENTS_DIR / agent_id
        mtime = _get_config_mtime(agent_dir)
        if mtime > 0:
            self._config_mtimes[agent_id] = mtime

        # Subscribe agent to system event triggers
        system_events = ["system:start", "chat:message_received", "topic:created", "topic:completed"]
        agent_triggers = self._get_agent_triggers(config)
        subscribed = [t.get("event") for t in agent_triggers if t.get("event") in system_events]
        if subscribed:
            self.event_bus.subscribe(agent_id, subscribed)
            print(f"  Subscribed to system events: {subscribed}")

        # Create stop event for this agent
        stop_event = threading.Event()
        self._agent_stop_events[agent_id] = stop_event

        # Create thread for agent loop
        thread = threading.Thread(
            target=self._run_agent_loop,
            args=(agent, stop_event),
            name=f"agent-{agent_id}",
            daemon=True
        )
        self.threads[agent_id] = thread
        thread.start()

    def register_new_agent(self, agent_id: str) -> dict:
        """Dynamically register and start a newly created agent.

        Called after create_agent to immediately activate the agent
        without requiring a restart.

        Args:
            agent_id: The ID of the newly created agent

        Returns:
            Status dict with success/error info
        """
        # Check if already registered
        if agent_id in self.agents:
            return {"error": f"Agent {agent_id} is already running"}

        # Load the agent's config (layered: defaults + overrides)
        from src.core.config import load_layered_config

        agent_dir = AGENTS_DIR / agent_id
        if not _has_config(agent_dir):
            return {"error": f"Agent config not found: {agent_id}"}

        config = load_layered_config(agent_dir)
        if not config:
            return {"error": f"Agent config not found: {agent_id}"}
        config["_dir"] = str(agent_dir)

        # Track config mtime so watcher knows this agent was seen
        # (even if disabled, we don't want to keep re-registering)
        self._config_mtimes[agent_id] = _get_config_mtime(agent_dir)

        # Sync agent inbox topics to create the inbox for this agent
        from src.core.data.topics import sync_agent_inbox_topics
        sync_agent_inbox_topics()

        # Start the agent if enabled (check state field)
        if config.get("state", "enabled") != "disabled":
            self.start_agent(config)

            # Initialize topic cache for this agent
            from src.core.data.topics import list_topics
            topics = list_topics(status="todo", assignee=agent_id, actionable=True)
            self.agents_with_topics[agent_id] = bool(topics)

            return {"registered": True, "agent_id": agent_id, "started": True}

        return {"registered": True, "agent_id": agent_id, "started": False, "note": "Agent is disabled"}

    def stop_agent(self, agent_id: str, timeout: float = 5.0) -> dict:
        """Stop a running agent gracefully.

        Args:
            agent_id: The agent to stop
            timeout: How long to wait for the agent to stop (seconds)

        Returns:
            Status dict with success/error info
        """
        if agent_id not in self.agents:
            return {"error": f"Agent {agent_id} is not running"}

        print(f"Stopping agent: {agent_id}")

        # Signal the agent to stop
        stop_event = self._agent_stop_events.get(agent_id)
        if stop_event:
            stop_event.set()

        # Wait for thread to finish
        thread = self.threads.get(agent_id)
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
            if thread.is_alive():
                print(f"Warning: Agent {agent_id} did not stop within {timeout}s")

        # Unsubscribe from event bus
        self.event_bus.unsubscribe(agent_id)

        # Clean up
        self.agents.pop(agent_id, None)
        self.threads.pop(agent_id, None)
        self._agent_stop_events.pop(agent_id, None)
        self._config_mtimes.pop(agent_id, None)
        self.agents_with_topics.pop(agent_id, None)

        return {"stopped": True, "agent_id": agent_id}

    def reload_agent(self, agent_id: str) -> dict:
        """Reload an agent by stopping it and starting with fresh config.

        Args:
            agent_id: The agent to reload

        Returns:
            Status dict with success/error info
        """
        print(f"Reloading agent: {agent_id}")

        # Stop if running
        if agent_id in self.agents:
            stop_result = self.stop_agent(agent_id)
            if "error" in stop_result:
                return stop_result

        # Load fresh config
        config_path = AGENTS_DIR / agent_id / "config.json"
        if not config_path.exists():
            return {"error": f"Agent config not found: {agent_id}"}

        with open(config_path) as f:
            config = json.load(f)
            config["_dir"] = str(AGENTS_DIR / agent_id)

        # Start with new config if enabled (check state field)
        if config.get("state", "enabled") != "disabled":
            self.start_agent(config)

            # Initialize topic cache
            from src.core.data.topics import list_topics
            topics = list_topics(status="todo", assignee=agent_id, actionable=True)
            self.agents_with_topics[agent_id] = bool(topics)

            return {"reloaded": True, "agent_id": agent_id, "started": True}

        return {"reloaded": True, "agent_id": agent_id, "started": False, "note": "Agent is disabled"}

    def _watch_configs(self):
        """Background thread that watches for config changes and reloads agents.

        Watches both config.defaults.json and config.json for layered config.
        """
        check_interval = 2.0  # Check every 2 seconds

        while self.running:
            try:
                # Check each agent's config for changes
                for agent_id in list(self._config_mtimes.keys()):
                    agent_dir = AGENTS_DIR / agent_id
                    if not _has_config(agent_dir):
                        # Both config files deleted - stop the agent
                        print(f"Config deleted for agent {agent_id}, stopping...")
                        self.stop_agent(agent_id)
                        continue

                    current_mtime = _get_config_mtime(agent_dir)
                    last_mtime = self._config_mtimes.get(agent_id, 0)

                    if current_mtime > last_mtime:
                        print(f"Config changed for agent {agent_id}, reloading...")
                        self.reload_agent(agent_id)

                # Check for new agent directories
                if AGENTS_DIR.exists():
                    for agent_dir in AGENTS_DIR.iterdir():
                        if agent_dir.is_dir():
                            agent_id = agent_dir.name
                            # Only register if not already tracked (running or seen)
                            if _has_config(agent_dir) and agent_id not in self._config_mtimes:
                                # New agent found - register it
                                print(f"New agent found: {agent_id}, registering...")
                                self.register_new_agent(agent_id)

            except Exception as e:
                print(f"Config watcher error: {e}")

            time.sleep(check_interval)

    def _get_system_config(self) -> dict:
        """Load system configuration."""
        config_path = DATA_DIR / "system" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

    def _get_system_state(self) -> dict:
        """Load system state from data/system/state.json."""
        if SYSTEM_STATE_PATH.exists():
            with open(SYSTEM_STATE_PATH) as f:
                return json.load(f)
        return {}

    def _save_system_state(self, state: dict):
        """Save system state to data/system/state.json."""
        SYSTEM_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SYSTEM_STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)

    def _get_agent_state(self, agent_id: str) -> dict:
        """Load agent state from data/agents/{agent_id}/state.json."""
        state_path = AGENTS_DIR / agent_id / "state.json"
        if state_path.exists():
            with open(state_path) as f:
                return json.load(f)
        return {}

    def _save_agent_state(self, agent_id: str, state: dict):
        """Save agent state to data/agents/{agent_id}/state.json."""
        state_path = AGENTS_DIR / agent_id / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

    def _update_agent_last_ran(self, agent_id: str):
        """Update the last_ran timestamp for an agent."""
        state = self._get_agent_state(agent_id)
        state["last_ran"] = datetime.now().isoformat()
        self._save_agent_state(agent_id, state)

    def _get_trigger_key(self, trigger: dict) -> str:
        """Generate a unique key for a trigger.

        Format: interval:hourly:euno:quote (event + topic_name)

        Args:
            trigger: Trigger configuration dict

        Returns:
            Unique trigger key string
        """
        event = trigger.get("event", "")
        topic_name = trigger.get("topic_name", "")
        return f"{event}:{topic_name}"

    def _get_trigger_state(self, agent_id: str, trigger_key: str) -> dict:
        """Get state for a specific trigger.

        Args:
            agent_id: The agent ID
            trigger_key: The trigger key from _get_trigger_key()

        Returns:
            Trigger state dict with last_ran and next_run
        """
        state = self._get_agent_state(agent_id)
        triggers_state = state.get("triggers", {})
        return triggers_state.get(trigger_key, {})

    def _save_trigger_state(self, agent_id: str, trigger_key: str, trigger_state: dict):
        """Save state for a specific trigger.

        Args:
            agent_id: The agent ID
            trigger_key: The trigger key from _get_trigger_key()
            trigger_state: Dict with last_ran and next_run
        """
        state = self._get_agent_state(agent_id)
        if "triggers" not in state:
            state["triggers"] = {}
        state["triggers"][trigger_key] = trigger_state
        self._save_agent_state(agent_id, state)

    def _calculate_next_run(self, interval: str, last_ran: datetime) -> datetime:
        """Calculate the next run time for an interval trigger.

        Args:
            interval: Interval name (e.g., "hourly", "daily")
            last_ran: When the trigger last ran

        Returns:
            Next run datetime
        """
        duration = INTERVAL_DURATIONS.get(interval)
        if not duration:
            return last_ran  # Unknown interval, don't schedule
        return last_ran + duration

    def _should_fire_interval_trigger(self, agent_id: str, trigger: dict) -> bool:
        """Check if an interval trigger should fire.

        Args:
            agent_id: The agent ID
            trigger: Trigger configuration dict

        Returns:
            True if the trigger should fire
        """
        event = trigger.get("event", "")
        if not event.startswith("interval:"):
            return False

        interval = event.split(":", 1)[1]
        if interval not in INTERVAL_DURATIONS:
            return False

        trigger_key = self._get_trigger_key(trigger)
        trigger_state = self._get_trigger_state(agent_id, trigger_key)

        now = datetime.now()

        # If never run, fire immediately
        if not trigger_state.get("last_ran"):
            return True

        # Check if we've passed next_run time
        next_run_str = trigger_state.get("next_run")
        if next_run_str:
            next_run = datetime.fromisoformat(next_run_str)
            return now >= next_run

        # Fallback: calculate from last_ran
        last_ran = datetime.fromisoformat(trigger_state["last_ran"])
        next_run = self._calculate_next_run(interval, last_ran)
        return now >= next_run

    def _update_interval_trigger_state(self, agent_id: str, trigger: dict):
        """Update the state for an interval trigger after it fires.

        Args:
            agent_id: The agent ID
            trigger: Trigger configuration dict
        """
        event = trigger.get("event", "")
        interval = event.split(":", 1)[1]

        now = datetime.now()
        next_run = self._calculate_next_run(interval, now)

        trigger_key = self._get_trigger_key(trigger)
        self._save_trigger_state(agent_id, trigger_key, {
            "last_ran": now.isoformat(),
            "next_run": next_run.isoformat()
        })

    def _get_agent_triggers(self, config: dict) -> list:
        """Get triggers from agent config.

        Triggers are objects with:
        - event: schedule name (e.g., "morning", "evening") or future system event
        - action: "tool" (direct execution) or "llm" (agent processes via LLM loop)
        - tool: tool to execute directly (required when action="tool")
        - topic_name: e.g., "euno:consolidate", "euno:quote"
        - topic_description: description for the topic (optional)

        Args:
            config: Agent configuration dict

        Returns:
            List of trigger dicts
        """
        triggers = config.get("triggers", [])
        return [t for t in triggers if isinstance(t, dict)]

    def _has_open_internal_topic(self, topic_name: str, agent_id: str) -> bool:
        """Check if there's already an open (todo or working) topic for this internal action.

        Prevents duplicate topics - only one euno:consolidate or euno:quote
        can be pending or in-progress at a time per agent.

        Args:
            topic_name: The topic name to check (e.g., "euno:consolidate")
            agent_id: The agent ID

        Returns:
            True if an open topic with this name exists for this agent
        """
        from src.core.data.topics import list_topics

        # Check for any todo OR working topics with this exact name assigned to this agent
        # Must check both statuses to prevent creating duplicates while topic is being executed
        for status in ["todo", "working"]:
            topics = list_topics(status=status, assignee=agent_id)
            for topic in topics:
                if topic.get("name") == topic_name:
                    return True
        return False

    def _run_agent_loop(self, agent: Agent, stop_event: threading.Event):
        """Run an agent's work loop - monitors health while agent polls for topics.

        The manager doesn't claim or work topics - that's the agent's responsibility.
        The manager monitors agent state; regulation handles rate limits and budgets.

        Args:
            agent: The agent to run
            stop_event: Event to signal this agent should stop (for reload/shutdown)
        """
        from src.core.data.topics import list_topics

        poll_interval = 0.1  # seconds between topic polls
        token_awareness = get_token_awareness()

        while self.running and not stop_event.is_set():
            try:
                # Check agent state (token awareness handles budgets and pausing)
                agent_state = token_awareness.get_agent_state(agent.id)
                if agent_state == AgentState.DISABLED:
                    if stop_event.wait(poll_interval):
                        break  # Stop requested
                    continue
                if agent_state == AgentState.PAUSED:
                    # Agent is paused - wait for manual intervention
                    pause_info = token_awareness.get_pause_info(agent.id)
                    agent._log("agent_paused_waiting", {
                        "reason": pause_info.get("reason", "unknown")
                    })
                    if stop_event.wait(30):
                        break  # Stop requested
                    continue


                # Check cache first (fast) - skip work cycle if no topics pending
                if not self.agents_with_topics.get(agent.id, False):
                    # Periodically re-query to catch due-date transitions
                    now = time.time()
                    last_check = self._last_topic_check.get(agent.id, 0)
                    if now - last_check >= 60:
                        self._last_topic_check[agent.id] = now
                        topics = list_topics(status="todo", assignee=agent.id, actionable=True)
                        if topics:
                            self.agents_with_topics[agent.id] = True
                            continue  # Wake up and work
                    if stop_event.wait(poll_interval):
                        break  # Stop requested
                    continue

                # Let the agent discover, claim, work, and release topics autonomously
                agent.work_cycle_sync()

                # Update last_ran timestamp
                self._update_agent_last_ran(agent.id)

                # Re-check for more topics and update cache
                topics = list_topics(status="todo", assignee=agent.id, actionable=True)
                self.agents_with_topics[agent.id] = bool(topics)

                # Apply pacing between work cycles to prevent runaway spinning
                MIN_CYCLE_DELAY = 0.5  # 500ms minimum between cycles
                if topics:
                    if stop_event.wait(MIN_CYCLE_DELAY):
                        break  # Stop requested
                else:
                    # No more topics - clear cache
                    self.agents_with_topics[agent.id] = False

            except AgentPausedError as e:
                # Agent paused due to threshold breach or runaway detection
                agent._log("agent_paused", {
                    "reason": e.reason
                })
                print(f"\n[{agent.id}] PAUSED: {e.reason} - waiting for manual resume")
                # Wait until resumed or shutdown (no auto-resume for token-based pauses)
                while self.running and not stop_event.is_set():
                    agent_state = token_awareness.get_agent_state(agent.id)
                    if agent_state == AgentState.ENABLED:
                        agent._log("agent_resumed", {"resumed_by": "user"})
                        print(f"[{agent.id}] Resumed")
                        break
                    if stop_event.wait(30):
                        break  # Stop requested

            except Exception as e:
                # Log error and wait briefly before retry
                # Rate limits and budgets are handled by agent regulation (AgentPausedError)
                agent._log("error", {"message": str(e)})
                print(f"Agent {agent.id} error: {e}")
                if stop_event.wait(5):
                    break  # Stop requested

        # Log that agent loop has ended
        agent._log("agent_loop_stopped", {"reason": "stop_requested" if stop_event.is_set() else "shutdown"})

    def _run_time_scheduler(self):
        """Background thread that creates trigger topics based on schedules."""
        from src.core.data.topics import create_topic, get_agent_inbox_topic

        last_fired: Dict[str, str] = {}  # schedule_name -> last fired date-hour-minute

        while self.running:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                current_key = now.strftime("%Y-%m-%d-%H-%M")
                today = now.strftime("%Y-%m-%d")

                schedules = self._get_system_config().get("schedules", {})

                for name, schedule in schedules.items():
                    fire_key = f"{name}:{current_key}"

                    # Skip if already fired this minute
                    if last_fired.get(name) == fire_key:
                        continue

                    should_fire = False

                    if schedule == "every_hour":
                        # Fire on the hour (minute 0)
                        if now.minute == 0:
                            should_fire = True
                    elif schedule == current_time:
                        # Exact time match
                        should_fire = True

                    if should_fire:
                        last_fired[name] = fire_key
                        trigger_name = f"time:{name}"

                        # Process each agent's triggers
                        for agent_id, agent in self.agents.items():
                            config = agent.config
                            if config.get("state", "enabled") == "disabled":
                                continue

                            # Get agent's inbox topic as parent for all trigger topics
                            inbox = get_agent_inbox_topic(agent_id)
                            parent_id = inbox["id"] if inbox else None

                            # Handle object triggers
                            triggers = self._get_agent_triggers(config)
                            for trigger in triggers:
                                if trigger.get("event") == name:
                                    topic_name = trigger.get("topic_name")
                                    topic_desc = trigger.get("topic_description", f"Scheduled {topic_name}")

                                    # Check for duplicate - only one pending at a time
                                    if not self._has_open_internal_topic(topic_name, agent_id):
                                        print(f"[scheduler] Creating topic: {topic_name} for {agent_id}")
                                        create_topic(
                                            name=topic_name,
                                            description=topic_desc,
                                            parent_id=parent_id,
                                            assignee=agent_id,
                                            tags=[topic_name],  # Tag for querying
                                            due_date=None,
                                            created_by="system"
                                        )

                        # Save state for morning/evening triggers
                        if name in ["morning", "evening"]:
                            state = self._get_system_state()
                            state[f"last_{name}"] = today
                            self._save_system_state(state)

                # Process interval-based triggers
                for agent_id, agent in self.agents.items():
                    config = agent.config
                    if config.get("state", "enabled") == "disabled":
                        continue

                    # Get agent's inbox topic as parent for all trigger topics
                    inbox = get_agent_inbox_topic(agent_id)
                    parent_id = inbox["id"] if inbox else None

                    triggers = self._get_agent_triggers(config)
                    for trigger in triggers:
                        event = trigger.get("event", "")
                        if not event.startswith("interval:"):
                            continue

                        # Check if this interval trigger should fire
                        if self._should_fire_interval_trigger(agent_id, trigger):
                            topic_name = trigger.get("topic_name")
                            topic_desc = trigger.get("topic_description", f"Interval {topic_name}")

                            # Check for duplicate - only one pending at a time
                            if not self._has_open_internal_topic(topic_name, agent_id):
                                print(f"[scheduler] Creating interval topic: {topic_name} for {agent_id}")
                                create_topic(
                                    name=topic_name,
                                    description=topic_desc,
                                    parent_id=parent_id,
                                    assignee=agent_id,
                                    tags=[topic_name],
                                    due_date=None,
                                    created_by="system"
                                )

                            # Update trigger state (even if topic already exists, mark as handled)
                            self._update_interval_trigger_state(agent_id, trigger)

            except Exception as e:
                print(f"Scheduler error: {e}")

            time.sleep(10)  # Check every 10 seconds

    def _run_event_handler(self):
        """Background thread that handles system events and creates trigger topics."""
        from src.core.data.topics import create_topic, get_agent_inbox_topic

        while self.running:
            try:
                # Poll each agent's event queue (non-blocking)
                for agent_id, agent in list(self.agents.items()):
                    config = agent.config
                    if config.get("state", "enabled") == "disabled":
                        continue

                    # Check for events in agent's queue
                    event = self.event_bus.get_event_nonblocking(agent_id)
                    if not event:
                        continue

                    # Skip events from triggers to prevent loops
                    event_data = event.data or {}
                    if event_data.get("_source") == "trigger":
                        continue

                    # Handle the event
                    self._handle_system_event(agent_id, agent, event)

            except Exception as e:
                print(f"Event handler error: {e}")

            time.sleep(0.1)  # Poll every 100ms

    def _handle_system_event(self, agent_id: str, agent, event):
        """Handle a system event for an agent by creating trigger topics.

        Args:
            agent_id: The agent to handle the event for
            agent: The agent instance
            event: The Event object
        """
        from src.core.data.topics import create_topic, get_agent_inbox_topic

        config = agent.config
        event_name = event.event

        # Get agent's inbox topic as parent for trigger topics
        inbox = get_agent_inbox_topic(agent_id)
        parent_id = inbox["id"] if inbox else None

        # Match event against agent's triggers
        triggers = self._get_agent_triggers(config)
        for trigger in triggers:
            if trigger.get("event") != event_name:
                continue

            topic_name = trigger.get("topic_name")
            topic_desc = trigger.get("topic_description", f"Triggered by {event_name}")

            # Check for duplicate - only one pending at a time
            if not self._has_open_internal_topic(topic_name, agent_id):
                print(f"[event-handler] Creating topic: {topic_name} for {agent_id} (event: {event_name})")
                create_topic(
                    name=topic_name,
                    description=topic_desc,
                    parent_id=parent_id,
                    assignee=agent_id,
                    tags=[topic_name],
                    due_date=None,
                    created_by="trigger"  # Mark as trigger-created for loop prevention
                )

    def run(self):
        """Run the agent manager."""
        self.running = True

        # Initialize event bus globally
        set_event_bus(self.event_bus)

        # Start time scheduler
        scheduler_thread = threading.Thread(
            target=self._run_time_scheduler,
            name="time-scheduler",
            daemon=True
        )
        scheduler_thread.start()
        print("Time scheduler started")

        # Start event handler for system events
        event_handler_thread = threading.Thread(
            target=self._run_event_handler,
            name="event-handler",
            daemon=True
        )
        event_handler_thread.start()
        print("Event handler started")

        # Load and start all enabled agents (check state field)
        configs = self.load_agent_configs()
        enabled = [c for c in configs if c.get("state", "enabled") != "disabled"]
        disabled = [c for c in configs if c.get("state", "enabled") == "disabled"]

        print(f"Found {len(configs)} agents, {len(enabled)} enabled")

        # Sync agent inbox topics
        from src.core.data.topics import sync_agent_inbox_topics
        sync_agent_inbox_topics()
        print("Agent inbox topics synced")

        for config in enabled:
            self.start_agent(config)

        # Track disabled agents so config watcher doesn't keep trying to register them
        for config in disabled:
            agent_id = config["id"]
            agent_dir = AGENTS_DIR / agent_id
            mtime = _get_config_mtime(agent_dir)
            if mtime > 0:
                self._config_mtimes[agent_id] = mtime

        if not enabled:
            print("No enabled agents. Waiting...")

        # Emit system:start event for agents subscribed to it
        emit_system_event("system:start", data={"agents": [c["id"] for c in enabled]})

        # Initialize topic cache - check for existing actionable topics
        from src.core.data.topics import list_topics
        for agent_id in self.agents:
            topics = list_topics(status="todo", assignee=agent_id, actionable=True)
            self.agents_with_topics[agent_id] = bool(topics)
        print("Topic cache initialized")

        # Start config watcher for hot reloading
        self._config_watch_thread = threading.Thread(
            target=self._watch_configs,
            name="config-watcher",
            daemon=True
        )
        self._config_watch_thread.start()
        print("Config watcher started")

        # Signal that startup is complete
        self._startup_complete.set()

        # Wait until shutdown
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        self.shutdown()

    def shutdown(self):
        """Gracefully shut down all agents."""
        print("Shutting down agents...")
        self.running = False

        # Signal all agents to stop
        for stop_event in self._agent_stop_events.values():
            stop_event.set()

        # Emit shutdown event to wake any waiting agents
        for agent_id in self.agents:
            self.event_bus.emit("system:shutdown", scope=agent_id)

        # Wait for threads to finish (they're daemons, so they'll die with main)
        for agent_id, thread in self.threads.items():
            thread.join(timeout=2)

        print("All agents stopped")


def run_agent_manager():
    """Convenience function to run the agent manager."""
    manager = AgentManager()
    set_manager(manager)
    manager.run()
