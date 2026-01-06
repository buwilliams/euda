#!/usr/bin/env python3
"""
Euno - Personal Intelligence System

Entry point for the application.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


def main():
    parser = argparse.ArgumentParser(
        description="Euno - Personal Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start            Start the web server with agents
  chat             Interactive chat with an agent
  agents           List all agents
  jobs             List all jobs
  points           Show contribution points summary
  set-password     Set the access password
  remove-password  Remove the password (disable auth)
  fresh-start      Reset all user data (lifelog, jobs, logs, password)

Examples:
  python main.py start             # Run web server + agents
  python main.py chat              # Chat with default agent (friend)
  python main.py chat friend       # Chat with specific agent
  python main.py agents            # List agents
  python main.py jobs              # List jobs
  python main.py points            # Show contribution points
  python main.py set-password      # Set access password
  python main.py remove-password   # Disable authentication
  python main.py fresh-start       # Clean slate (keeps agent configs)
"""
    )

    parser.add_argument("command", nargs="?", default="help",
                        help="Command to run")
    parser.add_argument("args", nargs="*", help="Command arguments")

    args = parser.parse_args()

    commands = {
        "start": cmd_start,
        "chat": cmd_chat,
        "agents": cmd_agents,
        "jobs": cmd_jobs,
        "points": cmd_points,
        "set-password": cmd_set_password,
        "remove-password": cmd_remove_password,
        "fresh-start": cmd_fresh_start,
        "help": lambda _: parser.print_help(),
    }

    if args.command not in commands:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

    commands[args.command](args.args)


def cmd_start(args):
    """Start web server with agents."""
    import signal
    import threading
    import uvicorn
    from src.manager import AgentManager
    from src.web.app import app
    from src.llms import ConfigError
    from src.llms.base import _load_config
    from src.events import trigger_shutdown

    # Validate config at startup
    try:
        _load_config()
    except ConfigError as e:
        print(f"Error: {e}")
        print("\nPlease ensure data/system/config.json exists and is valid.")
        sys.exit(1)

    print("=" * 60)
    print("Euno - Personal Intelligence System")
    print("=" * 60)
    print()
    print("Web UI: http://localhost:8000")
    print("API:    http://localhost:8000/docs")
    print()

    # Start agents in background thread
    def run_agents():
        from src.manager import set_manager
        from src.events import set_event_bus
        manager = AgentManager()
        set_manager(manager)
        set_event_bus(manager.event_bus)
        asyncio.run(manager.run())

    agent_thread = threading.Thread(target=run_agents, daemon=True)
    agent_thread.start()
    print("Agents running in background")
    print()

    # Run web server with custom signal handling
    async def serve():
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)

        # Custom signal handler: close SSE connections BEFORE uvicorn shutdown
        def handle_signal():
            trigger_shutdown()  # Close SSE connections immediately
            server.should_exit = True

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_signal)

        await server.serve()

    asyncio.run(serve())


def cmd_chat(args):
    """Interactive chat with an agent."""
    from src.agent import Agent
    from src.tools import get_tools_for_agent
    from src.cost_tracker import BudgetExceeded, print_summary
    from src.llms import ConfigError
    from src.llms.base import _load_config

    # Validate config at startup
    try:
        _load_config()
    except ConfigError as e:
        print(f"Error: {e}")
        print("\nPlease ensure data/system/config.json exists and is valid.")
        sys.exit(1)

    agent_id = args[0] if args else "friend"

    print("=" * 60)
    print(f"Euno - Chat with {agent_id}")
    print("=" * 60)
    print()
    print("Type 'quit' to exit.")
    print()

    agent = Agent(agent_id)

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nGoodbye!")
                break

            response = agent.chat(user_input)
            print(f"\n{agent_id}: {response}\n")

        except BudgetExceeded as e:
            print(f"\n\nBUDGET EXCEEDED: ${e.spent:.4f} spent of ${e.budget:.2f} limit")
            print_summary()
            print("\nExiting due to budget limit.")
            break
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def cmd_agents(args):
    """List all agents."""
    from src.tools.agents import list_agents

    print("=" * 60)
    print("Euno - Agents")
    print("=" * 60)
    print()

    agents = list_agents()
    if not agents:
        print("No agents configured.")
        return

    for agent in agents:
        status = "enabled" if agent.get("enabled") else "disabled"
        print(f"  {agent['id']}: {agent['name']} [{status}]")


