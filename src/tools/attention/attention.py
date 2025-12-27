"""
Attention tools for the Attention Agent (The Curator).

Tools for managing energy signals, surfacing queues, and attention timing.
"""

from datetime import datetime, timedelta
from pathlib import Path
import json

# Base paths - Attention agent uses shared signals and its own queue
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
SIGNALS_DIR = SHARED_DIR / "state" / "signals"
ATTENTION_DIR = DATA_DIR / "attention"
QUEUES_DIR = ATTENTION_DIR / "state" / "queue"

# Ensure directories exist
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
QUEUES_DIR.mkdir(parents=True, exist_ok=True)


# ============== Energy Signals ==============

def record_energy(
    physical: str = "",
    mental: str = "",
    emotional: str = "",
    social: str = "",
    notes: str = ""
) -> str:
    """
    Record current energy levels across dimensions.

    Args:
        physical: Physical energy observation (e.g., "tired", "energized")
        mental: Mental clarity observation
        emotional: Emotional state observation
        social: Social capacity observation
        notes: Additional context

    Returns:
        Confirmation message
    """
    timestamp = datetime.now().isoformat()
    date_str = datetime.now().strftime('%Y-%m-%d')

    signal = {
        "timestamp": timestamp,
        "physical": physical,
        "mental": mental,
        "emotional": emotional,
        "social": social,
        "notes": notes
    }

    # Append to daily signal file
    signal_file = SIGNALS_DIR / f"energy_{date_str}.json"

    signals = []
    if signal_file.exists():
        with open(signal_file, 'r') as f:
            signals = json.load(f)

    signals.append(signal)

    with open(signal_file, 'w') as f:
        json.dump(signals, f, indent=2)

    return f"Energy recorded at {timestamp}"


def get_recent_energy(hours: int = 24) -> str:
    """
    Get recent energy signals.

    Args:
        hours: How many hours back to look

    Returns:
        Recent energy observations
    """
    cutoff = datetime.now() - timedelta(hours=hours)
    signals = []

    # Check recent days
    for i in range(3):  # Last 3 days max
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        signal_file = SIGNALS_DIR / f"energy_{date_str}.json"

        if signal_file.exists():
            with open(signal_file, 'r') as f:
                day_signals = json.load(f)

            for s in day_signals:
                signal_time = datetime.fromisoformat(s["timestamp"])
                if signal_time >= cutoff:
                    signals.append(s)

    if not signals:
        return "No recent energy signals recorded."

    # Format output
    output = f"Energy signals from last {hours} hours:\n\n"
    for s in sorted(signals, key=lambda x: x["timestamp"], reverse=True):
        time = s["timestamp"][11:16]  # HH:MM
        parts = []
        if s.get("physical"):
            parts.append(f"Physical: {s['physical']}")
        if s.get("mental"):
            parts.append(f"Mental: {s['mental']}")
        if s.get("emotional"):
            parts.append(f"Emotional: {s['emotional']}")
        if s.get("social"):
            parts.append(f"Social: {s['social']}")

        output += f"**{time}**: {', '.join(parts)}\n"
        if s.get("notes"):
            output += f"  Notes: {s['notes']}\n"

    return output


def infer_energy_state() -> str:
    """
    Infer current energy state from signals and time of day.

    Returns:
        Inferred energy state with reasoning
    """
    now = datetime.now()
    hour = now.hour

    # Time-based baseline
    if 6 <= hour < 10:
        time_energy = "Morning - typically rising energy, good for focused work"
    elif 10 <= hour < 14:
        time_energy = "Midday - often peak mental energy"
    elif 14 <= hour < 17:
        time_energy = "Afternoon - potential dip, varies by person"
    elif 17 <= hour < 21:
        time_energy = "Evening - winding down, better for reflection than creation"
    else:
        time_energy = "Night - typically low energy, rest recommended"

    # Check recent signals
    recent = get_recent_energy(hours=4)

    output = f"## Energy State Inference\n\n"
    output += f"**Time context**: {time_energy}\n\n"

    if "No recent energy" in recent:
        output += "**Signals**: No recent energy readings. Consider asking user.\n"
    else:
        output += f"**Recent signals**:\n{recent}\n"

    output += "\n*Note: This is inference. When uncertain, ask rather than assume.*"

    return output


