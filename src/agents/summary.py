"""
Summary Agent - The Historian

Distills daily logs into meaningful yearly narratives.
Finds patterns in the noise, tracks entities across time.
"""

from datetime import datetime
from .base import create_agent
from ..tools.summary import SUMMARY_TOOLS, SUMMARY_HANDLERS, list_years, check_summary_needed


def create_summary_agent():
    """Create a Summary Agent instance."""
    return create_agent(
        persona_name="summary",
        tools=SUMMARY_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Summary Agent."""
    print("=" * 60)
    print("Me and Us - Summary Agent (The Historian)")
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

    prompt = f"""Please analyze and summarize the logs for {year}.

Steps:
1. First use list_years to see what's available
2. Use get_year_logs to read all entries for {year}
3. Look for patterns:
   - Key themes and topics
   - People mentioned frequently
   - Places and activities
   - Emotional tones and energy levels
   - What's present AND what's notably absent
   - Weekly/monthly rhythms if visible
4. Write a comprehensive summary using write_summary

The summary should:
- Stand alone (someone could understand the year from just the summary)
- Capture both facts and feelings
- Note patterns and outliers
- Be honest about gaps in the data
"""

    return agent.process(prompt, SUMMARY_HANDLERS)


def check_and_summarize_all():
    """Check all years and generate summaries where needed."""
    print("Checking all years for summary needs...")

    from ..tools.summary import LOG_DIR

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


if __name__ == "__main__":
    run_interactive()
