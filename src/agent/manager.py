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
from ..web.events import EventBus, set_event_bus, get_event_bus


DATA_DIR = Path(__file__).parent.parent.parent / "data"
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
        self.agents_with_jobs: Dict[str, bool] = {}  # Cache: agent_id -> has_jobs
        self.event_bus = EventBus()

    def get_enabled_agent_count(self) -> int:
        """Get the number of enabled agents for budget splitting.

        Returns:
            Count of agents in ENABLED state
        """
        token_awareness = get_token_awareness()
        count = 0
        for agent_id in self.agents:
            state = token_awareness.get_agent_state(agent_id)
            if state == AgentState.ENABLED:
                count += 1
        return max(1, count)  # At least 1 to avoid division by zero

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

        # Load the agent's config
        config_path = AGENTS_DIR / agent_id / "config.json"
        if not config_path.exists():
            return {"error": f"Agent config not found: {agent_id}"}

        with open(config_path) as f:
            config = json.load(f)
            config["_dir"] = str(AGENTS_DIR / agent_id)

        # Sync agent inbox jobs to create the inbox for this agent
        from ..tools.data.jobs import sync_agent_inbox_jobs
        sync_agent_inbox_jobs()

        # Start the agent if enabled
        if config.get("enabled", True):
            self.start_agent(config)

            # Initialize job cache for this agent
            from ..tools.data.jobs import list_jobs
            jobs = list_jobs(status="todo", assignee=agent_id, actionable=True)
            self.agents_with_jobs[agent_id] = bool(jobs)

            return {"registered": True, "agent_id": agent_id, "started": True}

        return {"registered": True, "agent_id": agent_id, "started": False, "note": "Agent is disabled"}

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
        from ..tools.data.jobs import create_job, list_jobs, get_system_container

        today = datetime.now().strftime("%Y-%m-%d")
        system_container = get_system_container()

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
                        parent_id=system_container["id"],
                        assignees=[agent_id],
                        tags=["trigger:start"],
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
                                parent_id=system_container["id"],
                                assignees=[agent_id],
                                tags=[f"trigger:{trigger_type}"],
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
        from ..tools.data.jobs import list_jobs, claim_job, release_job

        poll_interval = self._get_system_config().get("agents", {}).get("poll_interval", 0.1)
        token_awareness = get_token_awareness()

        while self.running:
            try:
                # Check agent state (new token awareness system)
                agent_state = token_awareness.get_agent_state(agent.id)
                if agent_state == AgentState.DISABLED:
                    time.sleep(poll_interval)
                    continue
                if agent_state == AgentState.PAUSED:
                    # Agent is paused - wait for manual intervention
                    pause_info = token_awareness.get_pause_info(agent.id)
                    agent._log("agent_paused_waiting", {
                        "reason": pause_info.get("reason", "unknown")
                    })
                    time.sleep(30)  # Check every 30 seconds
                    continue

                # Legacy check (backward compatibility)
                if not agent.config.get("enabled", True):
                    time.sleep(poll_interval)
                    continue

                # Check if we're in backoff period
                if agent.id in self.error_backoff:
                    backoff_state = self.error_backoff[agent.id]
                    if backoff_state["backoff_until"] and datetime.now() < backoff_state["backoff_until"]:
                        # Use total_seconds() not .seconds to get actual remaining time
                        remaining = int((backoff_state["backoff_until"] - datetime.now()).total_seconds())
                        agent._log("backoff_wait", {
                            "reason": "quota_or_rate_limit",
                            "remaining_seconds": remaining,
                            "retry_at": backoff_state["backoff_until"].isoformat(),
                            "attempt": backoff_state["count"]
                        })
                        # Sleep for 1 minute or remaining time, with minimum 1 second
                        time.sleep(max(min(remaining, 60), 1))
                        continue

                # Check cache first (fast) - skip DB query if no jobs pending
                if not self.agents_with_jobs.get(agent.id, False):
                    time.sleep(poll_interval)
                    continue

                # Cache says jobs may exist - query DB to confirm
                jobs = list_jobs(status="todo", assignee=agent.id, actionable=True)

                if jobs:
                    # Track the job being processed for cooldown decision
                    current_job = jobs[0]
                    job_id = current_job.get("id")
                    is_background = "background" in current_job.get("tags", [])

                    # Try to claim the job exclusively
                    claim_result = claim_job(job_id, agent.id)
                    if "error" in claim_result:
                        # Job already claimed by another agent, skip it
                        agent._log("job_already_claimed", {
                            "job_id": job_id,
                            "error": claim_result.get("error")
                        })
                        time.sleep(0.5)  # Brief delay before re-polling
                        continue

                    agent._log("polling_found_jobs", {"count": len(jobs), "claimed": job_id})
                    try:
                        agent.work_cycle_sync()
                    finally:
                        # Always release the job claim when done
                        release_job(job_id, agent.id)

                    # Success - reset backoff and update last_ran
                    self._reset_backoff(agent.id)
                    self._update_agent_last_ran(agent.id)

                    # Clear failure tags from previous attempts on success
                    from ..tools.data.jobs import update_job, get_job
                    job = get_job(job_id)
                    if job:
                        tags = job.get("tags", [])
                        clean_tags = [t for t in tags if not t.startswith("failure:")]
                        if len(clean_tags) != len(tags):
                            update_job(job_id, tags=clean_tags)

                    # Re-check for more jobs and update cache
                    jobs = list_jobs(status="todo", assignee=agent.id, actionable=True)
                    self.agents_with_jobs[agent.id] = bool(jobs)

                    # Apply pacing between work cycles to prevent runaway spinning
                    # When jobs fail fast (errors swallowed, etc.), this prevents CPU-speed loops
                    MIN_CYCLE_DELAY = 0.5  # 500ms minimum between cycles

                    if is_background and jobs:
                        # Background jobs: pacing with minimum floor
                        delay = MIN_CYCLE_DELAY * 2  # 1 second for background jobs
                        agent._log("background_job_pacing", {
                            "delay": delay,
                            "remaining_jobs": len(jobs)
                        })
                        time.sleep(delay)
                    elif jobs:
                        # Non-background jobs with more work: minimum delay to prevent spinning
                        time.sleep(MIN_CYCLE_DELAY)
                else:
                    # Cache was stale - clear it
                    self.agents_with_jobs[agent.id] = False

            except AgentPausedError as e:
                # Agent paused due to threshold breach or runaway detection
                agent._log("agent_paused", {
                    "reason": e.reason
                })
                print(f"\n[{agent.id}] PAUSED: {e.reason} - waiting for manual resume")
                # Wait until resumed or shutdown (no auto-resume for token-based pauses)
                while self.running:
                    agent_state = token_awareness.get_agent_state(agent.id)
                    if agent_state == AgentState.ENABLED:
                        agent._log("agent_resumed", {"resumed_by": "user"})
                        print(f"[{agent.id}] Resumed")
                        break
                    time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                error_msg = str(e)
                agent._log("error", {"message": error_msg})
                print(f"Agent {agent.id} error: {e}")

                # Track job failures and escalate to user after 3 consecutive failures
                # This prevents infinite retry loops when jobs fail persistently
                if 'job_id' in locals() and 'current_job' in locals():
                    from ..tools.data.jobs import update_job, handoff_job, get_job

                    job = get_job(job_id)
                    if job:
                        tags = job.get("tags", [])

                        # Count existing failure tags for this agent
                        failure_prefix = f"failure:{agent.id}:"
                        failure_count = sum(1 for t in tags if t.startswith(failure_prefix))

                        # Add new failure tag (replacing previous count)
                        new_tag = f"failure:{agent.id}:{failure_count + 1}"
                        updated_tags = [t for t in tags if not t.startswith(failure_prefix)] + [new_tag]
                        update_job(job_id, tags=updated_tags)

                        if failure_count + 1 >= 3:
                            # 3 strikes - hand off to user
                            agent._log("job_escalated_to_user", {
                                "job_id": job_id,
                                "failure_count": failure_count + 1,
                                "error": error_msg[:200]
                            })
                            handoff_job(job_id, "user", f"Agent {agent.id} failed 3 times: {error_msg[:200]}")
                            print(f"[{agent.id}] Job {job_id} escalated to user after 3 failures")

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

    def _create_reflection_jobs(self, trigger_name: str):
        """Create reflection jobs for agents with matching reflection trigger.

        Reflection is now a first-class behavioral trigger. Instead of running
        consolidation directly, we create a reflection job that the agent
        processes using the reflection.md prompt and memory tools.

        Args:
            trigger_name: The trigger that fired (e.g., "time:evening")
        """
        from ..tools.data.jobs import create_job, list_jobs, get_system_container
        from datetime import datetime

        system_container = get_system_container()
        today = datetime.now().strftime("%Y-%m-%d")

        for agent_id, agent in self.agents.items():
            if not agent.config.get("enabled", True):
                continue

            # Check if agent has reflection enabled and if this trigger matches
            reflection_config = agent.config.get("reflection", {})
            if not reflection_config.get("enabled", True):
                continue

            reflection_trigger = reflection_config.get("trigger", "time:evening")

            if trigger_name == reflection_trigger:
                job_name = f"Trigger:reflection:{today}"

                # Check if reflection job already exists for this agent today
                existing = list_jobs(status="todo", assignee=agent_id)
                already_exists = any(j["name"] == job_name for j in existing)

                if not already_exists:
                    print(f"[scheduler] Creating reflection job for {agent_id}")
                    create_job(
                        name=job_name,
                        description="Scheduled reflection: review memories, evolve identity, graduate learnings",
                        parent_id=system_container["id"],
                        assignees=[agent_id],
                        tags=["trigger:reflection"],
                        due_date=None,
                        created_by="system"
                    )

    def _create_exploration_jobs(self, trigger_name: str):
        """Create exploration jobs for agents with matching exploration trigger.

        Exploration is a first-class behavioral trigger for scheduled discovery.
        Agents use the exploration.md prompt to research opportunities aligned
        with their purpose and the user's interests.

        Args:
            trigger_name: The trigger that fired (e.g., "time:hour_04")
        """
        from ..tools.data.jobs import create_job, list_jobs, get_system_container
        from datetime import datetime

        system_container = get_system_container()
        today = datetime.now().strftime("%Y-%m-%d")

        for agent_id, agent in self.agents.items():
            if not agent.config.get("enabled", True):
                continue

            # Check if agent has exploration enabled and if this trigger matches
            exploration_config = agent.config.get("exploration", {})
            if not exploration_config.get("enabled", False):
                continue

            exploration_trigger = exploration_config.get("trigger")
            if not exploration_trigger:
                continue

            if trigger_name == exploration_trigger:
                # Extract schedule name from trigger (e.g., "time:hour_04" -> "hour_04")
                schedule_name = trigger_name.replace("time:", "") if trigger_name.startswith("time:") else trigger_name
                job_name = f"Trigger:exploration:{today}"

                # Check if exploration job already exists for this agent today
                existing = list_jobs(status="todo", assignee=agent_id)
                already_exists = any(j["name"] == job_name for j in existing)

                if not already_exists:
                    print(f"[scheduler] Creating exploration job for {agent_id}")
                    create_job(
                        name=job_name,
                        description="Scheduled exploration: research opportunities, create suggestions for user",
                        parent_id=system_container["id"],
                        assignees=[agent_id],
                        tags=["trigger:exploration"],
                        due_date=None,
                        created_by="system"
                    )

    def _run_time_scheduler(self):
        """Background thread that creates trigger jobs based on schedules."""
        from ..tools.data.jobs import create_job, list_jobs, get_system_container

        last_fired: Dict[str, str] = {}  # schedule_name -> last fired date-hour-minute
        system_container = get_system_container()

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
                                        parent_id=system_container["id"],
                                        assignees=[agent_id],
                                        tags=[f"trigger:{name}"],
                                        due_date=None,
                                        created_by="system"
                                    )

                        # Save state for morning/evening triggers
                        if name in ["morning", "evening"]:
                            state = self._get_system_state()
                            state[f"last_{name}"] = today
                            self._save_system_state(state)

                        # Create reflection jobs for agents with matching reflection trigger
                        self._create_reflection_jobs(trigger_name)

                        # Create exploration jobs for agents with matching exploration trigger
                        self._create_exploration_jobs(trigger_name)

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
        from ..tools.data.jobs import sync_agent_inbox_jobs
        sync_agent_inbox_jobs()
        print("Agent inbox jobs synced")

        for config in enabled:
            self.start_agent(config)

        if not enabled:
            print("No enabled agents. Waiting...")

        # Emit startup triggers (system:start and any missed time triggers)
        if enabled:
            self._emit_startup_triggers()

        # Initialize job cache - check for existing actionable jobs
        from ..tools.data.jobs import list_jobs
        for agent_id in self.agents:
            jobs = list_jobs(status="todo", assignee=agent_id, actionable=True)
            self.agents_with_jobs[agent_id] = bool(jobs)
        print("Job cache initialized")

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
