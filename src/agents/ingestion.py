"""
Ingestion Agent - The Archivist

Transforms messy data into clean log entries. Watches inbox, processes files,
extracts content from any file type.
"""

from .base import create_agent
from ..tools.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.files import FILE_TOOLS, FILE_HANDLERS


# Combined tools and handlers for file processing mode
ALL_TOOLS = LOG_TOOLS + FILE_TOOLS
ALL_HANDLERS = {**LOG_HANDLERS, **FILE_HANDLERS}


def create_ingestion_agent(include_file_tools: bool = False):
    """
    Create an Ingestion Agent instance.

    Args:
        include_file_tools: If True, include file processing tools
    """
    tools = ALL_TOOLS if include_file_tools else LOG_TOOLS
    return create_agent(
        persona_name="ingestion",
        tools=tools
    )


def run_interactive():
    """Run an interactive session with the Ingestion Agent."""
    print("=" * 60)
    print("Me and Us - Ingestion Agent (The Archivist)")
    print("=" * 60)
    print("\nI help you capture life data. Tell me what to log.")
    print("Examples:")
    print("  - 'Log that I had coffee with Sarah this morning'")
    print("  - 'I just read an interesting article about X'")
    print("  - 'Record this idea I had: ...'")
    print("\nType 'quit' to exit.\n")

    agent = create_ingestion_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nGoodbye! Your life log awaits.")
                break

            response = agent.process(user_input, LOG_HANDLERS)
            print(f"\nArchivist: {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    run_interactive()
