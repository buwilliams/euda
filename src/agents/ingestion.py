"""
Ingestion Agent - The Archivist

Transforms messy data into clean log entries. Uses a priority queue
with token budget management and intelligent file handling.

Pipeline:
1. Scan pending → classify → add to queue
2. Pop next file (highest priority)
3. Check token budget
4. If affordable: process with AI → log → mark processed
5. If not affordable: defer to tomorrow
6. Repeat until queue empty or budget exhausted
"""

from pathlib import Path
from .base import create_agent, AutonomousAgent
from ..tools.shared.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.ingestion.files import FILE_TOOLS, FILE_HANDLERS, list_pending_files
from ..tools.ingestion.token_budget import get_budget, TOKEN_BUDGET_TOOLS, TOKEN_BUDGET_HANDLERS
from ..tools.ingestion.classifier import CLASSIFIER_TOOLS, CLASSIFIER_HANDLERS, mark_as_processed
from ..tools.ingestion.digest import generate_digest, get_content_for_ai, DIGEST_TOOLS, DIGEST_HANDLERS
from ..tools.ingestion.queue import get_queue, QUEUE_TOOLS, QUEUE_HANDLERS


# Combined tools and handlers for the enhanced ingestion agent
ALL_TOOLS = (
    LOG_TOOLS +
    FILE_TOOLS +
    TOKEN_BUDGET_TOOLS +
    CLASSIFIER_TOOLS +
    DIGEST_TOOLS +
    QUEUE_TOOLS
)

ALL_HANDLERS = {
    **LOG_HANDLERS,
    **FILE_HANDLERS,
    **TOKEN_BUDGET_HANDLERS,
    **CLASSIFIER_HANDLERS,
    **DIGEST_HANDLERS,
    **QUEUE_HANDLERS,
}

# Inbox paths - now under ingestion agent directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"
INGESTION_DIR = DATA_DIR / "ingestion"
INBOX_DIR = INGESTION_DIR / "inbox" / "pending"


def create_ingestion_agent(include_file_tools: bool = True):
    """
    Create an Ingestion Agent instance.

    Args:
        include_file_tools: If True, include all file processing tools
    """
    tools = ALL_TOOLS if include_file_tools else LOG_TOOLS
    return create_agent(
        persona_name="ingestion",
        tools=tools
    )


