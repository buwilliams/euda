"""
Interaction Agent - The Caring Friend

The user-facing conversational agent. Listens, adapts, encourages, challenges.
Detects intent and responds appropriately.
"""

from .base import create_agent
from ..tools.log import LOG_TOOLS, LOG_HANDLERS


# Tools for the Interaction Agent
# Includes all log tools for reading context and writing conversations
INTERACTION_TOOLS = LOG_TOOLS

# Handlers for tool execution
INTERACTION_HANDLERS = LOG_HANDLERS.copy()


def create_interaction_agent():
    """Create an Interaction Agent instance."""
    return create_agent(
        persona_name="interaction",
        tools=INTERACTION_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Interaction Agent."""
    print("=" * 60)
    print("Me and Us - The Caring Friend")
    print("=" * 60)
    print("\nHey. I'm here to listen, think with you, or help capture ideas.")
    print("Whatever you need right now.")
    print("\nType 'quit' to exit.\n")

    agent = create_interaction_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nTake care. I'll be here when you need me.")
                break

            response = agent.process(user_input, INTERACTION_HANDLERS)
            print(f"\nFriend: {response}\n")

        except KeyboardInterrupt:
            print("\n\nTake care!")
            break
        except Exception as e:
            print(f"\nSomething went wrong: {e}\n")


if __name__ == "__main__":
    run_interactive()