# ============== Surfacing Queue ==============

def add_to_queue(
    content: str,
    priority: str = "normal",
    surface_after: str = "",
    source: str = "",
    tags: str = ""
) -> str:
    """
    Add an item to the surfacing queue.

    Args:
        content: What to surface
        priority: "high", "normal", or "low"
        surface_after: ISO timestamp - don't surface before this time
        source: Where this came from (e.g., "world_agent", "user_request")
        tags: Comma-separated tags

    Returns:
        Confirmation message
    """
    timestamp = datetime.now().isoformat()

    item = {
        "id": timestamp.replace(":", "-").replace(".", "-"),
        "added": timestamp,
        "content": content,
        "priority": priority,
        "surface_after": surface_after or timestamp,
        "source": source,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "surfaced": False
    }

    queue_file = QUEUES_DIR / "surfacing.json"

    queue = []
    if queue_file.exists():
        with open(queue_file, 'r') as f:
            queue = json.load(f)

    queue.append(item)

    with open(queue_file, 'w') as f:
        json.dump(queue, f, indent=2)

    return f"Added to surfacing queue: {content[:50]}..."


def get_queue(include_surfaced: bool = False) -> str:
    """
    Get items in the surfacing queue.

    Args:
        include_surfaced: Whether to include already-surfaced items

    Returns:
        Queue contents
    """
    queue_file = QUEUES_DIR / "surfacing.json"

    if not queue_file.exists():
        return "Surfacing queue is empty."

    with open(queue_file, 'r') as f:
        queue = json.load(f)

    now = datetime.now().isoformat()

    # Filter
    items = []
    for item in queue:
        if not include_surfaced and item.get("surfaced"):
            continue
        items.append(item)

    if not items:
        return "No pending items in surfacing queue."

    # Sort by priority and time
    priority_order = {"high": 0, "normal": 1, "low": 2}
    items.sort(key=lambda x: (priority_order.get(x.get("priority", "normal"), 1), x.get("surface_after", "")))

    output = "## Surfacing Queue\n\n"
    for item in items:
        ready = "✓" if item.get("surface_after", "") <= now else "⏳"
        output += f"{ready} **[{item.get('priority', 'normal')}]** {item['content'][:80]}\n"
        if item.get("tags"):
            output += f"   Tags: {', '.join(item['tags'])}\n"

    return output


def mark_surfaced(item_id: str) -> str:
    """
    Mark a queue item as surfaced.

    Args:
        item_id: The item ID to mark

    Returns:
        Confirmation message
    """
    queue_file = QUEUES_DIR / "surfacing.json"

    if not queue_file.exists():
        return "Queue not found"

    with open(queue_file, 'r') as f:
        queue = json.load(f)

    for item in queue:
        if item.get("id") == item_id:
            item["surfaced"] = True
            item["surfaced_at"] = datetime.now().isoformat()

            with open(queue_file, 'w') as f:
                json.dump(queue, f, indent=2)

            return f"Marked as surfaced: {item_id}"

    return f"Item not found: {item_id}"


# ============== Attention Timing ==============

def get_attention_context() -> str:
    """
    Get current context for attention decisions.

    Returns:
        Context including time, energy, values summary
    """
    now = datetime.now()
    hour = now.hour
    day = now.strftime("%A")

    # Determine attention mode
    if 6 <= hour < 10:
        mode = "morning"
        mode_desc = "Morning attention - focused, action-oriented"
    elif 18 <= hour < 22:
        mode = "evening"
        mode_desc = "Evening attention - warm, reflective (user may be tired)"
    else:
        mode = "ad-hoc"
        mode_desc = "Ad-hoc attention - responsive to user needs"

    output = f"""## Attention Context

**Time**: {now.strftime('%Y-%m-%d %H:%M')} ({day})
**Mode**: {mode_desc}

### Energy State
{infer_energy_state()}

### Queue Status
{get_queue()}
"""

    # Add values summary if available
    from ..values.values import get_current_values
    values = get_current_values()
    if not values.startswith("No current"):
        output += f"\n### Current Values (for alignment)\n{values[:500]}...\n"

    return output


