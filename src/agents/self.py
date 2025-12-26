"""
Self Agent - The Keeper

Maintains a comprehensive model of who the user is, with EPISTEMIC AXIOMS at the foundation.

Self hierarchy:
1. Epistemic Axioms (foundational) - the beliefs that drive decisions
2. Mental Models & Tools (foundational) - how you reason and process reality
3. Values (derived) - what you care about, emergent from epistemic core
4. Behaviors (reveals) - how you act, shows which axioms are operative
5. Context (supporting) - relationships, biographical facts

Each epistemic entry includes PROVENANCE: the behavior that revealed it.
"""

from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.self import (
    ALL_SELF_TOOLS, ALL_SELF_HANDLERS,
    EPISTEMIC_TOOLS, EPISTEMIC_HANDLERS,
    VALUES_TOOLS, VALUES_HANDLERS,
    BEHAVIOR_TOOLS, BEHAVIOR_HANDLERS,
    PROFILE_HANDLERS,
    get_all_epistemic, get_all_values, get_behaviors, generate_profile
)


def create_self_agent():
    """Create a Self Agent instance."""
    return create_agent(
        persona_name="self",
        tools=ALL_SELF_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Self Agent."""
    print("=" * 60)
    print("Euno - Self Agent (The Keeper)")
    print("=" * 60)
    print("\nI maintain who you are. Epistemic axioms are at the foundation.")
    print("Commands:")
    print("  - 'epistemic' - Display epistemic core (axioms, models, tools)")
    print("  - 'values' - Display values (derived from epistemic core)")
    print("  - 'behaviors' - Display behavioral patterns")
    print("  - 'derive' - Derive full self-model from summaries")
    print("  - 'profile' - Generate consolidated profile")
    print("  - Or ask me anything about yourself")
    print("\nType 'quit' to exit.\n")

    agent = create_self_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nThe self evolves. So do we.")
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

            if user_input.lower() == 'profile':
                print(f"\n{generate_profile()}\n")
                continue

            if user_input.lower() == 'derive':
                user_input = "Please analyze the yearly summaries and derive the full self-model: epistemic axioms, mental models, epistemic tools, values at all three temporal scopes, and behavioral patterns."

            response = agent.process(user_input, ALL_SELF_HANDLERS)
            print(f"\nKeeper: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def derive_self() -> str:
    """
    Analyze summaries and derive/update self-model.

    Loads the derive prompt from data/self/prompts/derive.md
    and uses it to guide the agent.

    Returns:
        Result of the derivation process
    """
    agent = create_self_agent()
    prompt = load_prompt("self", "derive")
    return agent.process(prompt, ALL_SELF_HANDLERS)


# Backwards compatibility aliases
def derive_identity() -> str:
    """Alias for derive_self. Deprecated."""
    return derive_self()


def derive_values() -> str:
    """Alias for derive_self. Deprecated."""
    return derive_self()


class AutonomousSelfAgent(AutonomousAgent):
    """
    Autonomous Self Agent that maintains user's self-model.

    Checks:
    - Signal: summaries_updated (derive self-model)

    Work:
    - Derive epistemic axioms from summaries (foundational)
    - Derive values from summaries (derived)
    - Derive behaviors from summaries (reveals axioms)
    - Generate consolidated profile

    Signals:
    - self_updated: After deriving self-model
    """

    def __init__(self):
        super().__init__(
            name="self",
            persona_name="self",
            tools=ALL_SELF_TOOLS,
            tool_handlers=ALL_SELF_HANDLERS,
            check_interval=600,  # Check every 10 minutes
            signals_on_complete=["self_updated"]
        )

    def check_work_needed(self) -> bool:
        """Check if self-model needs updating."""
        # Check for explicit signal
        if self.check_signal("summaries_updated"):
            self.logger.info("Received summaries_updated signal")
            return True

        # Could also check if summaries are newer than self files
        # For now, just respond to signals
        return False

    def do_work(self) -> str:
        """Derive self-model from summaries."""
        result = derive_self()
        self.agent.clear_context()
        return "Self-model derived from summaries"


# Backwards compatibility aliases
AutonomousIdentityAgent = AutonomousSelfAgent
AutonomousValuesAgent = AutonomousSelfAgent


if __name__ == "__main__":
    run_interactive()
