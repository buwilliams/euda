"""
Values Agent - The Philosopher

Derives and refines values from life patterns. Holds stated and revealed
values together. Tracks values across temporal scopes.
"""

from .base import create_agent
from ..tools.values import VALUES_TOOLS, VALUES_HANDLERS, get_all_values


def create_values_agent():
    """Create a Values Agent instance."""
    return create_agent(
        persona_name="values",
        tools=VALUES_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Values Agent."""
    print("=" * 60)
    print("Me and Us - Values Agent (The Philosopher)")
    print("=" * 60)
    print("\nI articulate what matters. Values are conjectures, not truths.")
    print("Commands:")
    print("  - 'show' - Display current values")
    print("  - 'derive' - Derive values from summaries")
    print("  - Or ask me anything about your values")
    print("\nType 'quit' to exit.\n")

    agent = create_values_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nValues evolve. So do we.")
                break

            # Handle quick commands
            if user_input.lower() == 'show':
                print(f"\n{get_all_values()}\n")
                continue

            if user_input.lower() == 'derive':
                user_input = "Please analyze the yearly summaries and derive values at all three temporal scopes: current (rolling year), life phase, and lifetime."

            response = agent.process(user_input, VALUES_HANDLERS)
            print(f"\nPhilosopher: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def derive_values() -> str:
    """
    Analyze summaries and derive/update values.

    Returns:
        Result of the derivation process
    """
    agent = create_values_agent()

    prompt = """Please analyze the yearly summaries and derive values.

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

Remember:
- Values are conjectures, not truths
- Plain language, not categories
- Let patterns emerge, don't force structure
- Current trumps historical (who you are now matters most)
"""

    return agent.process(prompt, VALUES_HANDLERS)


if __name__ == "__main__":
    run_interactive()
