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
    - purpose: First line/paragraph of identity (what they do)
    - enabled: Whether the agent is active
    """
    agents = []

    if not AGENTS_DIR.exists():
        return agents

    for agent_dir in AGENTS_DIR.iterdir():
        if agent_dir.is_dir():
            config_path = agent_dir / "config.json"
            identity_path = agent_dir / "identity.md"

            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)

                # Extract purpose from identity (first non-heading paragraph)
                purpose = ""
                if identity_path.exists():
                    content = identity_path.read_text()
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
                    "enabled": config.get("state", "enabled") == "enabled"
                })

    return agents


@tool("get_agent", "Get an agent's configuration and identity. Use when: need detailed info about a specific agent.", tool_type="agents")
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

    # Load identity
    identity_path = agent_dir / "identity.md"
    if identity_path.exists():
        result["identity"] = identity_path.read_text()

    return result


def get_agent_identity(agent_id: str) -> Optional[str]:
    """Get an agent's identity markdown."""
    identity_path = AGENTS_DIR / agent_id / "identity.md"
    if identity_path.exists():
        return identity_path.read_text()
    return None


def update_agent_identity_internal(agent_id: str, identity: str) -> dict:
    """Update an agent's identity markdown file."""
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    identity_path = agent_dir / "identity.md"
    identity_path.write_text(identity)

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


@tool("create_agent", "Create a new agent with config and identity. Use when: user asks for a new specialized agent or automation capability.", tool_type="agents", input_schema={
    "type": "object",
    "properties": {
        "agent_id": {"type": "string", "description": "Unique identifier (lowercase, no spaces, e.g., 'researcher')"},
        "name": {"type": "string", "description": "Display name (e.g., 'Researcher')"},
        "purpose": {"type": "string", "description": "Description of what the agent does"},
        "tools": {"type": "array", "items": {"type": "string"}, "description": "List of tool names to assign"},
        "triggers": {"type": "array", "items": {"type": "string"}, "description": "Wake-up triggers (e.g., ['time:morning'])"},
        "consolidation": {
            "type": "object",
            "description": "Enable memory consolidation behavior",
            "properties": {
                "enabled": {"type": "boolean", "description": "Whether consolidation is active"},
                "trigger": {"type": "string", "description": "When to run (e.g., 'time:evening')"}
            },
            "required": ["enabled", "trigger"]
        }
    },
    "required": ["agent_id", "name", "purpose"]
})
def create_agent(agent_id: str, name: str, purpose: str, tools: list = None, triggers: list = None, consolidation: dict = None) -> dict:
    """Create a new agent with the specified configuration.

    Args:
        agent_id: Unique identifier (lowercase, no spaces, e.g., 'researcher')
        name: Display name (e.g., 'Researcher')
        purpose: Description of what the agent does
        tools: List of tool names to assign (use list_available_tools to see options).
               If not provided, uses minimal base tools.
        triggers: Optional list of triggers (e.g., ['time:morning', 'system:start'])
        consolidation: Optional dict to enable consolidation (memory consolidation and identity updates).
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
        "state": "enabled",
        "order": max_order + 1,
        "token_budget": {
            "frequency": "daily",
            "input_ratio": 0.8,
            "output_ratio": 0.2
        },
        "tools": agent_tools,
        "triggers": triggers or []
    }

    # Add consolidation if provided
    if consolidation:
        config["consolidation"] = consolidation

    config_path = agent_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    # Create identity
    identity = f"""# {name}

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

    identity_path = agent_dir / "identity.md"
    identity_path.write_text(identity)

    # Dynamically register and start the agent if manager is running
    from ...agent.manager import get_manager
    manager = get_manager()
    if manager and manager.running:
        result = manager.register_new_agent(agent_id)
        started = result.get("started", False)
    else:
        started = False

    return {
        "created": True,
        "agent_id": agent_id,
        "config": config,
        "identity_path": str(identity_path),
        "started": started
    }


@tool("update_agent_identity", "Update an agent's identity/instructions. Use when: modifying how an agent behaves.", tool_type="agents")
def update_agent_identity(agent_id: str, identity: str) -> dict:
    """Update an agent's identity markdown file.

    Args:
        agent_id: The agent to update
        identity: The new identity markdown content
    """
    return update_agent_identity_internal(agent_id, identity)


@tool("update_own_identity", "Update your own identity with learnings from reflection. Use during reflection to codify behavioral patterns.", tool_type="agents")
def update_own_identity(updates: str, agent_id: str = None) -> dict:
    """Append a reflection update section to your own identity.

    Args:
        updates: Description of updates to apply (behavioral rules, voice adjustments, etc.)
        agent_id: Your agent ID (automatically set by the system)

    Note: This tool can only update your own identity, not other agents'.
    """
    from datetime import datetime

    if not agent_id:
        return {"error": "agent_id is required"}

    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    identity_path = agent_dir / "identity.md"

    if identity_path.exists():
        current_identity = identity_path.read_text()
    else:
        current_identity = f"# Identity: {agent_id}\n"

    # Add reflection update section
    today = datetime.now().strftime("%Y-%m-%d")
    update_section = f"\n\n---\n\n## Reflection Update ({today})\n\n{updates}"

    new_identity = current_identity + update_section
    identity_path.write_text(new_identity)

    return {"updated": True, "agent_id": agent_id, "date": today}


@tool("append_to_agent_identity", "Add a section to an agent's identity without overwriting existing content. Safer than update_agent_identity which replaces entirely.", tool_type="agents")
def append_to_agent_identity(agent_id: str, section_title: str, content: str) -> dict:
    """Safely append a new section to an agent's identity.

    Unlike update_agent_identity which replaces the entire identity, this appends
    a new section without losing reflection updates or other existing content.

    Args:
        agent_id: The agent to update
        section_title: Title for the new section (e.g., "New Learning", "Behavioral Update")
        content: Content to add under this section
    """
    from datetime import datetime

    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    identity_path = agent_dir / "identity.md"

    if identity_path.exists():
        current_identity = identity_path.read_text()
    else:
        current_identity = f"# {agent_id}\n"

    today = datetime.now().strftime("%Y-%m-%d")
    new_section = f"\n\n---\n\n## {section_title} ({today})\n\n{content}"

    new_identity = current_identity + new_section
    identity_path.write_text(new_identity)

    return {"updated": True, "agent_id": agent_id, "section": section_title, "date": today}




@tool("enable_agent", "Enable a disabled agent. Use when: reactivating an agent that was paused.", tool_type="agents")
def enable_agent(agent_id: str) -> dict:
    """Enable an agent so it can process jobs.

    Args:
        agent_id: The agent to enable
    """
    from ...agent.cognition.metacognition.regulation.tokens import get_token_awareness, AgentState

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()
    token_awareness.set_agent_state(agent_id, AgentState.ENABLED)
    return {"agent_id": agent_id, "state": "enabled"}


@tool("disable_agent", "Disable an agent so it stops processing jobs. Use when: pausing an agent temporarily.", tool_type="agents")
def disable_agent(agent_id: str) -> dict:
    """Disable an agent so it stops processing jobs.

    Args:
        agent_id: The agent to disable
    """
    from ...agent.cognition.metacognition.regulation.tokens import get_token_awareness, AgentState

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()
    token_awareness.set_agent_state(agent_id, AgentState.DISABLED)
    return {"agent_id": agent_id, "state": "disabled"}


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
    protected_agents = ["user", "worker"]
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
