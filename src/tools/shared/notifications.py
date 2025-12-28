"""
Agent-to-user communication via the Notifications project.

Agents use create_euno_task() to send notifications to users.
These appear as tasks in the Focus panel under the "Notifications" project.

For approval workflows, use create_approval_task() which links to an action.
When the user completes the task, the action is approved and executed.
When the user deletes the task, the action is rejected.
"""


def create_euno_task(
    agent_name: str,
    title: str,
    message: str = "",
    task_type: str = "notification",
    priority: str = "normal"
) -> str:
    """
    Create a task in the Notifications project for agent-to-user communication.

    Args:
        agent_name: Which agent is creating this (e.g., "attention", "worker")
        title: Short description of the notification/task
        message: Optional longer context (stored in task description)
        task_type: Type of task - "notification", "approval", "reminder", etc.
        priority: "low", "normal", "high"

    Returns:
        Confirmation message with task ID
    """
    from ...tools.worker.project import NOTIFICATIONS_PROJECT_ID, ensure_notifications_project
    from ...tools.worker.task import create_task

    # Ensure the Notifications project exists
    ensure_notifications_project()

    # Combine title and message for description
    description = title
    if message:
        description = f"{title}\n\n{message}"

    # Create the task in the Notifications project
    result = create_task(
        description=description,
        task_type=task_type,
        project_id=NOTIFICATIONS_PROJECT_ID,
        priority=priority,
        source_agent=agent_name,
        source_context="Agent notification"
    )

    return result


def create_approval_task(
    agent_name: str,
    action_id: str,
    action_type: str,
    summary: str,
    details: str,
    priority: str = "normal"
) -> str:
    """
    Create an approval task linked to a pending action.

    When the user completes this task (checkbox), the action is approved.
    When the user deletes this task, the action is rejected.

    Args:
        agent_name: Which agent is requesting approval
        action_id: The action ID to link to
        action_type: Type of action (calendar_create, email_send, etc.)
        summary: One-line summary of what will happen
        details: Full details in markdown format
        priority: "low", "normal", "high"

    Returns:
        Confirmation message with task ID
    """
    from ...tools.worker.project import NOTIFICATIONS_PROJECT_ID, ensure_notifications_project
    from ...tools.worker.task import create_task_with_action

    # Ensure the Notifications project exists
    ensure_notifications_project()

    # Format description with approval instructions
    description = f"""## Approval Needed: {action_type.replace('_', ' ').title()}

**{summary}**

{details}

---
*Check the box to approve and execute. Delete to reject.*"""

    # Create the task linked to the action
    result = create_task_with_action(
        description=description,
        action_id=action_id,
        task_type="approval",
        project_id=NOTIFICATIONS_PROJECT_ID,
        priority=priority,
        source_agent=agent_name,
        source_context=f"Approval for {action_type}"
    )

    return result
