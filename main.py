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
