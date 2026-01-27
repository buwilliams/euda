"""Done working command for the core plugin."""

import os
from typing import Optional
import typer


def _get_system_module():
    """Lazy import of system module."""
    from src.core.system.system import done_working
    return {
        "done_working": done_working,
    }


def done_working(
    summary: Optional[str] = typer.Argument(None, help="Brief summary of what was accomplished"),
):
    """Signal that you have finished your current work cycle.

    Use when:
    - All assigned work is complete
    - No more actions needed
    - Blocked and need to wait
    """
    m = _get_system_module()
    result = m["done_working"](summary=summary or "")

    print(result.get("message", "Work cycle complete."))
    if summary:
        print(f"Summary: {summary}")
