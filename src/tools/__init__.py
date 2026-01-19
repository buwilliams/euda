"""
Tool Registry - Central registry for all agent tools.

Tools are registered with decorators and can be looked up by name.
Agents are granted access to specific tools via their config.

Tools are organized by type:
- data: Jobs, assets, user identity, memory
- agents: Agent management and introspection
- system: Config, dates, notifications, work control
- integration: External knowledge and documentation
"""

from typing import Callable, Dict, List, Any


# Tool types
TOOL_TYPES = {"data", "agents", "system", "integration"}

# Global registry of all tools
_TOOL_REGISTRY: Dict[str, dict] = {}


def tool(name: str, description: str, input_schema: dict = None, tool_type: str = None):
    """Decorator to register a tool function.

    Args:
        name: Tool name
        description: Tool description (should include when to use)
        input_schema: Optional explicit schema (overrides auto-detection).
                     Use this for complex types like arrays of objects.
        tool_type: Category - one of: data, agents, system, integration
    """
    def decorator(func: Callable) -> Callable:
        # Validate tool_type if provided
        if tool_type and tool_type not in TOOL_TYPES:
            raise ValueError(f"Invalid tool_type '{tool_type}'. Must be one of: {TOOL_TYPES}")

        # If explicit schema provided, use it directly
        if input_schema is not None:
            _TOOL_REGISTRY[name] = {
                "name": name,
                "description": description,
                "function": func,
                "schema": input_schema,
                "type": tool_type
            }
            return func

        # Otherwise auto-detect from annotations
        import inspect
        sig = inspect.signature(func)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = "string"  # default
            param_schema = None
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                    # OpenAI requires items for array types
                    param_schema = {"type": "array", "items": {"type": "string"}}
                elif param.annotation == dict:
                    param_type = "object"

            properties[param_name] = param_schema if param_schema else {"type": param_type}

            # Check if parameter has a default
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        _TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "function": func,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": required
            },
            "type": tool_type
        }
        return func
    return decorator


def get_all_tools() -> List[dict]:
    """Get all registered tools as Claude tool definitions."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["schema"]
        }
        for t in _TOOL_REGISTRY.values()
    ]


def get_available_tools() -> Dict[str, dict]:
    """Get all registered tools as a dict keyed by tool name.

    Returns:
        Dict mapping tool name to tool info (name, description, schema)
    """
    return {
        name: {
            "name": t["name"],
            "description": t["description"],
            "schema": t["schema"]
        }
        for name, t in _TOOL_REGISTRY.items()
    }


def get_tools_for_agent(tool_names: List[str]) -> List[dict]:
    """Get tool definitions for specific tool names."""
    tools = []
    for name in tool_names:
        if name in _TOOL_REGISTRY:
            t = _TOOL_REGISTRY[name]
            tools.append({
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["schema"]
            })
    return tools


def get_tools_by_type(tool_type: str) -> List[dict]:
    """Get all tools of a specific type."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["schema"]
        }
        for t in _TOOL_REGISTRY.values()
        if t.get("type") == tool_type
    ]


def get_tools_grouped_by_type(tool_names: List[str]) -> Dict[str, List[dict]]:
    """Get tools grouped by type for system prompt building.

    Returns dict like:
    {
        "data": [{"name": "list_jobs", "description": "..."}],
        "agents": [...],
        "system": [...],
        "integration": [...]
    }
    """
    grouped = {t: [] for t in TOOL_TYPES}
    for name in tool_names:
        if name in _TOOL_REGISTRY:
            t = _TOOL_REGISTRY[name]
            tool_type = t.get("type", "system")  # default to system if untyped
            grouped[tool_type].append({
                "name": t["name"],
                "description": t["description"]
            })
    return grouped


def execute_tool(name: str, inputs: dict) -> Any:
    """Execute a tool by name with given inputs."""
    if name not in _TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}

    try:
        func = _TOOL_REGISTRY[name]["function"]
        return func(**inputs)
    except Exception as e:
        return {"error": str(e)}


# Import all tool modules to register them
from .data import jobs, assets, identity, memory
from .agents import agents
from .system import system, dates, notifications
from .integration import knowledge, mastodon, speech
