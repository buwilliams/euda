"""
Conversation History Tools.

Persistent storage and retrieval of chat conversations.
Enables loading previous conversations, searching by topic,
analyzing themes, and providing personalized suggestions.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import re

# Base paths - Conversations are owned by Interaction agent
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONVERSATIONS_DIR = BASE_DIR / "data" / "interaction" / "state" / "conversations"


def _ensure_dirs():
    """Ensure conversation directories exist."""
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    (CONVERSATIONS_DIR / "sessions").mkdir(parents=True, exist_ok=True)
    (CONVERSATIONS_DIR / "daily").mkdir(parents=True, exist_ok=True)


def _get_session_file(session_id: str) -> Path:
    """Get path for a session's conversation file."""
    return CONVERSATIONS_DIR / "sessions" / f"{session_id}.json"


def _get_daily_file(date: str) -> Path:
    """Get path for a day's conversation index."""
    return CONVERSATIONS_DIR / "daily" / f"{date}.json"


def save_message(
    session_id: str,
    user_message: str,
    assistant_response: str,
    tool_calls: list = None
) -> str:
    """
    Save a conversation exchange to persistent storage.

    Called automatically after each chat exchange.

    Args:
        session_id: The session identifier
        user_message: What the user said
        assistant_response: What the assistant replied
        tool_calls: Optional list of tools used

    Returns:
        Confirmation message
    """
    _ensure_dirs()

    timestamp = datetime.now()
    date_str = timestamp.strftime("%Y-%m-%d")

    # Load or create session file
    session_file = _get_session_file(session_id)
    if session_file.exists():
        with open(session_file, 'r') as f:
            session_data = json.load(f)
    else:
        session_data = {
            "session_id": session_id,
            "created": timestamp.isoformat(),
            "messages": []
        }

    # Add the exchange
    exchange = {
        "timestamp": timestamp.isoformat(),
        "user": user_message,
        "assistant": assistant_response,
    }
    if tool_calls:
        exchange["tools"] = tool_calls

    session_data["messages"].append(exchange)
    session_data["updated"] = timestamp.isoformat()

    # Save session
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)

    # Update daily index
    daily_file = _get_daily_file(date_str)
    if daily_file.exists():
        with open(daily_file, 'r') as f:
            daily_data = json.load(f)
    else:
        daily_data = {"date": date_str, "sessions": []}

    # Add session to daily index if not already there
    if session_id not in daily_data["sessions"]:
        daily_data["sessions"].append(session_id)

    with open(daily_file, 'w') as f:
        json.dump(daily_data, f, indent=2)

    return "Message saved"


def get_conversation(session_id: str) -> str:
    """
    Load a specific conversation by session ID.

    Args:
        session_id: The session to load

    Returns:
        Formatted conversation or error message
    """
    session_file = _get_session_file(session_id)

    if not session_file.exists():
        return f"No conversation found with session ID: {session_id}"

    with open(session_file, 'r') as f:
        data = json.load(f)

    # Format for display
    lines = [f"## Conversation from {data.get('created', 'unknown')[:10]}"]
    lines.append(f"Session: {session_id}")
    lines.append("")

    for msg in data.get("messages", []):
        time = msg.get("timestamp", "")[:16].replace("T", " ")
        lines.append(f"**[{time}] You:** {msg.get('user', '')}")
        lines.append(f"**Friend:** {msg.get('assistant', '')}")
        lines.append("")

    return "\n".join(lines)


def get_conversations_for_date(date: str = None) -> str:
    """
    Get all conversations from a specific date.

    Args:
        date: Date in YYYY-MM-DD format (default: today)

    Returns:
        Formatted conversations from that day
    """
    _ensure_dirs()

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    daily_file = _get_daily_file(date)

    if not daily_file.exists():
        return f"No conversations found for {date}"

    with open(daily_file, 'r') as f:
        daily_data = json.load(f)

    all_messages = []

    for session_id in daily_data.get("sessions", []):
        session_file = _get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                session_data = json.load(f)

            for msg in session_data.get("messages", []):
                # Only include messages from this date
                msg_date = msg.get("timestamp", "")[:10]
                if msg_date == date:
                    all_messages.append(msg)

    if not all_messages:
        return f"No conversations found for {date}"

    # Sort by timestamp
    all_messages.sort(key=lambda x: x.get("timestamp", ""))

    # Format
    lines = [f"## Conversations from {date}"]
    lines.append(f"Total exchanges: {len(all_messages)}")
    lines.append("")

    for msg in all_messages:
        time = msg.get("timestamp", "")[:16].replace("T", " ")
        lines.append(f"**[{time}] You:** {msg.get('user', '')}")
        lines.append(f"**Friend:** {msg.get('assistant', '')}")
        lines.append("")

    return "\n".join(lines)


