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


DATA_DIR = Path(__file__).parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"

# Global manager instance for tools to access
_manager_instance: 'AgentManager' = None


def get_manager() -> 'AgentManager':
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

    def _run_agent_loop(self, agent: Agent):
        """Run an agent's work loop in its own thread."""
        system_config = self._get_system_config()
        min_sleep = system_config.get("agents", {}).get("min_sleep_seconds", 60)

        sleep_seconds = agent.config.get("sleep_minutes", 5) * 60
        sleep_seconds = max(sleep_seconds, min_sleep)

        while self.running:
            try:
                # Do work cycle
                agent.work_cycle_sync()

                # Calculate wake time
                wake_time = datetime.now() + timedelta(seconds=sleep_seconds)
                agent._log("sleep", {
                    "duration_seconds": sleep_seconds,
                    "wake_at": wake_time.isoformat()
                })

                # Wait for wake event or timeout
                woken_early = agent.wait_for_wake(timeout=sleep_seconds)

                if woken_early:
                    agent._log("wake", {"reason": "triggered"})
                else:
                    agent._log("wake", {"reason": "timeout"})

            except Exception as e:
                agent._log("error", {"message": str(e)})
                print(f"Agent {agent.id} error: {e}")
                # Brief sleep before retry
                time.sleep(5)

    def wake_agent(self, agent_id: str) -> bool:
        """Wake an agent immediately.

        Args:
            agent_id: ID of agent to wake

        Returns:
            True if agent found and woken, False otherwise
        """
        if agent_id in self.agents:
            self.agents[agent_id].wake()
            return True
        return False

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
    set_manager(manager)
    manager.run()
