"""
Agent Tools - Introspection and management of agents.
"""

import json
from pathlib import Path
from typing import List, Optional

from . import tool


DATA_DIR = Path(__file__).parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


@tool("list_agents", "List all configured agents")
def list_agents() -> List[dict]:
    """List all agents with their configurations."""
    agents = []

    if not AGENTS_DIR.exists():
        return agents

    for agent_dir in AGENTS_DIR.iterdir():
        if agent_dir.is_dir():
            config_path = agent_dir / "config.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    agents.append(config)

    return agents


@tool("get_agent", "Get an agent's configuration and persona")
def get_agent(agent_id: str) -> Optional[dict]:
    """Get detailed info about an agent."""
    agent_dir = AGENTS_DIR / agent_id

    if not agent_dir.exists():
        return None

    result = {"id": agent_id}

    # Load config
    config_path = agent_dir / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            result["config"] = json.load(f)

    # Load persona
    persona_path = agent_dir / f"{agent_id}-persona.md"
    if persona_path.exists():
        result["persona"] = persona_path.read_text()

    return result


@tool("get_agent_memory", "Get an agent's persistent memory")
def get_agent_memory(agent_id: str) -> dict:
    """Get an agent's memory."""
    memory_path = AGENTS_DIR / agent_id / "state" / "memory.json"
    if memory_path.exists():
        with open(memory_path) as f:
            return json.load(f)
    return {}


@tool("update_agent_memory", "Update an agent's persistent memory")
def update_agent_memory(agent_id: str, key: str, value: str) -> dict:
    """Set a value in an agent's memory."""
    state_dir = AGENTS_DIR / agent_id / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    memory_path = state_dir / "memory.json"

    memory = {}
    if memory_path.exists():
        with open(memory_path) as f:
            memory = json.load(f)

    memory[key] = value

    with open(memory_path, "w") as f:
        json.dump(memory, f, indent=2)

    return memory


def get_agent_persona(agent_id: str) -> Optional[str]:
    """Get an agent's persona markdown."""
    persona_path = AGENTS_DIR / agent_id / f"{agent_id}-persona.md"
    if persona_path.exists():
        return persona_path.read_text()
    return None


def update_agent_persona(agent_id: str, persona: str) -> dict:
    """Update an agent's persona markdown file."""
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    persona_path = agent_dir / f"{agent_id}-persona.md"
    persona_path.write_text(persona)

    return {"updated": True, "agent_id": agent_id}


def get_agent_config(agent_id: str) -> Optional[dict]:
    """Get an agent's configuration."""
    config_path = AGENTS_DIR / agent_id / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return None


def update_agent_config(agent_id: str, config: dict) -> dict:
    """Update an agent's configuration.

    Note: Changes to triggers require a restart to take effect.
    """
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    config_path = agent_dir / "config.json"

    # Preserve the id field
    config["id"] = agent_id

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return {"updated": True, "agent_id": agent_id, "config": config}
