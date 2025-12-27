"""
Worker Agent - The Executor

Executes tasks on behalf of the user: emails, calendar events, research,
reminders. Handles task queue processing and action approval workflows.

Delegation Strategy:
- Learning tasks: Prepare materials, surface to user
- User-only tasks: Surface to user (cannot execute)
- High-stakes tasks: Create pending action (require approval)
- Read-only/research: Execute autonomously, store result

Can emit profile observations for Synthesis Agent to integrate (behavioral
patterns around task completion, work preferences, constraint violations).
"""

from pathlib import Path
from datetime import datetime
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.worker.worker import (
    WORKER_TOOLS, WORKER_HANDLERS, EXTENDED_WORKER_TOOLS,
    get_tasks, get_pending_actions, get_action
)
from ..tools.worker.task import (
    get_pending_tasks_for_worker,
    update_task_status,
    store_result
)
from ..tools.shared.notifications import queue_notification
from ..tools.shared.profile_signals import PROFILE_SIGNAL_TOOLS, PROFILE_SIGNAL_HANDLERS


# Data paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
WORKER_DIR = DATA_DIR / "worker"
TASKS_DIR = DATA_DIR / "tasks"

# Combined tools and handlers with profile signals
ALL_WORKER_TOOLS = EXTENDED_WORKER_TOOLS + PROFILE_SIGNAL_TOOLS
ALL_WORKER_HANDLERS = {**WORKER_HANDLERS, **PROFILE_SIGNAL_HANDLERS}


def create_worker_agent():
    """Create a Worker Agent instance with extended tools."""
    return create_agent(
        persona_name="worker",
        tools=ALL_WORKER_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Worker Agent."""
    print("=" * 60)
    print("Euno - Worker Agent (The Executor)")
    print("=" * 60)
    print("\nI help you execute tasks: emails, calendar, research, reminders.")
    print("Examples:")
    print("  - 'Show me pending tasks'")
    print("  - 'Create a task to email Sarah about the meeting'")
    print("  - 'What actions are waiting for approval?'")
    print("  - 'Approve action-xxx'")
    print("\nType 'quit' to exit.\n")

    agent = create_worker_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nGoodbye! Tasks will be here when you return.")
                break

            response = agent.process(user_input, ALL_WORKER_HANDLERS)
            print(f"\nExecutor: {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def process_task_queue():
    """
    Process the task queue once with delegation logic.

    Delegation Strategy:
    - Learning tasks: Prepare materials, notify user when ready
    - User-only tasks: Surface to user via notification
    - High-stakes tasks: Create pending action for approval
    - Read-only/research: Execute autonomously, store result

    Returns status of what was done.
    """
    agent = create_worker_agent()
    prompt = load_prompt("worker", "process_tasks")
    return agent.process(prompt, ALL_WORKER_HANDLERS)


def check_pending_approvals() -> str:
    """Check for actions waiting for user approval."""
    return get_pending_actions()


def approve_action(action_id: str) -> str:
    """Approve a specific action for execution."""
    from ..tools.worker.worker import approve_action as do_approve
    return do_approve(action_id)


def reject_action(action_id: str, reason: str = "") -> str:
    """Reject a specific action."""
    from ..tools.worker.worker import reject_action as do_reject
    return do_reject(action_id, reason)


def execute_approved_actions() -> str:
    """
    Execute all approved actions.

    This is where integration with real services happens.
    For now, marks actions as executed with mock results.
    """
    agent = create_worker_agent()
    prompt = load_prompt("worker", "execute_actions")
    return agent.process(prompt, ALL_WORKER_HANDLERS)


class AutonomousWorkerAgent(AutonomousAgent):
    """
    Autonomous Worker Agent that processes the task queue with delegation.

    Checks:
    - Are there pending tasks in the queue?
    - Are there approved actions ready for execution?
    - Are there projects with upcoming deadlines?

    Work:
    - Process pending tasks based on delegation strategy
    - Execute approved actions
    - Prepare learning materials
    - Store results
    - Update task statuses

    Signals:
    - task_completed: After completing a task
    - action_pending: When an action needs user approval
    - materials_ready: When learning materials are prepared
    """

    def __init__(self):
        super().__init__(
            name="worker",
            persona_name="worker",
            tools=ALL_WORKER_TOOLS,
            tool_handlers=ALL_WORKER_HANDLERS,
            check_interval=30,  # Check every 30 seconds
            signals_on_complete=["task_completed"]
        )

    def check_work_needed(self) -> bool:
        """Check if there are tasks or approved actions to process."""
        # Check for explicit signal
        if self.check_signal("new_task"):
            self.logger.info("Received new_task signal")
            return True

        # Check for pending tasks that the worker can process
        pending_tasks = get_pending_tasks_for_worker()
        if pending_tasks:
            self.logger.debug(f"Found {len(pending_tasks)} pending tasks for worker")
            return True

        # Check for approved actions ready for execution
        actions = get_pending_actions()
        if "approved" in actions.lower() and "pending_approval" not in actions.lower():
            self.logger.debug("Found approved actions to execute")
            return True

        return False

    def do_work(self) -> str:
        """Process tasks based on delegation and execute approved actions."""
        results = []
        tasks_processed = 0
        actions_executed = 0

        # Process pending tasks with delegation logic
        pending_tasks = get_pending_tasks_for_worker()
        if pending_tasks:
            tasks_processed = len(pending_tasks)
            self.logger.info(f"Processing {tasks_processed} pending tasks...")
            result = process_task_queue()
            results.append(f"Tasks: {result}")

        # Execute any approved actions
        actions = get_pending_actions()
        if "approved" in actions.lower():
            self.logger.info("Executing approved actions...")
            result = execute_approved_actions()
            results.append(f"Actions: {result}")
            actions_executed += 1

        # Update state
        state = self.load_state()
        state["last_work_time"] = datetime.now().isoformat()
        state["work_count"] = state.get("work_count", 0) + 1
        self.save_state(state)

        # Clear context to avoid memory buildup
        self.agent.clear_context()

        # Notify user about completed work
        if tasks_processed > 0 or actions_executed > 0:
            queue_notification(
                agent_name="worker",
                title=f"Completed {tasks_processed} task(s)",
                message=f"I've been working on your tasks. {'; '.join(results)}"[:200],
                notification_type="info",
                action_prompt="Show me what you completed",
                priority="low"
            )

        if results:
            return "; ".join(results)
        return "No work performed"


if __name__ == "__main__":
    run_interactive()
