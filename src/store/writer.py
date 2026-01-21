"""
Memory Writer - Write RLM processing results to long-term memory.
"""

from typing import List
from pathlib import Path

from .rlm_processor import StoreResult


DATA_DIR = Path(__file__).parent.parent.parent / "data"


def write_to_memory(results: List[StoreResult], agent_id: str = "user") -> dict:
    """Write RLM processing results to long-term memory.

    Args:
        results: List of StoreResult from RLM processing
        agent_id: Agent whose memory to write to

    Returns:
        {
            "written": [{"file": str, "date": str, "status": "ok"}],
            "errors": [{"file": str, "error": str}],
            "total_written": int
        }
    """
    from ..llms.tools.data.memory import write_long_term_memory

    written = []
    errors = []

    for result in results:
        if result.error:
            errors.append({
                "file": result.file,
                "error": result.error
            })
            continue

        if not result.date or not result.content:
            errors.append({
                "file": result.file,
                "error": "Missing date or content"
            })
            continue

        try:
            # Write to long-term memory
            write_long_term_memory(
                content=result.content,
                date=result.date,
                agent_id=agent_id,
                source=result.source
            )

            written.append({
                "file": result.file,
                "date": result.date,
                "date_source": result.date_source,
                "status": "ok"
            })

        except Exception as e:
            errors.append({
                "file": result.file,
                "error": str(e)
            })

    return {
        "written": written,
        "errors": errors,
        "total_written": len(written)
    }
