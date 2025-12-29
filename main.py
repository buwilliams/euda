#!/usr/bin/env python3
"""
Euno - AI Personal Assistant

Entry point for running agents and services.
"""

import sys


# Subcommand help texts
SUBCOMMAND_HELP = {
    "start": """
Usage: python main.py start

Start the Agent Manager which runs all autonomous agents and the web server.

This is the recommended way to run Euno. It starts:
  - Web server at http://localhost:8000
  - File watchers for inbox and lifelog
  - 6 autonomous agents (archivist, profiler, curator, friend, worker, adaptor)

Press Ctrl+C to stop.
""",
    "ingest": """
Usage: python main.py ingest [path] [options]

Batch process files from the inbox or an external directory.

Arguments:
  path                    Optional directory to ingest (default: inbox)

Options:
  -r, --recursive         Include subdirectories
  -t, --type TYPE         Filter by content type (text, images, video, audio)
                          Can be comma-separated: --type text,images
  --batch-size N          Files per batch (default: 5)
  -h, --help              Show this help message

Examples:
  python main.py ingest                       # Process inbox
  python main.py ingest ~/Documents           # Process directory
  python main.py ingest ~/Documents -r        # Include subdirectories
  python main.py ingest --type text           # Only text files
  python main.py ingest ~/Photos --type images -r
  python main.py ingest --batch-size 10       # Larger batches
""",
    "chat": """
Usage: python main.py chat

Start an interactive chat with The Friend.

This is the default command when no arguments are provided.
The agent supports thinking through problems without threatening identity coherence.

Type 'quit' or 'exit' to end the conversation.
""",
    "archivist": """
Usage: python main.py archivist

Start an interactive chat with The Archivist.

For manual ingestion conversations. For batch processing, use 'ingest' instead.

Type 'quit' or 'exit' to end the conversation.
""",
    "profiler": """
Usage: python main.py profiler

Start an interactive chat with The Profiler.

For discussing profile model, patterns, and behaviors.

Type 'quit' or 'exit' to end the conversation.
""",
    "derive": """
Usage: python main.py derive

Derive synthesis model (epistemic, values, behaviors) from summaries.

Uses existing yearly summaries to construct or update the user's
identity model through temporal derivation.
""",
    "curator": """
Usage: python main.py curator

Start an interactive chat with The Curator.

For discussing attention allocation, opportunities, and energy management.

Type 'quit' or 'exit' to end the conversation.
""",
    "morning": """
Usage: python main.py morning

Generate morning attention briefing.

Produces a curated set of items for the day based on:
  - Current energy state
  - Scheduled commitments
  - Surfaced opportunities
  - Identity-aligned priorities
""",
    "evening": """
Usage: python main.py evening

Generate evening reflection.

Reviews the day and prepares for rest:
  - What was accomplished
  - What needs attention tomorrow
  - Energy restoration suggestions
""",
    "worker": """
Usage: python main.py worker

Start an interactive chat with The Worker.

For discussing tasks, projects, and actions.

Type 'quit' or 'exit' to end the conversation.
""",
    "tasks": """
Usage: python main.py tasks

Process the task queue once.

Executes pending approved tasks and checks for new work.
""",
    "approvals": """
Usage: python main.py approvals

Show actions waiting for approval.

Lists tasks that require user confirmation before execution.
""",
    "adaptor": """
Usage: python main.py adaptor

Start an interactive chat with The Adaptor.

For discussing system improvements and agent evolution.

Type 'quit' or 'exit' to end the conversation.
""",
    "introspect": """
Usage: python main.py introspect

Run a full system analysis.

The Evolution Agent analyzes system capabilities, identifies
potential improvements, and may generate evolution proposals.
""",
    "evolve": """
Usage: python main.py evolve

Review pending agent evolution proposals.

Interactive interface to review, approve, or reject proposals
from the Adaptor.

Commands in review mode:
  review <filename>   View full proposal details
  approve <filename>  Approve and apply the evolution
  reject <filename>   Reject the proposal
  quit                Exit
""",
    "set-password": """
Usage: python main.py set-password

Set or change the password for web UI authentication.

The password is stored as a secure hash in data/shared/state/auth/.
After setting, all existing sessions are invalidated.
""",
    "watch": """
Usage: python main.py watch

Watch inbox for new files and process them automatically.

Runs continuously, processing files as they appear.
Press Ctrl+C to stop.
""",
    "process": """
Usage: python main.py process

Process pending files once and exit.

Unlike 'watch', this processes the current queue and exits.
""",
    "serve": """
Usage: python main.py serve

Start the web API server (standalone).

Starts the FastAPI server at http://localhost:8000 with background agents.
API documentation available at http://localhost:8000/docs

For full agent management, use 'start' instead.
""",
}


