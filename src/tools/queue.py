"""
Priority Queue for Ingestion Agent.

Manages the processing order of files based on relevance scores.
Handles deferral when token budget is exhausted and restores
deferred files on new days.
"""

import json
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List

from .digest import generate_digest
from .scorer import calculate_score
from .classifier import compute_file_hash


# Data paths
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "ingestion"
QUEUE_FILE = DATA_DIR / "queue.json"

INBOX_DIR = Path(__file__).parent.parent.parent / "data" / "inbox"
PENDING_DIR = INBOX_DIR / "pending"
PROCESSING_DIR = INBOX_DIR / "processing"
DEFERRED_DIR = INBOX_DIR / "deferred"
PROCESSED_DIR = INBOX_DIR / "processed"
FAILED_DIR = INBOX_DIR / "failed"


def ensure_dirs():
    """Ensure all inbox directories exist."""
    for d in [PENDING_DIR, PROCESSING_DIR, DEFERRED_DIR, PROCESSED_DIR, FAILED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


class IngestionQueue:
    """
    Priority queue for file ingestion.

    Files are scored and ordered by relevance. The queue persists
    to disk so it survives restarts.
    """

    def __init__(self):
        ensure_dirs()
        self.queue = self._load_queue()
        self._last_restore_date = self.queue.get("last_restore_date", "")

    def _load_queue(self) -> dict:
        """Load queue state from file."""
        if QUEUE_FILE.exists():
            with open(QUEUE_FILE, 'r') as f:
                return json.load(f)
        return {"items": [], "last_restore_date": ""}

    def _save_queue(self):
        """Persist queue state to file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(QUEUE_FILE, 'w') as f:
            json.dump(self.queue, f, indent=2)

    def scan_pending(self) -> int:
        """
        Scan pending directory and add new files to queue.

        Returns:
            Number of new files added
        """
        added = 0
        existing_paths = {item["path"] for item in self.queue.get("items", [])}

        for file_path in PENDING_DIR.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                path_str = str(file_path.absolute())
                if path_str not in existing_paths:
                    self.add(path_str)
                    added += 1

        return added

    def add(self, file_path: str) -> bool:
        """
        Add a file to the queue.

        Generates digest and calculates score.

        Args:
            file_path: Path to the file

        Returns:
            True if added, False if skipped (ignored/duplicate)
        """
        digest = generate_digest(file_path)

        # Skip if should be ignored or is duplicate
        status = digest.get("status", "")
        if status in ("ignored", "duplicate"):
            return False

        score = calculate_score(digest)
        file_hash = digest.get("classification", {}).get("file_hash", "")

        item = {
            "path": str(Path(file_path).absolute()),
            "name": Path(file_path).name,
            "hash": file_hash,
            "score": score,
            "added_at": datetime.now().isoformat(),
            "token_estimate": digest.get("token_estimate", 0),
            "category": digest.get("classification", {}).get("category", "unknown"),
        }

        # Add to queue
        items = self.queue.get("items", [])
        items.append(item)

        # Sort by score descending
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        self.queue["items"] = items

        self._save_queue()
        return True

    def peek(self) -> Optional[dict]:
        """
        Get the next file to process without removing it.

        Returns:
            Queue item dict or None if empty
        """
        items = self.queue.get("items", [])
        if items:
            return items[0]
        return None

    def pop(self) -> Optional[dict]:
        """
        Remove and return the next file to process.

        Also moves the file to the processing directory.

        Returns:
            Queue item dict or None if empty
        """
        items = self.queue.get("items", [])
        if not items:
            return None

        item = items.pop(0)
        self.queue["items"] = items
        self._save_queue()

        # Move to processing directory
        src = Path(item["path"])
        if src.exists():
            dst = PROCESSING_DIR / src.name
            try:
                shutil.move(str(src), str(dst))
                item["path"] = str(dst)
                item["original_path"] = str(src)
            except Exception as e:
                item["move_error"] = str(e)

        return item

    def complete(self, item: dict, success: bool = True, reason: str = ""):
        """
        Mark an item as complete.

        Moves from processing to processed or failed directory.

        Args:
            item: Queue item dict
            success: Whether processing succeeded
            reason: Failure reason if not successful
        """
        src = Path(item.get("path", ""))
        if not src.exists():
            return

        if success:
            dst = PROCESSED_DIR / src.name
            try:
                shutil.move(str(src), str(dst))
            except Exception:
                pass
        else:
            dst = FAILED_DIR / src.name
            try:
                shutil.move(str(src), str(dst))
                # Write reason file
                reason_file = FAILED_DIR / f"{src.name}.reason.txt"
                reason_file.write_text(reason)
            except Exception:
                pass

    def defer(self, item: dict, reason: str = "budget_exhausted"):
        """
        Defer a file for later processing.

        Moves from processing (or pending) to deferred directory.

        Args:
            item: Queue item dict
            reason: Why the file was deferred
        """
        src = Path(item.get("path", ""))
        if not src.exists():
            # Try original path
            src = Path(item.get("original_path", ""))
        if not src.exists():
            return

        dst = DEFERRED_DIR / src.name
        try:
            shutil.move(str(src), str(dst))

            # Write metadata about deferral
            meta_file = DEFERRED_DIR / f"{src.name}.meta.json"
            meta_file.write_text(json.dumps({
                "deferred_at": datetime.now().isoformat(),
                "reason": reason,
                "score": item.get("score", 0),
                "token_estimate": item.get("token_estimate", 0),
            }, indent=2))
        except Exception:
            pass

    def restore_deferred(self) -> int:
        """
        Restore deferred files to pending.

        Should be called at the start of each new day.

        Returns:
            Number of files restored
        """
        today = date.today().isoformat()

        # Check if we already restored today
        if self._last_restore_date == today:
            return 0

        restored = 0
        for file_path in DEFERRED_DIR.iterdir():
            if file_path.is_file() and not file_path.name.endswith('.json'):
                # Move back to pending
                dst = PENDING_DIR / file_path.name
                try:
                    shutil.move(str(file_path), str(dst))
                    restored += 1

                    # Remove meta file
                    meta_file = DEFERRED_DIR / f"{file_path.name}.meta.json"
                    if meta_file.exists():
                        meta_file.unlink()
                except Exception:
                    pass

        # Update restore date
        self._last_restore_date = today
        self.queue["last_restore_date"] = today
        self._save_queue()

        return restored

    def remove_by_path(self, file_path: str) -> bool:
        """
        Remove a specific file from the queue.

        Args:
            file_path: Path to remove

        Returns:
            True if found and removed
        """
        path_str = str(Path(file_path).absolute())
        items = self.queue.get("items", [])
        original_len = len(items)

        items = [item for item in items if item.get("path") != path_str]
        self.queue["items"] = items
        self._save_queue()

        return len(items) < original_len

    def clear(self):
        """Clear the entire queue."""
        self.queue["items"] = []
        self._save_queue()

    def stats(self) -> dict:
        """Get queue statistics."""
        items = self.queue.get("items", [])

        # Count files in each directory
        pending_count = sum(1 for f in PENDING_DIR.iterdir() if f.is_file() and not f.name.startswith('.'))
        processing_count = sum(1 for f in PROCESSING_DIR.iterdir() if f.is_file() and not f.name.startswith('.'))
        deferred_count = sum(1 for f in DEFERRED_DIR.iterdir() if f.is_file() and not f.name.endswith('.json'))
        processed_count = sum(1 for f in PROCESSED_DIR.iterdir() if f.is_file() and not f.name.startswith('.'))
        failed_count = sum(1 for f in FAILED_DIR.iterdir() if f.is_file() and not f.name.endswith('.txt'))

        # Queue stats
        total_tokens = sum(item.get("token_estimate", 0) for item in items)
        avg_score = sum(item.get("score", 0) for item in items) / len(items) if items else 0

        return {
            "queue_length": len(items),
            "pending_files": pending_count,
            "processing_files": processing_count,
            "deferred_files": deferred_count,
            "processed_files": processed_count,
            "failed_files": failed_count,
            "total_token_estimate": total_tokens,
            "average_score": round(avg_score, 3),
            "last_restore_date": self._last_restore_date,
        }

    def get_items(self, limit: int = 10) -> List[dict]:
        """Get the top items in the queue."""
        items = self.queue.get("items", [])
        return items[:limit]


# Singleton instance
_queue_instance: Optional[IngestionQueue] = None


def get_queue() -> IngestionQueue:
    """Get the singleton queue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = IngestionQueue()
    return _queue_instance


# Tool functions
def get_queue_status() -> str:
    """Get the current queue status."""
    queue = get_queue()
    stats = queue.stats()

    lines = [
        "Ingestion Queue Status:",
        f"  Queued: {stats['queue_length']} files",
        f"  Pending (not yet queued): {stats['pending_files']} files",
        f"  Processing: {stats['processing_files']} files",
        f"  Deferred: {stats['deferred_files']} files",
        f"  Processed: {stats['processed_files']} files",
        f"  Failed: {stats['failed_files']} files",
        f"  Total token estimate: {stats['total_token_estimate']:,}",
        f"  Average score: {stats['average_score']:.3f}",
    ]

    return "\n".join(lines)


def scan_and_queue() -> str:
    """Scan pending directory and add new files to queue."""
    queue = get_queue()
    added = queue.scan_pending()
    return f"Scanned pending directory. Added {added} new file(s) to queue."


def get_next_file() -> str:
    """Peek at the next file to process."""
    queue = get_queue()
    item = queue.peek()
    if item:
        return json.dumps(item, indent=2)
    return "Queue is empty."


# Tool definitions for LLM
QUEUE_TOOLS = [
    {
        "name": "get_queue_status",
        "description": "Get the current ingestion queue status - how many files are queued, pending, deferred, etc.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "scan_and_queue",
        "description": "Scan the pending directory for new files and add them to the processing queue.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_next_file",
        "description": "Get information about the next file to be processed (highest priority).",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

QUEUE_HANDLERS = {
    "get_queue_status": lambda: get_queue_status(),
    "scan_and_queue": lambda: scan_and_queue(),
    "get_next_file": lambda: get_next_file(),
}


# Test
if __name__ == "__main__":
    queue = get_queue()
    print(get_queue_status())

    print("\nScanning pending...")
    added = queue.scan_pending()
    print(f"Added {added} files")

    print("\nTop items:")
    for item in queue.get_items(5):
        print(f"  {item['name']}: score={item['score']:.3f}, tokens={item['token_estimate']}")
