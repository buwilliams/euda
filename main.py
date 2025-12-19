#!/usr/bin/env python3
"""
Me and Us - AI Personal Assistant

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
        "watch": lambda: __import__('src.watcher', fromlist=['watch_inbox']).watch_inbox(),
        "process": lambda: __import__('src.watcher', fromlist=['process_pending']).process_pending(),
        "serve": run_server,
    }

    if command in ("help", "-h", "--help"):
        print("Me and Us - AI Personal Assistant")
        print()
        print("Usage: python main.py [command]")
        print()
        print("Commands:")
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
        print("  watch      Watch inbox for new files to process")
        print("  process    Process pending files once and exit")
        print("  serve      Start the web API server")
        print()
        print("Examples:")
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
    """Run the FastAPI web server."""
    import uvicorn
    print("=" * 60)
    print("Me and Us - Web API Server")
    print("=" * 60)
    print()
    print("Starting server at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
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
    print("Me and Us - Deriving Values")
    print("=" * 60)
    print()
    result = derive_values()
    print(f"\n{result}")


def run_morning():
    """Generate morning attention."""
    from src.agents.attention import morning_attention
    print("=" * 60)
    print("Me and Us - Morning Attention")
    print("=" * 60)
    print()
    result = morning_attention()
    print(f"\n{result}")


def run_evening():
    """Generate evening reflection."""
    from src.agents.attention import evening_attention
    print("=" * 60)
    print("Me and Us - Evening Reflection")
    print("=" * 60)
    print()
    result = evening_attention()
    print(f"\n{result}")


def run_discover():
    """Run a discovery sweep for opportunities."""
    from src.agents.world import run_discovery_sweep
    print("=" * 60)
    print("Me and Us - Discovery Sweep")
    print("=" * 60)
    print()
    result = run_discovery_sweep()
    print(f"\n{result}")


if __name__ == "__main__":
    main()