def search_conversations(
    query: str,
    days_back: int = 30,
    limit: int = 10
) -> str:
    """
    Search conversation history for a topic or keyword.

    Args:
        query: Search term or phrase
        days_back: How many days to search (default 30)
        limit: Maximum results to return

    Returns:
        Matching conversation excerpts
    """
    _ensure_dirs()

    query_lower = query.lower()
    results = []

    # Search recent days
    today = datetime.now()
    for i in range(days_back):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_file = _get_daily_file(date)

        if not daily_file.exists():
            continue

        with open(daily_file, 'r') as f:
            daily_data = json.load(f)

        for session_id in daily_data.get("sessions", []):
            session_file = _get_session_file(session_id)
            if not session_file.exists():
                continue

            with open(session_file, 'r') as f:
                session_data = json.load(f)

            for msg in session_data.get("messages", []):
                user_text = msg.get("user", "").lower()
                assistant_text = msg.get("assistant", "").lower()

                if query_lower in user_text or query_lower in assistant_text:
                    results.append({
                        "date": msg.get("timestamp", "")[:10],
                        "time": msg.get("timestamp", "")[11:16],
                        "session_id": session_id,
                        "user": msg.get("user", ""),
                        "assistant": msg.get("assistant", "")
                    })

                    if len(results) >= limit:
                        break

            if len(results) >= limit:
                break

        if len(results) >= limit:
            break

    if not results:
        return f"No conversations found matching '{query}' in the last {days_back} days."

    # Format results
    lines = [f"## Search Results for '{query}'"]
    lines.append(f"Found {len(results)} matching conversation(s)")
    lines.append("")

    for r in results:
        lines.append(f"**{r['date']} {r['time']}**")
        lines.append(f"You: {r['user'][:200]}{'...' if len(r['user']) > 200 else ''}")
        lines.append(f"Friend: {r['assistant'][:200]}{'...' if len(r['assistant']) > 200 else ''}")
        lines.append(f"_Session: {r['session_id'][:8]}..._")
        lines.append("")

    return "\n".join(lines)


def find_conversation_by_topic(topic: str, days_back: int = 90) -> str:
    """
    Find when we last discussed a specific topic.

    Args:
        topic: The topic to search for
        days_back: How far back to search

    Returns:
        Date and context of the conversation about that topic
    """
    return search_conversations(topic, days_back=days_back, limit=5)


def get_conversation_themes(period: str = "week") -> str:
    """
    Analyze themes and patterns in recent conversations.

    Args:
        period: "day", "week", or "month"

    Returns:
        Summary of conversation themes and patterns
    """
    _ensure_dirs()

    days = {"day": 1, "week": 7, "month": 30}.get(period, 7)

    all_messages = []
    today = datetime.now()

    for i in range(days):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_file = _get_daily_file(date)

        if not daily_file.exists():
            continue

        with open(daily_file, 'r') as f:
            daily_data = json.load(f)

        for session_id in daily_data.get("sessions", []):
            session_file = _get_session_file(session_id)
            if session_file.exists():
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                all_messages.extend(session_data.get("messages", []))

    if not all_messages:
        return f"No conversations found in the last {period}."

    # Basic theme extraction (word frequency)
    word_counts = {}
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                  'could', 'should', 'may', 'might', 'can', 'to', 'of', 'in',
                  'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'about',
                  'that', 'this', 'it', 'its', 'i', 'you', 'we', 'they', 'me',
                  'my', 'your', 'our', 'what', 'when', 'where', 'how', 'why',
                  'and', 'or', 'but', 'not', 'no', 'yes', 'just', 'so', 'if',
                  'im', "i'm", "don't", "it's", 'get', 'got', 'like', 'know',
                  'think', 'want', 'need', 'make', 'let', 'see', 'go', 'going'}

    for msg in all_messages:
        text = f"{msg.get('user', '')} {msg.get('assistant', '')}"
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        for word in words:
            if word not in stop_words:
                word_counts[word] = word_counts.get(word, 0) + 1

    # Get top themes
    top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    # Group by topic areas
    topics = {}
    for word, count in top_words:
        if count >= 2:
            topics[word] = count

    # Format output
    lines = [f"## Conversation Themes ({period})"]
    lines.append(f"Based on {len(all_messages)} message exchanges")
    lines.append("")

    if topics:
        lines.append("**Top Topics:**")
        for word, count in list(topics.items())[:10]:
            lines.append(f"- {word}: {count} mentions")
    else:
        lines.append("Not enough data to identify themes yet.")

    lines.append("")
    lines.append(f"**Total conversations:** {len(all_messages)}")

    return "\n".join(lines)


