"""
World Agent - The Scout

Discovers opportunities in the external world that align with user values
while occasionally surprising with life-promoting novelty.
"""

from datetime import datetime, timedelta
from pathlib import Path
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.world.world import WORLD_TOOLS, WORLD_HANDLERS
from ..tools.synthesis import PROFILE_TOOLS, PROFILE_HANDLERS
from ..tools.shared.notifications import create_euno_task
from ..tools.shared.guidance import GUIDANCE_TOOLS, GUIDANCE_HANDLERS, should_skip_location_opportunities
from ..tools.shared.content_hash import (
    compute_directory_hash, load_cached_hash, save_cached_hash
)


# Paths for hash tracking
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SYNTHESIS_PROFILE_DIR = DATA_DIR / "synthesis" / "state" / "profile"
WORLD_STATE_DIR = DATA_DIR / "world" / "state"
# Tracks which version of the synthesis profile the World Agent last processed
PROCESSED_PROFILE_HASH_FILE = WORLD_STATE_DIR / "processed_profile.hash"

# Combined tools - World agent needs access to profile (identity) and guidance
ALL_TOOLS = WORLD_TOOLS + PROFILE_TOOLS + GUIDANCE_TOOLS
ALL_HANDLERS = {**WORLD_HANDLERS, **PROFILE_HANDLERS, **GUIDANCE_HANDLERS}


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

    def _has_profile_changed(self) -> bool:
        """Check if user profile has changed since last sweep."""
        if not SYNTHESIS_PROFILE_DIR.exists():
            return False

        current_hash = compute_directory_hash(SYNTHESIS_PROFILE_DIR, "*.md", exclude_prefix="_")
        cached_hash = load_cached_hash(PROCESSED_PROFILE_HASH_FILE)

        if cached_hash is None:
            self.logger.debug("No cached profile hash - first run")
            return True

        changed = current_hash != cached_hash
        if changed:
            self.logger.debug(f"Profile hash changed: {cached_hash[:8]}... -> {current_hash[:8]}...")
        return changed

    def _save_profile_hash(self):
        """Save current profile hash after successful sweep."""
        if SYNTHESIS_PROFILE_DIR.exists():
            current_hash = compute_directory_hash(SYNTHESIS_PROFILE_DIR, "*.md", exclude_prefix="_")
            WORLD_STATE_DIR.mkdir(parents=True, exist_ok=True)
            save_cached_hash(PROCESSED_PROFILE_HASH_FILE, current_hash)
            self.logger.debug(f"Saved profile hash: {current_hash[:8]}...")

    def check_work_needed(self) -> bool:
        """Check if a discovery sweep is needed."""
        # Check for explicit signal (identity includes values at core)
        if self.check_signal("synthesis_updated"):
            self.logger.info("Received synthesis_updated signal")
            # Verify profile actually changed
            if self._has_profile_changed():
                return True
            self.logger.debug("Signal received but profile unchanged - skipping early sweep")

        # Check if enough time has passed since last sweep
        state = self.load_state()
        last_sweep = state.get("last_sweep")

        if last_sweep:
            last_time = datetime.fromisoformat(last_sweep)
            if datetime.now() - last_time < self.sweep_interval:
                return False

        # Time for a sweep - also verify profile changed since last sweep
        if not self._has_profile_changed():
            self.logger.debug("Sweep interval elapsed but profile unchanged - skipping")
            # Still update last_sweep to avoid checking again
            self.save_state({"last_sweep": datetime.now().isoformat()})
            return False

        return True

    def do_work(self) -> str:
        """Run a discovery sweep."""
        result = run_discovery_sweep()

        # Save state and hash so we don't re-process unchanged profile
        self.save_state({"last_sweep": datetime.now().isoformat()})
        self._save_profile_hash()
        self.agent.clear_context()

        # Notify user via From Euno project task
        create_euno_task(
            agent_name="world",
            title="New opportunities discovered",
            message="I've found some new opportunities that might interest you based on your values.",
            task_type="notification",
            priority="normal"
        )

        return "Discovery sweep complete"


if __name__ == "__main__":
    run_interactive()
