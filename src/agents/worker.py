"""
Worker Agent - The Executor

Executes tasks on behalf of the user: emails, calendar events, research,
reminders. Handles task queue processing and action approval workflows.
"""

from pathlib import Path
from .base import create_agent, AutonomousAgent
from ..tools.worker import (
    WORKER_TOOLS, WORKER_HANDLERS,
    get_tasks, get_pending_actions, get_action
)


# Data paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
WORKER_DIR = DATA_DIR / "worker"


def create_worker_agent():
    """Create a Worker Agent instance."""
    return create_agent(
        persona_name="worker",
        tools=WORKER_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Worker Agent."""
    print("=" * 60)
    print("Me and Us - Worker Agent (The Executor)")
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

            response = agent.process(user_input, WORKER_HANDLERS)
            print(f"\nExecutor: {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def process_task_queue():
    """
    Process the task queue once.

    Returns status of what was done.
    """
    agent = create_worker_agent()

    prompt = """Check the task queue and process any pending tasks.

For each pending task:
1. Update its status to in_progress
2. Determine what action is needed
3. Create a pending action with clear summary
4. Update task status to awaiting_approval (for actions that need approval)

Prioritize high priority tasks and those with deadlines.

If there are approved actions ready for execution, execute them and mark complete.

Report what you did."""

    result = agent.process(prompt, WORKER_HANDLERS)
    return result


def check_pending_approvals() -> str:
    """Check for actions waiting for user approval."""
    return get_pending_actions()


def approve_action(action_id: str) -> str:
    """Approve a specific action for execution."""
    from ..tools.worker import approve_action as do_approve
    return do_approve(action_id)


def reject_action(action_id: str, reason: str = "") -> str:
    """Reject a specific action."""
    from ..tools.worker import reject_action as do_reject
    return do_reject(action_id, reason)


def execute_approved_actions() -> str:
    """
    Execute all approved actions.

    This is where integration with real services happens.
    For now, marks actions as executed with mock results.
    """
    agent = create_worker_agent()

    prompt = """Check for approved actions that are ready for execution.

For each approved action:
1. Execute it (or simulate execution in mock mode)
2. Mark it as executed with the result
3. Update the associated task status

Report what was executed."""

    result = agent.process(prompt, WORKER_HANDLERS)
    return result


class AutonomousWorkerAgent(AutonomousAgent):
    """
    Autonomous Worker Agent that processes the task queue.

    Checks:
    - Are there pending tasks in the queue?
    - Are there approved actions ready for execution?

    Work:
    - Process pending tasks
    - Execute approved actions
    - Update task statuses

    Signals:
    - task_completed: After completing a task
    - action_pending: When an action needs user approval
    """

    def __init__(self):
        super().__init__(
            name="worker",
            persona_name="worker",
            tools=WORKER_TOOLS,
            tool_handlers=WORKER_HANDLERS,
            check_interval=30,  # Check every 30 seconds
            signals_on_complete=["task_completed"]
        )

    def check_work_needed(self) -> bool:
        """Check if there are tasks or approved actions to process."""
        # Check for explicit signal
        if self.check_signal("new_task"):
            self.logger.info("Received new_task signal")
            return True

        # Check for pending tasks
        tasks = get_tasks(status="pending")
        if "No tasks found" not in tasks:
            self.logger.debug("Found pending tasks")
            return True

        # Check for approved actions ready for execution
        actions = get_pending_actions()
        if "approved" in actions.lower() and "pending_approval" not in actions.lower():
            self.logger.debug("Found approved actions to execute")
            return True

        return False

    def do_work(self) -> str:
        """Process tasks and execute approved actions."""
        results = []

        # First, process any pending tasks
        tasks = get_tasks(status="pending")
        if "No tasks found" not in tasks:
            self.logger.info("Processing pending tasks...")
            result = process_task_queue()
            results.append(f"Tasks: {result}")

        # Then, execute any approved actions
        actions = get_pending_actions()
        if "approved" in actions.lower():
            self.logger.info("Executing approved actions...")
            result = execute_approved_actions()
            results.append(f"Actions: {result}")

        # Clear context to avoid memory buildup
        self.agent.clear_context()

        if results:
            return "; ".join(results)
        return "No work performed"


if __name__ == "__main__":
    run_interactive()