def run_interactive():
    """Run an interactive session with the Ingestion Agent."""
    print("=" * 60)
    print("Euno - Ingestion Agent (The Archivist)")
    print("=" * 60)
    print("\nI help you capture life data. Tell me what to log.")
    print("Examples:")
    print("  - 'Log that I had coffee with Sarah this morning'")
    print("  - 'I just read an interesting article about X'")
    print("  - 'Record this idea I had: ...'")
    print("\nType 'quit' to exit.\n")

    agent = create_ingestion_agent(include_file_tools=False)

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
    Autonomous Ingestion Agent with priority queue and token budget.

    Pipeline:
    1. Restore deferred files (if new day)
    2. Scan pending directory → add to priority queue
    3. Pop highest-priority file
    4. Generate digest, check token budget
    5. If affordable: process → log → complete
    6. If not: defer to tomorrow
    7. Repeat until queue empty or all deferred

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
        self.files_processed_this_cycle = 0
        self.files_deferred_this_cycle = 0

    def check_work_needed(self) -> bool:
        """Check if there are files to process."""
        # Check for explicit signal from file watcher
        if self.check_signal("inbox_changed"):
            self.logger.info("Received inbox_changed signal")

        # Get queue instance
        queue = get_queue()

        # Restore deferred files if it's a new day
        restored = queue.restore_deferred()
        if restored > 0:
            self.logger.info(f"Restored {restored} deferred files")

        # Scan pending for new files
        added = queue.scan_pending()
        if added > 0:
            self.logger.info(f"Added {added} new files to queue")

        # Check if queue has items
        stats = queue.stats()
        has_work = stats["queue_length"] > 0

        if has_work:
            self.logger.debug(f"Queue has {stats['queue_length']} files")

        return has_work

    def do_work(self) -> str:
        """Process files from the priority queue."""
        queue = get_queue()
        budget = get_budget()

        self.files_processed_this_cycle = 0
        self.files_deferred_this_cycle = 0

        # Process files until queue empty or all deferred
        while True:
            # Get next file
            item = queue.pop()
            if item is None:
                break

            file_path = item.get("path", "")
            file_name = item.get("name", "unknown")
            file_hash = item.get("hash", "")

            self.logger.info(f"Processing: {file_name} (score: {item.get('score', 0):.3f})")

            try:
                # Generate digest for accurate token estimate
                digest = generate_digest(file_path)
                token_estimate = digest.get("token_estimate", 0)

                # Check token budget
                if not budget.can_spend(token_estimate):
                    self.logger.info(f"Budget exhausted, deferring: {file_name}")
                    queue.defer(item, "budget_exhausted")
                    self.files_deferred_this_cycle += 1
                    continue

                # Get content for AI processing
                content = get_content_for_ai(file_path, digest)

                # Get temporal hints
                temporal = digest.get("temporal_hints", {})
                timestamp = temporal.get("timestamp", "")
                temporal_note = ""
                if timestamp:
                    confidence = temporal.get("confidence", "unknown")
                    source = temporal.get("source", "unknown")
                    temporal_note = f"\nTemporal hint: {timestamp} (confidence: {confidence}, source: {source})"

                # Build prompt for the AI
                prompt = f"""Process this file and write a log entry.

File: {file_name}
Category: {digest.get('classification', {}).get('category', 'unknown')}
{temporal_note}

Content:
---
{content}
---

Instructions:
1. Analyze the content to understand what it represents
2. Write a meaningful log entry using write_log_entry
3. Use the temporal hint for the timestamp if available (otherwise use current time)
4. Choose appropriate source and entry_type based on the content
5. Keep the log entry concise but informative

Do NOT read the file again - use the content provided above."""

                # Process with AI
                result = self.agent.process(prompt, ALL_HANDLERS)

                # Record token usage (estimate for now)
                budget.spend(token_estimate, f"Processed: {file_name}")

                # Mark as complete
                queue.complete(item, success=True)
                if file_hash:
                    mark_as_processed(file_path, file_hash)

                self.files_processed_this_cycle += 1
                self.logger.info(f"Completed: {file_name}")

                # Clear context after each file to manage memory
                self.agent.clear_context()

            except Exception as e:
                self.logger.error(f"Error processing {file_name}: {e}")
                queue.complete(item, success=False, reason=str(e))

        # Build summary
        stats = queue.stats()
        budget_status = budget.get_status()

        summary_parts = []
        if self.files_processed_this_cycle > 0:
            summary_parts.append(f"Processed {self.files_processed_this_cycle} files")
        if self.files_deferred_this_cycle > 0:
            summary_parts.append(f"Deferred {self.files_deferred_this_cycle} files (budget)")
        if stats["deferred_files"] > 0:
            summary_parts.append(f"{stats['deferred_files']} files waiting for tomorrow")

        summary_parts.append(f"Budget: {budget_status['percent_used']:.1f}% used")

        return ". ".join(summary_parts) if summary_parts else "No files to process"


def get_ingestion_status() -> str:
    """Get current ingestion status for display."""
    queue = get_queue()
    budget = get_budget()

    stats = queue.stats()
    budget_status = budget.get_status()

    lines = [
        "=== Ingestion Status ===",
        f"Queue: {stats['queue_length']} files ({stats['total_token_estimate']:,} tokens est.)",
        f"Pending: {stats['pending_files']} | Processing: {stats['processing_files']}",
        f"Deferred: {stats['deferred_files']} | Processed: {stats['processed_files']} | Failed: {stats['failed_files']}",
        f"",
        f"Token Budget: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)",
        f"Remaining: {budget_status['remaining']:,} tokens",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    run_interactive()
