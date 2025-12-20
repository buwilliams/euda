"""
Introspection Tools - System self-awareness

Tools for analyzing agent identities, capabilities, and tools.
Used by the Introspection Agent to maintain a living document
of what the system can do.
"""

import re
import ast
from datetime import datetime
from pathlib import Path
from typing import Optional


# Base paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SRC_DIR = Path(__file__).parent.parent
IDENTITY_DIR = DATA_DIR / "agents" / "identity"
AGENTS_DIR = SRC_DIR / "agents"
TOOLS_DIR = SRC_DIR / "tools"
INTROSPECTION_DIR = DATA_DIR / "agents" / "introspection"

# Ensure output directory exists
INTROSPECTION_DIR.mkdir(parents=True, exist_ok=True)


def list_agents() -> str:
    """
    List all agents in the system by scanning identity files.

    Returns:
        A formatted list of agents with their persona names.
    """
    agents = []

    # Find all identity files (excluding _core)
    identity_files = list(IDENTITY_DIR.glob("*.identity.md"))

    for identity_file in sorted(identity_files):
        name = identity_file.stem.replace(".identity", "")
        if name.startswith("_"):
            continue  # Skip _core

        # Read first few lines to get the title
        content = identity_file.read_text()
        first_line = content.split("\n")[0]
        title = first_line.replace("#", "").strip()

        agents.append({
            "name": name,
            "title": title,
            "identity_file": str(identity_file)
        })

    result = f"Found {len(agents)} agents:\n\n"
    for agent in agents:
        result += f"- **{agent['name']}**: {agent['title']}\n"

    return result


def get_agent_identity(agent_name: str) -> str:
    """
    Read the full identity file for an agent.

    Args:
        agent_name: The agent name (e.g., 'ingestion', 'summary')

    Returns:
        The full identity content or error message.
    """
    identity_file = IDENTITY_DIR / f"{agent_name}.identity.md"

    if not identity_file.exists():
        return f"Error: No identity file found for agent '{agent_name}'"

    return identity_file.read_text()


def get_core_identity() -> str:
    """
    Read the core identity that all agents inherit.

    Returns:
        The core identity content.
    """
    core_file = IDENTITY_DIR / "_core.identity.md"

    if not core_file.exists():
        return "Error: Core identity file not found"

    return core_file.read_text()


