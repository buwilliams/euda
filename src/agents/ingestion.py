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

import shutil
from datetime import datetime, timedelta
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
INBOX_DIR = INGESTION_DIR / "inbox"
PENDING_DIR = INBOX_DIR / "pending"
PROCESSING_DIR = INBOX_DIR / "processing"


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
        self._initialize_session()

    def _initialize_session(self):
        """Initialize a new processing session."""
        state = self.load_state()
        state['session'] = {
            'started_at': datetime.now().isoformat(),
            'files_processed': 0,
            'files_failed': 0,
            'files_deferred': 0,
            'tokens_used': 0,
        }
        # Initialize totals if not present
        if 'totals' not in state:
            state['totals'] = {
                'lifetime_processed': 0,
                'lifetime_failed': 0,
                'lifetime_tokens': 0,
            }
        self.save_state(state)

    def _recover_stuck_files(self):
        """Move files stuck in processing/ back to pending/."""
        if not PROCESSING_DIR.exists():
            return

        state = self.load_state()
        current = state.get('current_file')

        for file in PROCESSING_DIR.iterdir():
            if not file.is_file() or file.name.startswith('.'):
                continue

            # Check if we were processing this file
            if current and current.get('name') == file.name:
                # Check timeout (10 minutes)
                try:
                    started = datetime.fromisoformat(current['started_at'])
                    if datetime.now() - started > timedelta(minutes=10):
                        self.logger.warning(f"File timed out, recovering: {file.name}")
                        shutil.move(str(file), str(PENDING_DIR / file.name))
                        state['current_file'] = None
                        self.save_state(state)
                except (KeyError, ValueError):
                    # Invalid state, recover the file
                    self.logger.warning(f"Invalid state, recovering: {file.name}")
                    shutil.move(str(file), str(PENDING_DIR / file.name))
                    state['current_file'] = None
                    self.save_state(state)
            else:
                # Unknown file in processing - move back to pending
                self.logger.warning(f"Unknown file in processing, recovering: {file.name}")
                shutil.move(str(file), str(PENDING_DIR / file.name))

    def check_work_needed(self) -> bool:
        """Check if there are files to process."""
        # Recover any files stuck in processing from a previous crash
        self._recover_stuck_files()

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

            # Track current file in state (for crash recovery)
            state = self.load_state()
            state['current_file'] = {
                'path': file_path,
                'name': file_name,
                'hash': file_hash,
                'started_at': datetime.now().isoformat()
            }
            self.save_state(state)

            try:
                # Generate digest for accurate token estimate
                digest = generate_digest(file_path)
                token_estimate = digest.get("token_estimate", 0)

                # Check token budget
                if not budget.can_spend(token_estimate):
                    self.logger.info(f"Budget exhausted, deferring: {file_name}")
                    queue.defer(item, "budget_exhausted")
                    self.files_deferred_this_cycle += 1

                    # Update state
                    state = self.load_state()
                    state['current_file'] = None
                    state['session']['files_deferred'] = state.get('session', {}).get('files_deferred', 0) + 1
                    self.save_state(state)
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

CRITICAL: First determine what kind of content this is:

**PRESERVE VERBATIM** (human expression):
- Personal writing: journals, musings, reflections, notes, blog posts
- Messages from others: texts, emails, letters, conversations
- Quotes, ideas, thoughts - yours or others'
→ Record the actual words. Voice and expression matter.

**SUMMARIZE** (data/information):
- Transactions, receipts, financial records
- Articles, reports, documentation
- Lists, logs, system output
→ Compress to essence. 2-5 sentences max.

Instructions:
1. Determine: Is this human expression or data/information?
2. If human expression → preserve the actual words, the voice, the meaning
3. If data/information → summarize briefly (what happened, key numbers, significance)
4. Use write_log_entry with appropriate entry_type:
   - "journal" / "reflection" / "thought" for personal writing
   - "message" / "conversation" for communications
   - "summary" for compressed data
5. Use the temporal hint for timestamp if available

The goal: Capture real thoughts and words verbatim. Compress everything else.

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

                # Update state - success
                state = self.load_state()
                state['current_file'] = None
                state['session']['files_processed'] = state.get('session', {}).get('files_processed', 0) + 1
                state['session']['tokens_used'] = state.get('session', {}).get('tokens_used', 0) + token_estimate
                state['totals']['lifetime_processed'] = state.get('totals', {}).get('lifetime_processed', 0) + 1
                state['totals']['lifetime_tokens'] = state.get('totals', {}).get('lifetime_tokens', 0) + token_estimate
                self.save_state(state)

                # Clear context after each file to manage memory
                self.agent.clear_context()

            except Exception as e:
                self.logger.error(f"Error processing {file_name}: {e}")
                queue.complete(item, success=False, reason=str(e))

                # Update state - failure
                state = self.load_state()
                state['current_file'] = None
                state['session']['files_failed'] = state.get('session', {}).get('files_failed', 0) + 1
                state['totals']['lifetime_failed'] = state.get('totals', {}).get('lifetime_failed', 0) + 1
                self.save_state(state)

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