def show_subcommand_help(command: str) -> bool:
    """Show help for a subcommand if --help/-h is in args. Returns True if help was shown."""
    args = sys.argv[2:]  # Skip script name and command
    if "-h" in args or "--help" in args:
        if command in SUBCOMMAND_HELP:
            print(SUBCOMMAND_HELP[command].strip())
        else:
            print(f"No detailed help available for '{command}'")
        return True
    return False


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "chat"

    # Lazy imports to avoid loading everything upfront
    commands = {
        "start": lambda: __import__('src.manager', fromlist=['start']).start(),
        "ingest": run_ingest,
        "archivist": lambda: __import__('src.agents.archivist', fromlist=['run_interactive']).run_interactive(),
        "chat": lambda: __import__('src.agents.friend', fromlist=['run_interactive']).run_interactive(),
        "profiler": lambda: __import__('src.agents.profiler', fromlist=['run_interactive']).run_interactive(),
        "derive": run_derive_synthesis,
        "curator": lambda: __import__('src.agents.curator', fromlist=['run_interactive']).run_interactive(),
        "morning": run_morning,
        "evening": run_evening,
        "worker": lambda: __import__('src.agents.worker', fromlist=['run_interactive']).run_interactive(),
        "tasks": run_tasks,
        "approvals": run_approvals,
        "adaptor": lambda: __import__('src.agents.adaptor', fromlist=['run_interactive']).run_interactive(),
        "introspect": run_introspect,
        "evolve": run_evolve,
        "set-password": run_set_password,
        "watch": lambda: __import__('src.watcher', fromlist=['watch_inbox']).watch_inbox(),
        "process": lambda: __import__('src.watcher', fromlist=['process_pending']).process_pending(),
        "serve": run_server,
    }

    if command in ("help", "-h", "--help"):
        print("Euno - AI Personal Assistant")
        print()
        print("Usage: python main.py [command]")
        print()
        print("Commands:")
        print("  start      Start the Agent Manager (runs all agents)")
        print("  ingest     Batch process files with progress (inbox or external dir)")
        print("  chat       Interactive chat with The Friend (default)")
        print("  archivist  Interactive chat with The Archivist")
        print("  profiler   Interactive chat with The Profiler")
        print("  derive     Derive profile model from lifelogs")
        print("  curator    Interactive chat with The Curator")
        print("  morning    Generate morning attention")
        print("  evening    Generate evening reflection")
        print("  worker     Interactive chat with The Worker")
        print("  tasks      Process the task queue once")
        print("  approvals  Show actions waiting for approval")
        print("  adaptor    Interactive chat with The Adaptor")
        print("  introspect Run a full system analysis")
        print("  evolve     Review pending agent evolution proposals")
        print("  set-password  Set password for web UI authentication")
        print("  watch      Watch inbox for new files to process")
        print("  process    Process pending files once and exit")
        print("  serve      Start the web API server (standalone)")
        print()
        print("Examples:")
        print("  python main.py start        # Run Agent Manager (recommended)")
        print("  python main.py              # Start chatting")
        print("  python main.py ingest       # Process inbox files")
        print("  python main.py ingest ~/Documents -r  # Ingest directory recursively")
        print("  python main.py ingest --batch-size 10  # Custom batch size (default: 5)")
        print("  python main.py serve        # Start API at http://localhost:8000")
        print()
        return

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available commands: {', '.join(commands.keys())}")
        print("Use 'python main.py help' for more info.")
        sys.exit(1)

    # Check for subcommand help (for commands that don't handle it themselves)
    # This catches lambda commands like chat, ingestion, summary, etc.
    if show_subcommand_help(command):
        return

    commands[command]()


