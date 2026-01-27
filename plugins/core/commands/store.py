"""Store command - Import files into long-term memory via topic-based processing."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


@app.command("import")
def import_files(
    path: str = typer.Argument(..., help="Path to file or directory to import"),
    force: bool = typer.Option(False, "--force", "-f", help="Reprocess already-imported files"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be processed"),
):
    """Import files into long-term memory.

    Files are loaded, checked for duplicates, and attached to a Store:ingest topic.
    The user agent processes the topic and writes content to long-term memory.
    """
    from plugins.core.integration.files.loader import load_files
    from plugins.core.integration.files.dedup import compute_hash

    path_obj = Path(path).expanduser().resolve()

    if not path_obj.exists():
        print(f"Error: Path does not exist: {path_obj}")
        raise typer.Exit(1)

    print(f"Loading files from: {path_obj}")

    loaded = load_files(path_obj)
    items = loaded["items"]
    metadata = loaded["metadata"]

    if not items:
        print("Error: No supported files found")
        if metadata["skipped"]["unsupported"]:
            print(f"  Skipped {len(metadata['skipped']['unsupported'])} unsupported files")
        if metadata["skipped"]["too_large"]:
            print(f"  Skipped {len(metadata['skipped']['too_large'])} files (too large)")
        raise typer.Exit(1)

    # Check for duplicates via topic tags
    to_process = []
    duplicates = []

    for item in items:
        content_hash = compute_hash(item.content)
        if not force and _is_already_processed(content_hash):
            duplicates.append(item.name)
        else:
            to_process.append((item, content_hash))

    print(f"Found {len(items)} files, {len(to_process)} to process")
    if duplicates:
        print(f"  Skipping {len(duplicates)} duplicates (use --force to reprocess)")

    if not to_process:
        print("Nothing to process. All files already imported.")
        return

    # Dry run - just show what would be processed
    if dry_run:
        print()
        print("Would create topic to process:")
        for item, content_hash in to_process:
            size_kb = len(item.content) / 1024
            print(f"  - {item.name} ({size_kb:.1f} KB)")
        print()
        print(f"Total: {len(to_process)} files")
        return

    # Create topic with files as assets
    print("Creating store topic...")

    topic = _create_store_topic(to_process)

    print()
    print(f"Created store topic: {topic['name']}")
    print(f"  Topic ID: {topic['id']}")
    print(f"  Files: {len(to_process)}")
    print()
    print("Files attached:")
    for item, _ in to_process:
        print(f"  - {item.name}")
    print()
    print("The user agent will process this topic and import files to long-term memory.")
    print("Run `uv run euno web` to trigger processing.")


@app.command("clear-manifest")
def clear_manifest():
    """Clear legacy processing history (manifest file)."""
    from plugins.core.integration.files.dedup import clear_manifest as do_clear

    count = do_clear()
    print(f"Cleared {count} entries from legacy manifest")


def _is_already_processed(content_hash: str) -> bool:
    """Check if content has already been processed via topic tags."""
    from plugins.core.data.topics import list_topics

    tag = f"store:hash:{content_hash}"
    topics = list_topics(status="done", tag=tag)
    return len(topics) > 0


def _create_store_topic(items_with_hashes: list) -> dict:
    """Create a store topic with files as assets."""
    from plugins.core.data.topics import create_topic, get_agent_inbox_topic
    from plugins.core.data.assets import write_asset

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Collect hash tags for deduplication
    hash_tags = [f"store:hash:{content_hash}" for _, content_hash in items_with_hashes]

    # Create the topic under user agent's inbox
    inbox = get_agent_inbox_topic("user")
    parent_id = inbox["id"] if inbox else None

    topic = create_topic(
        name=f"Store:ingest:{timestamp}",
        description=f"Import {len(items_with_hashes)} file(s) into long-term memory.\n\n"
                    f"Process each attached file:\n"
                    f"1. Extract date from content or filename\n"
                    f"2. Write content to long-term memory at that date\n"
                    f"3. Complete topic when done",
        parent_id=parent_id,
        assignee="user",
        tags=["store:ingest"] + hash_tags,
        created_by="user"
    )

    # Attach files as assets
    for item, _ in items_with_hashes:
        write_asset(topic["id"], item.name, item.content)

    return topic
