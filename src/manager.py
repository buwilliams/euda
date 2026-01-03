"""
Agent Manager - Manages lifecycle of all agents.

Responsibilities:
- Load agent configurations
- Start all enabled agents (each in its own thread)
- Monitor agent health
- Restart failed agents
- Handle graceful shutdown
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from .agent import Agent
from .cost_tracker import BudgetExceeded, print_summary as print_cost_summary


DATA_DIR = Path(__file__).parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class AgentManager:
    """Manages the lifecycle of all agents."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.running = False
        self.error_backoff: Dict[str, dict] = {}  # Track backoff state per agent

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
        print(f"Starting agent: {agent_id}")

        agent = Agent(agent_id, config)
        self.agents[agent_id] = agent

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

    def _run_agent_loop(self, agent: Agent):
        """Run an agent's work loop with intelligent error handling and backoff."""
        system_config = self._get_system_config()
        min_sleep = system_config.get("agents", {}).get("min_sleep_seconds", 60)

        sleep_seconds = agent.config.get("sleep_minutes", 5) * 60
        sleep_seconds = max(sleep_seconds, min_sleep)

        while self.running:
            try:
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

                # Do work cycle
                agent.work_cycle_sync()

                # Success - reset backoff
                self._reset_backoff(agent.id)

                # Calculate wake time
                wake_time = datetime.now() + timedelta(seconds=sleep_seconds)
                agent._log("sleep", {
                    "duration_seconds": sleep_seconds,
                    "wake_at": wake_time.isoformat()
                })

                # Sleep between cycles
                time.sleep(sleep_seconds)

                agent._log("wake")

            except BudgetExceeded as e:
                # Budget exceeded - trigger graceful shutdown
                agent._log("budget_exceeded", {
                    "budget": e.budget,
                    "spent": e.spent
                })
                print(f"\n[{agent.id}] BUDGET EXCEEDED: ${e.spent:.4f} spent of ${e.budget:.2f} limit")
                print_cost_summary()
                self.running = False  # Stop all agents
                return  # Exit this agent's loop

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

    def run(self):
        """Run the agent manager."""
        self.running = True

        # Load and start all enabled agents
        configs = self.load_agent_configs()
        enabled = [c for c in configs if c.get("enabled", True)]

        print(f"Found {len(configs)} agents, {len(enabled)} enabled")

        for config in enabled:
            self.start_agent(config)

        if not enabled:
            print("No enabled agents. Waiting...")

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

        # Wait for threads to finish (they're daemons, so they'll die with main)
        for agent_id, thread in self.threads.items():
            thread.join(timeout=2)

        print("All agents stopped")


def run_agent_manager():
    """Convenience function to run the agent manager."""
    manager = AgentManager()
    manager.run()