def analyze_agent_code(agent_name: str) -> str:
    """
    Analyze the Python code for an agent to find its tools and capabilities.

    Args:
        agent_name: The agent name (e.g., 'ingestion', 'summary')

    Returns:
        Analysis of the agent's code including tools and handlers.
    """
    agent_file = AGENTS_DIR / f"{agent_name}.py"

    if not agent_file.exists():
        return f"Error: No code file found for agent '{agent_name}'"

    content = agent_file.read_text()

    analysis = f"# Code Analysis: {agent_name}.py\n\n"

    # Find imported tools
    tool_imports = re.findall(r'from \.\.tools\.(\w+) import (.+)', content)
    if tool_imports:
        analysis += "## Tool Imports\n\n"
        for module, imports in tool_imports:
            analysis += f"- **{module}**: {imports}\n"
        analysis += "\n"

    # Find tool definitions (ALL_TOOLS, TOOLS, etc.)
    tool_vars = re.findall(r'(\w+_TOOLS)\s*=\s*(.+?)(?=\n\w|\nclass|\ndef|\Z)', content, re.DOTALL)
    if tool_vars:
        analysis += "## Tool Definitions\n\n"
        for var_name, _ in tool_vars:
            analysis += f"- Uses: `{var_name}`\n"
        analysis += "\n"

    # Find handler definitions
    handler_vars = re.findall(r'(\w+_HANDLERS)\s*=', content)
    if handler_vars:
        analysis += "## Handler Definitions\n\n"
        for var_name in handler_vars:
            analysis += f"- Uses: `{var_name}`\n"
        analysis += "\n"

    # Check for AutonomousAgent subclass
    if "AutonomousAgent" in content:
        analysis += "## Autonomous Behavior\n\n"
        analysis += "This agent runs autonomously in a continuous loop.\n\n"

        # Find check_interval
        interval_match = re.search(r'check_interval\s*[=:]\s*(\d+)', content)
        if interval_match:
            interval = int(interval_match.group(1))
            analysis += f"- Check interval: {interval} seconds\n"

        # Find signals
        signals_match = re.search(r'signals_on_complete\s*=\s*\[([^\]]+)\]', content)
        if signals_match:
            signals = signals_match.group(1)
            analysis += f"- Signals on complete: {signals}\n"

        analysis += "\n"

    # Find the check_work_needed logic
    work_check = re.search(r'def check_work_needed\(self\).*?(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    if work_check:
        analysis += "## Work Trigger\n\n"
        analysis += "```python\n"
        # Extract just the first few lines
        lines = work_check.group().split('\n')[:10]
        analysis += '\n'.join(lines)
        analysis += "\n...\n```\n\n"

    return analysis


def analyze_tools_module(module_name: str) -> str:
    """
    Analyze a tools module to extract tool definitions and descriptions.

    Args:
        module_name: The tool module name (e.g., 'log', 'worker')

    Returns:
        Analysis of the tools defined in the module.
    """
    tools_file = TOOLS_DIR / f"{module_name}.py"

    if not tools_file.exists():
        return f"Error: No tools file found: {module_name}.py"

    content = tools_file.read_text()

    analysis = f"# Tools Module: {module_name}.py\n\n"

    # Find tool definitions (list of dicts with name, description, etc.)
    # Look for patterns like {"name": "...", "description": "..."}
    tool_defs = re.findall(
        r'\{\s*"name":\s*"([^"]+)"[^}]*"description":\s*"([^"]+)"',
        content
    )

    if tool_defs:
        analysis += "## Available Tools\n\n"
        for name, description in tool_defs:
            # Clean up description (remove escaped newlines, etc.)
            description = description.replace("\\n", " ").strip()
            # Truncate if too long
            if len(description) > 150:
                description = description[:150] + "..."
            analysis += f"### {name}\n\n{description}\n\n"

    # Find handler functions
    handlers = re.findall(r'^def (\w+)\(', content, re.MULTILINE)
    if handlers:
        # Filter out private functions
        public_handlers = [h for h in handlers if not h.startswith('_')]
        if public_handlers:
            analysis += "## Handler Functions\n\n"
            for handler in public_handlers:
                analysis += f"- `{handler}()`\n"
            analysis += "\n"

    return analysis


def list_tools_modules() -> str:
    """
    List all tools modules in the system.

    Returns:
        A list of tools modules with brief descriptions.
    """
    modules = []

    for tools_file in sorted(TOOLS_DIR.glob("*.py")):
        if tools_file.name.startswith("__"):
            continue

        name = tools_file.stem

        # Read first docstring
        content = tools_file.read_text()
        doc_match = re.search(r'^"""(.+?)"""', content, re.DOTALL)
        description = ""
        if doc_match:
            # Get first line of docstring
            description = doc_match.group(1).split('\n')[0].strip()

        modules.append({
            "name": name,
            "description": description
        })

    result = f"Found {len(modules)} tools modules:\n\n"
    for module in modules:
        result += f"- **{module['name']}**: {module['description']}\n"

    return result


def get_last_introspection() -> str:
    """
    Read the last generated capabilities summary.

    Returns:
        The previous capabilities document or message if none exists.
    """
    capabilities_file = INTROSPECTION_DIR / "capabilities.md"

    if not capabilities_file.exists():
        return "No previous introspection found. This is the first run."

    return capabilities_file.read_text()


def save_capabilities(content: str) -> str:
    """
    Save the capabilities summary document.

    Args:
        content: The full markdown content to save

    Returns:
        Confirmation message with timestamp.
    """
    capabilities_file = INTROSPECTION_DIR / "capabilities.md"

    # Add generation timestamp if not present
    if "Last updated:" not in content:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = f"*Last updated: {timestamp}*\n\n{content}"

    capabilities_file.write_text(content)

    return f"Capabilities saved to {capabilities_file}"


def get_system_overview() -> str:
    """
    Generate a quick overview of the entire system structure.

    Returns:
        Overview including agent count, tool modules, and key directories.
    """
    # Count agents
    agent_identities = list(IDENTITY_DIR.glob("*.identity.md"))
    agent_count = len([f for f in agent_identities if not f.name.startswith("_")])

    # Count tools modules
    tools_modules = list(TOOLS_DIR.glob("*.py"))
    tools_count = len([f for f in tools_modules if not f.name.startswith("__")])

    # Count agent code files
    agent_files = list(AGENTS_DIR.glob("*.py"))
    agent_code_count = len([f for f in agent_files if not f.name.startswith("__")])

    overview = f"""# System Overview

## Structure
- **Agents**: {agent_count} defined (identity files)
- **Agent Code**: {agent_code_count} implementations
- **Tools Modules**: {tools_count} available

## Key Directories
- `data/agents/identity/` - Agent personas and beliefs
- `src/agents/` - Agent implementations
- `src/tools/` - Tool definitions and handlers
- `data/log/` - Life log entries
- `data/tasks/` - Project and task management
- `data/values/` - Derived user values

## Data Flow
```
Inbox → Ingestion → Log → Summary → Values → World → Attention
                                                    ↓
                                              User (via Interaction)
                                                    ↓
                                              Worker (executes tasks)
```
"""
    return overview


# Tool definitions for the agent
INTROSPECTION_TOOLS = [
    {
        "name": "list_agents",
        "description": "List all agents in the system with their names and titles. Use this first to understand what agents exist.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_agent_identity",
        "description": "Read the full identity file for a specific agent. Shows their purpose, beliefs, and behaviors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "The agent name (e.g., 'ingestion', 'summary', 'worker')"
                }
            },
            "required": ["agent_name"]
        }
    },
    {
        "name": "get_core_identity",
        "description": "Read the core identity that all agents inherit. Shows shared purpose, beliefs, and boundaries.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "analyze_agent_code",
        "description": "Analyze an agent's Python code to find its tools, triggers, and autonomous behavior.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "The agent name (e.g., 'ingestion', 'summary', 'worker')"
                }
            },
            "required": ["agent_name"]
        }
    },
    {
        "name": "list_tools_modules",
        "description": "List all tools modules in the system with brief descriptions.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "analyze_tools_module",
        "description": "Analyze a specific tools module to see what capabilities it provides.",
        "input_schema": {
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "The module name (e.g., 'log', 'worker', 'project')"
                }
            },
            "required": ["module_name"]
        }
    },
    {
        "name": "get_system_overview",
        "description": "Get a quick overview of the entire system structure including counts and data flow.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_last_introspection",
        "description": "Read the last generated capabilities summary to understand what's already documented.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "save_capabilities",
        "description": "Save the capabilities summary document. Call this after generating a complete analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The full markdown content of the capabilities document"
                }
            },
            "required": ["content"]
        }
    }
]

# Handler mapping
INTROSPECTION_HANDLERS = {
    "list_agents": list_agents,
    "get_agent_identity": get_agent_identity,
    "get_core_identity": get_core_identity,
    "analyze_agent_code": analyze_agent_code,
    "list_tools_modules": list_tools_modules,
    "analyze_tools_module": analyze_tools_module,
    "get_system_overview": get_system_overview,
    "get_last_introspection": get_last_introspection,
    "save_capabilities": save_capabilities,
}
