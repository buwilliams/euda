"""
Output formatters for dev CLI.

Provides human-readable (colored) and JSON output modes.
"""

import json
import sys
from datetime import datetime
from typing import Any, Optional


# ANSI color codes (disabled if not a TTY)
def _supports_color() -> bool:
    """Check if terminal supports color output."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


COLORS_ENABLED = _supports_color()

COLORS = {
    "reset": "\033[0m" if COLORS_ENABLED else "",
    "dim": "\033[2m" if COLORS_ENABLED else "",
    "bold": "\033[1m" if COLORS_ENABLED else "",
    "cyan": "\033[36m" if COLORS_ENABLED else "",
    "yellow": "\033[33m" if COLORS_ENABLED else "",
    "green": "\033[32m" if COLORS_ENABLED else "",
    "red": "\033[31m" if COLORS_ENABLED else "",
    "blue": "\033[34m" if COLORS_ENABLED else "",
    "magenta": "\033[35m" if COLORS_ENABLED else "",
}

# Event type to color mapping
EVENT_COLORS = {
    # Chat events
    "chat_start": "cyan",
    "chat_end": "cyan",
    # LLM events
    "llm_response": "blue",
    "llm_request": "blue",
    # Tool events
    "tool_call": "yellow",
    "tool_result": "green",
    "tool_error": "red",
    # Work cycle events
    "work_cycle_start": "magenta",
    "work_cycle_end": "magenta",
    "work_iteration": "dim",
    # Reflection events
    "append_start": "dim",
    "append_complete": "cyan",
    "append_llm_response": "dim",
    "consolidate_start": "magenta",
    "consolidate_complete": "magenta",
    "consolidate_llm_response": "dim",
    # Memory events
    "memory_add": "green",
    "memory_graduate": "cyan",
    # Error events
    "error": "red",
}


def format_human(event: str, data: dict, show_timestamp: bool = True) -> str:
    """Format event for human-readable output.

    Args:
        event: Event type name
        data: Event data dictionary
        show_timestamp: Whether to include timestamp

    Returns:
        Formatted string for terminal output
    """
    color_name = EVENT_COLORS.get(event, "reset")
    color = COLORS.get(color_name, "")
    reset = COLORS["reset"]
    dim = COLORS["dim"]
    bold = COLORS["bold"]
    green = COLORS["green"]
    red = COLORS["red"]

    # Timestamp
    ts = ""
    if show_timestamp:
        timestamp = data.get("timestamp", datetime.now().isoformat())
        # Extract time portion (HH:MM:SS)
        if "T" in timestamp:
            time_part = timestamp.split("T")[1][:8]
        else:
            time_part = timestamp[:8]
        ts = f"{dim}{time_part}{reset} "

    # Agent context
    agent_id = data.get("agent_id", "system")
    agent = f"{dim}[{agent_id}]{reset} "

    # Event-specific formatting
    if event == "chat_start":
        msg_len = data.get("message_length", 0)
        return f"{ts}{agent}{color}Chat started{reset} ({msg_len} chars)"

    elif event == "chat_end":
        resp_len = data.get("response_length", 0)
        return f"{ts}{agent}{color}Chat ended{reset} ({resp_len} chars)"

    elif event == "llm_response":
        usage = data.get("usage", {})
        input_tokens = usage.get("input", usage.get("input_tokens", 0))
        output_tokens = usage.get("output", usage.get("output_tokens", 0))
        tokens = f"in:{input_tokens} out:{output_tokens}"
        stop = data.get("stop_reason", "unknown")
        return f"{ts}{agent}{color}LLM response{reset} [{stop}] {dim}{tokens}{reset}"

    elif event == "tool_call":
        tool = data.get("tool", data.get("name", "unknown"))
        tool_input = data.get("input", {})
        # Truncate input for display
        input_str = json.dumps(tool_input) if tool_input else ""
        if len(input_str) > 60:
            input_str = input_str[:57] + "..."
        return f"{ts}{agent}{color}Calling{reset} {bold}{tool}{reset} {dim}{input_str}{reset}"

    elif event == "tool_result":
        tool = data.get("tool", data.get("name", "unknown"))
        success = data.get("success", True)
        status = f"{green}OK{reset}" if success else f"{red}FAIL{reset}"
        result = data.get("result", "")
        # Truncate result for display
        if isinstance(result, dict):
            result_str = json.dumps(result)
        else:
            result_str = str(result) if result else ""
        if len(result_str) > 60:
            result_str = result_str[:57] + "..."
        return f"{ts}{agent}{color}Result{reset} {tool} {status} {dim}{result_str}{reset}"

    elif event == "tool_error":
        tool = data.get("tool", "unknown")
        error = data.get("error", "unknown error")
        return f"{ts}{agent}{red}Error{reset} {tool}: {error}"

    elif event == "work_cycle_start":
        trigger = data.get("trigger", "")
        return f"{ts}{agent}{color}Work cycle started{reset} {dim}{trigger}{reset}"

    elif event == "work_cycle_end":
        reason = data.get("reason", "unknown")
        iterations = data.get("iterations", 0)
        return f"{ts}{agent}{color}Work cycle ended{reset} ({reason}, {iterations} iterations)"

    elif event == "work_iteration":
        iteration = data.get("iteration", 0)
        return f"{ts}{agent}{dim}Iteration {iteration}{reset}"

    elif event == "append_start":
        return f"{ts}{agent}{dim}Reflection append started{reset}"

    elif event == "append_complete":
        items = data.get("items_added", 0)
        return f"{ts}{agent}{color}Reflection append{reset} {items} items extracted"

    elif event == "append_llm_response":
        items = data.get("items_extracted", 0)
        return f"{ts}{agent}{dim}Append LLM response{reset} {items} items found"

    elif event == "consolidate_start":
        return f"{ts}{agent}{color}Reflection consolidate started{reset}"

    elif event == "consolidate_complete":
        graduated = data.get("items_graduated", 0)
        identity = " + identity updated" if data.get("identity_updated") else ""
        long_term = " + long-term entry" if data.get("long_term_entry") else ""
        return f"{ts}{agent}{color}Reflection consolidate{reset} {graduated} graduated{identity}{long_term}"

    elif event == "memory_add":
        mem_type = data.get("type", "unknown")
        desc = data.get("description", "")[:50]
        return f"{ts}{agent}{color}Memory added{reset} [{mem_type}] {desc}"

    elif event == "memory_graduate":
        mem_id = data.get("id", "unknown")
        return f"{ts}{agent}{color}Memory graduated{reset} {mem_id}"

    elif event == "error":
        error = data.get("error", data.get("message", "unknown error"))
        return f"{ts}{agent}{red}Error:{reset} {error}"

    # Default formatting
    else:
        # Show event name and any interesting data
        details = {k: v for k, v in data.items()
                   if k not in ("agent_id", "timestamp")}
        details_str = ""
        if details:
            details_str = " " + json.dumps(details)
            if len(details_str) > 80:
                details_str = details_str[:77] + "..."
        return f"{ts}{agent}{color}{event}{reset}{details_str}"


def format_json(event: str, data: dict) -> str:
    """Format event as JSON line.

    Args:
        event: Event type name
        data: Event data dictionary

    Returns:
        JSON string (single line)
    """
    output = {
        "event": event,
        "timestamp": data.get("timestamp", datetime.now().isoformat()),
        **{k: v for k, v in data.items() if k != "timestamp"}
    }
    return json.dumps(output)


def print_event(event: str, data: dict, json_mode: bool = False):
    """Print an event to stdout.

    Args:
        event: Event type name
        data: Event data dictionary
        json_mode: If True, output JSON; otherwise human-readable
    """
    if json_mode:
        print(format_json(event, data), flush=True)
    else:
        print(format_human(event, data), flush=True)


def print_header(title: str, json_mode: bool = False):
    """Print a section header.

    Args:
        title: Header title
        json_mode: If True, skip header (JSON mode is line-based)
    """
    if json_mode:
        return
    bold = COLORS["bold"]
    reset = COLORS["reset"]
    print(f"\n{bold}{title}{reset}")
    print("-" * len(title))


def print_key_value(key: str, value: Any, json_mode: bool = False, indent: int = 0):
    """Print a key-value pair.

    Args:
        key: Key name
        value: Value to display
        json_mode: If True, output JSON
        indent: Number of spaces to indent
    """
    if json_mode:
        print(json.dumps({key: value}), flush=True)
    else:
        dim = COLORS["dim"]
        reset = COLORS["reset"]
        prefix = " " * indent
        print(f"{prefix}{dim}{key}:{reset} {value}")


def print_memory_item(item: dict, json_mode: bool = False):
    """Print a memory item.

    Args:
        item: Memory item dictionary
        json_mode: If True, output JSON
    """
    if json_mode:
        print(json.dumps(item), flush=True)
    else:
        dim = COLORS["dim"]
        cyan = COLORS["cyan"]
        reset = COLORS["reset"]

        mem_id = item.get("id", "?")
        mem_type = item.get("type", "?")
        desc = item.get("short_description", "")
        date_mentioned = item.get("date_mentioned", "?")
        date_expected = item.get("date_expected")

        expected_str = f" (expected: {date_expected})" if date_expected else ""
        print(f"  {dim}{mem_id}{reset} [{cyan}{mem_type}{reset}] {desc}")
        print(f"    {dim}mentioned: {date_mentioned}{expected_str}{reset}")


def print_error(message: str, json_mode: bool = False):
    """Print an error message.

    Args:
        message: Error message
        json_mode: If True, output JSON
    """
    if json_mode:
        print(json.dumps({"error": message}), flush=True)
    else:
        red = COLORS["red"]
        reset = COLORS["reset"]
        print(f"{red}Error:{reset} {message}", file=sys.stderr)


def print_success(message: str, json_mode: bool = False):
    """Print a success message.

    Args:
        message: Success message
        json_mode: If True, output JSON
    """
    if json_mode:
        print(json.dumps({"success": message}), flush=True)
    else:
        green = COLORS["green"]
        reset = COLORS["reset"]
        print(f"{green}{message}{reset}")


def print_info(message: str, json_mode: bool = False):
    """Print an info message.

    Args:
        message: Info message
        json_mode: If True, output JSON
    """
    if json_mode:
        print(json.dumps({"info": message}), flush=True)
    else:
        cyan = COLORS["cyan"]
        reset = COLORS["reset"]
        print(f"{cyan}{message}{reset}")
