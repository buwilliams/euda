"""
Context aggregation for the context-first UI.

Computes time-aware context views: morning, active day, evening, weekly review.
"""

import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from typing import Optional

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
LOG_DIR = SHARED_DIR / "state" / "lifelog"
SIGNALS_DIR = SHARED_DIR / "state" / "signals"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
WORKER_DIR = DATA_DIR / "worker"
ATTENTION_DIR = DATA_DIR / "attention"


# ============== View Mode Detection ==============

def get_view_mode() -> str:
    """Determine the appropriate view mode based on current time."""
    now = datetime.now()
    hour = now.hour
    day_of_week = now.weekday()  # 0 = Monday, 6 = Sunday

    # Sunday during reasonable hours = weekly review
    if day_of_week == 6 and 9 <= hour <= 20:
        return "weekly"

    # Time-based routing
    if 7 <= hour < 10:
        return "morning"
    elif 10 <= hour < 18:
        return "active"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "active"  # Default to minimal view


def get_greeting() -> str:
    """Generate time-appropriate greeting."""
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 21:
        return "Good evening"
    else:
        return "Hello"


# ============== On Your Mind (Recurring Topics) ==============

def compute_on_your_mind(days: int = 7, min_mentions: int = 2) -> dict:
    """
    Analyze recent log entries to find recurring topics/themes.

    Args:
        days: Number of days to look back
        min_mentions: Minimum times a topic must appear

    Returns:
        {
            "topics": [{"topic": str, "mention_count": int, "last_mentioned": str}],
            "action_prompt": str
        }
    """
    # Get recent log entries
    today = datetime.now()
    all_content = []

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        log_file = LOG_DIR / str(date.year) / f"{date_str}.md"

        if log_file.exists():
            with open(log_file, 'r') as f:
                content = f.read()
            all_content.append((date_str, content))

    if not all_content:
        return {"topics": [], "action_prompt": None}

    # Simple keyword/phrase extraction
    # Look for repeated significant words (excluding common words)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
        'those', 'it', 'its', 'i', 'me', 'my', 'we', 'our', 'you', 'your',
        'he', 'she', 'they', 'them', 'his', 'her', 'their', 'what', 'which',
        'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
        'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now',
        'here', 'there', 'then', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under',
        'again', 'further', 'once', 'source', 'type', 'timestamp', 'locality',
        'temporal', 'confidence', 'high', 'medium', 'low', 'explicit', 'inferred'
    }

    # Extract words and count occurrences by day
    word_days = {}  # word -> set of dates mentioned
    word_contexts = {}  # word -> list of context snippets

    for date_str, content in all_content:
        # Remove metadata blocks
        content = re.sub(r'---[\s\S]*?---', '', content)

        # Extract words (3+ chars, alphabetic)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())

        for word in words:
            if word not in stop_words:
                if word not in word_days:
                    word_days[word] = set()
                    word_contexts[word] = []
                word_days[word].add(date_str)

                # Store a context snippet (find sentence containing word)
                if len(word_contexts[word]) < 3:
                    sentences = re.split(r'[.!?\n]', content)
                    for sentence in sentences:
                        if word in sentence.lower() and len(sentence.strip()) > 20:
                            word_contexts[word].append(sentence.strip()[:100])
                            break

    # Find words mentioned on multiple days
    recurring = []
    for word, days_mentioned in word_days.items():
        if len(days_mentioned) >= min_mentions:
            recurring.append({
                "topic": word,
                "mention_count": len(days_mentioned),
                "last_mentioned": max(days_mentioned),
                "context": word_contexts.get(word, [])[:1]
            })

    # Sort by mention count
    recurring.sort(key=lambda x: x["mention_count"], reverse=True)

    # Take top 5 topics
    topics = recurring[:5]

    # Generate action prompt if there's a clear recurring topic
    action_prompt = None
    if topics and topics[0]["mention_count"] >= 3:
        top_topic = topics[0]["topic"]
        action_prompt = f"You've mentioned '{top_topic}' {topics[0]['mention_count']} times this week. Ready to think it through?"

    return {
        "topics": topics,
        "action_prompt": action_prompt
    }


# ============== Noticed Patterns ==============

