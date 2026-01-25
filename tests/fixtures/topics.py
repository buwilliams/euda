"""
Topic test fixtures and factories.
"""

from typing import Optional, List
from datetime import datetime


def create_test_topic(
    name: str = "Test Topic",
    description: str = None,
    status: str = "todo",
    tags: List[str] = None,
    assignee: str = None,
    due_date: str = None,
    someday: bool = False,
    parent_id: str = None,
    created_by: str = "user",
    **overrides
) -> dict:
    """Create a topic dictionary for testing (does NOT persist to database).

    For actual database operations, use the create_topic tool directly.

    Args:
        name: Topic name
        description: Topic description
        status: Topic status (todo, working, done, error, archived)
        tags: List of tags
        assignee: Agent ID assigned to this topic
        due_date: Due date (YYYY-MM-DD)
        someday: Whether this is a someday/maybe topic
        parent_id: Parent topic ID
        created_by: Who created the topic
        **overrides: Additional fields

    Returns:
        Topic dictionary (not persisted)
    """
    now = datetime.utcnow().isoformat() + "Z"

    topic = {
        "id": f"topic-test-{name.lower().replace(' ', '-')[:8]}",
        "name": name,
        "description": description,
        "status": status,
        "tags": tags or [],
        "assignee": assignee,
        "due_date": due_date,
        "someday": someday,
        "parent_id": parent_id,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "agent_id": None,
        "pending_from": None,
        "log": []
    }
    topic.update(overrides)
    return topic


def create_topic_with_tags(tags: List[str], **kwargs) -> dict:
    """Create a topic with specific tags."""
    return create_test_topic(tags=tags, **kwargs)


def create_waiting_topic(waiting_for: str = "user", **kwargs) -> dict:
    """Create a topic with a waiting:* tag."""
    return create_test_topic(tags=[f"waiting:{waiting_for}"], **kwargs)


def create_blocked_topic(blocked_by: str = "dependency", **kwargs) -> dict:
    """Create a topic with a blocked:* tag."""
    return create_test_topic(tags=[f"blocked:{blocked_by}"], **kwargs)


def create_someday_topic(**kwargs) -> dict:
    """Create a someday/maybe topic."""
    return create_test_topic(someday=True, **kwargs)


def create_future_topic(days_ahead: int = 7, **kwargs) -> dict:
    """Create a topic with a future due date."""
    from datetime import date, timedelta
    future_date = (date.today() + timedelta(days=days_ahead)).isoformat()
    return create_test_topic(due_date=future_date, **kwargs)


def create_assigned_topic(agent_id: str = "test-agent", **kwargs) -> dict:
    """Create a topic assigned to a specific agent."""
    return create_test_topic(assignee=agent_id, **kwargs)