def run_ingest():
    """Batch process files with progress display."""
    # Check for help flag first
    if show_subcommand_help("ingest"):
        return

    import json
    import hashlib
    import time
    import tempfile
    from datetime import datetime
    from pathlib import Path
    from src.tools.archivist.queue import get_queue
    from src.tools.archivist.token_budget import get_budget
    from src.tools.archivist.digest import generate_digest, get_content_for_ai
    from src.tools.archivist.classifier import mark_as_processed, should_ignore, compute_file_hash
    from src.tools.archivist.content_types import (
        parse_content_types, matches_content_types, is_archive,
        VALID_CONTENT_TYPES
    )
    from src.tools.archivist.archive_extractor import (
        scan_archive_contents, extract_matching_files,
        get_archive_manifest_key, is_archive_supported, get_unsupported_reason
    )
    from src.agents.archivist import create_archivist_agent, ALL_HANDLERS

    # Parse arguments
    source_dir = None
    recursive = False
    content_types = set()  # Empty = all types
    batch_size = 5  # Default batch size

    args = sys.argv[2:]  # Skip 'main.py' and 'ingest'
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ('--recursive', '-r'):
            recursive = True
        elif arg == '--batch-size':
            if i + 1 < len(args):
                try:
                    batch_size = int(args[i + 1])
                    if batch_size < 1:
                        raise ValueError("Batch size must be at least 1")
                    i += 1
                except ValueError as e:
                    print(f"Error: Invalid batch size: {e}")
                    return
            else:
                print("Error: --batch-size requires a number (e.g., --batch-size 5)")
                return
        elif arg in ('--type', '-t'):
            if i + 1 < len(args):
                try:
                    content_types = parse_content_types(args[i + 1])
                    i += 1
                except ValueError as e:
                    print(f"Error: {e}")
                    return
            else:
                print("Error: --type requires a value (e.g., --type text,images)")
                return
        elif not arg.startswith('-'):
            source_dir = arg
        i += 1

    print("=" * 60)
    print("Euno - Batch Ingestion")
    print("=" * 60)
    print()

    # Always use batch processing
    print(f"Batch size: {batch_size}")
    from src.tools.archivist.batch_processor import (
        chunk_files, build_batch_prompt,
        parse_batch_response, write_batch_entries,
        load_batch_system_prompt
    )
    from src.providers import get_provider
    provider = get_provider()
    batch_system_prompt = load_batch_system_prompt()

    budget = get_budget()
    budget_status = budget.get_status()

    # External directory mode
    if source_dir:
        source_path = Path(source_dir).expanduser().resolve()
        if not source_path.exists():
            print(f"Error: Directory not found: {source_path}")
            return
        if not source_path.is_dir():
            print(f"Error: Not a directory: {source_path}")
            return

        print(f"Source: {source_path}")
        print(f"Mode:   {'Recursive' if recursive else 'Top-level only'}")
        if content_types:
            print(f"Types:  {', '.join(sorted(content_types))}")
        else:
            print(f"Types:  All")

        # Load manifest of already-processed files
        manifest_dir = Path(__file__).parent / "data" / "ingestion" / "manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)

        # Create a manifest file name based on the source path
        manifest_name = hashlib.md5(str(source_path).encode()).hexdigest()[:12]
        manifest_file = manifest_dir / f"{manifest_name}.json"

        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            print(f"Manifest: {len(manifest.get('processed', {}))} files previously processed")
        else:
            manifest = {
                "source": str(source_path),
                "created": datetime.now().isoformat(),
                "processed": {}
            }
            print("Manifest: New directory, no previous processing")

        # Scan directory for files
        print("\nScanning directory...")
        if recursive:
            all_files = list(source_path.rglob('*'))
        else:
            all_files = list(source_path.iterdir())

        # Filter to actual files (not dirs) and not ignored
        all_files = [f for f in all_files if f.is_file() and not should_ignore(f.name)[0]]
        print(f"Found {len(all_files)} file(s)")

        # Separate regular files and archives
        regular_files = []
        archive_files = []
        for f in all_files:
            if is_archive(f):
                archive_files.append(f)
            else:
                regular_files.append(f)

        # Filter regular files by content type
        if content_types:
            filtered_files = [f for f in regular_files if matches_content_types(f, content_types)]
            print(f"After type filter: {len(filtered_files)} file(s) match {', '.join(sorted(content_types))}")
        else:
            filtered_files = regular_files

        # Check which regular files are new or changed
        files_to_process = []
        for file_path in filtered_files:
            rel_path = str(file_path.relative_to(source_path))
            file_hash = compute_file_hash(str(file_path))

            prev = manifest["processed"].get(rel_path)
            if prev is None:
                # New file
                files_to_process.append((file_path, file_hash, "new", None))  # None = not from archive
            elif prev.get("hash") != file_hash:
                # Changed file
                files_to_process.append((file_path, file_hash, "changed", None))
            # else: unchanged, skip

        # Process archives - scan for matching content
        archive_contents = []  # List of (archive_path, archive_hash, internal_files)
        if archive_files and content_types:
            print(f"\nScanning {len(archive_files)} archive(s) for matching content...")
            for archive_path in archive_files:
                if not is_archive_supported(archive_path):
                    reason = get_unsupported_reason(archive_path)
                    print(f"  Skipping {archive_path.name}: {reason}")
                    continue

                archive_rel_path = str(archive_path.relative_to(source_path))
                archive_hash = compute_file_hash(str(archive_path))

                # Check if archive has changed since last scan
                prev_archive = manifest.get("archives", {}).get(archive_rel_path)
                if prev_archive and prev_archive.get("hash") == archive_hash:
                    # Archive unchanged, check individual files
                    pass  # Individual file checks happen below

                # Scan archive contents
                try:
                    matching_files = scan_archive_contents(archive_path, content_types)
                    if matching_files:
                        archive_contents.append((archive_path, archive_hash, matching_files))
                        print(f"  {archive_path.name}: {len(matching_files)} matching file(s)")
                except Exception as e:
                    print(f"  Error scanning {archive_path.name}: {e}")

        # Add archive contents to files_to_process
        for archive_path, archive_hash, internal_files in archive_contents:
            archive_rel_path = str(archive_path.relative_to(source_path))
            for file_info in internal_files:
                internal_path = file_info['internal_path']
                manifest_key = get_archive_manifest_key(archive_rel_path, internal_path)

                prev = manifest["processed"].get(manifest_key)
                prev_archive_hash = prev.get("archive_hash") if prev else None

                if prev is None:
                    # New file in archive
                    files_to_process.append((
                        archive_path,
                        archive_hash,
                        "new",
                        {"internal_path": internal_path, "archive_rel_path": archive_rel_path}
                    ))
                elif prev_archive_hash != archive_hash:
                    # Archive changed, need to re-process
                    files_to_process.append((
                        archive_path,
                        archive_hash,
                        "changed",
                        {"internal_path": internal_path, "archive_rel_path": archive_rel_path}
                    ))
                # else: unchanged, skip

        if not files_to_process:
            print("\nNo new or changed files to process.")
            print(f"Token budget: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)")
            return

        new_count = sum(1 for _, _, status, _ in files_to_process if status == "new")
        changed_count = sum(1 for _, _, status, _ in files_to_process if status == "changed")
        archive_count = sum(1 for _, _, _, archive_info in files_to_process if archive_info is not None)
        print(f"New files: {new_count}, Changed files: {changed_count}")
        if archive_count > 0:
            print(f"From archives: {archive_count}")

        # Estimate tokens
        total_estimate = 0
        for file_path, _, _, archive_info in files_to_process:
            try:
                digest = generate_digest(str(file_path))
                total_estimate += digest.get("token_estimate", 0)
            except:
                total_estimate += 500  # rough estimate for failed digests

        print(f"\nFiles to process: {len(files_to_process)}")
        print(f"Estimated tokens: {total_estimate:,}")
        print(f"Token budget: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)")
        print()
        print("Press Ctrl+C to stop gracefully")
        print("-" * 60)

        processed = 0
        failed = 0
        deferred = 0
        start_time = time.time()
        total_files = len(files_to_process)

        # Prepare file data for batch processing
        batch_files = []
        archive_files_to_process = []

        for file_path, file_hash, status, archive_info in files_to_process:
            if archive_info:
                # Archive files need special handling - process individually
                archive_files_to_process.append((file_path, file_hash, status, archive_info))
                continue

            try:
                digest = generate_digest(str(file_path))
                content = get_content_for_ai(str(file_path), digest)

                temporal = digest.get("temporal_hints", {})
                batch_files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'content': content,
                    'category': digest.get('classification', {}).get('category', 'unknown'),
                    'temporal': temporal if temporal.get('timestamp') else None,
                    'hash': file_hash,
                    'rel_path': str(file_path.relative_to(source_path)),
                    'token_estimate': digest.get('token_estimate', 0)
                })
            except Exception as e:
                print(f"Error preparing {file_path.name}: {e}")
                failed += 1

        # Process batches
        batches = chunk_files(batch_files, batch_size=batch_size)
        print(f"\nProcessing: {len(batch_files)} files in {len(batches)} batch(es)")
        if archive_files_to_process:
            print(f"Archive files: {len(archive_files_to_process)}")

        batch_num = 0
        try:
            for batch in batches:
                batch_num += 1
                batch_tokens = sum(f.get('token_estimate', 0) for f in batch)

                # Check budget
                if not budget.can_spend(batch_tokens):
                    print(f"\n[Batch {batch_num}/{len(batches)}] DEFERRED (budget exhausted)")
                    deferred += len(batch)
                    continue

                print(f"\n[Batch {batch_num}/{len(batches)}] Processing {len(batch)} files ({batch_tokens:,} tokens)...")

                try:
                    # Build prompt and call API (single call for entire batch!)
                    prompt = build_batch_prompt(batch)
                    response = provider.complete(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt=batch_system_prompt
                    )

                    # Parse and write entries
                    entries = parse_batch_response(response, len(batch))
                    results = write_batch_entries(entries)

                    # Track results and update manifest
                    for j, result in enumerate(results):
                        if j < len(batch):
                            file_info = batch[j]
                            if result['status'] == 'success':
                                manifest["processed"][file_info['rel_path']] = {
                                    "hash": file_info['hash'],
                                    "processed_at": datetime.now().isoformat(),
                                    "tokens": file_info['token_estimate'],
                                }
                                processed += 1
                                print(f"   ✓ {file_info['name']}")
                            else:
                                failed += 1
                                print(f"   ✗ {file_info['name']}: {result.get('error', 'unknown')}")

                    # Record budget usage
                    budget.spend(batch_tokens, f"Batch {batch_num}: {len(batch)} files")

                    # Save manifest periodically
                    manifest["updated"] = datetime.now().isoformat()
                    with open(manifest_file, 'w') as f:
                        json.dump(manifest, f, indent=2)

                except Exception as e:
                    print(f"   Batch failed: {e}")
                    failed += len(batch)

        except KeyboardInterrupt:
            print("\n\nStopping gracefully...")
            manifest["updated"] = datetime.now().isoformat()
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)

        # Final summary
        elapsed = time.time() - start_time
        final_budget = budget.get_status()

        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Source:    {source_path}")
        print(f"Processed: {processed} file(s)")
        print(f"Failed:    {failed} file(s)")
        print(f"Deferred:  {deferred} file(s)")
        print(f"Batches:   {batch_num}")
        print(f"Time:      {elapsed:.1f}s")
        if processed > 0:
            print(f"Avg time:  {elapsed/processed:.2f}s per file")
        print()
        print(f"Token usage today: {final_budget['used']:,} / {final_budget['daily_limit']:,} ({final_budget['percent_used']:.1f}%)")
        print(f"Remaining:         {final_budget['remaining']:,} tokens")

        if deferred > 0:
            print(f"\nNote: {deferred} file(s) deferred due to budget. Run again tomorrow.")

        return

    # Inbox mode
    queue = get_queue()

    # Recover any stuck files first
    from src.agents.archivist import AutonomousArchivistAgent
    agent_instance = AutonomousArchivistAgent()
    agent_instance._recover_stuck_files()

    # Restore deferred files if new day
    restored = queue.restore_deferred()
    if restored > 0:
        print(f"Restored {restored} deferred file(s) from yesterday")

    # Scan for new files
    added = queue.scan_pending()
    if added > 0:
        print(f"Found {added} new file(s) in inbox")

    # Get initial stats
    stats = queue.stats()

    total_files = stats['queue_length']
    if total_files == 0:
        print("\nNo files to process.")
        print(f"Token budget: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)")
        return

    print(f"\nFiles to process: {total_files}")
    print(f"Estimated tokens: {stats['total_token_estimate']:,}")
    print(f"Token budget: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)")
    print()
    print("Press Ctrl+C to stop gracefully")
    print("-" * 60)

    processed = 0
    failed = 0
    deferred = 0
    start_time = time.time()

    # BATCH PROCESSING MODE for inbox
    # Collect all items from queue for batch processing
    batch_files = []
    queue_items = []

    # Pop all items from queue to prepare batches
    while True:
        item = queue.pop()
        if item is None:
            break
        queue_items.append(item)

    for item in queue_items:
        file_path = item.get("path", "")
        file_name = item.get("name", "unknown")
        file_hash = item.get("hash", "")

        try:
            digest = generate_digest(file_path)
            content = get_content_for_ai(file_path, digest)
            token_estimate = digest.get("token_estimate", 0)

            # Check budget
            if not budget.can_spend(token_estimate):
                queue.defer(item, "budget_exhausted")
                deferred += 1
                continue

            temporal = digest.get("temporal_hints", {})
            batch_files.append({
                'name': file_name,
                'path': file_path,
                'content': content,
                'category': digest.get('classification', {}).get('category', 'unknown'),
                'temporal': temporal if temporal.get('timestamp') else None,
                'hash': file_hash,
                'token_estimate': token_estimate,
                'queue_item': item
            })
        except Exception as e:
            print(f"Error preparing {file_name}: {e}")
            queue.complete(item, success=False, reason=str(e))
            failed += 1

    # Process batches
    batches = chunk_files(batch_files, batch_size=batch_size)
    print(f"\nProcessing: {len(batch_files)} files in {len(batches)} batch(es)")

    batch_num = 0
    try:
        for batch in batches:
            batch_num += 1
            batch_tokens = sum(f.get('token_estimate', 0) for f in batch)

            print(f"\n[Batch {batch_num}/{len(batches)}] Processing {len(batch)} files ({batch_tokens:,} tokens)...")

            try:
                # Build prompt and call API (single call for entire batch!)
                prompt = build_batch_prompt(batch)
                response = provider.complete(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=batch_system_prompt
                )

                # Parse and write entries
                entries = parse_batch_response(response, len(batch))
                results = write_batch_entries(entries)

                # Track results
                for j, result in enumerate(results):
                    if j < len(batch):
                        file_info = batch[j]
                        if result['status'] == 'success':
                            queue.complete(file_info['queue_item'], success=True)
                            if file_info['hash']:
                                mark_as_processed(file_info['path'], file_info['hash'])
                            processed += 1
                            print(f"   ✓ {file_info['name']}")
                        else:
                            queue.complete(file_info['queue_item'], success=False, reason=result.get('error', 'unknown'))
                            failed += 1
                            print(f"   ✗ {file_info['name']}: {result.get('error', 'unknown')}")

                # Record budget usage
                budget.spend(batch_tokens, f"Batch {batch_num}: {len(batch)} files")

            except Exception as e:
                print(f"   Batch failed: {e}")
                for file_info in batch:
                    queue.complete(file_info['queue_item'], success=False, reason=str(e))
                failed += len(batch)

    except KeyboardInterrupt:
        print("\n\nStopping gracefully...")

    # Final summary
    elapsed = time.time() - start_time
    final_budget = budget.get_status()

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Processed: {processed} file(s)")
    print(f"Failed:    {failed} file(s)")
    print(f"Deferred:  {deferred} file(s)")
    print(f"Batches:   {batch_num}")
    print(f"Time:      {elapsed:.1f}s")
    if processed > 0:
        print(f"Avg time:  {elapsed/processed:.2f}s per file")
    print()
    print(f"Token usage today: {final_budget['used']:,} / {final_budget['daily_limit']:,} ({final_budget['percent_used']:.1f}%)")
    print(f"Remaining:         {final_budget['remaining']:,} tokens")

    final_stats = queue.stats()
    if final_stats['queue_length'] > 0:
        print(f"\nNote: {final_stats['queue_length']} file(s) still in queue")
    if final_stats['deferred_files'] > 0:
        print(f"Note: {final_stats['deferred_files']} file(s) deferred until tomorrow")


