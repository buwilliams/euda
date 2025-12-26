"""
Summary Agent - The Historian

Distills daily logs into meaningful yearly narratives.
Finds patterns in the noise, tracks entities across time.
"""

from datetime import datetime
from pathlib import Path
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.synthesis.summary import SUMMARY_TOOLS, SUMMARY_HANDLERS, list_years, check_summary_needed, LOG_DIR


def create_summary_agent():
    """Create a Summary Agent instance."""
    return create_agent(
        persona_name="summary",
        tools=SUMMARY_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Summary Agent."""
    print("=" * 60)
    print("Euno - Summary Agent (The Historian)")
    print("=" * 60)
    print("\nI find patterns in your life log and distill them into summaries.")
    print("Commands:")
    print("  - 'list' or 'years' - Show years with logs")
    print("  - 'check [year]' - Check if summary needed")
    print("  - 'summarize [year]' - Generate summary for year")
    print("  - Or ask me anything about patterns in your logs")
    print("\nType 'quit' to exit.\n")

    agent = create_summary_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nThe patterns remain, waiting to be found.")
                break

            # Handle quick commands
            if user_input.lower() in ('list', 'years'):
                print(f"\n{list_years()}\n")
                continue

            if user_input.lower().startswith('check'):
                parts = user_input.split()
                if len(parts) > 1 and parts[1].isdigit():
                    year = int(parts[1])
                    print(f"\n{check_summary_needed(year)}\n")
                else:
                    print("\nUsage: check [year]\n")
                continue

            response = agent.process(user_input, SUMMARY_HANDLERS)
            print(f"\nHistorian: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def summarize_year(year: int) -> str:
    """
    Generate a summary for a specific year.

    Args:
        year: The year to summarize

    Returns:
        The generated summary or status message
    """
    agent = create_summary_agent()
    prompt = load_prompt("summary", "summarize_year", year=year)
    return agent.process(prompt, SUMMARY_HANDLERS)


def check_and_summarize_all():
    """Check all years and generate summaries where needed."""
    print("Checking all years for summary needs...")

    from ..tools.synthesis.summary import LOG_DIR

    if not LOG_DIR.exists():
        print("No log directory found.")
        return

    for year_dir in sorted(LOG_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        year = int(year_dir.name)
        status = check_summary_needed(year)
        print(f"\n{year}: {status}")

        if "needed" in status.lower():
            print(f"Generating summary for {year}...")
            result = summarize_year(year)
            print(f"Result: {result}")


class AutonomousSummaryAgent(AutonomousAgent):
    """
    Autonomous Summary Agent that monitors logs for changes.

    Checks:
    - Signal: logs_updated
    - Any year where summary is outdated

    Work:
    - Generate/update summaries for years that need it

    Signals:
    - summaries_updated: After generating summaries
    """

    def __init__(self):
        super().__init__(
            name="summary",
            persona_name="summary",
            tools=SUMMARY_TOOLS,
            tool_handlers=SUMMARY_HANDLERS,
            check_interval=300,  # Check every 5 minutes
            signals_on_complete=["summaries_updated"]
        )
        self._years_needing_summary = []

    def check_work_needed(self) -> bool:
        """Check if any summaries need updating."""
        # First check for explicit signal
        if self.check_signal("logs_updated"):
            self.logger.info("Received logs_updated signal")

        # Check each year
        self._years_needing_summary = []

        if not LOG_DIR.exists():
            return False

        for year_dir in sorted(LOG_DIR.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue

            year = int(year_dir.name)
            status = check_summary_needed(year)

            if "needed" in status.lower() or "outdated" in status.lower():
                self._years_needing_summary.append(year)

        if self._years_needing_summary:
            self.logger.debug(f"Years needing summary: {self._years_needing_summary}")

        return len(self._years_needing_summary) > 0

    def do_work(self) -> str:
        """Generate summaries for years that need them."""
        results = []

        for year in self._years_needing_summary:
            self.logger.info(f"Generating summary for {year}...")
            result = summarize_year(year)
            results.append(f"{year}: done")
            self.agent.clear_context()

        return f"Summarized {len(results)} year(s)"


if __name__ == "__main__":
    run_interactive()
