#!/usr/bin/env python3
"""
Euno - AI Personal Assistant

Entry point for running agents and services.
"""

import sys


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
        "ingestion": lambda: __import__('src.agents.ingestion', fromlist=['run_interactive']).run_interactive(),
        "chat": lambda: __import__('src.agents.interaction', fromlist=['run_interactive']).run_interactive(),
        "summary": lambda: __import__('src.agents.summary', fromlist=['run_interactive']).run_interactive(),
        "summarize": run_summarize,
        "values": lambda: __import__('src.agents.values', fromlist=['run_interactive']).run_interactive(),
        "derive": run_derive_values,
        "attention": lambda: __import__('src.agents.attention', fromlist=['run_interactive']).run_interactive(),
        "morning": run_morning,
        "evening": run_evening,
        "world": lambda: __import__('src.agents.world', fromlist=['run_interactive']).run_interactive(),
        "discover": run_discover,
        "worker": lambda: __import__('src.agents.worker', fromlist=['run_interactive']).run_interactive(),
        "tasks": run_tasks,
        "approvals": run_approvals,
        "introspection": lambda: __import__('src.agents.introspection', fromlist=['run_interactive']).run_interactive(),
        "introspect": run_introspect,
        "evolve": run_evolve,
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
        print("  chat       Interactive chat with The Caring Friend (default)")
        print("  ingestion  Interactive chat with The Archivist")
        print("  summary    Interactive chat with The Historian")
        print("  summarize  Generate summaries for all years needing updates")
        print("  values     Interactive chat with The Philosopher")
        print("  derive     Derive values from summaries")
        print("  attention  Interactive chat with The Curator")
        print("  morning    Generate morning attention")
        print("  evening    Generate evening reflection")
        print("  world      Interactive chat with The Scout")
        print("  discover   Run a discovery sweep for opportunities")
        print("  worker     Interactive chat with The Executor")
        print("  tasks      Process the task queue once")
        print("  approvals  Show actions waiting for approval")
        print("  introspection  Interactive chat with The Mirror")
        print("  introspect Run a full system analysis")
        print("  evolve     Review pending identity evolution proposals")
        print("  watch      Watch inbox for new files to process")
        print("  process    Process pending files once and exit")
        print("  serve      Start the web API server (standalone)")
        print()
        print("Examples:")
        print("  python main.py start        # Run Agent Manager (recommended)")
        print("  python main.py              # Start chatting")
        print("  python main.py ingest       # Process inbox files")
        print("  python main.py ingest ~/Documents -r  # Ingest directory recursively")
        print("  python main.py summarize    # Generate yearly summaries")
        print("  python main.py serve        # Start API at http://localhost:8000")
        print()
        return

    if command not in commands:
        print(f"Unknown command: {command}")
        print(f"Available commands: {', '.join(commands.keys())}")
        print("Use 'python main.py help' for more info.")
        sys.exit(1)

    commands[command]()


