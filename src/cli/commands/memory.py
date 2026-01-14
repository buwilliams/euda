"""
Memory command - Inspect and manipulate agent memory.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from ..formatters import (
    print_header,
    print_memory_item,
    print_error,
    print_success,
    print_key_value,
)


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_memory(args: List[str], json_mode: bool = False):
    """Show or manipulate agent memory.

    Usage:
      dev memory <agent>            Show all memory
      dev memory <agent> --short    Show only short-term
      dev memory <agent> --long     Show only long-term (last 7 days)
      dev memory <agent> --add <type> <description>  Add entry
      dev memory <agent> --graduate <id>  Graduate to long-term
    """
    if not args:
        print_error("Usage: dev memory <agent> [--short|--long|--add|--graduate]", json_mode)
        sys.exit(1)

    agent_id = args[0]

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    # Parse flags
    show_short = "--short" in args or not any(a.startswith("--") for a in args[1:])
    show_long = "--long" in args or not any(a.startswith("--") for a in args[1:])

    # Handle --add
    if "--add" in args:
        add_idx = args.index("--add")
        if len(args) < add_idx + 3:
            print_error("Usage: dev memory <agent> --add <type> <description>", json_mode)
            sys.exit(1)
        mem_type = args[add_idx + 1]
        description = " ".join(args[add_idx + 2:])
        _add_memory(agent_id, mem_type, description, json_mode)
        return

    # Handle --graduate
    if "--graduate" in args:
        grad_idx = args.index("--graduate")
        if len(args) < grad_idx + 2:
            print_error("Usage: dev memory <agent> --graduate <id>", json_mode)
            sys.exit(1)
        mem_id = args[grad_idx + 1]
        _graduate_memory(agent_id, mem_id, json_mode)
        return

    # Show memory
    if show_short:
        _show_short_term(agent_id, json_mode)

    if show_long:
        _show_long_term(agent_id, json_mode)


def _show_short_term(agent_id: str, json_mode: bool):
    """Show short-term memory."""
    memory_path = AGENTS_DIR / agent_id / "memory" / "short-term.jsonl"

    if not memory_path.exists():
        if json_mode:
            print(json.dumps({"short_term": []}))
        else:
            print_header("Short-term Memory", json_mode)
            print("  (empty)")
        return

    entries = []
    with open(memory_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if json_mode:
        print(json.dumps({"short_term": entries}))
    else:
        print_header("Short-term Memory", json_mode)
        if not entries:
            print("  (empty)")
        else:
            # Group by type
            by_type = {}
            for entry in entries:
                t = entry.get("type", "unknown")
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(entry)

            for mem_type, items in sorted(by_type.items()):
                print(f"\n  {mem_type.upper()} ({len(items)})")
                for item in items:
                    print_memory_item(item, json_mode)


def _show_long_term(agent_id: str, json_mode: bool, days: int = 7):
    """Show recent long-term memory."""
    long_term_dir = AGENTS_DIR / agent_id / "memory" / "long-term"

    entries = []
    today = datetime.now()

    for i in range(days):
        date = today - timedelta(days=i)
        year = date.strftime("%Y")
        date_str = date.strftime("%Y-%m-%d")

        # Try year-based path first, then legacy flat path
        year_path = long_term_dir / year / f"{date_str}.md"
        legacy_path = long_term_dir / f"{date_str}.md"

        memory_path = None
        if year_path.exists():
            memory_path = year_path
        elif legacy_path.exists():
            memory_path = legacy_path

        if memory_path:
            content = memory_path.read_text()
            entries.append({
                "date": date_str,
                "content": content
            })

    if json_mode:
        print(json.dumps({"long_term": entries}))
    else:
        print_header(f"Long-term Memory (last {days} days)", json_mode)
        if not entries:
            print("  (empty)")
        else:
            for entry in entries:
                print(f"\n  --- {entry['date']} ---")
                # Show first few lines of content
                lines = entry["content"].split("\n")[:10]
                for line in lines:
                    print(f"  {line}")
                if len(entry["content"].split("\n")) > 10:
                    print("  ...")


def _add_memory(agent_id: str, mem_type: str, description: str, json_mode: bool):
    """Add a memory entry manually."""
    from ...tools.data.memory import add_memory, VALID_TYPES

    if mem_type not in VALID_TYPES:
        print_error(f"Invalid memory type: {mem_type}. Valid types: {', '.join(VALID_TYPES)}", json_mode)
        sys.exit(1)

    result = add_memory(
        description=description,
        mem_type=mem_type,
        date_expected=None,
        agent_id=agent_id
    )

    if json_mode:
        print(json.dumps(result))
    else:
        print_success(f"Added memory: {result.get('id')}", json_mode)
        print_memory_item(result, json_mode)


def _graduate_memory(agent_id: str, mem_id: str, json_mode: bool):
    """Graduate a memory to long-term."""
    from ...tools.data.memory import graduate_memory

    result = graduate_memory(
        memory_id=mem_id,
        reason="Manual graduation via dev CLI",
        agent_id=agent_id
    )

    if "error" in result:
        print_error(result["error"], json_mode)
        sys.exit(1)

    if json_mode:
        print(json.dumps(result))
    else:
        print_success(f"Graduated memory: {mem_id}", json_mode)
