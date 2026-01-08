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
from .cost_tracker import BudgetExceeded, print_cost_summary
from .events import EventBus, set_event_bus, get_event_bus


DATA_DIR = Path(__file__).parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"
SYSTEM_STATE_PATH = DATA_DIR / "system" / "state.json"

# Global manager instance for tools to access
_manager_instance: 'AgentManager' = None


def get_manager() -> Optional['AgentManager']:
    """Get the global AgentManager instance."""
    return _manager_instance


def set_manager(manager: 'AgentManager'):
    """Set the global AgentManager instance."""
    global _manager_instance
    _manager_instance = manager


class AgentManager:
    """Manages the lifecycle of all agents."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.running = False
        self.error_backoff: Dict[str, dict] = {}  # Track backoff state per agent
        self.event_bus = EventBus()

    def load_agent_configs(self) -> List[dict]:
        """Load all agent configurations from data/agents/*/config.json."""
        configs = []
        if not AGENTS_DIR.exists():
            return configs

        for agent_dir in AGENTS_DIR.iterdir():
            if agent_dir.is_dir():
                config_path = agent_dir / "config.json"
                if config_path.exists():
                    with open(config_path) as f:
                        config = json.load(f)
                        config["_dir"] = str(agent_dir)
                        configs.append(config)

        return configs

    def start_agent(self, config: dict):
        """Start a single agent in its own thread."""
        agent_id = config["id"]
        triggers = config.get("triggers", ["job:assigned"])

        print(f"Starting agent: {agent_id} (triggers: {triggers})")

        agent = Agent(agent_id, config)
        self.agents[agent_id] = agent

        # Subscribe agent to its triggers
        self.event_bus.subscribe(agent_id, triggers)

        # Create thread for agent loop
        thread = threading.Thread(
            target=self._run_agent_loop,
            args=(agent,),
            name=f"agent-{agent_id}",
            daemon=True
        )
        self.threads[agent_id] = thread
        thread.start()

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

    def _is_quota_or_rate_limit(self, error_msg: str) -> bool:
        """Detect quota or rate limit errors."""
        error_lower = str(error_msg).lower()
        return any(phrase in error_lower for phrase in [
            "429",
            "insufficient_quota",
            "rate_limit",
            "quota exceeded",
            "too many requests",
            "rate limit",
            "quota",
        ])

    def _calculate_backoff(self, agent_id: str) -> int:
        """Calculate exponential backoff duration in seconds.

        Returns backoff duration in seconds.
        """
        if agent_id not in self.error_backoff:
            self.error_backoff[agent_id] = {
                "count": 0,
                "last_error": None,
                "backoff_until": None
            }

        state = self.error_backoff[agent_id]
        state["count"] += 1
        state["last_error"] = datetime.now()

        # Exponential backoff: 1min, 5min, 15min, 30min, 1hr, 2hr, 4hr (max)
        # Formula: min(2^(count-1), 240) minutes
        backoff_minutes = min(2 ** (state["count"] - 1), 240)  # Max 4 hours
        state["backoff_until"] = datetime.now() + timedelta(minutes=backoff_minutes)

        return backoff_minutes * 60  # Return seconds

    def _reset_backoff(self, agent_id: str):
        """Reset backoff counter after successful work cycle."""
        if agent_id in self.error_backoff:
            del self.error_backoff[agent_id]

    def _check_missed_triggers(self) -> set:
        """Check if morning or evening triggers were missed since last run.

        Returns a set of trigger names that were missed (e.g., {'time:morning', 'time:evening'}).
        """
        missed = set()
        state = self._get_system_state()
        config = self._get_system_config()
        schedules = config.get("schedules", {})

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")

        for trigger_name in ["morning", "evening"]:
            if trigger_name not in schedules:
                continue

            schedule_time = schedules[trigger_name]
            last_ran_key = f"last_{trigger_name}"
            last_ran = state.get(last_ran_key)

            # Check if trigger time has passed today
            if current_time >= schedule_time:
                # The trigger should have fired today
                if last_ran != today:
                    # It hasn't fired today - it was missed
                    missed.add(f"time:{trigger_name}")
                    print(f"[startup] Detected missed trigger: time:{trigger_name}")

        return missed

    def _emit_startup_triggers(self):
        """Create trigger jobs for system:start and any missed time triggers at startup."""
        from .tools.jobs import create_job, list_jobs

        today = datetime.now().strftime("%Y-%m-%d")

        # Create system:start trigger jobs for subscribed agents
        print("[startup] Creating system:start trigger jobs")
        for agent_id, agent in self.agents.items():
            config = agent.config
            if not config.get("enabled", True):
                continue

            triggers = config.get("triggers", [])
            if "system:start" in triggers:
                job_name = f"Trigger:start:{today}"

                # Check if trigger job already exists for this agent today
                existing = list_jobs(status="todo", assignee=agent_id)
                already_exists = any(j["name"] == job_name for j in existing)

                if not already_exists:
                    print(f"[startup] Creating trigger job: {job_name} for {agent_id}")
                    create_job(
                        name=job_name,
                        description="System startup trigger",
                        assignees=[agent_id],
                        tags=["trigger:start", "auto-complete"],
                        due_date=None,
                        created_by="system"
                    )

        # Check for missed morning/evening triggers
        missed = self._check_missed_triggers()

        if missed:
            # Create trigger jobs for missed triggers
            for trigger in missed:
                trigger_type = trigger.split(":")[1]  # "morning" or "evening"

                for agent_id, agent in self.agents.items():
                    config = agent.config
                    if not config.get("enabled", True):
                        continue

                    triggers = config.get("triggers", [])
                    if trigger in triggers:
                        job_name = f"Trigger:{trigger_type}:{today}"

                        # Check if trigger job already exists for this agent today
                        existing = list_jobs(status="todo", assignee=agent_id)
                        already_exists = any(j["name"] == job_name for j in existing)

                        if not already_exists:
                            print(f"[startup] Creating missed trigger job: {job_name} for {agent_id}")
                            create_job(
                                name=job_name,
                                description=f"Missed {trigger} trigger",
                                assignees=[agent_id],
                                tags=[f"trigger:{trigger_type}", "auto-complete"],
                                due_date=None,
                                created_by="system"
                            )

            # Update state to mark these as "handled" by setting them to today
            state = self._get_system_state()
            if "time:morning" in missed:
                state["last_morning"] = today
            if "time:evening" in missed:
                state["last_evening"] = today
            self._save_system_state(state)

    def _run_agent_loop(self, agent: Agent):
        """Run an agent's work loop - polls for actionable jobs."""
        from .tools.jobs import list_jobs

        poll_interval = self._get_system_config().get("agents", {}).get("poll_interval", 30)

        while self.running:
            try:
                # Skip if agent is disabled
                if not agent.config.get("enabled", True):
                    time.sleep(poll_interval)
                    continue

                # Check if we're in backoff period
                if agent.id in self.error_backoff:
                    backoff_state = self.error_backoff[agent.id]
                    if backoff_state["backoff_until"] and datetime.now() < backoff_state["backoff_until"]:
                        remaining = (backoff_state["backoff_until"] - datetime.now()).seconds
                        agent._log("backoff_wait", {
                            "reason": "quota_or_rate_limit",
                            "remaining_seconds": remaining,
                            "retry_at": backoff_state["backoff_until"].isoformat(),
                            "attempt": backoff_state["count"]
                        })
                        # Sleep for 1 minute or remaining time, whichever is shorter
                        time.sleep(min(remaining, 60))
                        continue

                # Check for actionable jobs assigned to this agent
                jobs = list_jobs(status="todo", assignee=agent.id, actionable=True)

                if jobs:
                    agent._log("polling_found_jobs", {"count": len(jobs)})
                    agent.work_cycle_sync()
                    # Success - reset backoff and update last_ran
                    self._reset_backoff(agent.id)
                    self._update_agent_last_ran(agent.id)
                else:
                    # No actionable jobs - sleep for poll interval
                    time.sleep(poll_interval)

            except BudgetExceeded as e:
                # Budget exceeded - log warning but continue running
                agent._log("budget_exceeded", {
                    "budget": e.budget,
                    "spent": e.spent
                })
                print(f"\n[{agent.id}] BUDGET WARNING: ${e.spent:.4f} spent of ${e.budget:.2f} limit")
                # Continue running - don't hard exit

            except Exception as e:
                error_msg = str(e)
                agent._log("error", {"message": error_msg})
                print(f"Agent {agent.id} error: {e}")

                # Smart handling based on error type
                if self._is_quota_or_rate_limit(error_msg):
                    backoff_secs = self._calculate_backoff(agent.id)
                    backoff_mins = backoff_secs / 60

                    agent._log("entering_backoff", {
                        "reason": "quota_or_rate_limit",
                        "backoff_duration_seconds": backoff_secs,
                        "backoff_duration_minutes": backoff_mins,
                        "retry_count": self.error_backoff[agent.id]["count"],
                        "retry_at": self.error_backoff[agent.id]["backoff_until"].isoformat()
                    })

                    print(f"[{agent.id}] Quota/rate limit hit. Backing off for {backoff_mins:.1f} minutes (attempt #{self.error_backoff[agent.id]['count']})")

                    # Don't sleep here - let the top of the loop handle backoff checking
                else:
                    # Other errors: short retry for transient issues
                    agent._log("transient_error_retry", {"delay_seconds": 5})
                    time.sleep(5)

    def _run_time_scheduler(self):
        """Background thread that creates trigger jobs based on schedules."""
        from .tools.jobs import create_job, list_jobs

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

                        # Create trigger jobs for agents subscribed to this trigger
                        for agent_id, agent in self.agents.items():
                            config = agent.config
                            if not config.get("enabled", True):
                                continue
                            triggers = config.get("triggers", [])
                            if trigger_name in triggers:
                                job_name = f"Trigger:{name}:{today}"

                                # Check if trigger job already exists for this agent today
                                existing = list_jobs(status="todo", assignee=agent_id)
                                already_exists = any(j["name"] == job_name for j in existing)

                                if not already_exists:
                                    print(f"[scheduler] Creating trigger job: {job_name} for {agent_id}")
                                    create_job(
                                        name=job_name,
                                        description=f"Scheduled trigger for {trigger_name}",
                                        assignees=[agent_id],
                                        tags=[f"trigger:{name}", "auto-complete"],
                                        due_date=None,
                                        created_by="system"
                                    )

                        # Save state for morning/evening triggers
                        if name in ["morning", "evening"]:
                            state = self._get_system_state()
                            state[f"last_{name}"] = today
                            self._save_system_state(state)

            except Exception as e:
                print(f"Scheduler error: {e}")

            time.sleep(10)  # Check every 10 seconds

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

        # Load and start all enabled agents
        configs = self.load_agent_configs()
        enabled = [c for c in configs if c.get("enabled", True)]

        print(f"Found {len(configs)} agents, {len(enabled)} enabled")

        # Sync agent inbox jobs
        from .tools.jobs import sync_agent_inbox_jobs
        sync_agent_inbox_jobs()
        print("Agent inbox jobs synced")

        for config in enabled:
            self.start_agent(config)

        if not enabled:
            print("No enabled agents. Waiting...")

        # Emit startup triggers (system:start and any missed time triggers)
        if enabled:
            self._emit_startup_triggers()

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
