"""
Synthesis Agent - The Keeper

Constructs a PREDICTIVE IDENTITY MODEL to anticipate user behavior,
especially under stress, uncertainty, or change.

Models HOW THE USER WILL ACT, not how they wish to be seen.

Identity Stack (ordered by predictive power):
1. Identity Constraints (primary) - Non-negotiable rules revealed by sacrifice/refusal
2. Failure Modes (primary) - Predictable breakdowns under stress
3. Behavioral Attractors - Stable patterns across contexts
4. Utility Tradeoff Curves - What gets sacrificed first when goals conflict
5. Epistemic Style (supporting) - How uncertainty, revision, authority handled
6. Narrative Identity (supporting) - Self-concept, aspirational framing

Prime question: What would this person rather suffer than violate?

Temporal profiles provide biographical source data from which behavioral
patterns are extracted into the contract-compliant private profile.
"""

from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.synthesis import (
    ALL_SYNTHESIS_TOOLS, ALL_SYNTHESIS_HANDLERS,
    PROFILE_HANDLERS,
    list_temporal_profiles, get_evolution, generate_current_profile,
    get_profile, get_private_profile
)


def create_synthesis_agent():
    """Create a Synthesis Agent instance."""
    return create_agent(
        persona_name="synthesis",
        tools=ALL_SYNTHESIS_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Synthesis Agent."""
    print("=" * 60)
    print("Euno - Synthesis Agent (The Keeper)")
    print("=" * 60)
    print("\nI construct a predictive model of who you are. Behavior over belief.")
    print("Commands:")
    print("  - 'private' - Display private behavioral profile (constraints, failure modes)")
    print("  - 'temporal' - List temporal profiles (biographical source data)")
    print("  - 'evolution' - Show how you evolved over time")
    print("  - 'derive' - Full pipeline: temporal profiles + behavioral extraction")
    print("  - 'extract' - Extract behavioral profile from existing temporal data")
    print("  - 'profile' - Generate current profile for other agents")
    print("  - Or ask me anything about yourself")
    print("\nType 'quit' to exit.\n")

    agent = create_synthesis_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nThe synthesis evolves. So do we.")
                break

            # Handle quick commands
            if user_input.lower() == 'private':
                print(f"\n{get_private_profile()}\n")
                continue

            if user_input.lower() == 'temporal':
                print(f"\n{list_temporal_profiles()}\n")
                continue

            if user_input.lower() == 'evolution':
                print(f"\n{get_evolution()}\n")
                continue

            if user_input.lower() == 'profile':
                print(f"\n{generate_current_profile()}\n")
                continue

            if user_input.lower() == 'derive':
                print("\nDeriving temporal profiles and extracting behavioral model...")
                result = derive_synthesis()
                print(f"\n{result}\n")
                continue

            if user_input.lower() == 'extract':
                print("\nExtracting behavioral profile from temporal data...")
                result = extract_behavioral_profile()
                print(f"\n{result}\n")
                continue

            response = agent.process(user_input, ALL_SYNTHESIS_HANDLERS)
            print(f"\nKeeper: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def derive_synthesis() -> str:
    """
    Derive synthesis model with temporal profiles and behavioral extraction.

    Two-phase process:
    1. Generate temporal profiles (biographical data for each year)
    2. Extract behavioral profile (predictive model from biographical data)

    Returns:
        Result of the derivation and extraction process
    """
    agent = create_synthesis_agent()

    # Phase 1: Generate temporal profiles from summaries
    temporal_prompt = load_prompt("synthesis", "temporal")
    temporal_result = agent.process(temporal_prompt, ALL_SYNTHESIS_HANDLERS)

    # Phase 2: Extract behavioral profile from temporal data
    extraction_prompt = load_prompt("synthesis", "extract_behavioral")
    extraction_result = agent.process(extraction_prompt, ALL_SYNTHESIS_HANDLERS)

    return f"Temporal profiles generated. Behavioral profile extracted.\n\n{extraction_result}"


def extract_behavioral_profile() -> str:
    """
    Extract behavioral profile from existing temporal data.

    Reads temporal profiles and evolution narrative, then extracts:
    - Identity constraints (revealed by sacrifice/refusal)
    - Failure modes (stress → response patterns)
    - Behavioral attractors (stable patterns)
    - Utility tradeoff curves (sacrifice ordering)
    - Epistemic style (uncertainty handling)
    - Narrative identity (self-concept)

    Writes to contract-compliant private profile via write_private_profile().

    Returns:
        Result of extraction process
    """
    agent = create_synthesis_agent()
    prompt = load_prompt("synthesis", "extract_behavioral")
    return agent.process(prompt, ALL_SYNTHESIS_HANDLERS)


# Alias for backwards compatibility
derive_temporal = derive_synthesis


class AutonomousSynthesisAgent(AutonomousAgent):
    """
    Autonomous Synthesis Agent that maintains user's identity model over time.

    Checks:
    - Signal: summaries_updated (derive model)

    Work:
    - Generate temporal profiles for each year with data
    - Track evolution of values, beliefs, influences over time
    - Synthesize evolution narrative
    - Generate current profile from temporal data

    Signals:
    - synthesis_updated: After deriving model
    """

    def __init__(self):
        super().__init__(
            name="synthesis",
            persona_name="synthesis",
            tools=ALL_SYNTHESIS_TOOLS,
            tool_handlers=ALL_SYNTHESIS_HANDLERS,
            check_interval=600,  # Check every 10 minutes
            signals_on_complete=["synthesis_updated"]
        )

    def check_work_needed(self) -> bool:
        """Check if synthesis model needs updating."""
        # Check for explicit signal
        if self.check_signal("summaries_updated"):
            self.logger.info("Received summaries_updated signal")
            return True

        # Could also check if summaries are newer than synthesis files
        # For now, just respond to signals
        return False

    def do_work(self) -> str:
        """Derive temporal profiles and evolution narrative from summaries."""
        result = derive_synthesis()
        self.agent.clear_context()
        return "Temporal profiles and evolution narrative derived from summaries"


if __name__ == "__main__":
    run_interactive()