def compute_noticed_patterns() -> dict:
    """
    Identify patterns the user might not see themselves.

    Returns:
        {
            "relationship_neglect": [{name, last_contact, gap_days}],
            "energy_patterns": [{observation, source}],
            "general": [{observation, type}]
        }
    """
    result = {
        "relationship_neglect": [],
        "energy_patterns": [],
        "general": []
    }

    # Check for relationship neglect
    relationships_file = SYNTHESIS_DIR / "state" / "context" / "relationships.md"
    if relationships_file.exists():
        with open(relationships_file, 'r') as f:
            content = f.read()

        # Extract people mentioned with their last contact date
        # This is a simplified version - would need smarter parsing for real use
        # For now, check if relationships are populated
        if "(not yet populated)" not in content and "(To be filled" not in content:
            # Parse relationship data and check recency
            # TODO: Implement proper relationship tracking with last_contact dates
            pass

    # Check energy patterns
    now = datetime.now()
    energy_signals = []

    for i in range(7):  # Last 7 days
        date = now - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        signal_file = SIGNALS_DIR / f"energy_{date_str}.json"

        if signal_file.exists():
            with open(signal_file, 'r') as f:
                day_signals = json.load(f)
            energy_signals.extend(day_signals)

    if energy_signals:
        # Analyze energy trends
        low_energy_count = sum(
            1 for s in energy_signals
            if 'tired' in str(s.get('physical', '')).lower()
            or 'low' in str(s.get('mental', '')).lower()
            or 'foggy' in str(s.get('mental', '')).lower()
        )

        if low_energy_count >= 3:
            # Find when low energy started
            sorted_signals = sorted(energy_signals, key=lambda x: x.get('timestamp', ''))
            for s in sorted_signals:
                if ('tired' in str(s.get('physical', '')).lower() or
                    'low' in str(s.get('mental', '')).lower()):
                    start_date = s.get('timestamp', '')[:10]
                    result["energy_patterns"].append({
                        "observation": f"Energy has been low since {start_date}.",
                        "source": "energy_signals"
                    })
                    break

    return result


# ============== Actionable Patterns (for Proactive Creation) ==============

def detect_actionable_patterns(days: int = 14, min_mentions: int = 3) -> list:
    """
    Analyze lifelog for patterns suggesting needed projects/tasks.

    Looks for:
    - Topics mentioned 5+ times across 7+ days without existing project
    - Intent phrases ("need to", "should", "want to", "planning to")
    - Repeated goals or intentions

    Args:
        days: Number of days to look back
        min_mentions: Minimum times a topic/intent must appear

    Returns:
        List of dicts with: type, title, description, confidence, evidence
    """
    from ..worker.project import get_projects_data

    # Get existing project titles to avoid duplicates
    existing_projects = get_projects_data(status="all")
    existing_titles = {p.get("title", "").lower() for p in existing_projects}

    # Intent phrases that suggest actionable items
    intent_phrases = [
        (r"need to\s+(\w+(?:\s+\w+){0,4})", "task"),
        (r"should\s+(\w+(?:\s+\w+){0,4})", "task"),
        (r"want to\s+(\w+(?:\s+\w+){0,4})", "project"),
        (r"planning to\s+(\w+(?:\s+\w+){0,4})", "project"),
        (r"going to\s+(\w+(?:\s+\w+){0,4})", "task"),
        (r"have to\s+(\w+(?:\s+\w+){0,4})", "task"),
        (r"would like to\s+(\w+(?:\s+\w+){0,4})", "project"),
        (r"thinking about\s+(\w+(?:\s+\w+){0,4})", "project"),
    ]

    # Collect all content from logs
    today = datetime.now()
    all_content = []

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        log_file = LOG_DIR / str(date.year) / f"{date_str}.md"

        if log_file.exists():
            with open(log_file, 'r') as f:
                content = f.read()
            # Remove metadata blocks
            content = re.sub(r'---[\s\S]*?---', '', content)
            all_content.append((date_str, content))

    if not all_content:
        return []

    # Track intent patterns
    intent_counts = {}  # intent_phrase -> {dates: set, type: str, examples: list}

    for date_str, content in all_content:
        content_lower = content.lower()

        for pattern, item_type in intent_phrases:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                # Clean up the match
                intent = match.strip()
                if len(intent) < 4 or len(intent) > 50:
                    continue

                # Skip if it looks like an existing project
                if any(title in intent or intent in title for title in existing_titles):
                    continue

                if intent not in intent_counts:
                    intent_counts[intent] = {
                        "dates": set(),
                        "type": item_type,
                        "examples": []
                    }

                intent_counts[intent]["dates"].add(date_str)

                # Store context example
                if len(intent_counts[intent]["examples"]) < 2:
                    # Find the full sentence
                    sentences = re.split(r'[.!?\n]', content)
                    for sentence in sentences:
                        if intent in sentence.lower() and len(sentence.strip()) > 20:
                            intent_counts[intent]["examples"].append(sentence.strip()[:150])
                            break

    # Find actionable patterns
    patterns = []

    for intent, data in intent_counts.items():
        mention_count = len(data["dates"])

        if mention_count >= min_mentions:
            # Determine confidence
            if mention_count >= 5:
                confidence = "high"
            elif mention_count >= 3:
                confidence = "medium"
            else:
                confidence = "low"

            # Generate a proper title
            title = intent.title()
            if len(title) > 40:
                title = title[:37] + "..."

            patterns.append({
                "type": data["type"],
                "title": title,
                "description": f"Mentioned {mention_count} times over {days} days",
                "confidence": confidence,
                "evidence": data["examples"],
                "mention_count": mention_count,
                "last_mentioned": max(data["dates"])
            })

    # Sort by mention count (highest first)
    patterns.sort(key=lambda x: x["mention_count"], reverse=True)

    # Return top 3 actionable patterns
    return patterns[:3]