def generate_morning_attention() -> str:
    """
    Generate morning attention content.

    Returns:
        Morning attention prompt/content
    """
    context = get_attention_context()

    return f"""## Morning Attention

Good morning. Here's what deserves your attention today.

{context}

### Guidance for The Curator

Create a morning attention message that:
1. Is brief and actionable
2. Highlights 1-3 things that matter today
3. Integrates any queued opportunities naturally
4. Respects current energy state
5. Includes one thing to look forward to
6. Keeps the 90/10 balance (mostly aligned, small surprise integrated naturally)

Remember: Less is more. Don't overwhelm.
"""


def generate_evening_attention() -> str:
    """
    Generate evening attention/journal prompt.

    Returns:
        Evening attention prompt/content
    """
    # Get today's log entries
    from ..shared.log import read_log_entry
    today = datetime.now().strftime('%Y-%m-%d')
    today_log = read_log_entry(today)

    context = get_attention_context()

    return f"""## Evening Reflection

Time to wind down and reflect.

{context}

### Today's Log
{today_log}

### Guidance for The Curator

Create an evening journal prompt that:
1. Is warm and gentle (user is likely tired)
2. Invites reflection, not action
3. Asks about subjective experience
4. Notes what went well
5. Creates space for what's unfinished
6. Doesn't require much energy to engage with

Remember: Be a caring friend at the end of a long day.
"""


# Tool definitions for the LLM
ATTENTION_TOOLS = [
    {
        "name": "record_energy",
        "description": "Record current energy levels across dimensions (physical, mental, emotional, social).",
        "input_schema": {
            "type": "object",
            "properties": {
                "physical": {
                    "type": "string",
                    "description": "Physical energy observation (e.g., 'tired', 'energized', 'restless')"
                },
                "mental": {
                    "type": "string",
                    "description": "Mental clarity observation (e.g., 'focused', 'foggy', 'sharp')"
                },
                "emotional": {
                    "type": "string",
                    "description": "Emotional state observation (e.g., 'calm', 'anxious', 'content')"
                },
                "social": {
                    "type": "string",
                    "description": "Social capacity observation (e.g., 'need solitude', 'want connection')"
                },
                "notes": {
                    "type": "string",
                    "description": "Additional context about energy state"
                }
            }
        }
    },
    {
        "name": "get_recent_energy",
        "description": "Get recent energy signals to understand current state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "How many hours back to look (default 24)"
                }
            }
        }
    },
    {
        "name": "infer_energy_state",
        "description": "Infer current energy state from signals and time of day.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "add_to_queue",
        "description": "Add an item to the surfacing queue for later attention.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "What to surface"
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "normal", "low"],
                    "description": "Priority level"
                },
                "surface_after": {
                    "type": "string",
                    "description": "ISO timestamp - don't surface before this time"
                },
                "source": {
                    "type": "string",
                    "description": "Where this came from"
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tags"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "get_queue",
        "description": "Get items in the surfacing queue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_surfaced": {
                    "type": "boolean",
                    "description": "Whether to include already-surfaced items"
                }
            }
        }
    },
    {
        "name": "mark_surfaced",
        "description": "Mark a queue item as surfaced/delivered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "The item ID to mark"
                }
            },
            "required": ["item_id"]
        }
    },
    {
        "name": "get_attention_context",
        "description": "Get current context for attention decisions (time, energy, values, queue).",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "generate_morning_attention",
        "description": "Generate context for morning attention. Use this to prepare the morning message.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "generate_evening_attention",
        "description": "Generate context for evening reflection. Use this to prepare the evening journal prompt.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers mapping
ATTENTION_HANDLERS = {
    "record_energy": record_energy,
    "get_recent_energy": get_recent_energy,
    "infer_energy_state": infer_energy_state,
    "add_to_queue": add_to_queue,
    "get_queue": get_queue,
    "mark_surfaced": mark_surfaced,
    "get_attention_context": get_attention_context,
    "generate_morning_attention": generate_morning_attention,
    "generate_evening_attention": generate_evening_attention,
}


# Test
if __name__ == "__main__":
    print(get_attention_context())