def run_ingest():
    """Batch process files with progress display.

    Usage:
        python main.py ingest                    # Process inbox
        python main.py ingest /path/to/dir       # Process external directory
        python main.py ingest /path/to/dir --recursive  # Include subdirectories
    """
    import json
    import hashlib
    import time
    from datetime import datetime
    from pathlib import Path
    from src.tools.ingestion.queue import get_queue
    from src.tools.ingestion.token_budget import get_budget
    from src.tools.ingestion.digest import generate_digest, get_content_for_ai
    from src.tools.ingestion.classifier import mark_as_processed, should_ignore, compute_file_hash
    from src.agents.ingestion import create_ingestion_agent, ALL_HANDLERS

    # Parse arguments
    source_dir = None
    recursive = False

    args = sys.argv[2:]  # Skip 'main.py' and 'ingest'
    for arg in args:
        if arg in ('--recursive', '-r'):
            recursive = True
        elif not arg.startswith('-'):
            source_dir = arg

    print("=" * 60)
    print("Euno - Batch Ingestion")
    print("=" * 60)
    print()

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

        # Check which are new or changed
        files_to_process = []
        for file_path in all_files:
            rel_path = str(file_path.relative_to(source_path))
            file_hash = compute_file_hash(str(file_path))

            prev = manifest["processed"].get(rel_path)
            if prev is None:
                # New file
                files_to_process.append((file_path, file_hash, "new"))
            elif prev.get("hash") != file_hash:
                # Changed file
                files_to_process.append((file_path, file_hash, "changed"))
            # else: unchanged, skip

        if not files_to_process:
            print("\nNo new or changed files to process.")
            print(f"Token budget: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)")
            return

        new_count = sum(1 for _, _, status in files_to_process if status == "new")
        changed_count = sum(1 for _, _, status in files_to_process if status == "changed")
        print(f"New files: {new_count}, Changed files: {changed_count}")

        # Estimate tokens
        total_estimate = 0
        for file_path, _, _ in files_to_process:
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

        # Process files
        agent = create_ingestion_agent(include_file_tools=True)
        processed = 0
        failed = 0
        deferred = 0
        start_time = time.time()
        total_files = len(files_to_process)

        try:
            for i, (file_path, file_hash, status) in enumerate(files_to_process):
                rel_path = str(file_path.relative_to(source_path))
                file_name = file_path.name

                # Progress display
                progress = (i + 1) / total_files * 100
                budget_status = budget.get_status()

                status_label = "NEW" if status == "new" else "CHG"
                print(f"\n[{progress:5.1f}%] [{status_label}] {rel_path}")
                print(f"         Tokens: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)")

                try:
                    # Generate digest
                    digest = generate_digest(str(file_path))
                    token_estimate = digest.get("token_estimate", 0)

                    # Check budget
                    if not budget.can_spend(token_estimate):
                        print(f"         -> DEFERRED (budget exhausted, need {token_estimate:,} tokens)")
                        deferred += 1
                        continue

                    # Get content
                    content = get_content_for_ai(str(file_path), digest)

                    # Get temporal hints
                    temporal = digest.get("temporal_hints", {})
                    timestamp = temporal.get("timestamp", "")
                    temporal_note = ""
                    if timestamp:
                        confidence = temporal.get("confidence", "unknown")
                        source_type = temporal.get("source", "unknown")
                        temporal_note = f"\nTemporal hint: {timestamp} (confidence: {confidence}, source: {source_type})"

                    # Build prompt
                    prompt = f"""Process this file and write a log entry.

File: {file_name}
Path: {rel_path}
Category: {digest.get('classification', {}).get('category', 'unknown')}
{temporal_note}

Content:
---
{content}
---

Instructions:
1. Analyze the content to understand what it represents
2. Write a meaningful log entry using write_log_entry
3. Use the temporal hint for the timestamp if available (otherwise use current time)
4. Choose appropriate source and entry_type based on the content
5. Keep the log entry concise but informative

Do NOT read the file again - use the content provided above."""

                    # Process
                    result = agent.process(prompt, ALL_HANDLERS)

                    # Record usage
                    budget.spend(token_estimate, f"Processed: {rel_path}")

                    # Update manifest
                    manifest["processed"][rel_path] = {
                        "hash": file_hash,
                        "processed_at": datetime.now().isoformat(),
                        "tokens": token_estimate
                    }

                    # Save manifest after each file (in case of crash)
                    manifest["updated"] = datetime.now().isoformat()
                    with open(manifest_file, 'w') as f:
                        json.dump(manifest, f, indent=2)

                    processed += 1
                    print(f"         -> OK ({token_estimate:,} tokens)")

                    # Clear context
                    agent.clear_context()

                except Exception as e:
                    print(f"         -> FAILED: {e}")
                    failed += 1

        except KeyboardInterrupt:
            print("\n\nStopping gracefully...")
            # Save manifest on interrupt
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
        print(f"Time:      {elapsed:.1f}s")
        print()
        print(f"Token usage today: {final_budget['used']:,} / {final_budget['daily_limit']:,} ({final_budget['percent_used']:.1f}%)")
        print(f"Remaining:         {final_budget['remaining']:,} tokens")

        if deferred > 0:
            print(f"\nNote: {deferred} file(s) deferred due to budget. Run again tomorrow.")

        return

    # Inbox mode (original behavior)
    queue = get_queue()

    # Recover any stuck files first
    from src.agents.ingestion import AutonomousIngestionAgent
    agent_instance = AutonomousIngestionAgent()
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

    # Create agent for processing
    agent = create_ingestion_agent(include_file_tools=True)

    processed = 0
    failed = 0
    deferred = 0
    start_time = time.time()

    try:
        while True:
            # Get next file
            item = queue.pop()
            if item is None:
                break

            file_path = item.get("path", "")
            file_name = item.get("name", "unknown")
            file_hash = item.get("hash", "")

            # Progress display
            progress = (processed + failed + deferred + 1) / total_files * 100
            budget_status = budget.get_status()

            print(f"\n[{progress:5.1f}%] Processing: {file_name}")
            print(f"         Tokens: {budget_status['used']:,} / {budget_status['daily_limit']:,} ({budget_status['percent_used']:.1f}%)")

            try:
                # Generate digest
                digest = generate_digest(file_path)
                token_estimate = digest.get("token_estimate", 0)

                # Check budget
                if not budget.can_spend(token_estimate):
                    print(f"         -> DEFERRED (budget exhausted, need {token_estimate:,} tokens)")
                    queue.defer(item, "budget_exhausted")
                    deferred += 1
                    continue

                # Get content
                content = get_content_for_ai(file_path, digest)

                # Get temporal hints
                temporal = digest.get("temporal_hints", {})
                timestamp = temporal.get("timestamp", "")
                temporal_note = ""
                if timestamp:
                    confidence = temporal.get("confidence", "unknown")
                    source = temporal.get("source", "unknown")
                    temporal_note = f"\nTemporal hint: {timestamp} (confidence: {confidence}, source: {source})"

                # Build prompt
                prompt = f"""Process this file and write a log entry.

File: {file_name}
Category: {digest.get('classification', {}).get('category', 'unknown')}
{temporal_note}

Content:
---
{content}
---

Instructions:
1. Analyze the content to understand what it represents
2. Write a meaningful log entry using write_log_entry
3. Use the temporal hint for the timestamp if available (otherwise use current time)
4. Choose appropriate source and entry_type based on the content
5. Keep the log entry concise but informative

Do NOT read the file again - use the content provided above."""

                # Process
                result = agent.process(prompt, ALL_HANDLERS)

                # Record usage
                budget.spend(token_estimate, f"Processed: {file_name}")

                # Mark complete
                queue.complete(item, success=True)
                if file_hash:
                    mark_as_processed(file_path, file_hash)

                processed += 1
                print(f"         -> OK ({token_estimate:,} tokens)")

                # Clear context
                agent.clear_context()

            except Exception as e:
                print(f"         -> FAILED: {e}")
                queue.complete(item, success=False, reason=str(e))
                failed += 1

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
    print(f"Time:      {elapsed:.1f}s")
    print()
    print(f"Token usage today: {final_budget['used']:,} / {final_budget['daily_limit']:,} ({final_budget['percent_used']:.1f}%)")
    print(f"Remaining:         {final_budget['remaining']:,} tokens")

    # Check if more files waiting
    final_stats = queue.stats()
    if final_stats['queue_length'] > 0:
        print(f"\nNote: {final_stats['queue_length']} file(s) still in queue")
    if final_stats['deferred_files'] > 0:
        print(f"Note: {final_stats['deferred_files']} file(s) deferred until tomorrow")


