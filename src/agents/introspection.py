"""
Introspection Agent - The Mirror

Understands and documents what this system can do. Analyzes agent identities,
tools, and capabilities to maintain a living reference for the user.
"""

from datetime import datetime, timedelta
from pathlib import Path
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.introspection.introspection import (
    INTROSPECTION_TOOLS, INTROSPECTION_HANDLERS,
    get_last_introspection, INTROSPECTION_DIR
)


# State file for tracking
STATE_DIR = Path(__file__).parent.parent.parent / "data" / "agents" / "state"
CAPABILITIES_FILE = INTROSPECTION_DIR / "capabilities.md"


def create_introspection_agent():
    """Create an Introspection Agent instance."""
    return create_agent(
        persona_name="introspection",
        tools=INTROSPECTION_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Introspection Agent."""
    print("=" * 60)
    print("Euno - Introspection Agent (The Mirror)")
    print("=" * 60)
    print("\nI understand what this system can do and explain it clearly.")
    print("Commands:")
    print("  - 'analyze' - Run a full system analysis")
    print("  - 'agents' - List all agents")
    print("  - 'tools' - List all tools modules")
    print("  - 'capabilities' - Show current capabilities document")
    print("  - Or ask me anything about the system")
    print("\nType 'quit' to exit.\n")

    agent = create_introspection_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nUntil next time.")
                break

            # Handle shortcuts
            if user_input.lower() == 'analyze':
                user_input = """Please run a full system analysis:
                1. Get the system overview
                2. List and analyze all agents
                3. List and analyze key tools modules
                4. Generate a comprehensive capabilities document
                5. Save it for future reference"""
            elif user_input.lower() == 'agents':
                user_input = "List all agents in the system"
            elif user_input.lower() == 'tools':
                user_input = "List all tools modules"
            elif user_input.lower() == 'capabilities':
                user_input = "Show the current capabilities document"

            response = agent.process(user_input, INTROSPECTION_HANDLERS)
            print(f"\nMirror: {response}\n")

        except KeyboardInterrupt:
            print("\n\nUntil next time.")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def run_analysis() -> str:
    """
    Run a full system analysis and generate capabilities document.

    Returns:
        The result of the analysis.
    """
    agent = create_introspection_agent()
    prompt = load_prompt("introspection", "analyze_system")
    return agent.process(prompt, INTROSPECTION_HANDLERS)


class AutonomousIntrospectionAgent(AutonomousAgent):
    """
    Autonomous agent that periodically analyzes the system.

    Runs every 30 minutes to check if capabilities have changed
    and updates the documentation accordingly.
    """

    def __init__(self, check_interval: int = 1800):  # 30 minutes default
        super().__init__(
            name="introspection",
            persona_name="introspection",
            tools=INTROSPECTION_TOOLS,
            tool_handlers=INTROSPECTION_HANDLERS,
            check_interval=check_interval,
            signals_on_complete=["introspection_updated"]
        )

        # Track when we last did a full analysis
        self.last_analysis_time = None

    def check_work_needed(self) -> bool:
        """
        Check if introspection work is needed.

        Triggers:
        1. No capabilities document exists
        2. 30+ minutes since last analysis (force periodic refresh)
        3. Signal from other agents indicating changes
        """
        # Check for signal that code or identities changed
        if self.check_signal("code_changed") or self.check_signal("identity_evolved"):
            self.logger.info("Change signal detected, analysis needed")
            return True

        # Check if capabilities file exists
        if not CAPABILITIES_FILE.exists():
            self.logger.info("No capabilities file, analysis needed")
            return True

        # Check file age - refresh if older than 1 hour
        if CAPABILITIES_FILE.exists():
            mtime = datetime.fromtimestamp(CAPABILITIES_FILE.stat().st_mtime)
            age = datetime.now() - mtime

            if age > timedelta(hours=1):
                self.logger.info(f"Capabilities file is {age} old, refresh needed")
                return True

        # Always run at least once per 30 min cycle (the check_interval handles this)
        # But only if we haven't run recently
        if self.last_analysis_time is None:
            return True

        return False

    def do_work(self) -> str:
        """
        Perform the introspection analysis.

        Returns:
            Status message.
        """
        self.logger.info("Starting system introspection...")

        # Run the analysis
        result = run_analysis()

        self.last_analysis_time = datetime.now()

        # Update state
        state = self.load_state()
        state['last_analysis'] = self.last_analysis_time.isoformat()
        state['analysis_count'] = state.get('analysis_count', 0) + 1
        self.save_state(state)

        return f"Analysis complete. {len(result)} chars generated."


# Simple test
if __name__ == "__main__":
    run_interactive()
