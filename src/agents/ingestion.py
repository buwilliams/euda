"""
Ingestion Agent - The Archivist

Transforms messy data into clean log entries. Watches inbox, processes files,
extracts content from any file type.
"""

from pathlib import Path
from .base import create_agent, AutonomousAgent
from ..tools.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.files import FILE_TOOLS, FILE_HANDLERS, list_pending_files


# Combined tools and handlers for file processing mode
ALL_TOOLS = LOG_TOOLS + FILE_TOOLS
ALL_HANDLERS = {**LOG_HANDLERS, **FILE_HANDLERS}

# Inbox path
INBOX_DIR = Path(__file__).parent.parent.parent / "data" / "inbox" / "pending"


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
    print("me·an·dus - Ingestion Agent (The Archivist)")
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


class AutonomousIngestionAgent(AutonomousAgent):
    """
    Autonomous Ingestion Agent that watches the inbox for files.

    Checks:
    - Are there files in data/inbox/pending?

    Work:
    - Process each pending file through the LLM
    - Extract content and write to log
    - Move processed files to data/inbox/processed

    Signals:
    - logs_updated: After processing files
    """

    def __init__(self):
        super().__init__(
            name="ingestion",
            persona_name="ingestion",
            tools=ALL_TOOLS,
            tool_handlers=ALL_HANDLERS,
            check_interval=30,  # Check every 30 seconds
            signals_on_complete=["logs_updated"]
        )

    def check_work_needed(self) -> bool:
        """Check if there are pending files to process."""
        # Check for explicit signal from file watcher
        if self.check_signal("inbox_changed"):
            self.logger.info("Received inbox_changed signal")

        # Check actual inbox contents
        pending = list_pending_files()
        has_work = "No pending files" not in pending
        if has_work:
            self.logger.debug(f"Found pending files")
        return has_work

    def do_work(self) -> str:
        """Process all pending files."""
        # Get the list of files
        pending_info = list_pending_files()

        # Ask the agent to process them
        prompt = f"""Process all pending files in the inbox.

{pending_info}

For each file:
1. Read its content using read_file_content
2. Extract temporal hints if possible
3. Write a log entry with the content
4. Mark the file as processed

Process each file completely before moving to the next."""

        result = self.agent.process(prompt, ALL_HANDLERS)

        # Clear context to avoid memory buildup
        self.agent.clear_context()

        return f"Processed inbox files"


if __name__ == "__main__":
    run_interactive()