def run_server():
    """Run the FastAPI web server with background agents."""
    import asyncio
    import uvicorn
    import threading
    from src.agents.worker import AutonomousWorkerAgent
    from src.agents.attention import AutonomousAttentionAgent
    from src.agents.world import AutonomousWorldAgent
    from src.agents.ingestion import AutonomousIngestionAgent

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
                AutonomousAttentionAgent(morning_hour=7, evening_hour=21),
                AutonomousWorldAgent(sweep_interval_hours=24),
                AutonomousIngestionAgent(),
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
    print("Background agents running (Worker, Attention, World, Ingestion)")
    print("Press Ctrl+C to stop.")
    print()

    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


def run_summarize():
    """Generate summaries for all years needing updates."""
    from src.agents.summary import check_and_summarize_all
    check_and_summarize_all()


def run_derive_values():
    """Derive values from summaries."""
    from src.agents.values import derive_values
    print("=" * 60)
    print("Euno - Deriving Values")
    print("=" * 60)
    print()
    result = derive_values()
    print(f"\n{result}")


def run_morning():
    """Generate morning attention."""
    from src.agents.attention import morning_attention
    print("=" * 60)
    print("Euno - Morning Attention")
    print("=" * 60)
    print()
    result = morning_attention()
    print(f"\n{result}")


def run_evening():
    """Generate evening reflection."""
    from src.agents.attention import evening_attention
    print("=" * 60)
    print("Euno - Evening Reflection")
    print("=" * 60)
    print()
    result = evening_attention()
    print(f"\n{result}")


def run_discover():
    """Run a discovery sweep for opportunities."""
    from src.agents.world import run_discovery_sweep
    print("=" * 60)
    print("Euno - Discovery Sweep")
    print("=" * 60)
    print()
    result = run_discovery_sweep()
    print(f"\n{result}")


def run_tasks():
    """Process the task queue once."""
    from src.agents.worker import process_task_queue
    print("=" * 60)
    print("Euno - Task Queue Processing")
    print("=" * 60)
    print()
    result = process_task_queue()
    print(f"\n{result}")


def run_approvals():
    """Show actions waiting for approval."""
    from src.agents.worker import check_pending_approvals
    print("=" * 60)
    print("Euno - Pending Approvals")
    print("=" * 60)
    print()
    result = check_pending_approvals()
    print(f"\n{result}")


def run_introspect():
    """Run a full system analysis."""
    from src.agents.introspection import run_analysis
    print("=" * 60)
    print("Euno - System Introspection")
    print("=" * 60)
    print()
    print("Analyzing system capabilities...")
    print()
    result = run_analysis()
    print(f"\n{result}")


def run_evolve():
    """Interactive review of identity evolution proposals."""
    from src.tools.identity import (
        get_pending_evolutions, review_evolution,
        approve_evolution, reject_evolution
    )
    from pathlib import Path

    EVOLUTION_DIR = Path(__file__).parent / "data" / "agents" / "evolution"

    print("=" * 60)
    print("Euno - Identity Evolution Review")
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


if __name__ == "__main__":
    main()
