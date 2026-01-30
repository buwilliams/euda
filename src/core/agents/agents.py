"""
Agent Tools - Introspection and management of agents.
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional



DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"

def _normalize_identity_content(content: str) -> str:
    """Normalize escaped newlines to real newlines for markdown rendering."""
    if content is None:
        return ""
    normalized = content.replace("\\r\\n", "\n")
    normalized = normalized.replace("\\n", "\n")
    return normalized

# Minimal tools every agent needs to function
BASE_TOOLS = [
    "list_topics",
    "get_topic",
    "create_topic",
    "complete_topic",
    "add_topic_log",
    "done_working"
]


def list_agents() -> List[dict]:
    """List all agents with their configurations.

    Uses layered config: config.defaults.json (base) + config.json (overrides).
    """
    from src.core.config import load_layered_config

    agents = []

    if not AGENTS_DIR.exists():
        return agents

    for agent_dir in AGENTS_DIR.iterdir():
        if agent_dir.is_dir():
            config = load_layered_config(agent_dir)
            if config:
                agents.append(config)

    return agents


def list_agents_for_routing() -> List[dict]:
    """List agents with just enough info for routing decisions.

    Returns a minimal summary for each agent:
    - id: The agent's identifier
    - name: Display name
    - purpose: First line/paragraph of identity (what they do)
    - enabled: Whether the agent is active

    Uses layered config: config.defaults.json (base) + config.json (overrides).
    """
    from src.core.config import load_layered_config

    agents = []

    if not AGENTS_DIR.exists():
        return agents

    for agent_dir in AGENTS_DIR.iterdir():
        if agent_dir.is_dir():
            identity_path = agent_dir / "identity.md"
            config = load_layered_config(agent_dir)

            if config:

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


def get_agent(agent_id: str) -> Optional[dict]:
    """Get detailed info about an agent.

    Uses layered config: config.defaults.json (base) + config.json (overrides).
    """
    from src.core.config import load_layered_config

    agent_dir = AGENTS_DIR / agent_id

    if not agent_dir.exists():
        return None

    result = {"id": agent_id}

    # Load config (layered)
    config = load_layered_config(agent_dir)
    if config:
        result["config"] = config

    # Load identity
    identity_path = agent_dir / "identity.md"
    if identity_path.exists():
        result["identity"] = identity_path.read_text()

    return result


def get_agent_identity(agent_id: str) -> Optional[str]:
    """Get an agent's identity markdown."""
    identity_path = AGENTS_DIR / agent_id / "identity.md"
    if identity_path.exists():
        raw = identity_path.read_text()
        normalized = _normalize_identity_content(raw)
        if normalized != raw:
            identity_path.write_text(normalized)
        return normalized
    return None


def update_agent_identity_internal(agent_id: str, identity: str) -> dict:
    """Update an agent's identity markdown file."""
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    identity_path = agent_dir / "identity.md"
    identity_path.write_text(_normalize_identity_content(identity))

    return {"updated": True, "agent_id": agent_id}


def get_agent_config(agent_id: str) -> Optional[dict]:
    """Get an agent's configuration.

    Uses layered config: config.defaults.json (base) + config.json (overrides).
    """
    from src.core.config import load_layered_config

    agent_dir = AGENTS_DIR / agent_id
    return load_layered_config(agent_dir)


def update_agent_config(agent_id: str, config: dict) -> dict:
    """Update an agent's configuration.

    Writes to config.json (user overrides), preserving config.defaults.json.
    Note: Changes to triggers require a restart to take effect.
    """
    from src.core.config import save_config_overrides

    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    # Preserve the id field
    config["id"] = agent_id

    save_config_overrides(agent_dir, config)

    return {"updated": True, "agent_id": agent_id, "config": config}


def create_agent(agent_id: str, name: str, purpose: str, tools: list = None, triggers: list = None) -> dict:
    """Create a new agent with the specified configuration.

    Args:
        agent_id: Unique identifier (lowercase, no spaces, e.g., 'researcher')
        name: Display name (e.g., 'Researcher')
        purpose: Description of what the agent does
        tools: List of tool names to assign (use list_available_tools to see options).
               If not provided, uses minimal base tools.
        triggers: Optional list of trigger objects. Each trigger should have:
                  - topic_name: Name of topic to create (e.g., 'euno:consolidate')
                  - instructions: Full topic description/guidance (optional)
                  - schedule: When to fire ('morning', 'evening')

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
- Complete assigned topics thoroughly
- Use available tools appropriately
- Call done_working when finished with a work cycle

## How I Work

1. Check my assigned topics
2. Work on the highest priority topic
3. Use my tools to accomplish the task
4. Mark topics as complete when done
5. Call done_working to signal I'm finished
"""

    identity_path = agent_dir / "identity.md"
    identity_path.write_text(identity)

    # Dynamically register and start the agent if manager is running
    from src.agent.manager import get_manager
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


