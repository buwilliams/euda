"""
Synthesis Agent - The Keeper

Synthesizes a comprehensive model of who the user is, with EPISTEMIC AXIOMS at the foundation.
Tracks identity OVER TIME through temporal profiles.

Synthesis hierarchy:
1. Epistemic Axioms (foundational) - the beliefs that drive decisions
2. Mental Models & Tools (foundational) - how you reason and process reality
3. Values (derived) - what you care about, emergent from epistemic core
4. Behaviors (reveals) - how you act, shows which axioms are operative
5. Context (supporting) - relationships, biographical facts, influences
6. Temporal (evolution) - who you were at each point in time

Each epistemic entry includes PROVENANCE: the behavior that revealed it.
Temporal profiles track how identity evolved year by year.
"""

from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.synthesis import (
    ALL_SYNTHESIS_TOOLS, ALL_SYNTHESIS_HANDLERS,
    EPISTEMIC_TOOLS, EPISTEMIC_HANDLERS,
    VALUES_TOOLS, VALUES_HANDLERS,
    BEHAVIOR_TOOLS, BEHAVIOR_HANDLERS,
    PROFILE_HANDLERS,
    get_all_epistemic, get_all_values, get_behaviors, generate_profile,
    list_temporal_profiles, get_evolution, generate_current_profile
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
    print("\nI synthesize who you are. Epistemic axioms at the foundation, tracked over time.")
    print("Commands:")
    print("  - 'epistemic' - Display epistemic core (axioms, models, tools)")
    print("  - 'values' - Display values (derived from epistemic core)")
    print("  - 'behaviors' - Display behavioral patterns")
    print("  - 'temporal' - List temporal profiles (who you were each year)")
    print("  - 'evolution' - Show how you evolved over time")
    print("  - 'derive' - Derive full model from summaries")
    print("  - 'derive-temporal' - Generate temporal profiles for all years")
    print("  - 'profile' - Generate current profile from temporal data")
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
            if user_input.lower() == 'epistemic':
                print(f"\n{get_all_epistemic()}\n")
                continue

            if user_input.lower() == 'values':
                print(f"\n{get_all_values()}\n")
                continue

            if user_input.lower() == 'behaviors':
                print(f"\n{get_behaviors()}\n")
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
                user_input = "Please analyze the yearly summaries and derive the full model: epistemic axioms, mental models, epistemic tools, values at all three temporal scopes, and behavioral patterns."

            if user_input.lower() == 'derive-temporal':
                print("\nGenerating temporal profiles for all years...")
                result = derive_temporal()
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
    Analyze summaries and derive/update synthesis model.

    Loads the derive prompt from data/synthesis/prompts/derive.md
    and uses it to guide the agent.

    Returns:
        Result of the derivation process
    """
    agent = create_synthesis_agent()
    prompt = load_prompt("synthesis", "derive")
    return agent.process(prompt, ALL_SYNTHESIS_HANDLERS)


def derive_temporal() -> str:
    """
    Generate temporal profiles for all years with summaries.

    Creates a profile for each year showing who the user was at that time,
    then synthesizes an evolution narrative and generates the current profile.

    Loads the temporal prompt from data/synthesis/prompts/temporal.md
    and uses it to guide the agent.

    Returns:
        Result of the temporal derivation process
    """
    agent = create_synthesis_agent()
    prompt = load_prompt("synthesis", "temporal")
    return agent.process(prompt, ALL_SYNTHESIS_HANDLERS)


# Backwards compatibility aliases
def derive_self() -> str:
    """Alias for derive_synthesis. Deprecated."""
    return derive_synthesis()


def derive_identity() -> str:
    """Alias for derive_synthesis. Deprecated."""
    return derive_synthesis()


def derive_values() -> str:
    """Alias for derive_synthesis. Deprecated."""
    return derive_synthesis()


class AutonomousSynthesisAgent(AutonomousAgent):
    """
    Autonomous Synthesis Agent that maintains user's identity model.

    Checks:
    - Signal: summaries_updated (derive model)

    Work:
    - Derive epistemic axioms from summaries (foundational)
    - Derive values from summaries (derived)
    - Derive behaviors from summaries (reveals axioms)
    - Generate consolidated profile

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
        """Derive synthesis model from summaries."""
        result = derive_synthesis()
        self.agent.clear_context()
        return "Synthesis model derived from summaries"


# Backwards compatibility aliases
AutonomousSelfAgent = AutonomousSynthesisAgent
AutonomousIdentityAgent = AutonomousSynthesisAgent
AutonomousValuesAgent = AutonomousSynthesisAgent


if __name__ == "__main__":
    run_interactive()
