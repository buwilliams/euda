"""
Topic Actionability Invariant Tests.

Spec: specs/1_agents.md lines 169-189, specs/2_data.md

These tests verify the topic actionability rules that determine which topics
an agent should work on.

Invariants tested:
- Topics with waiting:* tags are never actionable
- Topics with blocked:* tags are never actionable
- Topics with someday=true are never actionable
- Topics with future due_date are not actionable (unless actionable=False)
- Unassigned topics are not returned for assignee filter
- Topics claimed by other agents are excluded when actionable=True
"""

import pytest
from datetime import date, timedelta


@pytest.fixture
def setup_topics(test_db, mock_emit_event, mock_emit_ui_event):
    """Setup common topics for testing actionability."""
    from plugins.core.data.topics import create_topic, _get_connection

    # Bypass the default parent routing for tests
    conn = _get_connection()

    topics = {}

    # Normal actionable topic
    topics["normal"] = create_topic(
        name="Normal Topic",
        assignee="test-agent",
        parent_id=None,
        created_by="test"
    )

    # Topic with waiting tag
    topics["waiting"] = create_topic(
        name="Waiting Topic",
        assignee="test-agent",
        tags=["waiting:user-response"],
        parent_id=None,
        created_by="test"
    )

    # Topic with blocked tag
    topics["blocked"] = create_topic(
        name="Blocked Topic",
        assignee="test-agent",
        tags=["blocked:dependency"],
        parent_id=None,
        created_by="test"
    )

    # Someday topic
    topics["someday"] = create_topic(
        name="Someday Topic",
        assignee="test-agent",
        someday=True,
        parent_id=None,
        created_by="test"
    )

    # Future due date topic
    future_date = (date.today() + timedelta(days=7)).isoformat()
    topics["future"] = create_topic(
        name="Future Topic",
        assignee="test-agent",
        due_date=future_date,
        parent_id=None,
        created_by="test"
    )

    # Unassigned topic
    topics["unassigned"] = create_topic(
        name="Unassigned Topic",
        assignee=None,
        parent_id=None,
        created_by="test"
    )

    # Topic with status 'working' (another agent is processing it)
    topics["working"] = create_topic(
        name="Working Topic",
        assignee="test-agent",
        parent_id=None,
        created_by="test"
    )
    # Set status to 'working'
    conn.execute(
        "UPDATE topics SET status = 'working' WHERE id = ?",
        (topics["working"]["id"],)
    )
    conn.commit()

    return topics


@pytest.mark.invariant
class TestTopicActionabilityInvariants:
    """Test topic actionability invariants from spec."""

    def test_actionable_excludes_waiting_tag(self, setup_topics):
        """Topics with waiting:* tags should never be actionable.

        Spec: Topics waiting for external input are not actionable.
        """
        from plugins.core.data.topics import list_topics

        actionable = list_topics(assignee="test-agent", actionable=True)
        topic_ids = [t["id"] for t in actionable]

        assert setup_topics["waiting"]["id"] not in topic_ids, \
            "Topics with waiting:* tags must not be actionable"

    def test_actionable_excludes_blocked_tag(self, setup_topics):
        """Topics with blocked:* tags should never be actionable.

        Spec: Topics blocked by dependencies are not actionable.
        """
        from plugins.core.data.topics import list_topics

        actionable = list_topics(assignee="test-agent", actionable=True)
        topic_ids = [t["id"] for t in actionable]

        assert setup_topics["blocked"]["id"] not in topic_ids, \
            "Topics with blocked:* tags must not be actionable"

    def test_actionable_excludes_someday(self, setup_topics):
        """Topics with someday=true should never be actionable.

        Spec: Someday/maybe topics are not in the active queue.
        """
        from plugins.core.data.topics import list_topics

        actionable = list_topics(assignee="test-agent", actionable=True)
        topic_ids = [t["id"] for t in actionable]

        assert setup_topics["someday"]["id"] not in topic_ids, \
            "Someday topics must not be actionable"

    def test_actionable_excludes_future_due(self, setup_topics):
        """Topics with future due_date should not be actionable.

        Spec: Only topics due today or past (or no due date) are actionable.
        """
        from plugins.core.data.topics import list_topics

        actionable = list_topics(assignee="test-agent", actionable=True)
        topic_ids = [t["id"] for t in actionable]

        assert setup_topics["future"]["id"] not in topic_ids, \
            "Future-dated topics must not be actionable"

    def test_actionable_requires_assignee(self, setup_topics):
        """Unassigned topics should not be returned for assignee filter.

        Spec: Agent only sees topics assigned to them.
        """
        from plugins.core.data.topics import list_topics

        assigned_topics = list_topics(assignee="test-agent")
        topic_ids = [t["id"] for t in assigned_topics]

        assert setup_topics["unassigned"]["id"] not in topic_ids, \
            "Unassigned topics must not appear in assignee-filtered results"

    def test_actionable_excludes_working_status(self, setup_topics):
        """Topics with status='working' should be excluded when actionable.

        Spec: Topics with 'working' status are currently being processed.
        """
        from plugins.core.data.topics import list_topics

        actionable = list_topics(assignee="test-agent", actionable=True)
        topic_ids = [t["id"] for t in actionable]

        assert setup_topics["working"]["id"] not in topic_ids, \
            "Topics with 'working' status must not be actionable"

    def test_normal_topic_is_actionable(self, setup_topics):
        """Normal topic without blocking conditions should be actionable.

        This is the positive case to ensure we're not over-filtering.
        """
        from plugins.core.data.topics import list_topics

        actionable = list_topics(assignee="test-agent", actionable=True)
        topic_ids = [t["id"] for t in actionable]

        assert setup_topics["normal"]["id"] in topic_ids, \
            "Normal topics should be actionable"


@pytest.mark.invariant
class TestUnblockBehavior:
    """Test that unblocking topics makes them actionable again."""

    def test_unblock_removes_waiting_tag(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Unblocking a topic should remove waiting:* tags."""
        from plugins.core.data.topics import create_topic, unblock_topic, get_topic

        topic = create_topic(
            name="Waiting Topic",
            assignee="test-agent",
            tags=["waiting:user-response", "important"],
            parent_id=None,
            created_by="test"
        )

        result = unblock_topic(topic["id"])
        assert result is True

        updated = get_topic(topic["id"])
        assert "waiting:user-response" not in updated["tags"]
        assert "important" in updated["tags"]  # Other tags preserved

    def test_unblock_removes_blocked_tag(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Unblocking a topic should remove blocked:* tags."""
        from plugins.core.data.topics import create_topic, unblock_topic, get_topic

        topic = create_topic(
            name="Blocked Topic",
            assignee="test-agent",
            tags=["blocked:dependency"],
            parent_id=None,
            created_by="test"
        )

        result = unblock_topic(topic["id"])
        assert result is True

        updated = get_topic(topic["id"])
        assert "blocked:dependency" not in updated["tags"]

    def test_unblock_returns_false_if_not_blocked(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Unblocking a topic that's not blocked should return False."""
        from plugins.core.data.topics import create_topic, unblock_topic

        topic = create_topic(
            name="Normal Topic",
            assignee="test-agent",
            parent_id=None,
            created_by="test"
        )

        result = unblock_topic(topic["id"])
        assert result is False
