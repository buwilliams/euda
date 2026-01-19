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
  dev              Developer tools for debugging agents
  set-password     Set the access password
  remove-password  Remove the password (disable auth)
  fresh-start      Reset all user data (memory, jobs, logs, password)

Examples:
  python main.py start             # Run web server + agents
  python main.py chat              # Chat with default agent (chat)
  python main.py chat chat         # Chat with specific agent
  python main.py agents            # List agents
  python main.py jobs              # List jobs
  python main.py points            # Show contribution points
  python main.py dev help          # Show dev commands
  python main.py set-password      # Set access password
  python main.py remove-password   # Disable authentication
  python main.py fresh-start       # Clean slate (keeps agent configs)
"""
    )

    parser.add_argument("command", nargs="?", default="help",
                        help="Command to run")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Command arguments")

    args = parser.parse_args()

    commands = {
        "start": cmd_start,
        "chat": cmd_chat,
        "agents": cmd_agents,
        "jobs": cmd_jobs,
        "points": cmd_points,
        "dev": cmd_dev,
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
    from src.cost_tracker import BudgetExceeded, print_cost_summary
    from src.llms import ConfigError
    from src.llms.base import _load_config

    # Validate config at startup
    try:
        _load_config()
    except ConfigError as e:
        print(f"Error: {e}")
        print("\nPlease ensure data/system/config.json exists and is valid.")
        sys.exit(1)

    agent_id = args[0] if args else "chat"

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
            print_cost_summary()
            print("\nExiting due to budget limit.")
            break
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def cmd_agents(args):
    """List agents or perform agent actions."""
    import json
    from src.tools.agents.agents import list_agents

    # Handle help action
    if args and args[0] == 'help':
        print("Usage: python main.py agents [name] [action]")
        print()
        print("Arguments:")
        print("  [name]    Agent ID to filter or act on")
        print()
        print("Actions:")
        print("  (none)    Show agent info")
        print("  enable    Enable the agent")
        print("  disable   Disable the agent")
        print("  logs      Show last 50 log entries")
        print("  help      Show this help")
        return

    data_dir = Path(__file__).parent / "data"

    # Parse args: [name] [action]
    agent_filter = args[0] if args else None
    action = args[1] if len(args) > 1 else None

    # Handle actions
    if agent_filter and action:
        if action == "enable":
            _agent_set_enabled(agent_filter, True)
        elif action == "disable":
            _agent_set_enabled(agent_filter, False)
        elif action == "logs":
            _agent_show_logs(agent_filter)
        else:
            print(f"Unknown action: {action}")
            print("Valid actions: enable, disable, logs")
        return

    print("=" * 60)
    print("Euno - Agents")
    print("=" * 60)
    print()

    # Show system state (only when listing all agents)
    if not agent_filter:
        system_state_path = data_dir / "system" / "state.json"
        if system_state_path.exists():
            with open(system_state_path) as f:
                system_state = json.load(f)
            last_morning = system_state.get("last_morning", "never")
            last_evening = system_state.get("last_evening", "never")
        else:
            last_morning = "never"
            last_evening = "never"

        print(f"System: last_morning={last_morning}, last_evening={last_evening}")
        print()

    agents = list_agents()
    if not agents:
        print("No agents configured.")
        return

    # Filter by name if provided
    if agent_filter:
        agents = [a for a in agents if a['id'] == agent_filter]
        if not agents:
            print(f"Agent not found: {agent_filter}")
            return

    # Sort agents by order
    agents.sort(key=lambda a: a.get("order", 999))

    for agent in agents:
        status = "enabled" if agent.get("enabled") else "disabled"
        agent_id = agent['id']
        order = agent.get("order", "-")
        triggers = ", ".join(agent.get("triggers", [])) or "none"

        # Load agent state to get last_ran
        state_path = data_dir / "agents" / agent_id / "state.json"
        last_ran = "never"
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
                if "last_ran" in state:
                    last_ran = state["last_ran"]

        print(f"  [{order}] {agent_id}: {agent['name']} [{status}]")
        print(f"      triggers: {triggers}")
        print(f"      last_ran: {last_ran}")
        print()


def _agent_set_enabled(agent_id: str, enabled: bool):
    """Enable or disable an agent."""
    import json

    config_path = Path(__file__).parent / "data" / "agents" / agent_id / "config.json"
    if not config_path.exists():
        print(f"Agent not found: {agent_id}")
        return

    with open(config_path) as f:
        config = json.load(f)

    config["enabled"] = enabled

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    status = "enabled" if enabled else "disabled"
    print(f"Agent {agent_id} {status}.")


def _agent_show_logs(agent_id: str):
    """Show last 50 log entries for an agent."""
    import json

    logs_dir = Path(__file__).parent / "data" / "agents" / agent_id / "logs"
    if not logs_dir.exists():
        print(f"No logs found for agent: {agent_id}")
        return

    # Find most recent log file
    log_files = sorted(logs_dir.glob("*.json*"), reverse=True)
    if not log_files:
        print(f"No log files found for agent: {agent_id}")
        return

    log_file = log_files[0]
    print(f"Showing logs from: {log_file.name}")
    print()

    # Read last 50 entries (JSONL format - one JSON object per line)
    entries = []
    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    for entry in entries[-50:]:
        ts = entry.get("timestamp", "?")[:19]
        event = entry.get("event", "?")
        details = entry.get("details", {})
        details_str = json.dumps(details)
        if len(details_str) > 80:
            details_str = details_str[:77] + "..."
        print(f"[{ts}] {event}: {details_str}")


def cmd_jobs(args):
    """List all jobs."""
    from src.tools.data.jobs import list_jobs

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

    CORE_AGENTS = {"chat", "user", "worker"}

    print("=" * 60)
    print("Euno - Fresh Start")
    print("=" * 60)
    print()
    print("This will DELETE:")
    print("  - All agent memory (short-term and long-term)")
    print("  - All agent logs, state, and conversation history")
    print("  - All jobs and job assets")
    print("  - Cost tracking history")
    print("  - Reflection logs")
    print("  - Prompt logs (LLM API call history)")
    print("  - System trigger state")
    print("  - Password (if set)")
    print("  - Non-core agents (anything except chat, user, worker)")
    print()
    print("This will RESET:")
    print("  - Core agent identities (from identity.template.md templates)")
    print()
    print("This will KEEP:")
    print("  - Agent configurations")
    print("  - System configuration")
    print()

    confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return

    data_dir = Path(__file__).parent / "data"
    deleted = []
    reset = []

    # 1. Clear user data (costs)
    user_dir = data_dir / "agents" / "user"
    if user_dir.exists():
        # Remove cost tracking
        costs_dir = user_dir / "costs"
        if costs_dir.exists():
            for f in costs_dir.glob("*.jsonl"):
                f.unlink()
                deleted.append(f"agents/user/costs/{f.name}")

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

    # 3. Process agents - clear data for core agents, remove non-core agents entirely
    agents_dir = data_dir / "agents"
    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                agent_id = agent_dir.name

                if agent_id in CORE_AGENTS:
                    # Core agent: clear logs, state, memory but keep config
                    # Remove logs
                    logs_dir = agent_dir / "logs"
                    if logs_dir.exists():
                        shutil.rmtree(logs_dir)
                        deleted.append(f"agents/{agent_id}/logs/")
                    # Remove state directory (conversation history)
                    state_dir = agent_dir / "state"
                    if state_dir.exists():
                        shutil.rmtree(state_dir)
                        deleted.append(f"agents/{agent_id}/state/")
                    # Remove state.json (last_ran timestamp)
                    state_file = agent_dir / "state.json"
                    if state_file.exists():
                        state_file.unlink()
                        deleted.append(f"agents/{agent_id}/state.json")
                    # Remove memory directory (short-term and long-term)
                    memory_dir = agent_dir / "memory"
                    if memory_dir.exists():
                        shutil.rmtree(memory_dir)
                        deleted.append(f"agents/{agent_id}/memory/")
                    # Remove uploads directory (user agent)
                    uploads_dir = agent_dir / "uploads"
                    if uploads_dir.exists():
                        shutil.rmtree(uploads_dir)
                        deleted.append(f"agents/{agent_id}/uploads/")

                    # Reset identity from template if available
                    identity_template = agent_dir / "identity.template.md"
                    identity_file = agent_dir / "identity.md"
                    if identity_template.exists():
                        template_content = identity_template.read_text()
                        identity_file.write_text(template_content)
                        reset.append(f"agents/{agent_id}/identity.md")
                    elif identity_file.exists():
                        # No template, just remove the identity
                        identity_file.unlink()
                        deleted.append(f"agents/{agent_id}/identity.md")
                else:
                    # Non-core agent: remove entirely
                    shutil.rmtree(agent_dir)
                    deleted.append(f"agents/{agent_id}/ (entire agent)")

    # 4. Remove system state, logs, and password
    system_dir = data_dir / "system"
    if system_dir.exists():
        # Remove system state (trigger tracking)
        state_file = system_dir / "state.json"
        if state_file.exists():
            state_file.unlink()
            deleted.append("system/state.json")
        # Remove password
        auth_file = system_dir / "auth.json"
        if auth_file.exists():
            auth_file.unlink()
            deleted.append("system/auth.json")
        # Remove reflection logs
        reflection_logs = system_dir / "logs" / "reflection"
        if reflection_logs.exists():
            shutil.rmtree(reflection_logs)
            deleted.append("system/logs/reflection/")
        # Remove prompt logs
        prompt_logs = system_dir / "logs" / "prompts"
        if prompt_logs.exists():
            shutil.rmtree(prompt_logs)
            deleted.append("system/logs/prompts/")

    print()
    if deleted:
        print(f"Deleted {len(deleted)} items:")
        for item in deleted[:10]:
            print(f"  - {item}")
        if len(deleted) > 10:
            print(f"  ... and {len(deleted) - 10} more")

    if reset:
        print()
        print(f"Reset {len(reset)} identities from templates:")
        for item in reset:
            print(f"  - {item}")

    print()
    print("Fresh start complete. Ready for new data.")


def cmd_dev(args):
    """Developer tools for debugging and improving agents."""
    from src.cli import cmd_dev as dev_main
    dev_main(args)


if __name__ == "__main__":
    main()