def update_agent_identity(agent_id: str, identity: str) -> dict:
    """Update an agent's identity markdown file.

    Args:
        agent_id: The agent to update
        identity: The new identity markdown content
    """
    return update_agent_identity_internal(agent_id, identity)


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
        current_identity = _normalize_identity_content(identity_path.read_text())
    else:
        current_identity = f"# Identity: {agent_id}\n"

    # Add reflection update section
    today = datetime.now().strftime("%Y-%m-%d")
    update_section = f"\n\n---\n\n## Reflection Update ({today})\n\n{updates}"

    new_identity = _normalize_identity_content(current_identity + update_section)
    identity_path.write_text(new_identity)

    return {"updated": True, "agent_id": agent_id, "date": today}


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
        current_identity = _normalize_identity_content(identity_path.read_text())
    else:
        current_identity = f"# {agent_id}\n"

    today = datetime.now().strftime("%Y-%m-%d")
    new_section = f"\n\n---\n\n## {section_title} ({today})\n\n{content}"

    new_identity = _normalize_identity_content(current_identity + new_section)
    identity_path.write_text(new_identity)

    return {"updated": True, "agent_id": agent_id, "section": section_title, "date": today}




def enable_agent(agent_id: str) -> dict:
    """Enable an agent so it can process topics.

    Args:
        agent_id: The agent to enable
    """
    from src.agent.cognition.metacognition.regulation.tokens import get_token_awareness, AgentState

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()
    token_awareness.set_agent_state(agent_id, AgentState.ENABLED)
    return {"agent_id": agent_id, "state": "enabled"}


def disable_agent(agent_id: str) -> dict:
    """Disable an agent so it stops processing topics.

    Args:
        agent_id: The agent to disable
    """
    from src.agent.cognition.metacognition.regulation.tokens import get_token_awareness, AgentState

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()
    token_awareness.set_agent_state(agent_id, AgentState.DISABLED)
    return {"agent_id": agent_id, "state": "disabled"}


def update_agent_triggers(agent_id: str, triggers: list) -> dict:
    """Update which triggers wake an agent.

    Args:
        agent_id: The agent to update
        triggers: List of trigger objects. Each trigger should have:
                  - topic_name: Name of topic to create (e.g., 'euno:consolidate')
                  - instructions: Full topic description/guidance (optional)
                  - schedule: When to fire ('morning', 'evening')

    Note: Changes require a restart to take effect.
    """
    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    config["triggers"] = triggers
    result = update_agent_config(agent_id, config)
    result["note"] = "Restart Euno for trigger changes to take effect"
    return result


def delete_agent(agent_id: str) -> dict:
    """Permanently delete an agent and all its data.

    Args:
        agent_id: The agent to delete

    Warning: This cannot be undone!
    """
    # Prevent deleting core agents
    protected_agents = ["user", "soul"]
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


def list_available_tools() -> List[dict]:
    """List all available tools that can be assigned to agents.

    Returns a list of tool names and descriptions.
    Note: Tools are now provided via skills, not a static registry.
    """
    # Skills replaced the old tool registry - return the meta-tools
    from src.skills.tools import get_meta_tools
    return get_meta_tools()


def pause_agent(agent_id: str, reason: str = None) -> dict:
    """Pause an agent so it stops processing topics.

    Unlike disable, a paused agent:
    - Is still counted in budget calculations
    - Can be auto-resumed when budget resets
    - Is expected to be temporary

    Args:
        agent_id: The agent to pause
        reason: Optional reason for pausing
    """
    from src.agent.cognition.metacognition.regulation.tokens import get_token_awareness, AgentState

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()
    token_awareness.set_agent_state(agent_id, AgentState.PAUSED, reason or "manually paused")
    return {"agent_id": agent_id, "state": "paused", "reason": reason or "manually paused"}


def resume_agent(agent_id: str) -> dict:
    """Resume a paused agent so it can process topics again.

    Args:
        agent_id: The agent to resume
    """
    from src.agent.cognition.metacognition.regulation.tokens import get_token_awareness, AgentState

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()
    current_state = token_awareness.get_agent_state(agent_id)

    if current_state != AgentState.PAUSED:
        return {"error": f"Agent is not paused (current state: {current_state.value})"}

    token_awareness.set_agent_state(agent_id, AgentState.ENABLED)
    return {"agent_id": agent_id, "state": "enabled"}


