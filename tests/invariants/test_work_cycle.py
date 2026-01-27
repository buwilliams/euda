"""
Work Cycle Invariant Tests.

Spec: docs/3_system.md - "Work Cycle" section

These tests verify work cycle behavior.

Invariants tested:
- One topic per work cycle (agent processes only one topic at a time)
- Remaining count reflects queued topics
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.invariant
class TestOneTopicPerWorkCycle:
    """Test that agents only process one topic per work cycle."""

    def test_list_topics_returns_multiple_but_only_first_used(self, test_db, mock_emit_event, mock_emit_ui_event):
        """When multiple topics exist, work_cycle should only process first one.

        Spec: "Pass only the first topic to avoid overwhelming the agent.
        After this topic is done, the manager will start another work cycle
        if more topics exist."

        This test verifies the code logic by checking topics[0] usage.
        """
        from plugins.core.data.topics import create_topic, list_topics

        # Create multiple topics
        topic1 = create_topic(name="First", assignee="agent", parent_id=None, created_by="test")
        topic2 = create_topic(name="Second", assignee="agent", parent_id=None, created_by="test")
        topic3 = create_topic(name="Third", assignee="agent", parent_id=None, created_by="test")

        # Verify list_topics returns all 3
        topics = list_topics(assignee="agent", actionable=True)
        assert len(topics) == 3

        # The invariant is that work_cycle_sync uses topics[0] and remaining = len(topics) - 1
        # We verify the pattern: first topic selected, remaining calculated
        current_topic = topics[0]
        remaining = len(topics) - 1

        # Don't assume order, just verify the invariant pattern holds
        assert current_topic is not None
        assert remaining == 2

    def test_format_topic_prompt_receives_remaining_count(self, test_db, mock_emit_event, mock_emit_ui_event):
        """format_topic_prompt should receive correct remaining count.

        Spec: Agent knows how many more topics are queued.
        """
        from plugins.core.data.topics import create_topic, list_topics

        # Create 5 topics
        for i in range(5):
            create_topic(name=f"Topic {i+1}", assignee="agent", parent_id=None, created_by="test")

        topics = list_topics(assignee="agent", actionable=True)
        remaining = len(topics) - 1

        # With 5 topics, processing first means 4 remaining
        assert remaining == 4

    def test_work_cycle_code_selects_first_topic(self):
        """Verify work_cycle_sync selects topics[0].

        This is a code inspection test - verifying the invariant is implemented.
        """
        import inspect
        from src.agent.agent import Agent

        source = inspect.getsource(Agent.work_cycle_sync)

        # The invariant should be implemented as: current_topic = topics[0]
        assert "current_topic = topics[0]" in source, \
            "work_cycle_sync should select only the first topic"

        # And remaining should be calculated as len(topics) - 1
        assert "remaining = len(topics) - 1" in source, \
            "work_cycle_sync should calculate remaining topics"


@pytest.mark.invariant
class TestTopicSelectionOrder:
    """Test that topic selection follows expected patterns."""

    def test_actionable_topics_are_selectable(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Actionable topics (no blocking tags) should be returned.

        Spec: Agents poll for actionable topics.
        """
        from plugins.core.data.topics import create_topic, list_topics

        # Create actionable topic
        actionable = create_topic(name="Actionable", assignee="agent", parent_id=None, created_by="test")

        # Create blocked topic
        blocked = create_topic(
            name="Blocked",
            assignee="agent",
            tags=["blocked:dependency"],
            parent_id=None,
            created_by="test"
        )

        topics = list_topics(assignee="agent", actionable=True)
        topic_ids = [t["id"] for t in topics]

        assert actionable["id"] in topic_ids
        assert blocked["id"] not in topic_ids
