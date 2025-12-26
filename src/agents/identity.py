"""
Identity Agent - The Keeper

Maintains a comprehensive model of who the user is, with VALUES at the core.

Identity hierarchy:
1. Values & Beliefs (core) - who you ARE
2. Behaviors (derived) - how you actually act
3. Relationships (context) - who matters to you
4. Biographical facts (context) - background information
"""

from pathlib import Path
from .base import create_agent, AutonomousAgent
from ..tools.identity import (
    ALL_IDENTITY_TOOLS, ALL_IDENTITY_HANDLERS,
    VALUES_TOOLS, VALUES_HANDLERS,
    BEHAVIOR_TOOLS, BEHAVIOR_HANDLERS,
    PROFILE_HANDLERS,
    get_all_values, get_behaviors, generate_profile
)


def create_identity_agent():
    """Create an Identity Agent instance."""
    return create_agent(
        persona_name="identity",
        tools=ALL_IDENTITY_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Identity Agent."""
    print("=" * 60)
    print("Euno - Identity Agent (The Keeper)")
    print("=" * 60)
    print("\nI maintain who you are. Values are at the core of identity.")
    print("Commands:")
    print("  - 'values' - Display current values (core)")
    print("  - 'behaviors' - Display behavioral patterns")
    print("  - 'derive' - Derive identity from summaries")
    print("  - 'profile' - Generate consolidated profile")
    print("  - Or ask me anything about identity")
    print("\nType 'quit' to exit.\n")

    agent = create_identity_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nIdentity evolves. So do we.")
                break

            # Handle quick commands
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
                user_input = "Please analyze the yearly summaries and derive the full identity: values at all three temporal scopes (current, phase, lifetime) and behavioral patterns."

            response = agent.process(user_input, ALL_IDENTITY_HANDLERS)
            print(f"\nKeeper: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def derive_identity() -> str:
    """
    Analyze summaries and derive/update identity.

    Focuses on VALUES as the core, with behaviors derived from patterns.

    Returns:
        Result of the derivation process
    """
    agent = create_identity_agent()

    prompt = """Please analyze the yearly summaries and derive identity.

## CORE FOCUS: VALUES

Values are the primary definition of identity - who you ARE.

Steps:
1. Use get_all_summaries to read all available summaries
2. Use get_all_values to see any existing values
3. Analyze patterns across the summaries looking for:
   - What consistently appears (reveals priorities)
   - What's notably absent (reveals what's not prioritized)
   - Emotional weight (what brings joy, meaning, frustration)
   - Resource allocation (time, energy, money)
   - Relationships and their patterns

4. Derive values at three temporal scopes:

   CURRENT VALUES (rolling year):
   - What matters right now based on recent patterns
   - May differ from historical values
   - Written in plain language, not categories

   PHASE VALUES (life phase):
   - Values characteristic of this phase of life
   - Name the phase if one is evident
   - Note phase transition signals if any

   LIFETIME VALUES (enduring):
   - Values that persist across phases
   - Deep patterns that appear consistently
   - Core to identity across time

5. Write each using the appropriate tool:
   - write_current_values
   - write_phase_values (with phase_name if identified)
   - write_lifetime_values

6. If you notice tensions between stated and revealed values,
   use note_value_tension to record them thoughtfully.

## DERIVED: BEHAVIORAL PATTERNS

After deriving values, examine the summaries for behavioral patterns:

1. Use get_behaviors to see any existing patterns
2. Look for:
   - Daily rhythms and routines
   - Decision-making patterns
   - Communication style
   - Recurring activities
   - How they actually spend time vs what they say matters

3. Use write_behaviors to record these patterns

## GENERATE PROFILE

Finally, use generate_profile to create a consolidated view.

Remember:
- VALUES ARE CORE - they define who the user is
- Behaviors are derived from what they actually do
- Context (biographical, relationships) supports but doesn't define
- Plain language, not categories
- Let patterns emerge, don't force structure
- Current trumps historical (who you are now matters most)
"""

    return agent.process(prompt, ALL_IDENTITY_HANDLERS)


# Backwards compatibility alias
def derive_values() -> str:
    """
    Alias for derive_identity, focusing on values.

    Deprecated: Use derive_identity() instead.
    """
    return derive_identity()


class AutonomousIdentityAgent(AutonomousAgent):
    """
    Autonomous Identity Agent that maintains user identity.

    Checks:
    - Signal: summaries_updated (derive values and behaviors)

    Work:
    - Derive values from summaries (core)
    - Derive behaviors from summaries (derived)
    - Generate consolidated profile

    Signals:
    - identity_updated: After deriving identity
    """

    def __init__(self):
        super().__init__(
            name="identity",
            persona_name="identity",
            tools=ALL_IDENTITY_TOOLS,
            tool_handlers=ALL_IDENTITY_HANDLERS,
            check_interval=600,  # Check every 10 minutes
            signals_on_complete=["identity_updated"]
        )

    def check_work_needed(self) -> bool:
        """Check if identity needs updating."""
        # Check for explicit signal
        if self.check_signal("summaries_updated"):
            self.logger.info("Received summaries_updated signal")
            return True

        # Could also check if summaries are newer than identity files
        # For now, just respond to signals
        return False

    def do_work(self) -> str:
        """Derive identity from summaries."""
        result = derive_identity()
        self.agent.clear_context()
        return "Identity derived from summaries"


# Backwards compatibility alias
AutonomousValuesAgent = AutonomousIdentityAgent


if __name__ == "__main__":
    run_interactive()
