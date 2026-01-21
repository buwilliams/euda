"""
Patterns command - View and manage discovered patterns and hypotheses.
"""

import json
import sys
from pathlib import Path
from typing import List

from ..formatters import (
    print_header,
    print_error,
    print_success,
    print_key_value,
)


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_patterns(args: List[str], json_mode: bool = False):
    """Show discovered patterns for an agent.

    Usage:
      dev patterns <agent>              Show all patterns
      dev patterns <agent> --temporal   Show only temporal patterns
      dev patterns <agent> --corr       Show only correlations
      dev patterns <agent> --traj       Show only trajectories
      dev patterns <agent> --hyp        Show only hypotheses
      dev patterns <agent> --clear      Clear all patterns (reset)
    """
    if not args:
        print_error("Usage: dev patterns <agent> [--temporal|--corr|--traj|--hyp|--clear]", json_mode)
        sys.exit(1)

    agent_id = args[0]

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    # Parse flags
    show_temporal = "--temporal" in args
    show_corr = "--corr" in args
    show_traj = "--traj" in args
    show_hyp = "--hyp" in args
    clear = "--clear" in args

    # If no specific flag, show all
    show_all = not (show_temporal or show_corr or show_traj or show_hyp or clear)

    # Handle --clear
    if clear:
        _clear_patterns(agent_id, json_mode)
        return

    # Load patterns
    from ...agent.cognition.metacognition.consolidation.patterns import load_patterns
    store = load_patterns(agent_id)

    if json_mode:
        output = {
            "agent_id": agent_id,
            "last_updated": store.last_updated,
        }
        if show_all or show_temporal:
            output["temporal"] = store.temporal
        if show_all or show_corr:
            output["correlations"] = store.correlations
        if show_all or show_traj:
            output["trajectories"] = store.trajectories
        if show_all or show_hyp:
            output["hypotheses"] = store.hypotheses
        print(json.dumps(output, indent=2))
    else:
        print_header(f"Patterns for {agent_id}", json_mode)
        print_key_value("Last Updated", store.last_updated or "(never)", json_mode)
        print()

        if show_all or show_temporal:
            _show_temporal(store.temporal, json_mode)

        if show_all or show_corr:
            _show_correlations(store.correlations, json_mode)

        if show_all or show_traj:
            _show_trajectories(store.trajectories, json_mode)

        if show_all or show_hyp:
            _show_hypotheses(store.hypotheses, json_mode)


def _show_temporal(patterns: list, json_mode: bool):
    """Display temporal patterns."""
    print_header("Temporal Patterns", json_mode)
    if not patterns:
        print("  (none discovered)")
        return

    for p in patterns:
        confidence = p.get("confidence", 0)
        confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        print(f"\n  [{p.get('id', '?')}] {p.get('granularity', '?').upper()}")
        print(f"    {p.get('description', '(no description)')}")
        print(f"    Confidence: {confidence_bar} {confidence:.0%}")
        print(f"    Evidence: {p.get('evidence_count', 0)} observations")
        print(f"    Observed: {p.get('first_observed', '?')} → {p.get('last_observed', '?')}")
        if p.get("time_window"):
            tw = p["time_window"]
            if "start" in tw and "end" in tw:
                print(f"    Time Window: {tw['start']} - {tw['end']}")
            elif "day" in tw:
                print(f"    Day: {tw['day']}")
    print()


def _show_correlations(correlations: list, json_mode: bool):
    """Display correlations."""
    print_header("Correlations", json_mode)
    if not correlations:
        print("  (none discovered)")
        return

    for c in correlations:
        confidence = c.get("confidence", 0)
        confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        items = c.get("items", [])
        item_str = " ↔ ".join(f"{i.get('type', '?')}:{i.get('pattern', '?')}" for i in items)

        print(f"\n  [{c.get('id', '?')}] {c.get('type', 'co_occurrence').upper()}")
        print(f"    {c.get('description', '(no description)')}")
        print(f"    Items: {item_str}")
        print(f"    Confidence: {confidence_bar} {confidence:.0%}")
        if c.get("lag_days", 0) != 0:
            print(f"    Lag: {c['lag_days']} day(s)")
        print(f"    Observed: {c.get('first_observed', '?')} → {c.get('last_observed', '?')}")
    print()


def _show_trajectories(trajectories: list, json_mode: bool):
    """Display trajectories."""
    print_header("Trajectories", json_mode)
    if not trajectories:
        print("  (none discovered)")
        return

    direction_emoji = {
        "clarifying": "🎯",
        "expanding": "📈",
        "resolving": "✅",
        "intensifying": "⚡",
        "diminishing": "📉"
    }

    for t in trajectories:
        confidence = t.get("confidence", 0)
        confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        direction = t.get("direction", "clarifying")
        emoji = direction_emoji.get(direction, "→")

        print(f"\n  [{t.get('id', '?')}] {t.get('type', 'goal_evolution').upper()}")
        print(f"    Subject: {t.get('subject', '(unknown)')}")
        print(f"    Direction: {emoji} {direction}")
        print(f"    Confidence: {confidence_bar} {confidence:.0%}")

        stages = t.get("stages", [])
        if stages:
            print("    Stages:")
            for s in stages:
                print(f"      • {s.get('date', '?')}: {s.get('state', '?')}")
    print()


def _show_hypotheses(hypotheses: list, json_mode: bool):
    """Display hypotheses."""
    print_header("Hypotheses", json_mode)
    if not hypotheses:
        print("  (none pending)")
        return

    for h in hypotheses:
        status = h.get("status", "pending")
        status_emoji = {
            "pending": "⏳",
            "validated": "✅",
            "rejected": "❌",
            "expired": "⏰"
        }.get(status, "?")

        print(f"\n  [{h.get('id', '?')}] {status_emoji} {status.upper()}")
        print(f"    Type: {h.get('type', '?')}")
        print(f"    {h.get('hypothesis', '(no hypothesis)')}")
        print(f"    Evidence: {h.get('evidence_collected', 0)}/{h.get('evidence_required', 3)}")
        print(f"    Created: {h.get('created_at', '?')[:10]}")
        print(f"    Expires: {h.get('expires_at', '?')}")

        evidence = h.get("evidence_details", [])
        if evidence:
            print("    Evidence collected:")
            for e in evidence:
                print(f"      • {e.get('date', '?')}: {e.get('evidence', '?')[:50]}...")
    print()


def _clear_patterns(agent_id: str, json_mode: bool):
    """Clear all patterns for an agent."""
    from ...agent.cognition.metacognition.consolidation.patterns import create_empty_patterns, save_patterns

    store = create_empty_patterns()
    save_patterns(agent_id, store)

    if json_mode:
        print(json.dumps({"agent_id": agent_id, "cleared": True}))
    else:
        print_success(f"Cleared all patterns for {agent_id}", json_mode)
