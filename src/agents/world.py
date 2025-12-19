"""
World Agent - The Scout

Discovers opportunities in the external world that align with user values
while occasionally surprising with life-promoting novelty.
"""

from .base import create_agent
from ..tools.world import WORLD_TOOLS, WORLD_HANDLERS
from ..tools.values import VALUES_TOOLS, VALUES_HANDLERS


# Combined tools - World agent needs access to values
ALL_TOOLS = WORLD_TOOLS + VALUES_TOOLS
ALL_HANDLERS = {**WORLD_HANDLERS, **VALUES_HANDLERS}


def create_world_agent():
    """Create a World Agent instance."""
    return create_agent(
        persona_name="world",
        tools=ALL_TOOLS
    )


def run_interactive():
    """Run an interactive session with the World Agent."""
    print("=" * 60)
    print("Me and Us - World Agent (The Scout)")
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
                from ..tools.world import suggest_discoveries
                print(f"\n{suggest_discoveries()}\n")
                continue

            if user_input.lower() == 'opportunities':
                from ..tools.world import get_opportunities
                print(f"\n{get_opportunities()}\n")
                continue

            if user_input.lower() == 'discover':
                user_input = """Run a discovery sweep. Based on current values:
1. Use suggest_discoveries to see what directions make sense
2. Think about what opportunities would align with these values
3. Record 3-5 opportunities using write_opportunity:
   - At least one for learning/growth
   - At least one for connection/people
   - At least one expansive/surprising opportunity (the 10%)
4. Share what you found"""

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

    prompt = """Time for a discovery sweep.

Your mission:
1. Use get_discovery_context to understand current values
2. Use suggest_discoveries to see recommended directions
3. Based on values, imagine/generate relevant opportunities in these categories:
   - Events: Gatherings, conferences, meetups that align
   - People: Interesting individuals or communities
   - Places: Locations or experiences worth exploring
   - Learning: Skills, courses, knowledge to pursue
   - Goals: Meaningful challenges or projects

4. Record 5-8 opportunities using write_opportunity:
   - ~80% should be "aligned" (clear value match)
   - ~20% should be "expansive" (life-promoting surprises)
   - Mix categories for variety
   - Be specific and actionable

5. Summarize what you found and why each matters

Remember:
- Popularity doesn't matter, alignment with THIS user does
- The 10% expansive should still be plausibly life-promoting
- Be concrete, not generic
"""

    return agent.process(prompt, ALL_HANDLERS)


if __name__ == "__main__":
    run_interactive()
