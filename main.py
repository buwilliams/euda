#!/usr/bin/env python3
"""
Euno - Personal Intelligence System

Entry point for the application.
"""

import argparse
import asyncio
import sys


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
  set-password     Set the access password
  remove-password  Remove the password (disable auth)

Examples:
  python main.py start             # Run web server + agents
  python main.py chat              # Chat with default agent (assistant)
  python main.py chat friend       # Chat with specific agent
  python main.py agents            # List agents
  python main.py jobs              # List jobs
  python main.py set-password      # Set access password
  python main.py remove-password   # Disable authentication
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
        "set-password": cmd_set_password,
        "remove-password": cmd_remove_password,
        "help": lambda _: parser.print_help(),
    }

    if args.command not in commands:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

    commands[args.command](args.args)


def cmd_start(args):
    """Start web server with agents."""
    import threading
    import uvicorn
    from src.manager import AgentManager
    from src.web.app import app

    print("=" * 60)
    print("Euno - Personal Intelligence System")
    print("=" * 60)
    print()
    print("Web UI: http://localhost:8000")
    print("API:    http://localhost:8000/docs")
    print()

    # Start agents in background thread
    def run_agents():
        manager = AgentManager()
        asyncio.run(manager.run())

    agent_thread = threading.Thread(target=run_agents, daemon=True)
    agent_thread.start()
    print("Agents running in background")
    print()

    # Run web server
    uvicorn.run(app, host="0.0.0.0", port=8000)


def cmd_chat(args):
    """Interactive chat with an agent."""
    from src.agent import Agent
    from src.tools import get_tools_for_agent

    agent_id = args[0] if args else "assistant"

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


if __name__ == "__main__":
    main()
