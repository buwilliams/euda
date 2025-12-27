"""
Agent-to-user communication via the "From Euno" project.

Agents use create_euno_task() to send notifications to users.
These appear as tasks in the Focus panel under the "From Euno" project.
"""


def create_euno_task(
    agent_name: str,
    title: str,
    message: str = "",
    task_type: str = "notification",
    priority: str = "normal"
) -> str:
    """
    Create a task in the "From Euno" project for agent-to-user communication.

    Args:
        agent_name: Which agent is creating this (e.g., "attention", "worker")
        title: Short description of the notification/task
        message: Optional longer context (stored in task description)
        task_type: Type of task - "notification", "approval", "reminder", etc.
        priority: "low", "normal", "high"

    Returns:
        Confirmation message with task ID
    """
    from ...tools.worker.project import EUNO_PROJECT_ID, ensure_euno_project
    from ...tools.worker.task import create_task

    # Ensure the From Euno project exists
    ensure_euno_project()

    # Combine title and message for description
    description = title
    if message:
        description = f"{title}\n\n{message}"

    # Create the task in the From Euno project
    result = create_task(
        description=description,
        task_type=task_type,
        project_id=EUNO_PROJECT_ID,
        priority=priority,
        source_agent=agent_name,
        source_context="Agent notification"
    )

    return result