def get_recent_conversations(count: int = 5) -> str:
    """
    Get the most recent conversations.

    Args:
        count: Number of recent conversations to return

    Returns:
        Formatted recent conversations
    """
    _ensure_dirs()

    all_sessions = []
    today = datetime.now()

    # Look back up to 30 days for recent conversations
    for i in range(30):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_file = _get_daily_file(date)

        if daily_file.exists():
            with open(daily_file, 'r') as f:
                daily_data = json.load(f)
            all_sessions.extend(daily_data.get("sessions", []))

        if len(all_sessions) >= count * 2:  # Get extra to account for filtering
            break

    if not all_sessions:
        return "No recent conversations found."

    # Load session data and sort by most recent
    sessions_with_data = []
    seen = set()

    for session_id in all_sessions:
        if session_id in seen:
            continue
        seen.add(session_id)

        session_file = _get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
            sessions_with_data.append({
                "session_id": session_id,
                "updated": data.get("updated", data.get("created", "")),
                "message_count": len(data.get("messages", [])),
                "preview": data.get("messages", [{}])[0].get("user", "")[:50] if data.get("messages") else ""
            })

    # Sort by most recent
    sessions_with_data.sort(key=lambda x: x["updated"], reverse=True)

    # Format
    lines = ["## Recent Conversations"]
    lines.append("")

    for s in sessions_with_data[:count]:
        date = s["updated"][:10] if s["updated"] else "unknown"
        time = s["updated"][11:16] if len(s["updated"]) > 11 else ""
        lines.append(f"**{date} {time}** ({s['message_count']} messages)")
        if s["preview"]:
            lines.append(f"  Started with: \"{s['preview']}...\"")
        lines.append(f"  Session: {s['session_id'][:8]}...")
        lines.append("")

    return "\n".join(lines)


def load_conversation_into_context(session_id: str = None, date: str = None) -> list:
    """
    Load conversation history to restore into the chat context.

    This returns the raw message list so the UI can display it.

    Args:
        session_id: Specific session to load
        date: Or load all from a specific date

    Returns:
        List of message dictionaries for the UI
    """
    _ensure_dirs()

    messages = []

    if session_id:
        session_file = _get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
            for msg in data.get("messages", []):
                messages.append({
                    "role": "user",
                    "content": msg.get("user", ""),
                    "timestamp": msg.get("timestamp", "")
                })
                messages.append({
                    "role": "assistant",
                    "content": msg.get("assistant", ""),
                    "timestamp": msg.get("timestamp", "")
                })

    elif date:
        daily_file = _get_daily_file(date)
        if daily_file.exists():
            with open(daily_file, 'r') as f:
                daily_data = json.load(f)

            for sid in daily_data.get("sessions", []):
                session_file = _get_session_file(sid)
                if session_file.exists():
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    for msg in data.get("messages", []):
                        msg_date = msg.get("timestamp", "")[:10]
                        if msg_date == date:
                            messages.append({
                                "role": "user",
                                "content": msg.get("user", ""),
                                "timestamp": msg.get("timestamp", "")
                            })
                            messages.append({
                                "role": "assistant",
                                "content": msg.get("assistant", ""),
                                "timestamp": msg.get("timestamp", "")
                            })

    # Sort by timestamp
    messages.sort(key=lambda x: x.get("timestamp", ""))

    return messages


def get_conversation_data(session_id: str = None, date: str = None) -> dict:
    """
    Get raw conversation data for API response.

    Args:
        session_id: Specific session to load
        date: Or load all from a specific date

    Returns:
        Dictionary with messages for UI rendering
    """
    messages = load_conversation_into_context(session_id=session_id, date=date)
    return {
        "messages": messages,
        "count": len(messages),
        "session_id": session_id,
        "date": date
    }


