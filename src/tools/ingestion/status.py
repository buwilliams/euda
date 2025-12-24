"""
Ingestion Status Tools - Progress and state reporting

Provides comprehensive status information about the ingestion process
for the Introspection Agent and other consumers. Includes:
- Current processing state
- Queue statistics
- Session and lifetime progress
- Historical processing data
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from .queue import get_queue
from .token_budget import get_budget


# Data paths (4 levels up from src/tools/ingestion/status.py)
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
INGESTION_DIR = DATA_DIR / "ingestion"
STATE_FILE = INGESTION_DIR / "state" / "state.json"
LOGS_DIR = INGESTION_DIR / "logs"


def _load_state() -> dict:
    """Load ingestion state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def get_ingestion_status() -> str:
    """
    Get comprehensive ingestion status.

    Returns:
        Formatted status including queue, budget, current file, and session stats.
    """
    queue = get_queue()
    budget = get_budget()
    state = _load_state()

    stats = queue.stats()
    budget_status = budget.get_status()

    lines = [
        "# Ingestion Status",
        "",
        "## Current Processing",
    ]

    # Current file being processed
    current = state.get('current_file')
    if current:
        started = current.get('started_at', 'unknown')
        lines.append(f"- **Currently processing**: {current.get('name', 'unknown')}")
        lines.append(f"- **Started at**: {started}")
    else:
        lines.append("- No file currently being processed")

    lines.extend([
        "",
        "## Queue Status",
        f"- **Queued**: {stats['queue_length']} files ({stats['total_token_estimate']:,} tokens est.)",
        f"- **Pending** (not yet queued): {stats['pending_files']} files",
        f"- **Processing**: {stats['processing_files']} files",
        f"- **Deferred** (waiting for tomorrow): {stats['deferred_files']} files",
        "",
        "## Completed",
        f"- **Processed**: {stats['processed_files']} files",
        f"- **Failed**: {stats['failed_files']} files",
        "",
        "## Token Budget",
        f"- **Today's usage**: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)",
        f"- **Remaining**: {budget_status['remaining']:,} tokens",
    ])

    # Session stats
    session = state.get('session', {})
    if session:
        lines.extend([
            "",
            "## Current Session",
            f"- **Started**: {session.get('started_at', 'unknown')}",
            f"- **Files processed**: {session.get('files_processed', 0)}",
            f"- **Files failed**: {session.get('files_failed', 0)}",
            f"- **Files deferred**: {session.get('files_deferred', 0)}",
            f"- **Tokens used**: {session.get('tokens_used', 0):,}",
        ])

    # Lifetime stats
    totals = state.get('totals', {})
    if totals:
        lines.extend([
            "",
            "## Lifetime Totals",
            f"- **Total processed**: {totals.get('lifetime_processed', 0):,}",
            f"- **Total failed**: {totals.get('lifetime_failed', 0):,}",
            f"- **Total tokens**: {totals.get('lifetime_tokens', 0):,}",
        ])

    return "\n".join(lines)


def get_ingestion_progress() -> str:
    """
    Get session and lifetime progress statistics.

    Returns:
        Formatted progress statistics.
    """
    state = _load_state()

    session = state.get('session', {})
    totals = state.get('totals', {})

    lines = [
        "# Ingestion Progress",
        "",
        "## Current Session",
    ]

    if session:
        lines.extend([
            f"- Started: {session.get('started_at', 'N/A')}",
            f"- Files processed: {session.get('files_processed', 0)}",
            f"- Files failed: {session.get('files_failed', 0)}",
            f"- Files deferred: {session.get('files_deferred', 0)}",
            f"- Tokens used: {session.get('tokens_used', 0):,}",
        ])
    else:
        lines.append("No active session.")

    lines.extend([
        "",
        "## Lifetime Totals",
    ])

    if totals:
        lines.extend([
            f"- Total files processed: {totals.get('lifetime_processed', 0):,}",
            f"- Total files failed: {totals.get('lifetime_failed', 0):,}",
            f"- Total tokens used: {totals.get('lifetime_tokens', 0):,}",
        ])
    else:
        lines.append("No lifetime data yet.")

    return "\n".join(lines)


def get_processing_history(days: int = 7) -> str:
    """
    Get daily processing statistics from activity logs.

    Args:
        days: Number of days to look back (default: 7)

    Returns:
        Formatted daily statistics.
    """
    lines = [
        f"# Processing History (Last {days} days)",
        "",
    ]

    today = date.today()

    for i in range(days):
        target_date = today - timedelta(days=i)
        log_file = LOGS_DIR / f"{target_date.isoformat()}.json"

        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    entries = json.load(f)

                # Count actions
                work_starts = sum(1 for e in entries if e.get('action') == 'work_start')
                work_completes = sum(1 for e in entries if e.get('action') == 'work_complete')
                errors = sum(1 for e in entries if e.get('action') == 'error')
                tool_calls = sum(1 for e in entries if e.get('action') == 'tool_call')

                date_label = "Today" if i == 0 else ("Yesterday" if i == 1 else target_date.isoformat())
                lines.append(f"## {date_label}")
                lines.append(f"- Work cycles started: {work_starts}")
                lines.append(f"- Work cycles completed: {work_completes}")
                lines.append(f"- Errors: {errors}")
                lines.append(f"- Tool calls: {tool_calls}")
                lines.append("")

            except (json.JSONDecodeError, KeyError):
                lines.append(f"## {target_date.isoformat()}")
                lines.append("- Log file corrupted or invalid")
                lines.append("")
        else:
            date_label = "Today" if i == 0 else ("Yesterday" if i == 1 else target_date.isoformat())
            lines.append(f"## {date_label}")
            lines.append("- No activity recorded")
            lines.append("")

    return "\n".join(lines)


# Tool definitions for LLM
INGESTION_STATUS_TOOLS = [
    {
        "name": "get_ingestion_status",
        "description": "Get comprehensive ingestion status including queue, budget, current file being processed, and session statistics. Use this to understand what the ingestion system is currently doing.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_ingestion_progress",
        "description": "Get session and lifetime progress statistics for ingestion. Shows how many files have been processed overall.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_processing_history",
        "description": "Get daily processing statistics from activity logs. Shows work cycles, errors, and tool calls per day.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default: 7)",
                    "default": 7
                }
            }
        }
    }
]

INGESTION_STATUS_HANDLERS = {
    "get_ingestion_status": lambda: get_ingestion_status(),
    "get_ingestion_progress": lambda: get_ingestion_progress(),
    "get_processing_history": lambda days=7: get_processing_history(days),
}


# Test
if __name__ == "__main__":
    print(get_ingestion_status())
    print("\n" + "="*50 + "\n")
    print(get_ingestion_progress())
    print("\n" + "="*50 + "\n")
    print(get_processing_history(3))
