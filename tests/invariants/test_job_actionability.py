"""
Job Actionability Invariant Tests.

Spec: specs/1_agents.md lines 169-189, specs/2_data.md

These tests verify the job actionability rules that determine which jobs
an agent should work on.

Invariants tested:
- Jobs with waiting:* tags are never actionable
- Jobs with blocked:* tags are never actionable
- Jobs with someday=true are never actionable
- Jobs with future due_date are not actionable (unless actionable=False)
- Unassigned jobs are not returned for assignee filter
- Jobs claimed by other agents are excluded when actionable=True
"""

import pytest
from datetime import date, timedelta


@pytest.fixture
def setup_jobs(test_db, mock_emit_event, mock_emit_ui_event):
    """Setup common jobs for testing actionability."""
    from src.tools.data.jobs import create_job, _get_connection

    # Bypass the default parent routing for tests
    conn = _get_connection()

    jobs = {}

    # Normal actionable job
    jobs["normal"] = create_job(
        name="Normal Job",
        assignees=["test-agent"],
        parent_id=None,
        created_by="test"
    )

    # Job with waiting tag
    jobs["waiting"] = create_job(
        name="Waiting Job",
        assignees=["test-agent"],
        tags=["waiting:user-response"],
        parent_id=None,
        created_by="test"
    )

    # Job with blocked tag
    jobs["blocked"] = create_job(
        name="Blocked Job",
        assignees=["test-agent"],
        tags=["blocked:dependency"],
        parent_id=None,
        created_by="test"
    )

    # Someday job
    jobs["someday"] = create_job(
        name="Someday Job",
        assignees=["test-agent"],
        someday=True,
        parent_id=None,
        created_by="test"
    )

    # Future due date job
    future_date = (date.today() + timedelta(days=7)).isoformat()
    jobs["future"] = create_job(
        name="Future Job",
        assignees=["test-agent"],
        due_date=future_date,
        parent_id=None,
        created_by="test"
    )

    # Unassigned job
    jobs["unassigned"] = create_job(
        name="Unassigned Job",
        assignees=[],
        parent_id=None,
        created_by="test"
    )

    # Job claimed by another agent
    jobs["claimed"] = create_job(
        name="Claimed Job",
        assignees=["test-agent"],
        parent_id=None,
        created_by="test"
    )
    # Manually set in_progress_by
    conn.execute(
        "UPDATE jobs SET in_progress_by = ? WHERE id = ?",
        ("other-agent", jobs["claimed"]["id"])
    )
    conn.commit()

    return jobs


@pytest.mark.invariant
class TestJobActionabilityInvariants:
    """Test job actionability invariants from spec."""

    def test_actionable_excludes_waiting_tag(self, setup_jobs):
        """Jobs with waiting:* tags should never be actionable.

        Spec: Jobs waiting for external input are not actionable.
        """
        from src.tools.data.jobs import list_jobs

        actionable = list_jobs(assignee="test-agent", actionable=True)
        job_ids = [j["id"] for j in actionable]

        assert setup_jobs["waiting"]["id"] not in job_ids, \
            "Jobs with waiting:* tags must not be actionable"

    def test_actionable_excludes_blocked_tag(self, setup_jobs):
        """Jobs with blocked:* tags should never be actionable.

        Spec: Jobs blocked by dependencies are not actionable.
        """
        from src.tools.data.jobs import list_jobs

        actionable = list_jobs(assignee="test-agent", actionable=True)
        job_ids = [j["id"] for j in actionable]

        assert setup_jobs["blocked"]["id"] not in job_ids, \
            "Jobs with blocked:* tags must not be actionable"

    def test_actionable_excludes_someday(self, setup_jobs):
        """Jobs with someday=true should never be actionable.

        Spec: Someday/maybe jobs are not in the active queue.
        """
        from src.tools.data.jobs import list_jobs

        actionable = list_jobs(assignee="test-agent", actionable=True)
        job_ids = [j["id"] for j in actionable]

        assert setup_jobs["someday"]["id"] not in job_ids, \
            "Someday jobs must not be actionable"

    def test_actionable_excludes_future_due(self, setup_jobs):
        """Jobs with future due_date should not be actionable.

        Spec: Only jobs due today or past (or no due date) are actionable.
        """
        from src.tools.data.jobs import list_jobs

        actionable = list_jobs(assignee="test-agent", actionable=True)
        job_ids = [j["id"] for j in actionable]

        assert setup_jobs["future"]["id"] not in job_ids, \
            "Future-dated jobs must not be actionable"

    def test_actionable_requires_assignee(self, setup_jobs):
        """Unassigned jobs should not be returned for assignee filter.

        Spec: Agent only sees jobs assigned to them.
        """
        from src.tools.data.jobs import list_jobs

        assigned_jobs = list_jobs(assignee="test-agent")
        job_ids = [j["id"] for j in assigned_jobs]

        assert setup_jobs["unassigned"]["id"] not in job_ids, \
            "Unassigned jobs must not appear in assignee-filtered results"

    def test_actionable_excludes_other_claimed(self, setup_jobs):
        """Jobs claimed by other agents should be excluded when actionable.

        Spec: in_progress_by != agent_id means another agent is working on it.
        """
        from src.tools.data.jobs import list_jobs

        actionable = list_jobs(assignee="test-agent", actionable=True)
        job_ids = [j["id"] for j in actionable]

        assert setup_jobs["claimed"]["id"] not in job_ids, \
            "Jobs claimed by other agents must not be actionable"

    def test_normal_job_is_actionable(self, setup_jobs):
        """Normal job without blocking conditions should be actionable.

        This is the positive case to ensure we're not over-filtering.
        """
        from src.tools.data.jobs import list_jobs

        actionable = list_jobs(assignee="test-agent", actionable=True)
        job_ids = [j["id"] for j in actionable]

        assert setup_jobs["normal"]["id"] in job_ids, \
            "Normal jobs should be actionable"


@pytest.mark.invariant
class TestUnblockBehavior:
    """Test that unblocking jobs makes them actionable again."""

    def test_unblock_removes_waiting_tag(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Unblocking a job should remove waiting:* tags."""
        from src.tools.data.jobs import create_job, unblock_job, get_job

        job = create_job(
            name="Waiting Job",
            assignees=["test-agent"],
            tags=["waiting:user-response", "important"],
            parent_id=None,
            created_by="test"
        )

        result = unblock_job(job["id"])
        assert result is True

        updated = get_job(job["id"])
        assert "waiting:user-response" not in updated["tags"]
        assert "important" in updated["tags"]  # Other tags preserved

    def test_unblock_removes_blocked_tag(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Unblocking a job should remove blocked:* tags."""
        from src.tools.data.jobs import create_job, unblock_job, get_job

        job = create_job(
            name="Blocked Job",
            assignees=["test-agent"],
            tags=["blocked:dependency"],
            parent_id=None,
            created_by="test"
        )

        result = unblock_job(job["id"])
        assert result is True

        updated = get_job(job["id"])
        assert "blocked:dependency" not in updated["tags"]

    def test_unblock_returns_false_if_not_blocked(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Unblocking a job that's not blocked should return False."""
        from src.tools.data.jobs import create_job, unblock_job

        job = create_job(
            name="Normal Job",
            assignees=["test-agent"],
            parent_id=None,
            created_by="test"
        )

        result = unblock_job(job["id"])
        assert result is False