# Tool definitions for the LLM
CONVERSATION_HISTORY_TOOLS = [
    {
        "name": "get_conversations_for_date",
        "description": "Load all conversations from a specific date. Use when the user wants to see what we talked about on a particular day, or to restore a previous day's conversation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (default: today)"
                }
            }
        }
    },
    {
        "name": "search_conversations",
        "description": "Search conversation history for a topic, keyword, or phrase. Use when the user asks 'when did we talk about X' or 'find our conversation about Y'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term or phrase"
                },
                "days_back": {
                    "type": "integer",
                    "description": "How many days back to search (default: 30)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 10)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_conversation_themes",
        "description": "Analyze themes and patterns in recent conversations. Use when user asks 'what have we been talking about', 'themes this week', 'what topics have come up'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["day", "week", "month"],
                    "description": "Time period to analyze (default: week)"
                }
            }
        }
    },
    {
        "name": "get_recent_conversations",
        "description": "Get a list of the most recent conversations with previews. Use to show the user what recent chats are available to load.",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of recent conversations to show (default: 5)"
                }
            }
        }
    },
    {
        "name": "load_previous_conversation",
        "description": "Load a previous conversation back into the chat. Use when user wants to 'restore', 'load', or 'bring back' a previous conversation. Returns data that will be displayed in the UI.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Specific session ID to load"
                },
                "date": {
                    "type": "string",
                    "description": "Or load all conversations from a date (YYYY-MM-DD)"
                }
            }
        }
    },
    {
        "name": "suggest_activities",
        "description": "Suggest activities based on the agent's deep understanding of the user. Combines values, world discoveries, recent activity, and conversation themes. Use when user asks 'what should I do', 'any suggestions for my free time', 'I have some time, what do you recommend', or similar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Optional context like 'free evening', 'weekend', 'need energy', 'feeling social', 'want to learn something'"
                }
            }
        }
    },
    {
        "name": "get_personalized_context",
        "description": "Get a comprehensive view of what we know about the user (values, recent activity, conversation patterns). Use this internally to personalize responses.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Handler for load_previous_conversation (special - returns data for UI)
def load_previous_conversation(session_id: str = None, date: str = None) -> str:
    """
    Load a previous conversation. Returns formatted text for now,
    but the API can also return raw data for UI rendering.
    """
    if session_id:
        return get_conversation(session_id)
    elif date:
        return get_conversations_for_date(date)
    else:
        return "Please specify either a session_id or a date to load."


def suggest_activities(context: str = "") -> str:
    """
    Suggest activities based on the agent's understanding of the user.

    Combines:
    - User values (current, phase, lifetime)
    - World agent discoveries
    - Recent conversation themes
    - Optional context (e.g., "free evening", "weekend", "need energy")

    Args:
        context: Optional context like time available, energy level, mood

    Returns:
        Personalized activity suggestions
    """
    from ..synthesis.profile import get_profile
    from ..world.world import get_opportunities
    from ..shared.log import get_recent_entries

    # Gather context
    sections = []

    # Profile (identity, values, behavioral patterns)
    profile = get_profile()
    if not profile.startswith("No identity"):
        sections.append(("Identity Profile", profile[:2000]))

    # Opportunities
    opportunities = get_opportunities(include_surfaced=False)
    if not opportunities.startswith("No opportunities"):
        sections.append(("Discovered Opportunities", opportunities))

    # Recent activity
    recent = get_recent_entries(days=7)
    if recent:
        sections.append(("Recent Activity (Last 7 Days)", recent[:2000]))

    # Conversation themes
    themes = get_conversation_themes("week")
    if themes and not "No conversations" in themes:
        sections.append(("Conversation Themes This Week", themes))

    # Build output
    lines = ["## Activity Suggestions"]

    if context:
        lines.append(f"\n**Context:** {context}")

    lines.append("\n### Based on your values and interests:")
    lines.append("")

    if not sections:
        lines.append("I don't have enough information about your values and interests yet.")
        lines.append("Share more about what matters to you, and I'll be able to make better suggestions.")
        return "\n".join(lines)

    # Include the gathered context for the agent to reason about
    lines.append("**What I know about you:**")
    lines.append("")

    for title, content in sections:
        # Truncate long sections
        preview = content[:500] + "..." if len(content) > 500 else content
        lines.append(f"**{title}:**")
        lines.append(preview)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Based on this understanding, I can suggest activities that align with your values.*")
    lines.append("*Tell me more about what you're looking for (energy level, time available, mood) for tailored suggestions.*")

    return "\n".join(lines)


def get_personalized_context() -> str:
    """
    Get a comprehensive view of the user for personalized responses.

    Returns:
        Combined context from values, recent activity, and patterns
    """
    from ..synthesis.profile import get_profile
    from ..shared.log import get_recent_entries

    lines = ["## User Context"]

    # Profile
    profile = get_profile()
    if not profile.startswith("No identity"):
        lines.append("\n### Identity Profile")
        lines.append(profile[:1500])

    # Recent activity
    recent = get_recent_entries(days=3)
    if recent:
        lines.append("\n### Recent Activity")
        lines.append(recent[:1000])

    # Conversation themes
    themes = get_conversation_themes("week")
    if themes and "No conversations" not in themes:
        lines.append("\n### Recent Conversation Themes")
        lines.append(themes)

    return "\n".join(lines)


CONVERSATION_HISTORY_HANDLERS = {
    "get_conversations_for_date": get_conversations_for_date,
    "search_conversations": search_conversations,
    "get_conversation_themes": get_conversation_themes,
    "get_recent_conversations": get_recent_conversations,
    "load_previous_conversation": load_previous_conversation,
    "suggest_activities": suggest_activities,
    "get_personalized_context": get_personalized_context,
}
