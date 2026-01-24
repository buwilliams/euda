"""
Unit tests for jobs module.

Tests for src/tools/data/jobs.py
"""

import json
import pytest
from datetime import datetime


class TestJobCreation:
    """Test job creation functionality."""

    def test_create_job_basic(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Create a basic job with minimal fields."""
        from src.tools.data.jobs import create_job

        job = create_job(name="Test Job", parent_id=None, created_by="test")

        assert job["name"] == "Test Job"
        assert job["status"] == "todo"
        assert job["id"].startswith("job-")
        assert len(job["id"]) == 12  # job- + 8 hex chars

    def test_create_job_with_all_fields(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Create a job with all optional fields."""
        from src.tools.data.jobs import create_job

        job = create_job(
            name="Full Job",
            description="A complete job",
            parent_id=None,
            tags=["important", "urgent"],
            assignees=["agent1", "agent2"],
            due_date="2024-12-31",
            someday=False,
            created_by="test"
        )

        assert job["name"] == "Full Job"
        assert job["description"] == "A complete job"
        assert job["tags"] == ["important", "urgent"]
        assert job["assignees"] == ["agent1", "agent2"]
        assert job["due_date"] == "2024-12-31"
        assert job["someday"] is False

    def test_create_job_with_someday(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Create a someday/maybe job."""
        from src.tools.data.jobs import create_job

        job = create_job(name="Maybe Later", someday=True, parent_id=None, created_by="test")

        assert job["someday"] is True

    def test_create_job_adds_log_entry(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Created job should have initial log entry."""
        from src.tools.data.jobs import create_job

        job = create_job(name="Logged Job", parent_id=None, created_by="test")

        assert len(job["log"]) == 1
        assert job["log"][0]["action"] == "created"
        assert job["log"][0]["agent"] == "test"


class TestJobRetrieval:
    """Test job retrieval functionality."""

    def test_get_job_exists(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Get an existing job by ID."""
        from src.tools.data.jobs import create_job, get_job

        created = create_job(name="Find Me", parent_id=None, created_by="test")
        found = get_job(created["id"])

        assert found is not None
        assert found["name"] == "Find Me"
        assert found["id"] == created["id"]

    def test_get_job_not_exists(self, test_db):
        """Get a non-existent job returns None."""
        from src.tools.data.jobs import get_job

        result = get_job("job-nonexistent")

        assert result is None

    def test_list_jobs_by_status(self, test_db, mock_emit_event, mock_emit_ui_event):
        """List jobs filtered by status."""
        from src.tools.data.jobs import create_job, complete_job, list_jobs

        job1 = create_job(name="Todo Job", parent_id=None, created_by="test")
        job2 = create_job(name="Done Job", parent_id=None, created_by="test")
        complete_job(job2["id"], agent="test")

        todo_jobs = list_jobs(status="todo")
        done_jobs = list_jobs(status="done")

        todo_ids = [j["id"] for j in todo_jobs]
        done_ids = [j["id"] for j in done_jobs]

        assert job1["id"] in todo_ids
        assert job2["id"] in done_ids
        assert job2["id"] not in todo_ids

    def test_list_jobs_by_tag(self, test_db, mock_emit_event, mock_emit_ui_event):
        """List jobs filtered by tag."""
        from src.tools.data.jobs import create_job, list_jobs

        job1 = create_job(name="Tagged Job", tags=["important"], parent_id=None, created_by="test")
        job2 = create_job(name="Untagged Job", parent_id=None, created_by="test")

        tagged = list_jobs(tag="important")
        job_ids = [j["id"] for j in tagged]

        assert job1["id"] in job_ids
        assert job2["id"] not in job_ids


class TestJobUpdate:
    """Test job update functionality."""

    def test_update_job_name(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Update job name."""
        from src.tools.data.jobs import create_job, update_job

        job = create_job(name="Original", parent_id=None, created_by="test")
        updated = update_job(job["id"], name="Updated")

        assert updated["name"] == "Updated"

    def test_update_job_tags(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Update job tags."""
        from src.tools.data.jobs import create_job, update_job

        job = create_job(name="Tagged", tags=["old"], parent_id=None, created_by="test")
        updated = update_job(job["id"], tags=["new1", "new2"])

        assert updated["tags"] == ["new1", "new2"]

    def test_update_job_not_found(self, test_db):
        """Update non-existent job returns error."""
        from src.tools.data.jobs import update_job

        result = update_job("job-nonexistent", name="New Name")

        assert "error" in result


class TestJobCompletion:
    """Test job completion functionality."""

    def test_complete_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Complete a job."""
        from src.tools.data.jobs import create_job, complete_job

        job = create_job(name="Complete Me", parent_id=None, created_by="test")
        completed = complete_job(job["id"], agent="test")

        assert completed["status"] == "done"
        assert "completed_at" in completed

    def test_complete_job_adds_log(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Completing job adds log entry."""
        from src.tools.data.jobs import create_job, complete_job

        job = create_job(name="Log Me", parent_id=None, created_by="test")
        completed = complete_job(job["id"], agent="test-agent")

        completion_log = [l for l in completed["log"] if l["action"] == "completed"]
        assert len(completion_log) == 1
        assert completion_log[0]["agent"] == "test-agent"

    def test_restore_completed_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Restore a completed job back to todo."""
        from src.tools.data.jobs import create_job, complete_job, restore_job

        job = create_job(name="Restore Me", parent_id=None, created_by="test")
        complete_job(job["id"], agent="test")
        restored = restore_job(job["id"], agent="test")

        assert restored["status"] == "todo"
        assert "completed_at" not in restored or restored["completed_at"] is None


class TestJobClaiming:
    """Test job claim/release functionality."""

    def test_claim_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Claim a job for exclusive work."""
        from src.tools.data.jobs import create_job, claim_job, get_job

        job = create_job(name="Claim Me", assignees=["agent1"], parent_id=None, created_by="test")
        result = claim_job(job["id"], "agent1")

        assert result["claimed"] is True

        updated = get_job(job["id"])
        assert updated["in_progress_by"] == "agent1"
        assert updated["status"] == "working"  # Per spec: claim sets status to 'working'

    def test_claim_already_claimed_fails(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot claim job already claimed by another agent."""
        from src.tools.data.jobs import create_job, claim_job

        job = create_job(name="Contested", assignees=["agent1", "agent2"], parent_id=None, created_by="test")

        # First claim succeeds
        result1 = claim_job(job["id"], "agent1")
        assert result1["claimed"] is True

        # Second claim fails
        result2 = claim_job(job["id"], "agent2")
        assert "error" in result2
        assert "claimed by" in result2["error"].lower()

    def test_release_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Release a claimed job."""
        from src.tools.data.jobs import create_job, claim_job, release_job, get_job

        job = create_job(name="Release Me", assignees=["agent1"], parent_id=None, created_by="test")
        claim_job(job["id"], "agent1")
        release_job(job["id"], "agent1")

        updated = get_job(job["id"])
        assert updated["in_progress_by"] is None
        assert updated["status"] == "todo"  # Per spec: release resets status to 'todo'


class TestJobError:
    """Test job error functionality."""

    def test_error_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Mark a job as failed with error."""
        from src.tools.data.jobs import create_job, error_job, get_job

        job = create_job(name="Error Me", parent_id=None, created_by="test")
        result = error_job(job["id"], "Something went wrong", agent="test-agent")

        assert result["status"] == "error"
        assert result["in_progress_by"] is None

    def test_error_job_adds_log(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Error job should add log entry with error message."""
        from src.tools.data.jobs import create_job, error_job

        job = create_job(name="Log Error", parent_id=None, created_by="test")
        result = error_job(job["id"], "Database connection failed", agent="worker")

        error_logs = [l for l in result["log"] if "error:" in l.get("action", "")]
        assert len(error_logs) == 1
        assert "Database connection failed" in error_logs[0]["action"]
        assert error_logs[0]["agent"] == "worker"


class TestJobHierarchy:
    """Test job parent/child relationships."""

    def test_create_child_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Create a job under a parent."""
        from src.tools.data.jobs import create_job

        parent = create_job(name="Parent", parent_id=None, created_by="test")
        child = create_job(name="Child", parent_id=parent["id"], created_by="test")

        assert child["parent_id"] == parent["id"]

    def test_get_child_jobs(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Get all children of a parent job."""
        from src.tools.data.jobs import create_job, get_child_jobs

        parent = create_job(name="Parent", parent_id=None, created_by="test")
        child1 = create_job(name="Child 1", parent_id=parent["id"], created_by="test")
        child2 = create_job(name="Child 2", parent_id=parent["id"], created_by="test")
        orphan = create_job(name="Orphan", parent_id=None, created_by="test")

        children = get_child_jobs(parent["id"])
        child_ids = [c["id"] for c in children]

        assert child1["id"] in child_ids
        assert child2["id"] in child_ids
        assert orphan["id"] not in child_ids


class TestJobHandoff:
    """Test job handoff functionality."""

    def test_handoff_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Hand off a job to another agent."""
        from src.tools.data.jobs import create_job, handoff_job

        job = create_job(name="Hand Me Off", assignees=["agent1"], parent_id=None, created_by="test")
        result = handoff_job(job["id"], to="agent2", note="Please review", agent="agent1")

        assert result["assignees"] == ["agent2"]
        assert result["pending_from"] == "agent1"

    def test_handoff_adds_log(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Handoff should add log entry with note."""
        from src.tools.data.jobs import create_job, handoff_job

        job = create_job(name="Log Handoff", assignees=["agent1"], parent_id=None, created_by="test")
        result = handoff_job(job["id"], to="agent2", note="Check this", agent="agent1")

        handoff_logs = [l for l in result["log"] if "Handed off" in l.get("action", "")]
        assert len(handoff_logs) == 1
        assert "Check this" in handoff_logs[0]["action"]


class TestSystemJobProtection:
    """Test protection of system jobs."""

    def test_cannot_complete_system_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot complete system container jobs."""
        from src.tools.data.jobs import create_job, complete_job

        job = create_job(
            name="System Container",
            tags=["system:projects"],
            parent_id=None,
            created_by="system"
        )
        result = complete_job(job["id"], agent="test")

        assert "error" in result

    def test_cannot_archive_system_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot archive system container jobs."""
        from src.tools.data.jobs import create_job, archive_job

        job = create_job(
            name="System Container",
            tags=["system:agents"],
            parent_id=None,
            created_by="system"
        )
        result = archive_job(job["id"], agent="test")

        assert "error" in result

    def test_cannot_claim_system_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot claim system container jobs."""
        from src.tools.data.jobs import create_job, claim_job

        job = create_job(
            name="Agents Container",
            tags=["system:agents"],
            parent_id=None,
            created_by="system"
        )
        result = claim_job(job["id"], "test-agent")

        assert "error" in result


class TestJobDeletion:
    """Test job deletion functionality."""

    def test_delete_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Delete a job."""
        from src.tools.data.jobs import create_job, delete_job, get_job

        job = create_job(name="Delete Me", parent_id=None, created_by="test")
        result = delete_job(job["id"])

        assert result["deleted"] == job["id"]
        assert get_job(job["id"]) is None

    def test_delete_job_with_children(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Delete job and its children."""
        from src.tools.data.jobs import create_job, delete_job, get_job

        parent = create_job(name="Parent", parent_id=None, created_by="test")
        child = create_job(name="Child", parent_id=parent["id"], created_by="test")

        delete_job(parent["id"], delete_children=True)

        assert get_job(parent["id"]) is None
        assert get_job(child["id"]) is None

    def test_cannot_delete_system_job(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Cannot delete system jobs."""
        from src.tools.data.jobs import create_job, delete_job

        job = create_job(
            name="System",
            tags=["system:projects"],
            parent_id=None,
            created_by="system"
        )
        result = delete_job(job["id"])

        assert "error" in result
