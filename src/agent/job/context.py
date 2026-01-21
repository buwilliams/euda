"""
Job Context - Build job context for agent reasoning.

Job context is injected into the agent's system prompt to provide
information about the current task being worked on.
"""

from typing import Optional


class JobContext:
    """Manages job context for agent reasoning.

    Job context provides the agent with information about:
    - Current job details (name, description, due date)
    - Attached assets (text files)
    - Parent job context (for hierarchical jobs)
    """

    def __init__(self, agent_id: str):
        """Initialize job context manager.

        Args:
            agent_id: The agent's ID
        """
        self.agent_id = agent_id
        self._current_job_id: Optional[str] = None

    @property
    def job_id(self) -> Optional[str]:
        """Get current job ID."""
        return self._current_job_id

    def set(self, job_id: str) -> None:
        """Set the current job context.

        Args:
            job_id: The job ID to set as context
        """
        self._current_job_id = job_id

    def clear(self) -> None:
        """Clear the current job context."""
        self._current_job_id = None

    def build_prompt_context(self) -> str:
        """Build job context string for system prompt.

        Returns:
            Formatted job context string, or empty string if no job set
        """
        if not self._current_job_id:
            return ""

        # Import here to avoid circular imports
        from ...tools.data.jobs import get_job
        from ...tools.data.assets import list_assets, read_asset

        job = get_job(self._current_job_id)
        if not job:
            return ""

        parts = ["## Current Job Context\n"]
        parts.append(f"**Job:** {job.get('name', 'Untitled')}")

        if job.get('description'):
            parts.append(f"\n**Description:** {job['description']}")

        if job.get('due_date'):
            parts.append(f"\n**Due:** {job['due_date']}")

        # Get text-based assets
        assets = list_assets(self._current_job_id)
        text_assets = []
        for asset in assets:
            mime = asset.get('mime_type', '')
            if mime and (mime.startswith('text/') or mime in ['application/json', 'application/xml']):
                text_assets.append(asset)

        if text_assets:
            parts.append("\n\n### Attached Files\n")
            for asset in text_assets:
                content = read_asset(self._current_job_id, asset['filename'])
                if content and 'content' in content:
                    parts.append(f"\n**{asset['filename']}:**\n```\n{content['content']}\n```")

        return "\n".join(parts)


def build_job_context(job_id: str) -> str:
    """Build job context string for a specific job.

    Args:
        job_id: The job ID

    Returns:
        Formatted job context string
    """
    ctx = JobContext("")
    ctx.set(job_id)
    return ctx.build_prompt_context()
