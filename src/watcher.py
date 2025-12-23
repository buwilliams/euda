"""
File watcher for the inbox directory.

Monitors data/inbox/pending for new files and triggers the Ingestion Agent.
"""

import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .agents.base import create_agent
from .tools.shared.log import LOG_TOOLS, LOG_HANDLERS
from .tools.ingestion.files import FILE_TOOLS, FILE_HANDLERS, PENDING_DIR


class InboxHandler(FileSystemEventHandler):
    """Handle file events in the inbox."""

    def __init__(self, agent):
        self.agent = agent
        self.handlers = {**LOG_HANDLERS, **FILE_HANDLERS}
        # Track recently processed to avoid duplicates
        self.recently_processed = set()

    def on_created(self, event):
        """Handle new file creation."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Skip hidden files and temp files
        filename = Path(file_path).name
        if filename.startswith('.') or filename.endswith('.tmp'):
            return

        # Skip if recently processed (debounce)
        if file_path in self.recently_processed:
            return

        self.recently_processed.add(file_path)

        # Wait a moment for file to finish writing
        time.sleep(0.5)

        print(f"\n[Inbox] New file detected: {filename}")
        self.process_file(file_path)

        # Clean up recently processed after a delay
        time.sleep(5)
        self.recently_processed.discard(file_path)

    def process_file(self, file_path: str):
        """Process a single file through the Ingestion Agent."""
        try:
            prompt = f"""A new file has arrived in the inbox: {file_path}

Please:
1. Read the file content using read_file_content
2. Extract any temporal hints using extract_temporal_hints
3. Based on the content and hints, write an appropriate log entry
4. Mark the file as processed

Be thoughtful about:
- What type of entry this is (note, photo, event, article, etc.)
- What timestamp to use (prefer EXIF/filename dates over current time)
- What source to record (file type, app it came from if evident)
- Extracting the meaningful content, not just raw text
"""
            response = self.agent.process(prompt, self.handlers)
            print(f"[Archivist] {response}")

        except Exception as e:
            print(f"[Error] Failed to process {file_path}: {e}")


def create_watcher_agent():
    """Create an Ingestion Agent with file processing tools."""
    return create_agent(
        persona_name="ingestion",
        tools=LOG_TOOLS + FILE_TOOLS
    )


def watch_inbox(once: bool = False):
    """
    Watch the inbox for new files.

    Args:
        once: If True, process existing files and exit. If False, watch continuously.
    """
    print("=" * 60)
    print("Euno - Inbox Watcher")
    print("=" * 60)
    print(f"\nWatching: {PENDING_DIR}")
    print("Drop files here to process them into your life log.")
    print("Press Ctrl+C to stop.\n")

    # Create agent
    agent = create_watcher_agent()
    handler = InboxHandler(agent)

    # Process any existing files first
    existing_files = list(PENDING_DIR.glob('*'))
    existing_files = [f for f in existing_files if f.is_file() and not f.name.startswith('.')]

    if existing_files:
        print(f"Found {len(existing_files)} existing file(s) to process...\n")
        for f in existing_files:
            handler.process_file(str(f))
            print()

    if once:
        print("Processed existing files. Exiting.")
        return

    # Set up the watcher
    observer = Observer()
    observer.schedule(handler, str(PENDING_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping watcher...")
        observer.stop()

    observer.join()
    print("Watcher stopped.")


def process_pending():
    """Process all pending files once and exit."""
    watch_inbox(once=True)


if __name__ == "__main__":
    watch_inbox()
