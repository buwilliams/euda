"""
Trace command - Show execution trace of a topic.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from ..formatters import print_header, print_error, COLORS


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_trace(args: List[str], json_mode: bool = False):
    """Show execution trace of a topic.

    Usage:
      dev trace <topic_id>
    """
    if not args:
        print_error("Usage: dev trace <topic_id>", json_mode)
        sys.exit(1)

    topic_id = args[0]

    from src.core.data.topics import get_topic

    topic = get_topic(topic_id)
    if not topic:
        print_error(f"Topic not found: {topic_id}", json_mode)
        sys.exit(1)

    # Collect trace events from multiple sources
    events = []

    # 1. Topic logs from the database
    topic_logs = topic.get("log", [])
    for log in topic_logs:
        events.append({
            "timestamp": log.get("timestamp"),
            "source": log.get("agent", "system"),
            "event": "topic_log",
            "action": log.get("action"),
            "data": {}
        })

    # 2. Agent logs (find relevant entries)
    assignees = topic.get("assignees", [])
    for agent_id in assignees:
        agent_events = _find_agent_events_for_topic(agent_id, topic_id)
        events.extend(agent_events)

    # Sort by timestamp
    events.sort(key=lambda e: e.get("timestamp", ""))

    if json_mode:
        print(json.dumps({
            "topic_id": topic_id,
            "topic_name": topic.get("name"),
            "status": topic.get("status"),
            "events": events
        }))
    else:
        _print_trace(topic, events)


def _find_agent_events_for_topic(agent_id: str, topic_id: str) -> List[dict]:
    """Find events in agent logs related to a topic."""
    events = []

    agent_logs_dir = AGENTS_DIR / agent_id / "logs"
    if not agent_logs_dir.exists():
        return events

    # Look at recent log files
    log_files = sorted(agent_logs_dir.glob("*.jsonl"), reverse=True)[:7]  # Last 7 days

    for log_file in log_files:
        try:
            with open(log_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        details = entry.get("details", {})

                        # Check if this entry is related to the topic
                        if topic_id in str(details) or topic_id in str(entry):
                            events.append({
                                "timestamp": entry.get("timestamp"),
                                "source": agent_id,
                                "event": entry.get("event"),
                                "data": details
                            })
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

    return events


def _print_trace(topic: dict, events: List[dict]):
    """Print trace in human-readable format."""
    dim = COLORS["dim"]
    cyan = COLORS["cyan"]
    yellow = COLORS["yellow"]
    green = COLORS["green"]
    reset = COLORS["reset"]

    print_header(f"Trace: {topic.get('name', topic['id'])}", False)
    print(f"\n{dim}Topic ID:{reset} {topic['id']}")
    print(f"{dim}Status:{reset} {topic.get('status')}")
    print(f"{dim}Created:{reset} {topic.get('created_at')}")

    assignees = topic.get("assignees", [])
    if assignees:
        print(f"{dim}Assignees:{reset} {', '.join(assignees)}")

    if not events:
        print(f"\n{dim}No execution events found{reset}")
        return

    print(f"\n{dim}Timeline ({len(events)} events):{reset}\n")

    for event in events:
        timestamp = event.get("timestamp", "")
        if timestamp:
            # Format timestamp
            ts = timestamp[11:19] if "T" in timestamp else timestamp[:8]
        else:
            ts = "??:??:??"

        source = event.get("source", "system")
        event_type = event.get("event", "unknown")
        data = event.get("data", {})
        action = event.get("action")

        # Color code by event type
        if event_type == "topic_log":
            color = cyan
            detail = action or ""
        elif "tool" in event_type:
            color = yellow
            tool = data.get("tool", data.get("name", ""))
            detail = f"{tool}" if tool else ""
        elif "llm" in event_type:
            color = green
            stop = data.get("stop_reason", "")
            detail = f"[{stop}]" if stop else ""
        elif "work" in event_type:
            color = cyan
            detail = data.get("reason", "")
        else:
            color = dim
            detail = ""

        print(f"  {dim}{ts}{reset} [{source}] {color}{event_type}{reset} {detail}")

        # Show additional details for some events
        if event_type == "tool_call" and data.get("input"):
            input_str = json.dumps(data["input"])
            if len(input_str) > 60:
                input_str = input_str[:57] + "..."
            print(f"          {dim}{input_str}{reset}")
