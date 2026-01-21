"""
Job Module - Job lifecycle and context management.

This module provides:
- Job lifecycle management (claim, complete, fail, release)
- Job context building for agent reasoning
- Job state machine

Jobs follow this lifecycle:
- pending → working (agent claims job)
- working → done (success)
- working → error (failure)
- working → pending (release)
"""

from .lifecycle import (
    JobState,
    claim_job,
    complete_job,
    fail_job,
    release_job,
    get_pending_jobs,
)
from .context import (
    JobContext,
    build_job_context,
)

__all__ = [
    # Lifecycle
    "JobState",
    "claim_job",
    "complete_job",
    "fail_job",
    "release_job",
    "get_pending_jobs",
    # Context
    "JobContext",
    "build_job_context",
]
