"""
Store command - Import files into long-term memory using RLM.
"""

import json
import sys
from pathlib import Path
from typing import List

from ..formatters import print_error, print_success, print_info


def cmd_store(args: List[str], json_mode: bool = False):
    """Import files into long-term memory using RLM processing.

    Usage:
      euno store [path]              Process files with RLM
      euno store                     Show help
      euno store --force             Reprocess duplicates
      euno store --dry-run           Show what would be processed
      euno store --clear-manifest    Clear processing history
    """
    # Parse flags
    force = "--force" in args
    dry_run = "--dry-run" in args
    clear_manifest = "--clear-manifest" in args
    args = [a for a in args if not a.startswith("--")]

    # Handle clear manifest
    if clear_manifest:
        from ...store.dedup import clear_manifest as do_clear
        count = do_clear()
        if json_mode:
            print(json.dumps({"cleared": count}))
        else:
            print_success(f"Cleared {count} entries from processing manifest", json_mode)
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
    from ...store.loader import load_files, files_to_rlm_format
    from ...store.dedup import is_duplicate, record_processed, compute_hash

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

    # Check for duplicates
    to_process = []
    duplicates = []

    for item in items:
        if not force and is_duplicate(item.content):
            duplicates.append(item.name)
        else:
            to_process.append(item)

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
                "would_process": [item.name for item in to_process],
                "duplicates": duplicates,
                "total_chars": sum(len(item.content) for item in to_process)
            }))
        else:
            print()
            print("Would process:")
            for item in to_process:
                size_kb = len(item.content) / 1024
                print(f"  - {item.name} ({size_kb:.1f} KB)")
            print()
            print(f"Total: {len(to_process)} files")
        return

    # Process with RLM
    if not json_mode:
        print_info("Processing with RLM...", json_mode)

    from ...store.loader import files_to_rlm_format
    from ...store.rlm_processor import process_with_rlm
    from ...store.writer import write_to_memory

    files_data = files_to_rlm_format(to_process)
    result = process_with_rlm(files_data)

    if result.error:
        print_error(f"RLM processing failed: {result.error}", json_mode)
        sys.exit(1)

    if not json_mode:
        print_info(f"RLM completed in {result.iterations} iterations, {result.sub_calls} sub-calls", json_mode)

    # Write to memory
    if not json_mode:
        print_info("Writing to long-term memory...", json_mode)

    write_result = write_to_memory(result.results)

    # Record processed files
    for res in result.results:
        if not res.error:
            # Find original item to get content for hashing
            for item in to_process:
                if item.name == res.file:
                    record_processed(
                        path=item.path,
                        content=item.content,
                        date=res.date,
                        date_source=res.date_source
                    )
                    break

    # Output results
    if json_mode:
        print(json.dumps({
            "status": "completed",
            "written": write_result["written"],
            "errors": write_result["errors"],
            "total_written": write_result["total_written"],
            "rlm_iterations": result.iterations,
            "rlm_sub_calls": result.sub_calls
        }))
    else:
        print()
        if write_result["written"]:
            print_success(f"Imported {write_result['total_written']} files to long-term memory", json_mode)
            print()
            for w in write_result["written"]:
                print(f"  {w['file']}")
                print(f"    -> {w['date']} (from {w['date_source']})")

        if write_result["errors"]:
            print()
            print_error(f"Failed to import {len(write_result['errors'])} files:", json_mode)
            for e in write_result["errors"]:
                print(f"  {e['file']}: {e['error']}")


def print_store_help():
    """Print help for store command."""
    print("""
Store Command - Import files into long-term memory using RLM

Usage:
  euno store <path>              Process files at path
  euno store <path> --dry-run    Show what would be processed
  euno store <path> --force      Reprocess already-imported files
  euno store --clear-manifest    Clear processing history

Examples:
  euno store ~/journal/          Import all journal files
  euno store ~/notes/2024/       Import notes from 2024
  euno store ./my-notes.md       Import a single file
  euno store ~/docs --dry-run    Preview without processing

Supported file types:
  .txt, .md, .markdown, .json, .yaml, .yml, .csv, .log, .rst, .org

How it works:
  1. Files are loaded and checked for duplicates
  2. RLM (Recursive Language Model) analyzes each file
  3. Dates are extracted from content, filename, or file metadata
  4. Content is written to long-term memory at the appropriate date

Date extraction priority:
  1. Dates found in file content (headers, metadata)
  2. Dates parsed from filename (2024-01-15, 20240115, etc.)
  3. File modification time (fallback)

The processing manifest tracks imported files to avoid duplicates.
Use --force to reimport files, or --clear-manifest to reset history.
""")