def cmd_jobs(args):
    """List all jobs."""
    from src.tools.jobs import list_jobs

    print("=" * 60)
    print("Euno - Jobs")
    print("=" * 60)
    print()

    jobs = list_jobs()
    if not jobs:
        print("No jobs found.")
        return

    for job in jobs:
        print(f"  [{job['status']}] {job['name']} ({job['id']})")


def cmd_points(args):
    """Show contribution points summary."""
    import re

    # Optional fuzzy name filter
    name_filter = args[0].lower() if args else None

    print("=" * 60)
    print("Euno - Contribution Points")
    print("=" * 60)
    print()

    contrib_dir = Path(__file__).parent / "contrib"
    if not contrib_dir.exists():
        print("No contrib/ directory found.")
        return

    # Parse all contributor files (exclude README.md)
    contributors = []
    total_points = 0
    filtered_points = 0

    for file in sorted(contrib_dir.glob("*.md")):
        if file.name.lower() == "readme.md":
            continue

        content = file.read_text()

        # Extract name from filename (firstname-lastname.md)
        name_parts = file.stem.split("-")
        first_name = name_parts[0].title() if name_parts else "Unknown"
        last_name = name_parts[1].title() if len(name_parts) > 1 else ""

        # Parse point entries: [yyyy-mm-dd][points] or [yyyy-mm-dd][--]
        # Match patterns like [2025-01-06][25] or [2025-01-06][--] or [2025-01-06][-]
        pattern = r'\[[\d-]+\]\[([^\]]+)\]'
        matches = re.findall(pattern, content)

        user_points = 0
        has_points = False
        for match in matches:
            # Skip non-numeric values like "--" or "-"
            if match.strip() in ('--', '-', ''):
                continue
            try:
                points = int(match)
                user_points += points
                has_points = True
            except ValueError:
                # Not a number, skip
                continue

        contributor = {
            "first_name": first_name,
            "last_name": last_name,
            "points": user_points,
            "has_points": has_points
        }
        contributors.append(contributor)
        total_points += user_points

        # Check if matches filter
        if name_filter:
            full_name = f"{first_name} {last_name}".lower()
            if name_filter in full_name:
                filtered_points += user_points
                contributor["matches_filter"] = True
            else:
                contributor["matches_filter"] = False
        else:
            contributor["matches_filter"] = True

    if not contributors:
        print("No contributor files found.")
        return

    # Filter contributors if name filter provided
    display_contributors = [c for c in contributors if c["matches_filter"]]

    if name_filter and not display_contributors:
        print(f"No contributors matching '{name_filter}' found.")
        return

    # Display results
    print(f"Total Points: {total_points}")
    if name_filter:
        print(f"Filter: '{name_filter}' ({len(display_contributors)} match{'es' if len(display_contributors) != 1 else ''})")
    print()
    print(f"{'First Name':<15} {'Last Name':<15} {'Points':>10} {'Percent':>10}")
    print("-" * 52)

    for c in display_contributors:
        if total_points > 0 and c["has_points"]:
            percent = (c["points"] / total_points) * 100
            percent_str = f"{percent:.1f}%"
        elif not c["has_points"]:
            percent_str = "--"
        else:
            percent_str = "0.0%"

        points_str = str(c["points"]) if c["has_points"] else "--"
        print(f"{c['first_name']:<15} {c['last_name']:<15} {points_str:>10} {percent_str:>10}")