# ============== Schedule & Tasks ==============

def get_schedule_context() -> dict:
    """
    Get today's schedule from tasks and calendar (when available).

    Returns:
        {
            "events": [],
            "next_event": None,
            "deep_work_windows": []
        }
    """
    # For now, just return empty - calendar integration comes later
    return {
        "events": [],
        "next_event": None,
        "deep_work_windows": [],
        "calendar_connected": False
    }


def get_tasks_context() -> dict:
    """
    Get today's tasks for context display.

    Returns:
        {
            "due_today": [],
            "high_priority": [],
            "overdue": [],
            "could_do_today": []
        }
    """
    from ..worker.task import get_tasks_data

    today = datetime.now().strftime('%Y-%m-%d')

    # Get all pending tasks
    all_tasks = get_tasks_data(status="pending")

    due_today = []
    high_priority = []
    overdue = []
    could_do_today = []

    for task in all_tasks:
        due_date = task.get("scheduling", {}).get("due_date")
        priority = task.get("priority", "normal")

        task_summary = {
            "id": task.get("id"),
            "description": task.get("description", "")[:100],
            "priority": priority,
            "due_date": due_date
        }

        if due_date == today:
            due_today.append(task_summary)
        elif due_date and due_date < today:
            overdue.append(task_summary)
        elif priority == "high":
            high_priority.append(task_summary)
        elif not due_date or due_date > today:
            could_do_today.append(task_summary)

    return {
        "due_today": due_today[:5],
        "high_priority": high_priority[:3],
        "overdue": overdue[:3],
        "could_do_today": could_do_today[:5]
    }


# ============== Day Summary (Evening View) ==============

def get_day_summary() -> dict:
    """
    Summarize what happened today for evening view.

    Returns:
        {
            "completed_tasks": [],
            "logged_entries": int,
            "energy_trend": str
        }
    """
    from ..worker.task import get_tasks_data

    today = datetime.now().strftime('%Y-%m-%d')

    # Completed tasks today
    completed = get_tasks_data(status="completed")
    completed_today = [
        t for t in completed
        if t.get("completed_at", "")[:10] == today
    ]

    # Count log entries today
    log_file = LOG_DIR / str(datetime.now().year) / f"{today}.md"
    log_count = 0
    if log_file.exists():
        with open(log_file, 'r') as f:
            content = f.read()
        log_count = content.count('---') // 2  # Each entry has --- before and after

    return {
        "completed_tasks": [
            {"description": t.get("description", "")[:50]}
            for t in completed_today[:5]
        ],
        "logged_entries": log_count,
        "energy_trend": "unknown"  # TODO: compute from signals
    }


