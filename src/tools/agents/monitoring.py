"""
Agent Monitoring - LLM API call statistics and activity tracking.

Provides monitoring data for agents including:
- API call counts by time period (week, today, hour)
- Token usage and costs
- Recent prompts list with full content (paginated)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
TOKEN_USAGE_DIR = DATA_DIR / "system" / "token_usage"
PROMPTS_DIR = DATA_DIR / "system" / "logs" / "prompts"


def get_agent_monitoring(agent_id: str, offset: int = 0, limit: int = 20) -> dict:
    """Get LLM monitoring stats for an agent with pagination.

    Reads from cost tracking logs for stats and prompt logs for full content.

    Args:
        agent_id: The agent ID to query
        offset: Number of entries to skip (for pagination)
        limit: Maximum number of entries to return (default 20)

    Returns:
        {
            "stats": {
                "week": {"calls": int, "tokens": int, "cost": float},
                "today": {"calls": int, "tokens": int, "cost": float},
                "hour": {"calls": int, "tokens": int, "cost": float}
            },
            "prompts": [
                {
                    "timestamp": str,
                    "input_tokens": int,
                    "output_tokens": int,
                    "model": str,
                    "duration_ms": int,
                    "cost": float,
                    "system": str (if available),
                    "messages": list (if available),
                    "tools": list (if available)
                },
                ...
            ],
            "pagination": {
                "offset": int,
                "limit": int,
                "total": int,
                "has_more": bool
            }
        }
    """
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = now.strftime("%Y-%m-%d")
    week_ago = now - timedelta(days=7)

    # Load cost entries from monthly token usage files
    # We need to check current month and possibly previous month for 7-day window
    entries = []
    months_to_check = {now.strftime("%Y-%m")}
    if week_ago.month != now.month:
        months_to_check.add(week_ago.strftime("%Y-%m"))

    for month_str in months_to_check:
        path = TOKEN_USAGE_DIR / f"{month_str}.jsonl"

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
                                # Parse timestamp to check if within last 7 days
                                ts_str = entry.get("timestamp", "")
                                if ts_str:
                                    try:
                                        ts = datetime.fromisoformat(ts_str.replace("Z", ""))
                                        if ts >= week_ago:
                                            entry["_date"] = ts.strftime("%Y-%m-%d")
                                            entries.append(entry)
                                    except ValueError:
                                        continue
                        except json.JSONDecodeError:
                            continue
            except IOError:
                continue

    # Sort by timestamp descending for pagination
    def sort_key(e):
        ts = e.get("timestamp", "")
        return ts if ts else ""

    entries.sort(key=sort_key, reverse=True)

    # Get total count before pagination
    total_count = len(entries)

    # Apply pagination
    paginated_entries = entries[offset:offset + limit]

    # Collect timestamps from paginated entries to load only needed prompt content
    needed_timestamps = {e.get("timestamp", "") for e in paginated_entries}
    needed_timestamps.discard("")

    # Load prompt logs only for entries we need (based on their dates)
    prompt_content = {}
    if needed_timestamps:
        # Determine which dates we need to check
        needed_dates = set()
        for e in paginated_entries:
            date_str = e.get("_date")
            if date_str:
                needed_dates.add(date_str)

        for date_str in needed_dates:
            path = PROMPTS_DIR / f"{date_str}.jsonl"

            if path.exists():
                try:
                    with open(path) as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entry = json.loads(line)
                                entry_agent = entry.get("agent", "")
                                if entry_agent == agent_id or entry_agent.startswith(f"{agent_id}/"):
                                    ts = entry.get("timestamp", "")
                                    if ts and ts in needed_timestamps:
                                        prompt_content[ts] = {
                                            "system": entry.get("system_prompt"),
                                            "messages": entry.get("messages"),
                                            "tools": entry.get("tools"),
                                            "response": entry.get("response")
                                        }
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

    # Build prompts with content from prompt logs
    prompts = []
    for e in paginated_entries:
        ts = e.get("timestamp", "")
        content = prompt_content.get(ts, {})

        prompt_data = {
            "timestamp": ts,
            "input_tokens": e.get("input_tokens", 0),
            "output_tokens": e.get("output_tokens", 0),
            "model": e.get("model"),
            "duration_ms": e.get("duration_ms"),
            "cost": e.get("cost", 0),
        }

        # Add prompt content if available
        if content.get("system"):
            prompt_data["system"] = content["system"]
        if content.get("messages"):
            prompt_data["messages"] = content["messages"]
        if content.get("tools"):
            prompt_data["tools"] = content["tools"]
        if content.get("response"):
            prompt_data["response"] = content["response"]

        prompts.append(prompt_data)

    return {
        "stats": {
            "week": compute_stats(entries),
            "today": compute_stats(today_entries),
            "hour": compute_stats(hour_entries)
        },
        "prompts": prompts,
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total": total_count,
            "has_more": offset + limit < total_count
        }
    }
