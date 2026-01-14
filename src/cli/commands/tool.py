"""
Tool command - List and execute tools directly.
"""

import json
import sys
from typing import List

from ..formatters import print_header, print_error, print_success, COLORS


def cmd_tools(args: List[str], json_mode: bool = False):
    """List all available tools.

    Usage:
      dev tools                 List all tools
      dev tools <pattern>       Filter tools by name
    """
    from ...tools import get_all_tools

    tools = get_all_tools()
    pattern = args[0].lower() if args else None

    if pattern:
        tools = [t for t in tools if pattern in t["name"].lower()]

    if json_mode:
        print(json.dumps({"tools": tools}))
    else:
        print_header("Available Tools", json_mode)

        # Group by type
        by_type = {}
        for tool in tools:
            t = tool.get("tool_type", "unknown")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(tool)

        type_labels = {
            "data": "Data Tools",
            "agents": "Agent Tools",
            "system": "System Tools",
            "integration": "Integration Tools",
            "unknown": "Other Tools"
        }

        dim = COLORS["dim"]
        cyan = COLORS["cyan"]
        reset = COLORS["reset"]

        for tool_type in ["data", "agents", "system", "integration", "unknown"]:
            type_tools = by_type.get(tool_type, [])
            if type_tools:
                print(f"\n{type_labels.get(tool_type, tool_type)}")
                for tool in sorted(type_tools, key=lambda x: x["name"]):
                    name = tool["name"]
                    desc = tool.get("description", "")
                    # Show first line of description
                    desc_line = desc.split("\n")[0][:60]
                    print(f"  {cyan}{name}{reset}  {dim}{desc_line}{reset}")


def cmd_tool(args: List[str], json_mode: bool = False):
    """Execute a tool directly.

    Usage:
      dev tool <name>                Execute tool with no input
      dev tool <name> <json_input>   Execute tool with JSON input
    """
    if not args:
        print_error("Usage: dev tool <name> [json_input]", json_mode)
        sys.exit(1)

    tool_name = args[0]
    tool_input = {}

    # Parse JSON input if provided
    if len(args) > 1:
        json_str = " ".join(args[1:])
        try:
            tool_input = json.loads(json_str)
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON input: {e}", json_mode)
            sys.exit(1)

    # Execute tool
    from ...tools import execute_tool, get_all_tools

    # Verify tool exists
    all_tools = get_all_tools()
    tool_info = next((t for t in all_tools if t["name"] == tool_name), None)
    if not tool_info:
        print_error(f"Tool not found: {tool_name}", json_mode)
        # Suggest similar tools
        similar = [t["name"] for t in all_tools if tool_name.lower() in t["name"].lower()]
        if similar:
            print(f"Did you mean: {', '.join(similar[:5])}")
        sys.exit(1)

    try:
        result = execute_tool(tool_name, tool_input)

        if json_mode:
            print(json.dumps({
                "tool": tool_name,
                "input": tool_input,
                "result": result
            }))
        else:
            print_header(f"Tool: {tool_name}", json_mode)
            print(f"\nInput: {json.dumps(tool_input, indent=2)}")
            print(f"\nResult:")
            if isinstance(result, dict):
                print(json.dumps(result, indent=2))
            else:
                print(result)

    except Exception as e:
        print_error(f"Tool execution failed: {e}", json_mode)
        sys.exit(1)
