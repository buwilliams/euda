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
from ..tools.worker.project import append_research_result
from ..tools.shared.notifications import create_euno_task
from ..tools.shared.profile_signals import PROFILE_SIGNAL_TOOLS, PROFILE_SIGNAL_HANDLERS
from ..tools.world.fetch import fetch_url, FETCH_TOOLS, FETCH_HANDLERS


# Combined tools and handlers with profile signals and fetch capability
ALL_WORKER_TOOLS = EXTENDED_WORKER_TOOLS + PROFILE_SIGNAL_TOOLS + FETCH_TOOLS
ALL_WORKER_HANDLERS = {**WORKER_HANDLERS, **PROFILE_SIGNAL_HANDLERS, **FETCH_HANDLERS}


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
    - Are there research tasks to execute autonomously?

    Work:
    - Process pending tasks based on delegation strategy
    - Execute approved actions
    - Prepare learning materials
    - Execute research tasks autonomously
    - Store results and append to project notes
    - Update task statuses

    Signals:
    - task_completed: After completing a task
    - action_pending: When an action needs user approval
    - materials_ready: When learning materials are prepared
    - research_completed: When research task finished
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

    def _get_research_tasks(self) -> list:
        """Get research tasks that can be executed autonomously."""
        pending_tasks = get_pending_tasks_for_worker()
        return [
            t for t in pending_tasks
            if t.get("type") == "research"
            and t.get("delegation", {}).get("strategy") == "agent_autonomous"
        ]

    def _execute_research_task(self, task: dict) -> str:
        """
        Execute a research task autonomously.

        1. Execute research using agent with fetch_url tool
        2. Store result
        3. Auto-append to project notes
        4. Send notification
        5. Mark task completed

        Returns:
            Result summary
        """
        task_id = task["id"]
        description = task["description"]
        project_id = task.get("project_id")

        self.logger.info(f"Executing research task: {description[:50]}...")

        # Mark as in progress
        update_task_status(task_id, "in_progress")

        try:
            # Use agent to research the topic
            prompt = f"""Research the following task and provide a comprehensive summary:

Task: {description}

Instructions:
1. Use the fetch_url tool to gather relevant information from the web
2. Synthesize the findings into a clear, actionable summary
3. Include key details, options, and recommendations
4. List your sources

Provide your response in this format:
SUMMARY: (2-3 sentence overview)
KEY FINDINGS:
- (bullet points)
DETAILS:
(expanded information)
SOURCES:
- (URLs used)
"""
            # Process with agent
            response = self.agent.process(prompt, ALL_WORKER_HANDLERS)

            # Parse response into structured format
            summary = ""
            details = response
            sources = []

            # Try to extract summary
            if "SUMMARY:" in response:
                parts = response.split("SUMMARY:", 1)
                if len(parts) > 1:
                    summary_part = parts[1].split("\n")[0].strip()
                    summary = summary_part if summary_part else description

            if not summary:
                summary = description

            # Try to extract sources
            if "SOURCES:" in response:
                sources_part = response.split("SOURCES:", 1)[1]
                for line in sources_part.split("\n"):
                    line = line.strip()
                    if line.startswith("-") or line.startswith("http"):
                        url = line.lstrip("- ").strip()
                        if url:
                            sources.append(url)

            # Store result
            store_result(
                task_id=task_id,
                summary=summary,
                content={"research": details, "sources": sources},
                recommendations=None
            )

            # Append to project notes if project exists
            if project_id:
                append_research_result(
                    project_id=project_id,
                    task_description=description,
                    summary=summary,
                    details=details,
                    sources=sources
                )

            # Mark completed
            update_task_status(task_id, "completed")

            # Notify user via From Euno project task
            create_euno_task(
                agent_name="worker",
                title=f"Research complete: {description[:40]}...",
                message=f"I've finished researching and saved the results to your project notes. {summary[:100]}",
                task_type="notification",
                priority="normal"
            )

            self.logger.info(f"Research task completed: {task_id}")
            return f"Research completed: {summary[:100]}"

        except Exception as e:
            self.logger.error(f"Research task failed: {e}")
            update_task_status(task_id, "pending")  # Reset to pending for retry
            return f"Research failed: {e}"

    def check_work_needed(self) -> bool:
        """Check if there are tasks or approved actions to process."""
        # Check for explicit signal
        if self.check_signal("new_task"):
            self.logger.info("Received new_task signal")
            return True

        # Check for research tasks (high priority - execute immediately)
        research_tasks = self._get_research_tasks()
        if research_tasks:
            self.logger.debug(f"Found {len(research_tasks)} research tasks to execute")
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
        research_completed = 0
        actions_executed = 0

        # Execute research tasks first (autonomous)
        research_tasks = self._get_research_tasks()
        for task in research_tasks[:3]:  # Limit to 3 research tasks per cycle
            result = self._execute_research_task(task)
            results.append(result)
            research_completed += 1

        # Process other pending tasks with delegation logic
        # Note: Most tasks require approval or are user-only, so they won't be
        # completed - they'll just have actions created. Don't create notifications
        # for simply processing the queue since it creates noise.
        pending_tasks = [
            t for t in get_pending_tasks_for_worker()
            if t.get("type") != "research" or t.get("delegation", {}).get("strategy") != "agent_autonomous"
        ]
        if pending_tasks:
            self.logger.info(f"Processing {len(pending_tasks)} pending tasks...")
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
        state["research_completed"] = state.get("research_completed", 0) + research_completed
        self.save_state(state)

        # Clear context to avoid memory buildup
        self.agent.clear_context()

        # Only notify user when actual autonomous work was completed
        # Research tasks have their own notifications, so only notify for actions
        if actions_executed > 0:
            create_euno_task(
                agent_name="worker",
                title=f"Executed {actions_executed} approved action(s)",
                message=f"I've executed actions you approved. {'; '.join(results)}"[:200],
                task_type="notification",
                priority="low"
            )

        if results:
            return "; ".join(results)
        return "No work performed"


if __name__ == "__main__":
    run_interactive()
