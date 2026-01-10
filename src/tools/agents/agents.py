"""
Agent Tools - Introspection and management of agents.
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional

from .. import tool, _TOOL_REGISTRY


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"

# Minimal tools every agent needs to function
BASE_TOOLS = [
    "list_jobs",
    "get_job",
    "create_job",
    "complete_job",
    "add_job_log",
    "done_working"
]


@tool("list_agents", "List all configured agents with their settings. Use when: checking what agents exist, finding who to assign work to.", tool_type="agents")
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


@tool("list_agents_for_routing", "List agents with minimal details for job routing decisions. Shows id, name, purpose, and enabled status.", tool_type="agents")
def list_agents_for_routing() -> List[dict]:
    """List agents with just enough info for routing decisions.

    Returns a minimal summary for each agent:
    - id: The agent's identifier
    - name: Display name
    - purpose: First line/paragraph of profile (what they do)
    - enabled: Whether the agent is active
    """
    agents = []

    if not AGENTS_DIR.exists():
        return agents

    for agent_dir in AGENTS_DIR.iterdir():
        if agent_dir.is_dir():
            config_path = agent_dir / "config.json"
            profile_path = agent_dir / "profile.md"

            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)

                # Extract purpose from profile (first non-heading paragraph)
                purpose = ""
                if profile_path.exists():
                    content = profile_path.read_text()
                    # Skip title and empty lines, get first real paragraph
                    for line in content.split("\n"):
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#"):
                            purpose = stripped
                            break

                agents.append({
                    "id": config.get("id"),
                    "name": config.get("name"),
                    "purpose": purpose,
                    "enabled": config.get("enabled", True)
                })

    return agents


@tool("get_agent", "Get an agent's configuration and profile. Use when: need detailed info about a specific agent.", tool_type="agents")
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

    # Load profile (with fallback to old persona location)
    profile_path = agent_dir / "profile.md"
    if profile_path.exists():
        result["profile"] = profile_path.read_text()
    else:
        # Fallback to old persona location
        persona_path = agent_dir / f"{agent_id}-persona.md"
        if persona_path.exists():
            result["profile"] = persona_path.read_text()

    return result


def get_agent_profile(agent_id: str) -> Optional[str]:
    """Get an agent's profile markdown."""
    profile_path = AGENTS_DIR / agent_id / "profile.md"
    if profile_path.exists():
        return profile_path.read_text()
    # Fallback to old persona location
    persona_path = AGENTS_DIR / agent_id / f"{agent_id}-persona.md"
    if persona_path.exists():
        return persona_path.read_text()
    return None


def update_agent_profile_internal(agent_id: str, profile: str) -> dict:
    """Update an agent's profile markdown file."""
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    profile_path = agent_dir / "profile.md"
    profile_path.write_text(profile)

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


@tool("create_agent", "Create a new agent with config and profile. Use when: user asks for a new specialized agent or automation capability.", tool_type="agents")
def create_agent(agent_id: str, name: str, purpose: str, tools: list = None, triggers: list = None, exploration: dict = None, reflection: dict = None) -> dict:
    """Create a new agent with the specified configuration.

    Args:
        agent_id: Unique identifier (lowercase, no spaces, e.g., 'researcher')
        name: Display name (e.g., 'Researcher')
        purpose: Description of what the agent does
        tools: List of tool names to assign (use list_available_tools to see options).
               If not provided, uses minimal base tools.
        triggers: Optional list of triggers (e.g., ['time:morning', 'system:start'])
        exploration: Optional dict to enable exploration (autonomous discovery).
                     Example: {"enabled": True, "trigger": "time:hour_04"}
        reflection: Optional dict to enable reflection (memory consolidation and profile updates).
                    Example: {"enabled": True, "trigger": "time:evening"}

    Returns:
        Success status and agent details
    """
    # Validate agent_id
    if not agent_id.replace("-", "").replace("_", "").isalnum():
        return {"error": "agent_id must be alphanumeric with optional hyphens/underscores"}

    agent_id = agent_id.lower()
    agent_dir = AGENTS_DIR / agent_id

    if agent_dir.exists():
        return {"error": f"Agent already exists: {agent_id}"}

    # Create agent directory and memory directories
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "memory" / "long-term").mkdir(parents=True, exist_ok=True)

    # Use provided tools or fall back to base tools
    agent_tools = list(tools) if tools else list(BASE_TOOLS)

    # Ensure base tools are always included
    for base_tool in BASE_TOOLS:
        if base_tool not in agent_tools:
            agent_tools.append(base_tool)

    # Get next order number
    existing_agents = list_agents()
    max_order = max((a.get("order", 0) for a in existing_agents), default=0)

    # Create config
    config = {
        "id": agent_id,
        "name": name,
        "enabled": True,
        "order": max_order + 1,
        "tools": agent_tools,
        "triggers": triggers or []
    }

    # Add exploration if provided
    if exploration:
        config["exploration"] = exploration

    # Add reflection if provided
    if reflection:
        config["reflection"] = reflection

    config_path = agent_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    # Create profile (replaces old persona)
    profile = f"""# {name}

{purpose}

## Purpose

{purpose}

## Behavioral Rules

I must:
- Complete assigned jobs thoroughly
- Use available tools appropriately
- Call done_working when finished with a work cycle

## How I Work

1. Check my assigned jobs
2. Work on the highest priority job
3. Use my tools to accomplish the task
4. Mark jobs as complete when done
5. Call done_working to signal I'm finished
"""

    profile_path = agent_dir / "profile.md"
    profile_path.write_text(profile)

    return {
        "created": True,
        "agent_id": agent_id,
        "config": config,
        "profile_path": str(profile_path),
        "note": "Restart Euno for the new agent to become active"
    }


