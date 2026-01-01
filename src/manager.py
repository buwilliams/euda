"""
Agent Manager - Manages lifecycle of all agents.

Responsibilities:
- Load agent configurations
- Start all enabled agents
- Monitor agent health
- Restart failed agents
- Handle graceful shutdown
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List

from .agent import Agent


DATA_DIR = Path(__file__).parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class AgentManager:
    """Manages the lifecycle of all agents."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
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

    async def start_agent(self, config: dict):
        """Start a single agent."""
        agent_id = config["id"]
        print(f"Starting agent: {agent_id}")

        agent = Agent(agent_id, config)
        self.agents[agent_id] = agent

        # Create task for agent loop
        self.tasks[agent_id] = asyncio.create_task(
            self._run_agent_loop(agent),
            name=f"agent-{agent_id}"
        )

    async def _run_agent_loop(self, agent: Agent):
        """Run an agent's work loop."""
        sleep_seconds = agent.config.get("sleep_minutes", 5) * 60

        while self.running:
            try:
                # Do work cycle
                await agent.work_cycle()

                # Sleep between cycles
                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                print(f"Agent {agent.id} cancelled")
                break
            except Exception as e:
                print(f"Agent {agent.id} error: {e}")
                # Brief sleep before retry
                await asyncio.sleep(5)

    async def run(self):
        """Run the agent manager."""
        self.running = True

        # Load and start all enabled agents
        configs = self.load_agent_configs()
        enabled = [c for c in configs if c.get("enabled", True)]

        print(f"Found {len(configs)} agents, {len(enabled)} enabled")

        for config in enabled:
            await self.start_agent(config)

        if not enabled:
            print("No enabled agents. Waiting...")

        # Wait until shutdown
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

        await self.shutdown()

    async def shutdown(self):
        """Gracefully shut down all agents."""
        print("Shutting down agents...")
        self.running = False

        # Cancel all agent tasks
        for task in self.tasks.values():
            task.cancel()

        # Wait for all to complete
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)

        print("All agents stopped")


def run_agent_manager():
    """Convenience function to run the agent manager."""
    manager = AgentManager()
    asyncio.run(manager.run())
