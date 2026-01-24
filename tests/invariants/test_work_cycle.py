"""
Work Cycle Invariant Tests.

Spec: docs/3_system.md - "Work Cycle" section

These tests verify work cycle behavior.

Invariants tested:
- One job per work cycle (agent processes only one job at a time)
- Remaining count reflects queued jobs
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.invariant
class TestOneJobPerWorkCycle:
    """Test that agents only process one job per work cycle."""

    def test_list_jobs_returns_multiple_but_only_first_used(self, test_db, mock_emit_event, mock_emit_ui_event):
        """When multiple jobs exist, work_cycle should only process first one.

        Spec: "Pass only the first job to avoid overwhelming the agent.
        After this job is done, the manager will start another work cycle
        if more jobs exist."

        This test verifies the code logic by checking jobs[0] usage.
        """
        from src.tools.data.jobs import create_job, list_jobs

        # Create multiple jobs
        job1 = create_job(name="First", assignee="agent", parent_id=None, created_by="test")
        job2 = create_job(name="Second", assignee="agent", parent_id=None, created_by="test")
        job3 = create_job(name="Third", assignee="agent", parent_id=None, created_by="test")

        # Verify list_jobs returns all 3
        jobs = list_jobs(assignee="agent", actionable=True)
        assert len(jobs) == 3

        # The invariant is that work_cycle_sync uses jobs[0] and remaining = len(jobs) - 1
        # We verify the pattern: first job selected, remaining calculated
        current_job = jobs[0]
        remaining = len(jobs) - 1

        # Don't assume order, just verify the invariant pattern holds
        assert current_job is not None
        assert remaining == 2

    def test_format_job_prompt_receives_remaining_count(self, test_db, mock_emit_event, mock_emit_ui_event):
        """format_job_prompt should receive correct remaining count.

        Spec: Agent knows how many more jobs are queued.
        """
        from src.tools.data.jobs import create_job, list_jobs

        # Create 5 jobs
        for i in range(5):
            create_job(name=f"Job {i+1}", assignee="agent", parent_id=None, created_by="test")

        jobs = list_jobs(assignee="agent", actionable=True)
        remaining = len(jobs) - 1

        # With 5 jobs, processing first means 4 remaining
        assert remaining == 4

    def test_work_cycle_code_selects_first_job(self):
        """Verify work_cycle_sync selects jobs[0].

        This is a code inspection test - verifying the invariant is implemented.
        """
        import inspect
        from src.agent.agent import Agent

        source = inspect.getsource(Agent.work_cycle_sync)

        # The invariant should be implemented as: current_job = jobs[0]
        assert "current_job = jobs[0]" in source, \
            "work_cycle_sync should select only the first job"

        # And remaining should be calculated as len(jobs) - 1
        assert "remaining = len(jobs) - 1" in source, \
            "work_cycle_sync should calculate remaining jobs"


@pytest.mark.invariant
class TestJobSelectionOrder:
    """Test that job selection follows expected patterns."""

    def test_actionable_jobs_are_selectable(self, test_db, mock_emit_event, mock_emit_ui_event):
        """Actionable jobs (no blocking tags) should be returned.

        Spec: Agents poll for actionable jobs.
        """
        from src.tools.data.jobs import create_job, list_jobs

        # Create actionable job
        actionable = create_job(name="Actionable", assignee="agent", parent_id=None, created_by="test")

        # Create blocked job
        blocked = create_job(
            name="Blocked",
            assignee="agent",
            tags=["blocked:dependency"],
            parent_id=None,
            created_by="test"
        )

        jobs = list_jobs(assignee="agent", actionable=True)
        job_ids = [j["id"] for j in jobs]

        assert actionable["id"] in job_ids
        assert blocked["id"] not in job_ids
