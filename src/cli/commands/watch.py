"""
Watch command - Live stream of system events.
"""

import json
import sys
from queue import Empty
from typing import List

from ..formatters import format_human, format_json, COLORS


def cmd_watch(args: List[str], json_mode: bool = False):
    """Watch all system events in real-time.

    Usage:
      dev watch                   Stream all events
      dev watch --agent <id>      Filter to specific agent
      dev watch --event <type>    Filter to specific event type
    """
    # Parse filters
    agent_filter = None
    event_filter = None

    i = 0
    while i < len(args):
        if args[i] == "--agent" and i + 1 < len(args):
            agent_filter = args[i + 1]
            i += 2
        elif args[i] == "--event" and i + 1 < len(args):
            event_filter = args[i + 1]
            i += 2
        else:
            i += 1

    from ...web.events import subscribe_dev, unsubscribe_dev

    # Subscribe to events
    q = subscribe_dev()

    if not json_mode:
        dim = COLORS["dim"]
        reset = COLORS["reset"]
        print(f"\n{dim}Watching system events... (Ctrl+C to stop){reset}")
        if agent_filter:
            print(f"{dim}Agent filter: {agent_filter}{reset}")
        if event_filter:
            print(f"{dim}Event filter: {event_filter}{reset}")
        print()

    try:
        while True:
            try:
                entry = q.get(timeout=1.0)

                # Apply filters
                source = entry.get("source", "system")
                event = entry.get("event", "unknown")

                if agent_filter and source != agent_filter:
                    continue

                if event_filter and event_filter not in event:
                    continue

                # Format and print
                data = {
                    "agent_id": source,
                    "timestamp": entry.get("timestamp"),
                    **entry.get("data", {})
                }

                if json_mode:
                    print(format_json(event, data), flush=True)
                else:
                    print(format_human(event, data), flush=True)

            except Empty:
                # No events, just keep waiting
                continue

    except KeyboardInterrupt:
        if not json_mode:
            print("\nStopped watching")

    finally:
        unsubscribe_dev(q)
