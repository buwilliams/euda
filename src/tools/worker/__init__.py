"""Worker tools for task and project management."""

from .task import (
    TASK_TOOLS, TASK_HANDLERS,
    create_task, create_learning_task, get_tasks, get_task, get_tasks_data,
    get_daily_view, add_quick_task, update_task_status,
    store_result, get_recent_results, get_result,
    get_pending_tasks_for_worker, process_rollover, determine_delegation,
    delete_task, delete_tasks_by_description, delete_tasks_by_project
)
from .project import (
    PROJECT_TOOLS, PROJECT_HANDLERS,
    create_project, get_projects, get_projects_data, get_project, update_project,
    add_milestone, archive_project, delete_project, get_projects_with_deadlines,
    increment_task_count
)
from .worker import (
    WORKER_TOOLS, WORKER_HANDLERS, EXTENDED_WORKER_TOOLS,
    create_pending_action, get_pending_actions, get_action,
    approve_action, reject_action, mark_action_executed,
    get_action_history, get_integration_status
)

__all__ = [
    # Task tools
    'TASK_TOOLS', 'TASK_HANDLERS',
    'create_task', 'create_learning_task', 'get_tasks', 'get_task', 'get_tasks_data',
    'get_daily_view', 'add_quick_task', 'update_task_status',
    'store_result', 'get_recent_results', 'get_result',
    'get_pending_tasks_for_worker', 'process_rollover', 'determine_delegation',
    'delete_task', 'delete_tasks_by_description', 'delete_tasks_by_project',
    # Project tools
    'PROJECT_TOOLS', 'PROJECT_HANDLERS',
    'create_project', 'get_projects', 'get_projects_data', 'get_project', 'update_project',
    'add_milestone', 'archive_project', 'delete_project', 'get_projects_with_deadlines',
    'increment_task_count',
    # Worker tools
    'WORKER_TOOLS', 'WORKER_HANDLERS', 'EXTENDED_WORKER_TOOLS',
    'create_pending_action', 'get_pending_actions', 'get_action',
    'approve_action', 'reject_action', 'mark_action_executed',
    'get_action_history', 'get_integration_status',
]
