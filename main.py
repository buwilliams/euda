#!/usr/bin/env python3
"""
Euno - Personal Intelligence System

Entry point for the application.
"""

import argparse
import asyncio
import readline  # noqa: F401 - enables arrow keys and history for input()
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
  skills           Run skill commands
  dev              Developer tools for debugging agents
  points           Show contribution points summary
  set-password     Set the access password (empty to disable auth)
  remove-password  Remove the password (disable auth)
  fresh-start      Reset all user data (memory, topics, logs, password)

Sync Commands:
  sync             Bidirectional sync with remote (default)
  sync --push      Push local data to remote
  sync --pull      Pull remote data to local
  sync --delete    Delete files not on source (requires --push or --pull)
  sync --dry-run   Preview changes without applying
  sync init        Initialize sync with remote server
  sync status      Show sync state and pending conflicts
  sync conflicts   List unresolved conflicts
  sync resolve     Resolve a conflict

Server Commands:
  server-deploy    Deploy code to remote server
  server-remote    SSH into remote server
  server-setup     Setup remote server
  server-remove    Remove remote server

Skill Commands:
  euno skills list                      List available skills
  euno skills <name> --help             Show skill help
  euno skills <name> <command> [args]   Run a skill command

Examples:
  euno web                              # Run web server + agents
  euno chat                             # Chat with default agent (user)
  euno chat worker                      # Chat with specific agent
  euno skills core topics list          # List topics
  euno skills core agents list          # List agents
  euno skills core store import ~/docs  # Import files to memory
  euno skills core memory list          # List memories
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
        "skills": cmd_skills,
        "dev": cmd_dev,
        "points": cmd_points,
        "set-password": cmd_set_password,
        "remove-password": cmd_remove_password,
        "fresh-start": cmd_fresh_start,
        "sync": cmd_sync,
        "server-deploy": cmd_server_deploy,
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


class Spinner:
    """Simple text spinner for CLI feedback with dynamic messages."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Thinking"):
        import threading
        self.message = message
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._last_line_len = 0

    def update(self, message: str):
        """Update the spinner message."""
        with self._lock:
            self.message = message

    def start(self):
        import threading
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        import time
        idx = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[idx % len(self.FRAMES)]
            with self._lock:
                line = f"\r{frame} {self.message}"
            # Clear previous line if shorter
            padding = max(0, self._last_line_len - len(line))
            print(line + " " * padding, end="", flush=True)
            self._last_line_len = len(line)
            idx += 1
            time.sleep(0.1)

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        # Clear the spinner line
        print("\r" + " " * (self._last_line_len + 5) + "\r", end="", flush=True)


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

    # Create manager in main thread so we can wait for startup
    manager = AgentManager()
    set_manager(manager)

    # Start agents in background thread
    def run_agents():
        manager.run()

    agent_thread = threading.Thread(target=run_agents, daemon=True)
    agent_thread.start()

    # Wait for platform startup to complete before showing prompt
    manager.wait_for_startup()
    print()
    print("Type 'quit' to exit.")
    print()

    agent = Agent(agent_id)
    spinner = Spinner("Preparing...")

    def status_callback(status: str):
        """Update spinner with current status."""
        spinner.update(status)

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nGoodbye!")
                break

            spinner.start()
            try:
                response = agent.chat(user_input, status_callback=status_callback)
            finally:
                spinner.stop()

            print(f"{agent_id}: {response}\n")

        except AgentPausedError as e:
            print(f"\n\nAGENT PAUSED: {e.reason}")
            print("\nThe agent has been paused. Use 'euno agents enable <agent_id>' to resume.")
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
    from skills.core.system.fresh_start import perform_fresh_start

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


def cmd_skills(args):
    """Run skill commands.

    Usage:
        euno skills list                    # List available skills
        euno skills <name> --help           # Show skill help
        euno skills <name> <command>        # Execute skill command
    """
    from src.skills import discover_skills, execute_skill, get_skill_usage
    from src.skills.exceptions import SkillError

    if not args or args[0] == "help":
        print("=" * 60)
        print("Euno - Skills")
        print("=" * 60)
        print()
        print("Usage:")
        print("  euno skills list                    # List available skills")
        print("  euno skills <name> --help           # Show skill help")
        print("  euno skills <name> <command>        # Execute skill command")
        print()
        print("Examples:")
        print("  euno skills core topics list")
        print("  euno skills core topics create 'My topic'")
        print("  euno skills core memory list")
        return

    if args[0] == "list":
        skills = discover_skills()
        print("=" * 60)
        print("Euno - Available Skills")
        print("=" * 60)
        print()
        if not skills:
            print("No skills found.")
            return
        for skill in skills:
            if skill.description:
                print(f"  {skill.name}: {skill.description}")
            else:
                print(f"  {skill.name}")
        print()
        print("Use 'euno skills <name> --help' for skill details.")
        return

    # Skill name is first arg, rest is the command
    import shlex
    skill_name = args[0]
    # Quote args that contain spaces to preserve them through shlex.split in executor
    command = " ".join(shlex.quote(a) for a in args[1:]) if len(args) > 1 else "--help"

    try:
        result = execute_skill(skill_name, command)
        print(result.output)
        if not result.success:
            sys.exit(result.exit_code)
    except SkillError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_sync(args):
    """Bidirectional sync with remote server.

    Usage:
        euno sync                     # Bidirectional sync (default)
        euno sync --dry-run           # Preview changes without applying
        euno sync --push              # Local -> remote only
        euno sync --pull              # Remote -> local only
        euno sync --no-backup         # Skip backup before sync
        euno sync init [server]       # Initialize sync with remote
        euno sync status              # Show sync state
        euno sync conflicts           # List unresolved conflicts
        euno sync resolve <id> --keep-local|--keep-remote

    Backups are created by default before applying changes:
    - Pull: backs up local data/ directory
    - Push: backs up remote data/ directory
    """
    # Handle help early - before any state checks
    if "--help" in args or "-h" in args:
        print("""Bidirectional sync with remote server.