def get_agent_status(agent_id: str) -> dict:
    """Get detailed status for an agent including pause info and usage.

    Args:
        agent_id: The agent to check

    Returns:
        Dict with state, pause_info, and usage summary
    """
    from src.agent.cognition.metacognition.regulation.tokens import get_token_awareness

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()

    state = token_awareness.get_agent_state(agent_id)
    pause_info = token_awareness.get_pause_info(agent_id)
    usage = token_awareness.get_agent_usage(agent_id)
    reset_info = token_awareness.get_time_until_reset(agent_id)

    return {
        "agent_id": agent_id,
        "name": config.get("name", agent_id),
        "state": state.value,
        "pause_info": pause_info,
        "usage": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "input_percent": usage.get("input_percent", 0),
            "output_percent": usage.get("output_percent", 0),
            "frequency": usage.get("frequency", "daily"),
        },
        "budget_reset": reset_info
    }


def get_agent_triggers(agent_id: str) -> dict:
    """Get triggers configured for an agent with their state.

    Args:
        agent_id: The agent to check

    Returns:
        Dict with triggers list and their state
    """
    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    # Load agent state for interval trigger info
    state_path = AGENTS_DIR / agent_id / "state.json"
    trigger_states = {}
    if state_path.exists():
        with open(state_path) as f:
            state = json.load(f)
            trigger_states = state.get("triggers", {})

    triggers = config.get("triggers", [])
    result = []

    for trigger in triggers:
        if not isinstance(trigger, dict):
            continue

        event = trigger.get("event", "")
        topic_name = trigger.get("topic_name", "")
        trigger_key = f"{event}:{topic_name}"

        trigger_info = {
            "event": event,
            "topic_name": topic_name,
            "instructions": trigger.get("instructions", ""),
        }

        # Add state for interval triggers
        if event.startswith("interval:"):
            state = trigger_states.get(trigger_key, {})
            trigger_info["last_ran"] = state.get("last_ran")
            trigger_info["next_run"] = state.get("next_run")

        result.append(trigger_info)

    return {
        "agent_id": agent_id,
        "triggers": result,
        "count": len(result)
    }


def trigger_agent(agent_id: str, topic_name: str, description: str = None) -> dict:
    """Manually fire a trigger for an agent by creating a topic.

    Args:
        agent_id: The agent to trigger
        topic_name: Name of the topic to create (e.g., "euno:consolidate")
        description: Optional description for the topic

    Returns:
        Dict with topic info
    """
    from src.core.data.topics import create_topic, get_agent_inbox_topic

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    inbox = get_agent_inbox_topic(agent_id)
    parent_id = inbox["id"] if inbox else None

    topic = create_topic(
        name=topic_name,
        description=description or f"Manual trigger: {topic_name}",
        parent_id=parent_id,
        assignee=agent_id,
        tags=["cli:manual", topic_name],
        created_by="cli"
    )

    return {
        "triggered": True,
        "agent_id": agent_id,
        "topic_name": topic_name,
        "topic_id": topic["id"]
    }


def get_agent_token_usage(agent_id: str) -> dict:
    """Get token usage statistics for an agent.

    Args:
        agent_id: The agent to check

    Returns:
        Dict with usage stats, budget info, and reset time
    """
    from src.agent.cognition.metacognition.regulation.tokens import get_token_awareness

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()
    usage = token_awareness.get_agent_usage(agent_id)
    reset_info = token_awareness.get_time_until_reset(agent_id)

    return {
        "agent_id": agent_id,
        "period": usage.get("period"),
        "frequency": usage.get("frequency", "daily"),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "input_budget": usage.get("input_budget", 0),
        "output_budget": usage.get("output_budget", 0),
        "input_percent": usage.get("input_percent", 0),
        "output_percent": usage.get("output_percent", 0),
        "reset_time": reset_info.get("reset_time"),
        "time_until_reset": reset_info.get("time_until")
    }


def reset_agent_token_usage(agent_id: str) -> dict:
    """Reset token usage for an agent to zero.

    This also auto-resumes the agent if it was paused due to budget limits.

    Args:
        agent_id: The agent to reset
    """
    from src.agent.cognition.metacognition.regulation.tokens import get_token_awareness

    config = get_agent_config(agent_id)
    if not config:
        return {"error": f"Agent not found: {agent_id}"}

    token_awareness = get_token_awareness()
    token_awareness.reset_agent_usage(agent_id)

    return {"agent_id": agent_id, "reset": True}