def run_server():
    """Run the FastAPI web server with background agents."""
    if show_subcommand_help("serve"):
        return

    import asyncio
    import uvicorn
    import threading
    from src.agents.worker import AutonomousWorkerAgent
    from src.agents.curator import AutonomousCuratorAgent
    from src.agents.archivist import AutonomousArchivistAgent

    print("=" * 60)
    print("Euno - Web API Server")
    print("=" * 60)
    print()
    print("Starting server at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    print()

    # Start background agents in a separate thread
    def run_agents():
        async def agent_loop():
            agents = [
                AutonomousWorkerAgent(),
                AutonomousCuratorAgent(morning_hour=7, evening_hour=21),
                AutonomousArchivistAgent(),
            ]

            # Start all agent loops
            tasks = [asyncio.create_task(agent.run()) for agent in agents]
            print(f"Started {len(agents)} background agents")

            # Keep running until cancelled
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                for agent in agents:
                    agent.stop()

        asyncio.run(agent_loop())

    # Start agents in background thread
    agent_thread = threading.Thread(target=run_agents, daemon=True)
    agent_thread.start()
    print("Background agents running (Worker, Curator, Archivist)")
    print("Press Ctrl+C to stop.")
    print()

    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


def run_derive_synthesis():
    """Derive synthesis model (epistemic, values, behaviors) from summaries."""
    if show_subcommand_help("derive"):
        return

    from src.agents.profiler import derive_synthesis
    print("=" * 60)
    print("Euno - Deriving Synthesis Model")
    print("=" * 60)
    print()
    print("Epistemic axioms are the foundation. Values and behaviors are derived.")
    print()
    result = derive_synthesis()
    print(f"\n{result}")


# Backwards compatibility aliases
run_derive_self = run_derive_synthesis
run_derive_identity = run_derive_synthesis


def run_morning():
    """Generate morning attention."""
    if show_subcommand_help("morning"):
        return

    from src.agents.curator import morning_attention
    print("=" * 60)
    print("Euno - Morning Attention")
    print("=" * 60)
    print()
    result = morning_attention()
    print(f"\n{result}")


def run_evening():
    """Generate evening reflection."""
    if show_subcommand_help("evening"):
        return

    from src.agents.curator import evening_attention
    print("=" * 60)
    print("Euno - Evening Reflection")
    print("=" * 60)
    print()
    result = evening_attention()
    print(f"\n{result}")


def run_tasks():
    """Process the task queue once."""
    if show_subcommand_help("tasks"):
        return

    from src.agents.worker import process_task_queue
    print("=" * 60)
    print("Euno - Task Queue Processing")
    print("=" * 60)
    print()
    result = process_task_queue()
    print(f"\n{result}")


def run_approvals():
    """Show actions waiting for approval."""
    if show_subcommand_help("approvals"):
        return

    from src.agents.worker import check_pending_approvals
    print("=" * 60)
    print("Euno - Pending Approvals")
    print("=" * 60)
    print()
    result = check_pending_approvals()
    print(f"\n{result}")


def run_introspect():
    """Run a full system analysis."""
    if show_subcommand_help("introspect"):
        return

    from src.agents.adaptor import run_analysis
    print("=" * 60)
    print("Euno - System Analysis")
    print("=" * 60)
    print()
    print("Analyzing system capabilities...")
    print()
    result = run_analysis()
    print(f"\n{result}")


def run_evolve():
    """Interactive review of agent evolution proposals."""
    if show_subcommand_help("evolve"):
        return

    from src.tools.shared.identity import (
        get_pending_evolutions, review_evolution,
        approve_evolution, reject_evolution
    )
    print("=" * 60)
    print("Euno - Agent Evolution Review")
    print("=" * 60)
    print()

    # Show pending proposals
    pending = get_pending_evolutions()
    print(pending)

    if "No pending" in pending:
        return

    print("\nCommands:")
    print("  review <filename>  - View full proposal details")
    print("  approve <filename> - Approve and apply the evolution")
    print("  reject <filename>  - Reject the proposal")
    print("  quit               - Exit")
    print()

    while True:
        try:
            cmd = input("> ").strip()

            if not cmd:
                continue

            if cmd.lower() in ('quit', 'exit', 'q'):
                break

            parts = cmd.split(maxsplit=1)
            action = parts[0].lower()

            if action == "review" and len(parts) > 1:
                print()
                print(review_evolution(parts[1]))
                print()
            elif action == "approve" and len(parts) > 1:
                print()
                print(approve_evolution(parts[1]))
                print()
            elif action == "reject" and len(parts) > 1:
                reason = input("Reason (optional): ").strip()
                print()
                print(reject_evolution(parts[1], reason))
                print()
            else:
                print("Unknown command. Use: review, approve, reject, or quit")

        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"Error: {e}")


def run_set_password():
    """Set or change the password for web UI authentication."""
    if show_subcommand_help("set-password"):
        return

    import getpass
    from src.web.auth import set_password, is_password_set

    print("=" * 60)
    print("Euno - Set Password")
    print("=" * 60)
    print()

    if is_password_set():
        print("A password is already set. This will replace it.")
        print("All existing sessions will be invalidated.")
        print()

    try:
        password = getpass.getpass("Enter new password: ")
        if not password:
            print("Cancelled.")
            return

        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match.")
            return

        result = set_password(password)
        print()
        print(result)

    except KeyboardInterrupt:
        print("\nCancelled.")


if __name__ == "__main__":
    main()