Usage:
    euno sync                     # Bidirectional sync (default)
    euno sync --dry-run           # Preview changes without applying
    euno sync --push              # Local -> remote only
    euno sync --pull              # Remote -> local only
    euno sync --push --delete     # Push and delete remote files not in local
    euno sync --pull --delete     # Pull and delete local files not in remote
    euno sync --no-backup         # Skip backup before sync
    euno sync init [server]       # Initialize sync with remote
    euno sync status              # Show sync state
    euno sync conflicts           # List unresolved conflicts
    euno sync resolve <id> --keep-local|--keep-remote|--keep-newest
    euno sync resolve --keep-local|--keep-remote  # Resolve all conflicts
    euno sync resolve --clear     # Delete resolved conflicts

Backups are created by default before applying changes:
    - Pull: backs up local data/ directory
    - Push: backs up remote data/ directory

The --delete flag propagates deletions (requires --push or --pull):
    - With --push: remote files not in local are deleted
    - With --pull: local files not in remote are deleted""")
        return

    from src.sync import (
        sync, sync_status, get_sync_state, init_sync, test_connection,
        list_conflicts, resolve_conflict, Conflict
    )
    from src.sync.conflicts import Resolution

    # Parse subcommand
    subcommand = args[0] if args else None

    if subcommand == "init":
        # Initialize sync with remote
        server = args[1] if len(args) > 1 else None
        if not server:
            # Try to get from .env
            import os
            server = os.environ.get("EUNO_SERVER")
            if not server:
                print("Usage: euno sync init <user@server>")
                print("Example: euno sync init root@192.168.1.100")
                print("\nOr set EUNO_SERVER in .env")
                sys.exit(1)

        print("=" * 60)
        print("Euno Sync - Initialize")
        print("=" * 60)
        print()
        print(f"Server: {server}")

        # Test connection first
        print("\nTesting connection...")
        success, message = test_connection(server)
        if not success:
            print(f"Error: {message}")
            sys.exit(1)
        print(f"Connected: {message}")

        # Initialize
        state = init_sync(server)
        print(f"\nSync initialized!")
        print(f"Instance ID: {state.instance_id}")
        print(f"Remote: {state.remote.host}:{state.remote.path}")
        print("\nRun 'euno sync' to perform first sync.")
        return

    if subcommand == "status":
        # Show sync status
        status = sync_status()
        print("=" * 60)
        print("Euno Sync - Status")
        print("=" * 60)
        print()
        print(f"Instance ID: {status['instance_id']}")

        if status['remote_configured']:
            print(f"Remote: {status['remote_host']}:{status['remote_path']}")
        else:
            print("Remote: Not configured (run 'sync init' first)")

        if status.get('last_sync'):
            ls = status['last_sync']
            print(f"\nLast sync: {ls['timestamp']}")
            print(f"  Direction: {ls['direction']}")
            print(f"  Pushed: {ls['changes_pushed']} | Pulled: {ls['changes_pulled']}")
            print(f"  Remote instance: {ls['remote_instance_id']}")

        if status['unresolved_conflicts'] > 0:
            print(f"\nUnresolved conflicts: {status['unresolved_conflicts']}")
            print("Run 'euno sync conflicts' to view.")

        return

    if subcommand == "conflicts":
        # List unresolved conflicts
        conflicts = list_conflicts(resolved=False)
        print("=" * 60)
        print("Euno Sync - Conflicts")
        print("=" * 60)
        print()

        if not conflicts:
            print("No unresolved conflicts.")
            return

        print(f"Found {len(conflicts)} unresolved conflict(s):\n")
        for c in conflicts:
            print(f"  [{c.id}] {c.type.value}: {c.description}")
            print(f"    Item: {c.item_id}")
            if c.local_timestamp and c.remote_timestamp:
                print(f"    Local: {c.local_timestamp}")
                print(f"    Remote: {c.remote_timestamp}")
            print()

        print("Resolve with:")
        print("  euno sync resolve <id> --keep-local")
        print("  euno sync resolve <id> --keep-remote")
        print("  euno sync resolve --keep-remote       (all conflicts)")
        print("  euno sync resolve --clear             (delete resolved conflicts)")
        return

    if subcommand == "resolve":
        # Resolve conflicts
        from src.sync.conflicts import clear_resolved_conflicts

        resolution_map = {
            "--keep-local": Resolution.KEEP_LOCAL,
            "--keep-remote": Resolution.KEEP_REMOTE,
            "--keep-newest": Resolution.KEEP_NEWEST,
            "--keep-both": Resolution.KEEP_BOTH,
            "--merge": Resolution.MERGE,
        }

        # Check for --clear option to delete all resolved conflicts
        if len(args) == 2 and args[1] == "--clear":
            deleted = clear_resolved_conflicts()
            print(f"Cleared {deleted} resolved conflict(s).")
            return

        # Check for bulk resolution: euno sync resolve --keep-remote
        if len(args) == 2 and args[1] in resolution_map:
            resolution_arg = args[1]
            conflicts = list_conflicts(resolved=False)
            if not conflicts:
                print("No unresolved conflicts.")
                return
            for c in conflicts:
                resolve_conflict(c.id, resolution_map[resolution_arg])
            print(f"Resolved {len(conflicts)} conflict(s): {resolution_arg}")
            return

        # Single resolution: euno sync resolve <id> --keep-remote
        if len(args) < 3:
            print("Usage:")
            print("  euno sync resolve <id> --keep-local|--keep-remote|--keep-newest")
            print("  euno sync resolve --keep-local|--keep-remote|--keep-newest  (all conflicts)")
            sys.exit(1)

        conflict_id = args[1]
        resolution_arg = args[2]

        if resolution_arg not in resolution_map:
            print(f"Unknown resolution: {resolution_arg}")
            print("Valid options: --keep-local, --keep-remote, --keep-newest, --keep-both, --merge")
            sys.exit(1)

        result = resolve_conflict(conflict_id, resolution_map[resolution_arg])
        if result:
            print(f"Resolved conflict {conflict_id}: {resolution_arg}")
        else:
            print(f"Conflict not found: {conflict_id}")
            sys.exit(1)
        return

    # Default: perform sync
    print("=" * 60)
    print("Euno Sync")
    print("=" * 60)
    print()

    # Parse flags
    dry_run = "--dry-run" in args or "-n" in args
    no_backup = "--no-backup" in args
    delete = "--delete" in args
    direction = "bidirectional"
    if "--push" in args:
        direction = "push"
    elif "--pull" in args:
        direction = "pull"

    if dry_run:
        print("DRY RUN - no changes will be applied\n")

    if no_backup:
        print("BACKUP DISABLED\n")

    if delete:
        if direction == "bidirectional":
            print("Error: --delete requires --push or --pull")
            sys.exit(1)
        print("DELETE MODE - files not on source will be removed\n")

    print(f"Direction: {direction}")

    # Check if remote is configured, auto-configure from .env if needed
    state = get_sync_state()
    if not state.remote:
        import os
        server = os.environ.get("EUNO_SERVER")
        if server:
            state = init_sync(server)
            print(f"Auto-configured from EUNO_SERVER: {server}")
        else:
            print("\nError: No remote configured.")
            print("Set EUNO_SERVER in .env or run 'euno sync init <server>'.")
            sys.exit(1)

    print(f"Remote: {state.remote.host}")
    print()

    # Perform sync
    result = sync(direction=direction, dry_run=dry_run, backup=not no_backup, verbose=True, delete=delete)

    # Handle errors (but not conflicts - those are shown separately)
    if not result.success and result.error:
        print(f"Error: {result.error}")
        sys.exit(1)

    # Show backup info
    if result.local_backup:
        print(f"Local backup: {result.local_backup}")
    if result.remote_backup:
        print(f"Remote backup: {result.remote_backup}")
    if result.local_backup or result.remote_backup:
        print()

    # Show results
    print(result.summary())

    if result.changes:
        print("\nChanges:")
        for change in result.changes:
            status = "applied" if change.applied else ("conflict" if change.type == "conflict" else "pending")
            print(f"  [{change.type}] {change.handler}: {change.description} ({status})")

    if result.conflicts:
        print(f"\n{len(result.conflicts)} conflict(s) detected.")
        print("Run 'euno sync conflicts' to view and resolve.")
        sys.exit(1)

    if not dry_run and result.success:
        print("\nSync complete!")


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
    """Deploy code to remote server."""
    _run_devops_script("deploy-euno.sh", args)


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