# ============== Open Threads ==============

def get_open_threads() -> list:
    """
    Get open threads/pending items for evening review.

    Returns:
        List of open items with descriptions and urgency
    """
    from ..worker.task import get_tasks_data

    # Get pending tasks
    pending = get_tasks_data(status="pending")

    threads = []
    for task in pending[:10]:
        urgency = "can wait"
        priority = task.get("priority", "normal")
        due_date = task.get("scheduling", {}).get("due_date")

        if priority == "high":
            urgency = "soon"
        if due_date and due_date <= datetime.now().strftime('%Y-%m-%d'):
            urgency = "do now"

        threads.append({
            "description": task.get("description", "")[:60],
            "urgency": urgency,
            "type": "task"
        })

    return threads


# ============== Tomorrow Preview ==============

def get_tomorrow_preview() -> dict:
    """
    Preview what's coming tomorrow.

    Returns:
        {
            "task_count": int,
            "high_priority_count": int,
            "calendar_events": [],
            "suggestion": str
        }
    """
    from ..worker.task import get_tasks_data

    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    # Tasks due tomorrow
    all_tasks = get_tasks_data(status="pending")
    tomorrow_tasks = [
        t for t in all_tasks
        if t.get("scheduling", {}).get("due_date") == tomorrow
    ]
    high_priority = [t for t in tomorrow_tasks if t.get("priority") == "high"]

    suggestion = None
    if len(tomorrow_tasks) > 5:
        suggestion = "Heavy day tomorrow - consider protecting some focus time?"
    elif len(high_priority) >= 2:
        suggestion = f"{len(high_priority)} high-priority items tomorrow."

    return {
        "task_count": len(tomorrow_tasks),
        "high_priority_count": len(high_priority),
        "calendar_events": [],  # Calendar integration later
        "suggestion": suggestion
    }


# ============== Main Context Aggregator ==============

def get_context_for_view(view_mode: str = None) -> dict:
    """
    Get aggregated context for a specific view mode.

    Args:
        view_mode: One of 'morning', 'active', 'evening', 'weekly'
                   If None, auto-detects based on time

    Returns:
        Complete context dictionary for the view
    """
    if view_mode is None:
        view_mode = get_view_mode()

    now = datetime.now()

    # Base context (always included)
    context = {
        "view_mode": view_mode,
        "time_context": {
            "current_time": now.isoformat(),
            "greeting": get_greeting(),
            "day_of_week": now.strftime("%A"),
            "date_formatted": now.strftime("%B %d, %Y")
        }
    }

    if view_mode == "morning":
        # Full morning briefing
        context["schedule"] = get_schedule_context()
        context["tasks"] = get_tasks_context()
        context["on_your_mind"] = compute_on_your_mind()
        context["noticed"] = compute_noticed_patterns()

    elif view_mode == "active":
        # Minimal, focus-protecting
        schedule = get_schedule_context()
        context["schedule"] = {
            "next_event": schedule.get("next_event"),
            "current_activity": "Deep work"  # Default
        }
        # Count unsurfaced items
        queue_file = ATTENTION_DIR / "state" / "queue" / "surfacing.json"
        surfaced_count = 0
        if queue_file.exists():
            with open(queue_file, 'r') as f:
                queue = json.load(f)
            surfaced_count = sum(1 for item in queue if not item.get("surfaced"))
        context["surfaced_count"] = surfaced_count

    elif view_mode == "evening":
        # Reflection and closure
        context["day_summary"] = get_day_summary()
        context["open_threads"] = get_open_threads()
        context["tomorrow"] = get_tomorrow_preview()
        context["tasks"] = get_tasks_context()

    elif view_mode == "weekly":
        # Weekly review
        context["day_summary"] = get_day_summary()  # TODO: week summary
        context["tasks"] = get_tasks_context()
        context["on_your_mind"] = compute_on_your_mind(days=7)
        context["noticed"] = compute_noticed_patterns()

    return context


# Export for API use
__all__ = [
    'get_view_mode',
    'get_greeting',
    'compute_on_your_mind',
    'compute_noticed_patterns',
    'get_context_for_view'
]


# Test
if __name__ == "__main__":
    import json
    context = get_context_for_view()
    print(json.dumps(context, indent=2, default=str))
