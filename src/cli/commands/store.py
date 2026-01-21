"""
Store command - Import files into long-term memory via job-based processing.

Architecture:
- Files are loaded and checked for duplicates via job tags
- A Store:ingest job is created with files as assets
- The chat agent processes the job using RLM
- Job completion marks the content as processed (no manifest file needed)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from ..formatters import print_error, print_success, print_info


def cmd_store(args: List[str], json_mode: bool = False):
    """Import files into long-term memory via job-based processing.

    Usage:
      euno store [path]              Create job to process files with RLM
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

    # Check for duplicates via job tags
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
            print("Would create job to process:")
            for item, content_hash in to_process:
                size_kb = len(item.content) / 1024
                print(f"  - {item.name} ({size_kb:.1f} KB)")
            print()
            print(f"Total: {len(to_process)} files")
        return

    # Create job with files as assets
    if not json_mode:
        print_info("Creating store job...", json_mode)

    job = _create_store_job(to_process)

    # Output results
    if json_mode:
        print(json.dumps({
            "status": "job_created",
            "job_id": job["id"],
            "job_name": job["name"],
            "files_count": len(to_process),
            "duplicates_skipped": len(duplicates)
        }))
    else:
        print()
        print_success(f"Created store job: {job['name']}", json_mode)
        print(f"  Job ID: {job['id']}")
        print(f"  Files: {len(to_process)}")
        print()
        print("Files attached:")
        for item, _ in to_process:
            print(f"  - {item.name}")
        print()
        print("The chat agent will process this job and import files to long-term memory.")
        print("Run `uv run euno start` to trigger processing.")


def _is_already_processed(content_hash: str) -> bool:
    """Check if content has already been processed via job tags.

    Args:
        content_hash: SHA-256 hash of the content

    Returns:
        True if a completed job exists with this hash tag
    """
    from ...tools.data.jobs import list_jobs

    # Check for completed jobs with this hash tag
    tag = f"store:hash:{content_hash}"
    jobs = list_jobs(status="completed", tag=tag)
    return len(jobs) > 0


def _create_store_job(items_with_hashes: List[tuple]) -> dict:
    """Create a store job with files as assets.

    Args:
        items_with_hashes: List of (FileItem, content_hash) tuples

    Returns:
        Created job dict
    """
    from ...tools.data.jobs import create_job, get_system_container
    from ...tools.data.assets import write_asset

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Collect hash tags for deduplication
    hash_tags = [f"store:hash:{content_hash}" for _, content_hash in items_with_hashes]

    # Create the job
    system_container = get_system_container()
    job = create_job(
        name=f"Store:ingest:{timestamp}",
        description=f"Import {len(items_with_hashes)} file(s) into long-term memory.\n\n"
                    f"Process each attached file:\n"
                    f"1. Extract date from content or filename\n"
                    f"2. Write content to long-term memory at that date\n"
                    f"3. Complete job when done",
        parent_id=system_container["id"] if system_container else None,
        assignees=["chat"],
        tags=["store:ingest", "trigger:store"] + hash_tags,
        created_by="user"
    )

    # Attach files as assets
    for item, _ in items_with_hashes:
        # Use the original filename
        filename = item.name

        # Write the content as an asset
        write_asset(job["id"], filename, item.content)

    return job


def print_store_help():
    """Print help for store command."""
    print("""
Store Command - Import files into long-term memory

Usage:
  euno store <path>              Create job to process files
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
  1. Files are loaded and checked for duplicates (via job tags)
  2. A Store:ingest job is created with files as assets
  3. The chat agent processes the job, extracting dates and writing to memory
  4. Job completion marks files as processed (no separate manifest)

Deduplication:
  Files are identified by content hash (SHA-256).
  Completed jobs with matching hash tags prevent reprocessing.
  Use --force to reimport files that were already processed.
""")
