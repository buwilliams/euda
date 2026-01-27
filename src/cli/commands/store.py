"""
Store command - Import files into long-term memory via topic-based processing.

Architecture:
- Files are loaded and checked for duplicates via topic tags
- A Store:ingest topic is created with files as assets
- The user agent processes the topic using RLM
- Topic completion marks the content as processed (no manifest file needed)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from ..formatters import print_error, print_success, print_info


def cmd_store(args: List[str], json_mode: bool = False):
    """Import files into long-term memory via topic-based processing.

    Usage:
      euno store [path]              Create topic to process files with RLM
      euno store                     Show help
      euno store --force             Reprocess duplicates
      euno store --dry-run           Show what would be processed
      euno store --clear-manifest    Clear processing history (legacy - clears old manifest)
    """
    # Parse flags
    force = "--force" in args
    dry_run = "--dry-run" in args
    clear_manifest = "--clear-manifest" in args
    args = [a for a in args if not a.startswith("--")]

    # Handle clear manifest (legacy support)
    if clear_manifest:
        from ...tools.integration.files.dedup import clear_manifest as do_clear
        count = do_clear()
        if json_mode:
            print(json.dumps({"cleared": count}))
        else:
            print_success(f"Cleared {count} entries from legacy manifest", json_mode)
        return

    # Check for path argument
    if not args:
        print_store_help()
        return

    path = Path(args[0]).expanduser().resolve()

    if not path.exists():
        print_error(f"Path does not exist: {path}", json_mode)
        sys.exit(1)

    # Load files
    from ...tools.integration.files.loader import load_files
    from ...tools.integration.files.dedup import compute_hash

    if not json_mode:
        print_info(f"Loading files from: {path}", json_mode)

    loaded = load_files(path)
    items = loaded["items"]
    metadata = loaded["metadata"]

    if not items:
        if json_mode:
            print(json.dumps({
                "error": "No supported files found",
                "skipped": metadata["skipped"]
            }))
        else:
            print_error("No supported files found", json_mode)
            if metadata["skipped"]["unsupported"]:
                print(f"  Skipped {len(metadata['skipped']['unsupported'])} unsupported files")
            if metadata["skipped"]["too_large"]:
                print(f"  Skipped {len(metadata['skipped']['too_large'])} files (too large)")
        sys.exit(1)

    # Check for duplicates via topic tags
    to_process = []
    duplicates = []

    for item in items:
        content_hash = compute_hash(item.content)
        if not force and _is_already_processed(content_hash):
            duplicates.append(item.name)
        else:
            to_process.append((item, content_hash))

    if not json_mode:
        print_info(f"Found {len(items)} files, {len(to_process)} to process", json_mode)
        if duplicates:
            print(f"  Skipping {len(duplicates)} duplicates (use --force to reprocess)")

    if not to_process:
        if json_mode:
            print(json.dumps({
                "status": "nothing_to_process",
                "duplicates": len(duplicates)
            }))
        else:
            print_info("Nothing to process. All files already imported.", json_mode)
        return

    # Dry run - just show what would be processed
    if dry_run:
        if json_mode:
            print(json.dumps({
                "dry_run": True,
                "would_process": [item.name for item, _ in to_process],
                "duplicates": duplicates,
                "total_chars": sum(len(item.content) for item, _ in to_process)
            }))
        else:
            print()
            print("Would create topic to process:")
            for item, content_hash in to_process:
                size_kb = len(item.content) / 1024
                print(f"  - {item.name} ({size_kb:.1f} KB)")
            print()
            print(f"Total: {len(to_process)} files")
        return

    # Create topic with files as assets
    if not json_mode:
        print_info("Creating store topic...", json_mode)

    topic = _create_store_topic(to_process)

    # Output results
    if json_mode:
        print(json.dumps({
            "status": "topic_created",
            "topic_id": topic["id"],
            "topic_name": topic["name"],
            "files_count": len(to_process),
            "duplicates_skipped": len(duplicates)
        }))
    else:
        print()
        print_success(f"Created store topic: {topic['name']}", json_mode)
        print(f"  Topic ID: {topic['id']}")
        print(f"  Files: {len(to_process)}")
        print()
        print("Files attached:")
        for item, _ in to_process:
            print(f"  - {item.name}")
        print()
        print("The user agent will process this topic and import files to long-term memory.")
        print("Run `uv run euno web` to trigger processing.")


def _is_already_processed(content_hash: str) -> bool:
    """Check if content has already been processed via topic tags.

    Args:
        content_hash: SHA-256 hash of the content

    Returns:
        True if a done topic exists with this hash tag
    """
    from ...tools.data.topics import list_topics

    # Check for done topics with this hash tag
    tag = f"store:hash:{content_hash}"
    topics = list_topics(status="done", tag=tag)
    return len(topics) > 0


def _create_store_topic(items_with_hashes: List[tuple]) -> dict:
    """Create a store topic with files as assets.

    Args:
        items_with_hashes: List of (FileItem, content_hash) tuples

    Returns:
        Created topic dict
    """
    from ...tools.data.topics import create_topic, get_agent_inbox_topic
    from ...tools.data.assets import write_asset

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
        # Use the original filename
        filename = item.name

        # Write the content as an asset
        write_asset(topic["id"], filename, item.content)

    return topic


def print_store_help():
    """Print help for store command."""
    print("""
Store Command - Import files into long-term memory

Usage:
  euno store <path>              Create topic to process files
  euno store <path> --dry-run    Show what would be processed
  euno store <path> --force      Reprocess already-imported files
  euno store --clear-manifest    Clear legacy processing history

Examples:
  euno store ~/journal/          Import all journal files
  euno store ~/notes/2024/       Import notes from 2024
  euno store ./my-notes.md       Import a single file
  euno store ~/docs --dry-run    Preview without processing

Supported file types:
  .txt, .md, .markdown, .json, .yaml, .yml, .csv, .log, .rst, .org

How it works:
  1. Files are loaded and checked for duplicates (via topic tags)
  2. A Store:ingest topic is created with files as assets
  3. The user agent processes the topic, extracting dates and writing to memory
  4. Topic completion marks files as processed (no separate manifest)

Deduplication:
  Files are identified by content hash (SHA-256).
  Completed topics with matching hash tags prevent reprocessing.
  Use --force to reimport files that were already processed.
""")
