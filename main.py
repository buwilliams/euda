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
  web              Start the web server with agents
  chat             Interactive chat with an agent
  plugin           Run plugin commands
  dev              Developer tools for debugging agents
  points           Show contribution points summary
  set-password     Set the access password (empty to disable auth)
  remove-password  Remove the password (disable auth)
  fresh-start      Reset all user data (memory, topics, logs, password)

Server Commands:
  server-deploy    Deploy to remote server
  server-pull      Pull data from remote server
  server-push      Push data to remote server
  server-push-agents  Push agent configs to remote server
  server-remote    SSH into remote server
  server-setup     Setup remote server
  server-remove    Remove remote server

Plugin Commands:
  euno plugin list                      List available plugins
  euno plugin <name> --help             Show plugin help
  euno plugin <name> <command> [args]   Run a plugin command

Examples:
  euno web                              # Run web server + agents
  euno chat                             # Chat with default agent (user)
  euno chat worker                      # Chat with specific agent
  euno plugin core topics list          # List topics
  euno plugin core agents list          # List agents
  euno plugin core store import ~/docs  # Import files to memory
  euno plugin core memory list          # List memories
  euno dev help                         # Show dev commands
  euno server-deploy                    # Deploy to remote server
"""
    )

    parser.add_argument("command", nargs="?", default="help",
                        help="Command to run")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Command arguments")

    args = parser.parse_args()

    commands = {
        "web": cmd_web,
        "chat": cmd_chat,
        "plugin": cmd_plugin,
        "dev": cmd_dev,
        "points": cmd_points,
        "set-password": cmd_set_password,
        "remove-password": cmd_remove_password,
        "fresh-start": cmd_fresh_start,
        "server-deploy": cmd_server_deploy,
        "server-pull": cmd_server_pull,
        "server-push": cmd_server_push,
        "server-push-agents": cmd_server_push_agents,
        "server-remote": cmd_server_remote,
        "server-setup": cmd_server_setup,
        "server-remove": cmd_server_remove,
        "help": lambda _: parser.print_help(),
    }

    if args.command not in commands:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

    commands[args.command](args.args)


def cmd_web(args):
    """Start web server with agents."""
    import signal
    import threading
    import uvicorn
    from src.agent.manager import AgentManager
    from src.web.app import app
    from src.llms import ConfigError
    from src.llms.base import _load_config
    from src.web.events import trigger_shutdown

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
        from src.agent.manager import set_manager
        from src.web.events import set_event_bus
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
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
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
    import threading
    from src.agent import Agent
    from src.agent.manager import AgentManager, set_manager
    from src.agent.cognition.metacognition import AgentPausedError
    from src.llms import ConfigError
    from src.llms.base import _load_config

    # Validate config at startup
    try:
        _load_config()
    except ConfigError as e:
        print(f"Error: {e}")
        print("\nPlease ensure data/system/config.json exists and is valid.")
        sys.exit(1)

    agent_id = args[0] if args else "user"

    print("=" * 60)
    print(f"Euno - Chat with {agent_id}")
    print("=" * 60)
    print()

    # Start agents in background thread (same as cmd_start)
    def run_agents():
        manager = AgentManager()
        set_manager(manager)
        asyncio.run(manager.run())

    agent_thread = threading.Thread(target=run_agents, daemon=True)
    agent_thread.start()
    print("Platform running in background (triggers, events)")
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

        except AgentPausedError as e:
            print(f"\n\nAGENT PAUSED: {e.reason}")
            print("\nThe agent has been paused. Use 'uv run euno agents enable <agent_id>' to resume.")
            break
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break




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
    from src.web.auth import set_password, remove_password, is_password_set

    print("=" * 60)
    print("Euno - Set Password")
    print("=" * 60)
    print()
    print("Enter an empty password to disable authentication.")
    print()

    if is_password_set():
        print("A password is already set.")
        confirm = input("Do you want to replace it? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return
        print()

    try:
        password = getpass.getpass("Enter new password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("Passwords do not match.")
            return

        if not password:
            remove_password()
            print("\nPassword removed.")
            print("The web UI no longer requires authentication.")
        else:
            set_password(password)
            print("\nPassword set successfully.")
            print("The web UI will now require authentication.")

    except ValueError as e:
        print(f"Error: {e}")
    except RuntimeError as e:
        print(f"Error: {e}")


def cmd_remove_password(args):
    """Remove the access password (disable authentication)."""
    from src.web.auth import remove_password, is_password_set

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
    from plugins.core.system.fresh_start import perform_fresh_start

    print("=" * 60)
    print("Euno - Fresh Start")
    print("=" * 60)
    print()
    print("This will DELETE:")
    print("  - All agent memory (short-term and long-term)")
    print("  - All agent logs, state, and conversation history")
    print("  - All topics and topic assets")
    print("  - Cost tracking history")
    print("  - All system logs (prompts, incidents, token usage, progress, etc.)")
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
    print("A backup will be created before resetting.")
    print()

    confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return

    result = perform_fresh_start(create_backup_first=True)

    print()
    if result.get("backup_name"):
        print(f"Backup created: {result['backup_name']}")

    deleted = result.get("deleted", [])
    if deleted:
        print()
        print(f"Deleted {len(deleted)} items:")
        for item in deleted[:10]:
            print(f"  - {item}")
        if len(deleted) > 10:
            print(f"  ... and {len(deleted) - 10} more")

    reset = result.get("reset", [])
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


def cmd_plugin(args):
    """Run plugin commands.

    Usage:
        euno plugin list                    # List available plugins
        euno plugin <name> --help           # Show plugin help
        euno plugin <name> <command>        # Execute plugin command
    """
    from src.plugins import discover_plugins, execute_plugin, get_plugin_usage
    from src.plugins.exceptions import PluginError

    if not args or args[0] == "help":
        print("=" * 60)
        print("Euno - Plugins")
        print("=" * 60)
        print()
        print("Usage:")
        print("  euno plugin list                    # List available plugins")
        print("  euno plugin <name> --help           # Show plugin help")
        print("  euno plugin <name> <command>        # Execute plugin command")
        print()
        print("Examples:")
        print("  euno plugin core topics list")
        print("  euno plugin core topics create 'My topic'")
        print("  euno plugin core memory list")
        return

    if args[0] == "list":
        plugins = discover_plugins()
        print("=" * 60)
        print("Euno - Available Plugins")
        print("=" * 60)
        print()
        if not plugins:
            print("No plugins found.")
            return
        for plugin in plugins:
            if plugin.description:
                print(f"  {plugin.name}: {plugin.description}")
            else:
                print(f"  {plugin.name}")
        print()
        print("Use 'euno plugin <name> --help' for plugin details.")
        return

    # Plugin name is first arg, rest is the command
    import shlex
    plugin_name = args[0]
    # Quote args that contain spaces to preserve them through shlex.split in executor
    command = " ".join(shlex.quote(a) for a in args[1:]) if len(args) > 1 else "--help"

    try:
        result = execute_plugin(plugin_name, command)
        print(result.output)
        if not result.success:
            sys.exit(result.exit_code)
    except PluginError as e:
        print(f"Error: {e}")
        sys.exit(1)


def _run_devops_script(script_name: str, args: list):
    """Run a devops script with optional arguments."""
    import subprocess

    script_path = Path(__file__).parent / "devops" / script_name
    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)

    try:
        result = subprocess.run(
            ["bash", str(script_path)] + args,
            cwd=Path(__file__).parent
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)


def cmd_server_deploy(args):
    """Deploy to remote server."""
    _run_devops_script("deploy-euno.sh", args)


def cmd_server_pull(args):
    """Pull data from remote server."""
    _run_devops_script("pull-data-remote.sh", args)


def cmd_server_push(args):
    """Push data to remote server."""
    _run_devops_script("push-data-remote.sh", args)


def cmd_server_push_agents(args):
    """Push agent configs to remote server."""
    _run_devops_script("push-agents-remote.sh", args)


def cmd_server_remote(args):
    """SSH into remote server."""
    _run_devops_script("manage.sh", args)


def cmd_server_setup(args):
    """Setup remote server."""
    _run_devops_script("setup-server.sh", args)


def cmd_server_remove(args):
    """Remove remote server."""
    _run_devops_script("remove-server.sh", args)


if __name__ == "__main__":
    main()
