"""
Dev CLI - Main command dispatcher.

Usage: python main.py dev <command> [args] [--json]
"""

import sys
from typing import List


def cmd_dev(args: List[str]):
    """Main dev command dispatcher."""
    if not args or args[0] == "help":
        print_help()
        return

    # Parse global flags
    json_mode = "--json" in args
    if json_mode:
        args = [a for a in args if a != "--json"]

    subcommand = args[0]
    sub_args = args[1:]

    # Dispatch to command handlers
    if subcommand == "memory":
        from .commands.memory import cmd_memory
        cmd_memory(sub_args, json_mode)

    elif subcommand == "identity":
        from .commands.identity import cmd_identity
        cmd_identity(sub_args, json_mode)

    elif subcommand == "prompt":
        from .commands.prompt import cmd_prompt
        cmd_prompt(sub_args, json_mode)

    elif subcommand == "topic":
        from .commands.topic import cmd_topic
        cmd_topic(sub_args, json_mode)

    elif subcommand == "run":
        from .commands.topic import cmd_run
        cmd_run(sub_args, json_mode)

    elif subcommand == "chat":
        from .commands.chat import cmd_chat
        cmd_chat(sub_args, json_mode)

    elif subcommand == "reflect":
        from .commands.reflect import cmd_reflect
        cmd_reflect(sub_args, json_mode)

    elif subcommand == "upload":
        from .commands.upload import cmd_upload
        cmd_upload(sub_args, json_mode)

    elif subcommand == "watch":
        from .commands.watch import cmd_watch
        cmd_watch(sub_args, json_mode)

    elif subcommand == "trace":
        from .commands.trace import cmd_trace
        cmd_trace(sub_args, json_mode)

    else:
        print(f"Unknown dev command: {subcommand}")
        print_help()
        sys.exit(1)


def print_help():
    """Print dev command help."""
    print("""
Dev CLI - Development tools for debugging and improving Euno agents

Usage: python main.py dev <command> [args] [--json]

Global Flags:
  --json                    Output as JSON lines (machine-readable)

Commands:

TOPIC EXECUTION
  topic <agent> <task>      Create topic and run immediately
    --no-reflect            Skip reflection append after execution
    --dry-run               Show prompt without executing
    --max-iterations N      Limit work cycle iterations

  run <agent> <topic_id>    Run an existing topic
    --no-reflect            Skip reflection append

REFLECTION
  reflect <agent>           Run full reflection (append + consolidate)
    --append                Run only append phase
    --consolidate           Run only consolidate phase

MEMORY
  memory <agent>            Show all memory
    --short                 Show only short-term memory
    --long                  Show only long-term memory (last 7 days)
    --add <type> <desc>     Add a memory entry manually
    --graduate <id>         Graduate a memory to long-term

IDENTITY
  identity <agent>          Show agent's identity
    --history               Show historical identity snapshots

SKILLS
  Use 'euno skills' commands instead:
    euno skills list                    List available skills
    euno skills <name> --help           Get skill help
    euno skills <name> <command>        Execute skill command

PROMPTS
  prompt <agent> system     Show system prompt
  prompt <agent> topic <id> Show topic prompt
  prompt <agent> reflect    Show reflection prompt

CHAT
  chat <agent> <message>    Single LLM turn (no work cycle)
    --no-tools              Disable tool execution
    --no-reflect            Skip reflection append

UPLOAD
  upload <target> <file>    Upload file to agent inbox or topic

OBSERVABILITY
  watch                     Live stream all system events
    --agent <id>            Filter to specific agent
    --event <type>          Filter to specific event type
  trace <topic_id>          Show execution trace of a topic

Examples:
  python main.py dev memory user
  python main.py dev topic user "List my current topics"
  python main.py dev reflect user --consolidate
  python main.py dev watch --agent user
  euno skills core topics list --status todo
""")
