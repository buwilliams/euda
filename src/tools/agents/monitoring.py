"""
Agent Monitoring - LLM API call statistics and activity tracking.

Provides monitoring data for agents including:
- API call counts by time period (week, today, hour)
- Token usage and costs
- Recent prompts list
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
COSTS_DIR = DATA_DIR / "agents" / "user" / "costs"


def get_agent_monitoring(agent_id: str) -> dict:
    """Get LLM monitoring stats for an agent.

    Reads from the cost tracking logs to aggregate statistics by time period.

    Args:
        agent_id: The agent ID to query

    Returns:
        {
            "stats": {
                "week": {"calls": int, "tokens": int, "cost": float},
                "today": {"calls": int, "tokens": int, "cost": float},
                "hour": {"calls": int, "tokens": int, "cost": float}
            },
            "recent_prompts": [
                {
                    "timestamp": str,
                    "input_tokens": int,
                    "output_tokens": int,
                    "model": str,
                    "duration_ms": int,
                    "cost": float
                },
                ...  # last 15
            ]
        }
    """
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = now.strftime("%Y-%m-%d")

    # Load cost entries for last 7 days
    entries = []
    for i in range(7):
        date = now - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        path = COSTS_DIR / f"{date_str}.jsonl"

        if path.exists():
            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            # Filter by agent (exact match or sub-agent prefix match)
                            entry_agent = entry.get("agent", "")
                            if entry_agent == agent_id or entry_agent.startswith(f"{agent_id}/"):
                                entry["_date"] = date_str  # Add date for filtering
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            except IOError:
                continue

    def compute_stats(filtered_entries: list) -> dict:
        """Compute aggregate stats for a list of entries."""
        return {
            "calls": len(filtered_entries),
            "tokens": sum(
                e.get("input_tokens", 0) + e.get("output_tokens", 0)
                for e in filtered_entries
            ),
            "cost": round(sum(e.get("cost", 0) for e in filtered_entries), 4)
        }

    def parse_timestamp(ts: str) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime."""
        if not ts:
            return None
        try:
            # Handle both with and without microseconds
            if "." in ts:
                return datetime.fromisoformat(ts.replace("Z", ""))
            return datetime.fromisoformat(ts.replace("Z", ""))
        except ValueError:
            return None

    # Filter entries by time period
    today_entries = [e for e in entries if e.get("_date") == today_str]

    hour_entries = []
    for e in today_entries:
        ts = parse_timestamp(e.get("timestamp"))
        if ts and ts >= one_hour_ago:
            hour_entries.append(e)

    # Sort by timestamp descending for recent prompts
    def sort_key(e):
        ts = e.get("timestamp", "")
        return ts if ts else ""

    entries.sort(key=sort_key, reverse=True)

    return {
        "stats": {
            "week": compute_stats(entries),
            "today": compute_stats(today_entries),
            "hour": compute_stats(hour_entries)
        },
        "recent_prompts": [
            {
                "timestamp": e.get("timestamp"),
                "input_tokens": e.get("input_tokens", 0),
                "output_tokens": e.get("output_tokens", 0),
                "model": e.get("model"),
                "duration_ms": e.get("duration_ms"),
                "cost": e.get("cost", 0)
            }
            for e in entries[:15]
        ]
    }
