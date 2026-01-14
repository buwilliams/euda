"""
Profile command - Inspect agent profiles.
"""

import json
import sys
from pathlib import Path
from typing import List

from ..formatters import print_header, print_error


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_profile(args: List[str], json_mode: bool = False):
    """Show agent profile.

    Usage:
      dev profile <agent>           Show current profile
      dev profile <agent> --history Show historical snapshots
    """
    if not args:
        print_error("Usage: dev profile <agent> [--history]", json_mode)
        sys.exit(1)

    agent_id = args[0]
    show_history = "--history" in args

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    profile_path = agent_dir / "profile.md"

    if not profile_path.exists():
        print_error(f"Profile not found for agent: {agent_id}", json_mode)
        sys.exit(1)

    profile_content = profile_path.read_text()

    if show_history:
        _show_profile_history(agent_id, profile_content, json_mode)
    else:
        _show_profile(agent_id, profile_content, json_mode)


def _show_profile(agent_id: str, content: str, json_mode: bool):
    """Show current profile."""
    if json_mode:
        print(json.dumps({
            "agent_id": agent_id,
            "profile": content
        }))
    else:
        print_header(f"Profile: {agent_id}", json_mode)
        print()
        print(content)


def _show_profile_history(agent_id: str, current_content: str, json_mode: bool):
    """Show profile history with historical snapshots."""
    agent_dir = AGENTS_DIR / agent_id

    # Find historical profile files (profile.YYYY.md)
    historical = []
    for f in agent_dir.glob("profile.*.md"):
        year = f.stem.split(".")[-1]
        if year.isdigit() and len(year) == 4:
            historical.append({
                "year": year,
                "content": f.read_text()
            })

    historical.sort(key=lambda x: x["year"], reverse=True)

    if json_mode:
        print(json.dumps({
            "agent_id": agent_id,
            "current": current_content,
            "historical": historical
        }))
    else:
        print_header(f"Profile History: {agent_id}", json_mode)

        if not historical:
            print("\n  No historical snapshots found.")
            print("  (Snapshots are created at year boundaries during reflection)")
        else:
            print(f"\n  Found {len(historical)} historical snapshot(s):")
            for h in historical:
                print(f"\n  --- {h['year']} ---")
                # Show first few lines
                lines = h["content"].split("\n")[:5]
                for line in lines:
                    print(f"  {line}")
                if len(h["content"].split("\n")) > 5:
                    print("  ...")

        print("\n  --- Current ---")
        lines = current_content.split("\n")[:10]
        for line in lines:
            print(f"  {line}")
        if len(current_content.split("\n")) > 10:
            print("  ...")
