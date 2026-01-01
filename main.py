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
  start       Start the agent manager (runs all enabled agents)
  serve       Start the web server with agents
  chat        Interactive chat with an agent
  agents      List all agents
  jobs        List all jobs

Examples:
  python main.py start          # Run agents in background
  python main.py serve          # Run web server + agents
  python main.py chat           # Chat with default agent
  python main.py chat worker    # Chat with specific agent
  python main.py agents         # List agents
  python main.py jobs           # List jobs
"""
    )

    parser.add_argument("command", nargs="?", default="help",
                        help="Command to run")
    parser.add_argument("args", nargs="*", help="Command arguments")

    args = parser.parse_args()

    commands = {
        "start": cmd_start,
        "serve": cmd_serve,
        "chat": cmd_chat,
        "agents": cmd_agents,
        "jobs": cmd_jobs,
        "help": lambda _: parser.print_help(),
    }

    if args.command not in commands:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

    commands[args.command](args.args)


def cmd_start(args):
    """Start the agent manager."""
    from src.manager import AgentManager

    print("=" * 60)
    print("Euno - Starting Agent Manager")
    print("=" * 60)
    print()

    manager = AgentManager()
    asyncio.run(manager.run())


def cmd_serve(args):
    """Start web server with agents."""
    import threading
    import uvicorn
    from src.manager import AgentManager
    from src.web.app import app

    print("=" * 60)
    print("Euno - Web Server")
    print("=" * 60)
    print()
    print("API: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print()

    # Start agents in background thread
    def run_agents():
        manager = AgentManager()
        asyncio.run(manager.run())

    agent_thread = threading.Thread(target=run_agents, daemon=True)
    agent_thread.start()
    print("Agent Manager started in background")
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


if __name__ == "__main__":
    main()
