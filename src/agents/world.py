"""
World Agent - The Scout

Discovers opportunities in the external world that align with user values
while occasionally surprising with life-promoting novelty.
"""

from datetime import datetime, timedelta
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.world.world import WORLD_TOOLS, WORLD_HANDLERS
from ..tools.synthesis import VALUES_TOOLS, VALUES_HANDLERS, PROFILE_TOOLS, PROFILE_HANDLERS
from ..tools.shared.notifications import queue_notification


# Combined tools - World agent needs access to identity (values at core)
ALL_TOOLS = WORLD_TOOLS + VALUES_TOOLS + PROFILE_TOOLS
ALL_HANDLERS = {**WORLD_HANDLERS, **VALUES_HANDLERS, **PROFILE_HANDLERS}


def create_world_agent():
    """Create a World Agent instance."""
    return create_agent(
        persona_name="world",
        tools=ALL_TOOLS
    )


def run_interactive():
    """Run an interactive session with the World Agent."""
    print("=" * 60)
    print("Euno - World Agent (The Scout)")
    print("=" * 60)
    print("\nI bring back news from beyond. Growth requires novelty.")
    print("Commands:")
    print("  - 'suggest' - Get discovery suggestions based on values")
    print("  - 'discover' - Run a discovery sweep")
    print("  - 'opportunities' - View discovered opportunities")
    print("  - Or ask me to search for something specific")
    print("\nType 'quit' to exit.\n")

    agent = create_world_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nThe world awaits. Stay curious.")
                break

            # Handle quick commands
            if user_input.lower() == 'suggest':
                from ..tools.world.world import suggest_discoveries
                print(f"\n{suggest_discoveries()}\n")
                continue

            if user_input.lower() == 'opportunities':
                from ..tools.world.world import get_opportunities
                print(f"\n{get_opportunities()}\n")
                continue

            if user_input.lower() == 'discover':
                user_input = load_prompt("world", "discovery_sweep")

            response = agent.process(user_input, ALL_HANDLERS)
            print(f"\nScout: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def run_discovery_sweep() -> str:
    """
    Run a discovery sweep based on current values.

    Returns:
        Summary of discovered opportunities
    """
    agent = create_world_agent()
    prompt = load_prompt("world", "discovery_sweep")
    return agent.process(prompt, ALL_HANDLERS)


class AutonomousWorldAgent(AutonomousAgent):
    """
    Autonomous World Agent that periodically discovers opportunities.

    Checks:
    - Signal: values_updated
    - Time since last discovery sweep

    Work:
    - Run discovery sweep to find new opportunities

    Signals:
    - opportunities_updated: After discovering new opportunities
    """

    def __init__(self, sweep_interval_hours: int = 24):
        super().__init__(
            name="world",
            persona_name="world",
            tools=ALL_TOOLS,
            tool_handlers=ALL_HANDLERS,
            check_interval=3600,  # Check every hour
            signals_on_complete=["opportunities_updated"]
        )
        self.sweep_interval = timedelta(hours=sweep_interval_hours)

    def check_work_needed(self) -> bool:
        """Check if a discovery sweep is needed."""
        # Check for explicit signal (identity includes values at core)
        if self.check_signal("synthesis_updated"):
            self.logger.info("Received synthesis_updated signal - running discovery")
            return True

        # Check if enough time has passed since last sweep
        state = self.load_state()
        last_sweep = state.get("last_sweep")

        if last_sweep:
            last_time = datetime.fromisoformat(last_sweep)
            if datetime.now() - last_time < self.sweep_interval:
                return False

        # Time for a sweep
        return True

    def do_work(self) -> str:
        """Run a discovery sweep."""
        result = run_discovery_sweep()

        # Save state
        self.save_state({"last_sweep": datetime.now().isoformat()})
        self.agent.clear_context()

        # Notify user about new discoveries
        queue_notification(
            agent_name="world",
            title="New opportunities discovered",
            message="I've found some new opportunities that might interest you based on your values.",
            notification_type="info",
            action_prompt="Show me the opportunities you discovered",
            priority="normal"
        )

        return "Discovery sweep complete"


if __name__ == "__main__":
    run_interactive()
