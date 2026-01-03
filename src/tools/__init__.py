"""
Tool Registry - Central registry for all agent tools.

Tools are registered with decorators and can be looked up by name.
Agents are granted access to specific tools via their config.
"""

from typing import Callable, Dict, List, Any


# Global registry of all tools
_TOOL_REGISTRY: Dict[str, dict] = {}


def tool(name: str, description: str):
    """Decorator to register a tool function."""
    def decorator(func: Callable) -> Callable:
        # Extract parameter info from function annotations
        import inspect
        sig = inspect.signature(func)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = "string"  # default
            param_schema = {}
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                    # OpenAI requires 'items' field for arrays
                    param_schema = {"type": param_type, "items": {"type": "string"}}
                elif param.annotation == dict:
                    param_type = "object"

            if not param_schema:
                param_schema = {"type": param_type}

            properties[param_name] = param_schema

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
            }
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
from . import jobs
from . import agents
from . import assets
from . import user
from . import system
