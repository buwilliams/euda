"""
Unit tests for topics module.

Tests for src/tools/data/topics.py
"""

import json
import pytest
from datetime import datetime


class TestTopicCreation:
    """Test topic creation functionality."""

    def test_create_topic_basic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Create a basic topicwith minimal fields."""
        from src.tools.data.topics import create_topic

        topic= create_topic(name="Test Topic", parent_id=None, created_by="test")

        assert topic["name"] == "Test Topic"
        assert topic["status"] == "todo"
        assert topic["id"].startswith("topic-")
        assert len(topic["id"]) == 14  # "topic-" (6 chars) + 8 hex chars

    def test_create_topic_with_all_fields(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Create a topicwith all optional fields."""
        from src.tools.data.topics import create_topic

        topic= create_topic(
            name="Full Topic",
            description="A complete topic",
            parent_id=None,
            tags=["important", "urgent"],
            assignee="agent1",
            due_date="2024-12-31",
            someday=False,
            created_by="test"
        )

        assert topic["name"] == "Full Topic"
        assert topic["description"] == "A complete topic"
        assert topic["tags"] == ["important", "urgent"]
        assert topic["assignee"] == "agent1"
        assert topic["due_date"] == "2024-12-31"
        assert topic["someday"] is False

    def test_create_topic_with_someday(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Create a someday/maybe topic."""
        from src.tools.data.topics import create_topic

        topic= create_topic(name="Maybe Later", someday=True, parent_id=None, created_by="test")

        assert topic["someday"] is True

    def test_create_topic_adds_log_entry(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Created topicshould have initial log entry."""
        from src.tools.data.topics import create_topic

        topic= create_topic(name="Logged Topic", parent_id=None, created_by="test")

        assert len(topic["log"]) == 1
        assert topic["log"][0]["action"] == "created"
        assert topic["log"][0]["agent"] == "test"


class TestTopicRetrieval:
    """Test topic retrieval functionality."""

    def test_get_topic_exists(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Get an existing topicby ID."""
        from src.tools.data.topics import create_topic, get_topic

        created = create_topic(name="Find Me", parent_id=None, created_by="test")
        found = get_topic(created["id"])

        assert found is not None
        assert found["name"] == "Find Me"
        assert found["id"] == created["id"]

    def test_get_topic_not_exists(self, test_db):
        """Get a non-existent topicreturns None."""
        from src.tools.data.topics import get_topic

        result = get_topic("topic-nonexistent")

        assert result is None

    def test_list_topics_by_status(self, test_db, mock_emit_event, mock_emit_ui_event):
        """List topics filtered by status."""
        from src.tools.data.topics import create_topic, complete_topic, list_topics

        topic1 = create_topic(name="Todo Topic", parent_id=None, created_by="test")
        topic2 = create_topic(name="Done Topic", parent_id=None, created_by="test")
        complete_topic(topic2["id"], agent="test")

        todo_topics = list_topics(status="todo")
        done_topics = list_topics(status="done")

        todo_ids = [j["id"] for j in todo_topics]
        done_ids = [j["id"] for j in done_topics]

        assert topic1["id"] in todo_ids
        assert topic2["id"] in done_ids
        assert topic2["id"] not in todo_ids

    def test_list_topics_by_tag(self, test_db, mock_emit_event, mock_emit_ui_event):
        """List topics filtered by tag."""
        from src.tools.data.topics import create_topic, list_topics

        topic1 = create_topic(name="Tagged Topic", tags=["important"], parent_id=None, created_by="test")
        topic2 = create_topic(name="Untagged Topic", parent_id=None, created_by="test")

        tagged = list_topics(tag="important")
        topic_ids = [j["id"] for j in tagged]

        assert topic1["id"] in topic_ids
        assert topic2["id"] not in topic_ids


class TestTopicUpdate:
    """Test topic update functionality."""

    def test_update_topic_name(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Update topicname."""
        from src.tools.data.topics import create_topic, update_topic

        topic= create_topic(name="Original", parent_id=None, created_by="test")
        updated = update_topic(topic["id"], name="Updated")

        assert updated["name"] == "Updated"

    def test_update_topic_tags(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Update topictags."""
        from src.tools.data.topics import create_topic, update_topic

        topic= create_topic(name="Tagged", tags=["old"], parent_id=None, created_by="test")
        updated = update_topic(topic["id"], tags=["new1", "new2"])

        assert updated["tags"] == ["new1", "new2"]

    def test_update_topic_not_found(self, test_db):
        """Update non-existent topicreturns error."""
        from src.tools.data.topics import update_topic

        result = update_topic("topic-nonexistent", name="New Name")

        assert "error" in result

    def test_update_topic_cannot_set_working_status(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot set status to 'working' via update_topic - must use claim_topic."""
        from src.tools.data.topics import create_topic, update_topic

        topic= create_topic(name="Test Topic", assignee="agent1", parent_id=None, created_by="test")
        result = update_topic(topic["id"], status="working")

        assert "error" in result
        assert "claim_topic" in result["error"]


class TestTopicCompletion:
    """Test topic completion functionality."""

    def test_complete_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Complete a topic."""
        from src.tools.data.topics import create_topic, complete_topic

        topic= create_topic(name="Complete Me", parent_id=None, created_by="test")
        completed = complete_topic(topic["id"], agent="test")

        assert completed["status"] == "done"
        assert "completed_at" in completed

    def test_complete_topic_adds_log(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Completing topicadds log entry."""
        from src.tools.data.topics import create_topic, complete_topic

        topic= create_topic(name="Log Me", parent_id=None, created_by="test")
        completed = complete_topic(topic["id"], agent="test-agent")

        completion_log = [l for l in completed["log"] if l["action"] == "completed"]
        assert len(completion_log) == 1
        assert completion_log[0]["agent"] == "test-agent"

    def test_restore_completed_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Restore a completed topicback to todo."""
        from src.tools.data.topics import create_topic, complete_topic, restore_topic

        topic= create_topic(name="Restore Me", parent_id=None, created_by="test")
        complete_topic(topic["id"], agent="test")
        restored = restore_topic(topic["id"], agent="test")

        assert restored["status"] == "todo"
        assert "completed_at" not in restored or restored["completed_at"] is None

    def test_complete_sets_done_status(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Completing a topicsets status to done."""
        from src.tools.data.topics import create_topic, claim_topic, complete_topic, get_topic

        topic= create_topic(name="Complete Me", assignee="agent1", parent_id=None, created_by="test")
        claim_topic(topic["id"], "agent1")
        complete_topic(topic["id"], agent="agent1")

        updated = get_topic(topic["id"])
        assert updated["status"] == "done"

    def test_release_noop_for_completed_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Release is a no-op for already completed topics - status stays done."""
        from src.tools.data.topics import create_topic, claim_topic, complete_topic, release_topic, get_topic

        topic= create_topic(name="Complete Then Release", assignee="agent1", parent_id=None, created_by="test")
        claim_topic(topic["id"], "agent1")
        complete_topic(topic["id"], agent="agent1")

        # Release should be a no-op since status is not 'working'
        release_topic(topic["id"], "agent1")

        updated = get_topic(topic["id"])
        assert updated["status"] == "done"  # Still done, not reset to todo


class TestTopicClaiming:
    """Test topic claim/release functionality."""

    def test_claim_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Claim a topicfor exclusive work."""
        from src.tools.data.topics import create_topic, claim_topic, get_topic

        topic= create_topic(name="Claim Me", assignee="agent1", parent_id=None, created_by="test")
        result = claim_topic(topic["id"], "agent1")

        assert result["claimed"] is True

        updated = get_topic(topic["id"])
        assert updated["status"] == "working"  # Per spec: claim sets status to 'working'

    def test_claim_unassigned_fails(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot claim topicnot assigned to the agent."""
        from src.tools.data.topics import create_topic, claim_topic

        topic= create_topic(name="Not Yours", assignee="agent1", parent_id=None, created_by="test")

        # Claim by different agent fails
        result = claim_topic(topic["id"], "agent2")
        assert "error" in result
        assert "not assigned" in result["error"].lower()

    def test_release_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Release a claimed topic."""
        from src.tools.data.topics import create_topic, claim_topic, release_topic, get_topic

        topic= create_topic(name="Release Me", assignee="agent1", parent_id=None, created_by="test")
        claim_topic(topic["id"], "agent1")
        release_topic(topic["id"], "agent1")

        updated = get_topic(topic["id"])
        assert updated["status"] == "todo"  # Per spec: release resets status to 'todo'


class TestTopicError:
    """Test topic error functionality."""

    def test_error_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Mark a topicas failed with error."""
        from src.tools.data.topics import create_topic, error_topic, get_topic

        topic= create_topic(name="Error Me", parent_id=None, created_by="test")
        result = error_topic(topic["id"], "Something went wrong", agent="test-agent")

        assert result["status"] == "error"

    def test_error_topic_adds_log(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Error topicshould add log entry with error message."""
        from src.tools.data.topics import create_topic, error_topic

        topic= create_topic(name="Log Error", parent_id=None, created_by="test")
        result = error_topic(topic["id"], "Database connection failed", agent="worker")

        error_logs = [l for l in result["log"] if "error:" in l.get("action", "")]
        assert len(error_logs) == 1
        assert "Database connection failed" in error_logs[0]["action"]
        assert error_logs[0]["agent"] == "worker"


class TestTopicHierarchy:
    """Test topic parent/child relationships."""

    def test_create_child_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Create a topicunder a parent."""
        from src.tools.data.topics import create_topic

        parent = create_topic(name="Parent", parent_id=None, created_by="test")
        child = create_topic(name="Child", parent_id=parent["id"], created_by="test")

        assert child["parent_id"] == parent["id"]

    def test_get_child_topics(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Get all children of a parent topic."""
        from src.tools.data.topics import create_topic, get_child_topics

        parent = create_topic(name="Parent", parent_id=None, created_by="test")
        child1 = create_topic(name="Child 1", parent_id=parent["id"], created_by="test")
        child2 = create_topic(name="Child 2", parent_id=parent["id"], created_by="test")
        orphan = create_topic(name="Orphan", parent_id=None, created_by="test")

        children = get_child_topics(parent["id"])
        child_ids = [c["id"] for c in children]

        assert child1["id"] in child_ids
        assert child2["id"] in child_ids
        assert orphan["id"] not in child_ids


class TestTopicHandoff:
    """Test topic handoff functionality."""

    def test_handoff_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Hand off a topicto another agent."""
        from src.tools.data.topics import create_topic, handoff_topic

        topic= create_topic(name="Hand Me Off", assignee="agent1", parent_id=None, created_by="test")
        result = handoff_topic(topic["id"], to="agent2", note="Please review", agent="agent1")

        assert result["assignee"] == "agent2"
        assert result["pending_from"] == "agent1"

    def test_handoff_adds_log(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Handoff should add log entry with note."""
        from src.tools.data.topics import create_topic, handoff_topic

        topic= create_topic(name="Log Handoff", assignee="agent1", parent_id=None, created_by="test")
        result = handoff_topic(topic["id"], to="agent2", note="Check this", agent="agent1")

        handoff_logs = [l for l in result["log"] if "Handed off" in l.get("action", "")]
        assert len(handoff_logs) == 1
        assert "Check this" in handoff_logs[0]["action"]

    def test_handoff_resets_working_to_todo(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Handoff should reset status to 'todo' if currently 'working'."""
        from src.tools.data.topics import create_topic, claim_topic, handoff_topic, get_topic

        topic = create_topic(name="Working Topic", assignee="agent1", parent_id=None, created_by="test")
        claim_topic(topic["id"], "agent1")  # Sets status to 'working'

        # Verify it's working
        working = get_topic(topic["id"])
        assert working["status"] == "working"

        # Handoff should reset to 'todo'
        result = handoff_topic(topic["id"], to="agent2", agent="agent1")
        assert result["status"] == "todo"

    def test_handoff_leaves_error_status_alone(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Handoff should not change 'error' status."""
        from src.tools.data.topics import create_topic, error_topic, handoff_topic

        topic = create_topic(name="Error Topic", assignee="agent1", parent_id=None, created_by="test")
        error_topic(topic["id"], "Something failed", agent="agent1")

        result = handoff_topic(topic["id"], to="agent2", agent="agent1")
        assert result["status"] == "error"

    def test_handoff_leaves_todo_status_alone(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Handoff should not change 'todo' status."""
        from src.tools.data.topics import create_topic, handoff_topic

        topic = create_topic(name="Todo Topic", assignee="agent1", parent_id=None, created_by="test")
        assert topic["status"] == "todo"

        result = handoff_topic(topic["id"], to="agent2", agent="agent1")
        assert result["status"] == "todo"


class TestTopicAssignment:
    """Test topic assignment functionality."""

    def test_assign_agent_basic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Assign an agent to a topic."""
        from src.tools.data.topics import create_topic, assign_agent

        topic = create_topic(name="Assign Me", parent_id=None, created_by="test")
        result = assign_agent(topic["id"], "agent1")

        assert result["assignee"] == "agent1"

    def test_assign_agent_resets_working_to_todo(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Assigning should reset status to 'todo' if currently 'working'."""
        from src.tools.data.topics import create_topic, claim_topic, assign_agent, get_topic

        topic = create_topic(name="Working Topic", assignee="agent1", parent_id=None, created_by="test")
        claim_topic(topic["id"], "agent1")  # Sets status to 'working'

        # Verify it's working
        working = get_topic(topic["id"])
        assert working["status"] == "working"

        # Assign to different agent should reset to 'todo'
        result = assign_agent(topic["id"], "agent2")
        assert result["status"] == "todo"
        assert result["assignee"] == "agent2"

    def test_assign_agent_leaves_error_status_alone(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Assignment should not change 'error' status."""
        from src.tools.data.topics import create_topic, error_topic, assign_agent

        topic = create_topic(name="Error Topic", parent_id=None, created_by="test")
        error_topic(topic["id"], "Something failed", agent="test")

        result = assign_agent(topic["id"], "agent1")
        assert result["status"] == "error"
        assert result["assignee"] == "agent1"

    def test_assign_agent_leaves_todo_status_alone(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Assignment should not change 'todo' status."""
        from src.tools.data.topics import create_topic, assign_agent

        topic = create_topic(name="Todo Topic", parent_id=None, created_by="test")
        assert topic["status"] == "todo"

        result = assign_agent(topic["id"], "agent1")
        assert result["status"] == "todo"

    def test_assign_same_agent_returns_error(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Assigning the same agent returns an error."""
        from src.tools.data.topics import create_topic, assign_agent

        topic = create_topic(name="Already Assigned", assignee="agent1", parent_id=None, created_by="test")

        result = assign_agent(topic["id"], "agent1")
        assert "error" in result


class TestSystemTopicProtection:
    """Test protection of system topics."""

    def test_cannot_complete_system_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot complete system container topics."""
        from src.tools.data.topics import create_topic, complete_topic

        topic= create_topic(
            name="System Container",
            tags=["system:projects"],
            parent_id=None,
            created_by="system"
        )
        result = complete_topic(topic["id"], agent="test")

        assert "error" in result

    def test_cannot_archive_system_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot archive system container topics."""
        from src.tools.data.topics import create_topic, archive_topic

        topic= create_topic(
            name="System Container",
            tags=["system:agents"],
            parent_id=None,
            created_by="system"
        )
        result = archive_topic(topic["id"], agent="test")

        assert "error" in result

    def test_cannot_claim_system_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot claim system container topics."""
        from src.tools.data.topics import create_topic, claim_topic

        topic= create_topic(
            name="Agents Container",
            tags=["system:agents"],
            parent_id=None,
            created_by="system"
        )
        result = claim_topic(topic["id"], "test-agent")

        assert "error" in result


class TestTopicDeletion:
    """Test topic deletion functionality."""

    def test_delete_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Delete a topic."""
        from src.tools.data.topics import create_topic, delete_topic, get_topic

        topic= create_topic(name="Delete Me", parent_id=None, created_by="test")
        result = delete_topic(topic["id"])

        assert result["deleted"] == topic["id"]
        assert get_topic(topic["id"]) is None

    def test_delete_topic_with_children(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Delete topicand its children."""
        from src.tools.data.topics import create_topic, delete_topic, get_topic

        parent = create_topic(name="Parent", parent_id=None, created_by="test")
        child = create_topic(name="Child", parent_id=parent["id"], created_by="test")

        delete_topic(parent["id"], delete_children=True)

        assert get_topic(parent["id"]) is None
        assert get_topic(child["id"]) is None

    def test_cannot_delete_system_topic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot delete system topics."""
        from src.tools.data.topics import create_topic, delete_topic

        topic= create_topic(
            name="System",
            tags=["system:projects"],
            parent_id=None,
            created_by="system"
        )
        result = delete_topic(topic["id"])

        assert "error" in result


class TestInterestExtractionOnAssignment:
    """Test automatic interest extraction when assigning topics to observing agents."""

    def test_assign_to_observing_agent_creates_interests(self, test_db, patch_data_dir, mock_emit_event, mock_emit_ui_event, create_test_agent):
        """Assigning a topic to an observation-enabled agent extracts interests."""
        from src.tools.data.topics import create_topic, assign_agent
        from src.tools.data.memory import list_memory

        # Create an observation-enabled agent
        create_test_agent("observer", observation={"enabled": True, "sources": ["chat"]})

        # Create memory directory
        agent_dir = patch_data_dir / "agents" / "observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Create topic with meaningful keywords
        topic = create_topic(
            name="Learn Python programming",
            description="Study machine learning basics",
            parent_id=None,
            created_by="test"
        )

        # Assign to observing agent
        assign_agent(topic["id"], "observer")

        # Check interests were created
        memories = list_memory(agent_id="observer")
        interests = [m for m in memories if m.get("type") == "interest"]

        assert len(interests) > 0
        interest_keywords = [i["short_description"].lower() for i in interests]
        # Should have extracted at least one keyword
        assert any(kw in interest_keywords for kw in ["python", "programming", "learn", "machine", "learning", "basics", "study"])

    def test_assign_to_non_observing_agent_no_interests(self, test_db, patch_data_dir, mock_emit_event, mock_emit_ui_event, create_test_agent):
        """Assigning a topic to a non-observing agent does not create interests."""
        from src.tools.data.topics import create_topic, assign_agent
        from src.tools.data.memory import list_memory

        # Create a non-observing agent
        create_test_agent("non-observer")

        # Create memory directory
        agent_dir = patch_data_dir / "agents" / "non-observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Create topic
        topic = create_topic(
            name="Learn Python programming",
            parent_id=None,
            created_by="test"
        )

        # Assign to non-observing agent
        assign_agent(topic["id"], "non-observer")

        # Check no interests were created
        memories = list_memory(agent_id="non-observer")
        interests = [m for m in memories if m.get("type") == "interest"]

        assert len(interests) == 0

    def test_assign_does_not_duplicate_interests(self, test_db, patch_data_dir, mock_emit_event, mock_emit_ui_event, create_test_agent):
        """Assigning multiple topics with same keywords doesn't duplicate interests."""
        from src.tools.data.topics import create_topic, assign_agent
        from src.tools.data.memory import list_memory, add_memory

        # Create an observation-enabled agent
        create_test_agent("observer", observation={"enabled": True, "sources": ["chat"]})

        # Create memory directory
        agent_dir = patch_data_dir / "agents" / "observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Pre-add an interest
        add_memory(short_description="python", type="interest", agent_id="observer")

        # Create topic with same keyword
        topic = create_topic(
            name="Advanced Python techniques",
            parent_id=None,
            created_by="test"
        )

        # Assign to observing agent
        assign_agent(topic["id"], "observer")

        # Check no duplicate python interest
        memories = list_memory(agent_id="observer")
        python_interests = [m for m in memories if m.get("type") == "interest" and m.get("short_description", "").lower() == "python"]

        assert len(python_interests) == 1  # Only the original one