def cmd_set_password(args):
    """Set the access password."""
    import getpass
    from src.auth import set_password, is_password_set

    print("=" * 60)
    print("Euno - Set Password")
    print("=" * 60)
    print()

    if is_password_set():
        print("A password is already set.")
        confirm = input("Do you want to replace it? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return

    try:
        password = getpass.getpass("Enter new password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("Passwords do not match.")
            return

        set_password(password)
        print("\nPassword set successfully.")
        print("The web UI will now require authentication.")

    except ValueError as e:
        print(f"Error: {e}")
    except RuntimeError as e:
        print(f"Error: {e}")


def cmd_remove_password(args):
    """Remove the access password (disable authentication)."""
    from src.auth import remove_password, is_password_set

    print("=" * 60)
    print("Euno - Remove Password")
    print("=" * 60)
    print()

    if not is_password_set():
        print("No password is currently set.")
        return

    confirm = input("Are you sure you want to remove the password? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    remove_password()
    print("\nPassword removed.")
    print("The web UI no longer requires authentication.")


def cmd_fresh_start(args):
    """Reset all user data for a clean slate."""
    import shutil
    from pathlib import Path

    print("=" * 60)
    print("Euno - Fresh Start")
    print("=" * 60)
    print()
    print("This will DELETE:")
    print("  - All lifelog entries")
    print("  - User profile")
    print("  - All jobs and job assets")
    print("  - All agent logs and conversation history")
    print("  - Password (if set)")
    print()
    print("This will KEEP:")
    print("  - Agent configurations and personas")
    print("  - System configuration")
    print()

    confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return

    data_dir = Path(__file__).parent / "data"
    deleted = []

    # 1. Clear user data (lifelog, profile)
    user_dir = data_dir / "user"
    if user_dir.exists():
        # Remove lifelog files
        lifelog_dir = user_dir / "lifelog"
        if lifelog_dir.exists():
            for f in lifelog_dir.glob("*.md"):
                f.unlink()
                deleted.append(f"lifelog/{f.name}")
        # Remove profile
        profile = user_dir / "user-profile.md"
        if profile.exists():
            profile.unlink()
            deleted.append("user-profile.md")

    # 2. Clear jobs database and assets
    jobs_dir = data_dir / "jobs"
    if jobs_dir.exists():
        # Remove SQLite database
        db_file = jobs_dir / "db.sqlite"
        if db_file.exists():
            db_file.unlink()
            deleted.append("jobs/db.sqlite")
        # Remove database journal files
        for pattern in ["db.sqlite-journal", "db.sqlite-wal", "db.sqlite-shm"]:
            journal = jobs_dir / pattern
            if journal.exists():
                journal.unlink()
                deleted.append(f"jobs/{pattern}")
        # Remove assets directory
        assets_dir = jobs_dir / "assets"
        if assets_dir.exists():
            shutil.rmtree(assets_dir)
            deleted.append("jobs/assets/")

    # 3. Clear agent logs and state (keep config and persona)
    agents_dir = data_dir / "agents"
    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                # Remove logs
                logs_dir = agent_dir / "logs"
                if logs_dir.exists():
                    shutil.rmtree(logs_dir)
                    deleted.append(f"agents/{agent_dir.name}/logs/")
                # Remove state (conversation history, memory)
                state_dir = agent_dir / "state"
                if state_dir.exists():
                    shutil.rmtree(state_dir)
                    deleted.append(f"agents/{agent_dir.name}/state/")

    # 4. Remove password
    auth_file = data_dir / "system" / "auth.json"
    if auth_file.exists():
        auth_file.unlink()
        deleted.append("system/auth.json")

    print()
    print(f"Deleted {len(deleted)} items:")
    for item in deleted[:10]:
        print(f"  - {item}")
    if len(deleted) > 10:
        print(f"  ... and {len(deleted) - 10} more")

    print()
    print("Fresh start complete. Ready for new data.")


if __name__ == "__main__":
    main()