@tool("update_agent_profile", "Update an agent's profile/instructions. Use when: modifying how an agent behaves.", tool_type="agents")
def update_agent_profile(agent_id: str, profile: str) -> dict:
    """Update an agent's profile markdown file.

    Args:
        agent_id: The agent to update
        profile: The new profile markdown content
    """
    return update_agent_profile_internal(agent_id, profile)


@tool("update_own_profile", "Update your own profile with learnings from reflection. Use during reflection to codify behavioral patterns.", tool_type="agents")
def update_own_profile(updates: str, agent_id: str = None) -> dict:
    """Append a reflection update section to your own profile.

    Args:
        updates: Description of updates to apply (behavioral rules, voice adjustments, etc.)
        agent_id: Your agent ID (automatically set by the system)

    Note: This tool can only update your own profile, not other agents'.
    """
    from datetime import datetime

    if not agent_id:
        return {"error": "agent_id is required"}

    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    profile_path = agent_dir / "profile.md"

    if profile_path.exists():
        current_profile = profile_path.read_text()
    else:
        current_profile = f"# Profile: {agent_id}\n"

    # Add reflection update section
    today = datetime.now().strftime("%Y-%m-%d")
    update_section = f"\n\n---\n\n## Reflection Update ({today})\n\n{updates}"

    new_profile = current_profile + update_section
    profile_path.write_text(new_profile)

    return {"updated": True, "agent_id": agent_id, "date": today}


# Backward-compatible alias for old tool name
@tool("update_agent_persona", "Update an agent's profile. (Alias for update_agent_profile)", tool_type="agents")
def update_agent_persona(agent_id: str, persona: str) -> dict:
    """Update an agent's profile. Alias for update_agent_profile."""
    return update_agent_profile_internal(agent_id, persona)


@tool("enable_agent", "Enable a disabled agent. Use when: reactivating an agent that was paused.", tool_type="agents")
def enable_agent(agent_id: str) -> dict:
    """Enable an agent so it can process jobs.

    Args:
        agent_id: The agent to enable
    """
    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    config["enabled"] = True
    return update_agent_config(agent_id, config)


@tool("disable_agent", "Disable an agent so it stops processing jobs. Use when: pausing an agent temporarily.", tool_type="agents")
def disable_agent(agent_id: str) -> dict:
    """Disable an agent so it stops processing jobs.

    Args:
        agent_id: The agent to disable
    """
    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    config["enabled"] = False
    return update_agent_config(agent_id, config)


@tool("update_agent_triggers", "Update an agent's trigger configuration. Use when: changing when an agent wakes up (requires restart).", tool_type="agents")
def update_agent_triggers(agent_id: str, triggers: list) -> dict:
    """Update which triggers wake an agent.

    Args:
        agent_id: The agent to update
        triggers: List of triggers (e.g., ['time:morning', 'system:start', 'memory:long-term'])

    Note: Changes require a restart to take effect.
    """
    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    config["triggers"] = triggers
    result = update_agent_config(agent_id, config)
    result["note"] = "Restart Euno for trigger changes to take effect"
    return result


@tool("delete_agent", "Permanently delete an agent. Use when: removing an agent that is no longer needed (cannot be undone).", tool_type="agents")
def delete_agent(agent_id: str) -> dict:
    """Permanently delete an agent and all its data.

    Args:
        agent_id: The agent to delete

    Warning: This cannot be undone!
    """
    # Prevent deleting core agents
    protected_agents = ["chat", "worker", "user"]
    if agent_id in protected_agents:
        return {"error": f"Cannot delete core agent: {agent_id}"}

    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    # Remove the agent directory
    shutil.rmtree(agent_dir)

    return {
        "deleted": True,
        "agent_id": agent_id,
        "note": "Restart Euno to fully remove the agent"
    }


@tool("list_available_tools", "List all tools that can be assigned to agents. Use when: creating/updating agents and need to know what capabilities to grant.", tool_type="agents")
def list_available_tools() -> List[dict]:
    """List all available tools that can be assigned to agents.

    Returns a list of tool names and descriptions.
    """
    tools = []
    for name, info in _TOOL_REGISTRY.items():
        tools.append({
            "name": name,
            "description": info["description"]
        })
    return sorted(tools, key=lambda x: x["name"])
