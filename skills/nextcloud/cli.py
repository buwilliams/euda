"""Nextcloud integration skill - Files, calendar, and deck operations."""

import sys
from pathlib import Path
from typing import Optional

import typer
import click

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.nextcloud.commands import files, calendar, deck


def _format_param(param: click.Parameter) -> str:
    """Format a Click parameter for display."""
    if isinstance(param, click.Argument):
        if param.required:
            return f"<{param.name}>"
        return f"[{param.name}]"
    elif isinstance(param, click.Option):
        opts = "/".join(param.opts)
        if param.is_flag:
            return f"[{opts}]"
        return f"[{opts} <{param.name}>]"
    return ""


def _get_command_signature(name: str, cmd: click.Command) -> str:
    """Get the full signature for a command."""
    parts = [name]
    for param in cmd.params:
        # Skip the help option
        if isinstance(param, click.Option) and param.name == "help":
            continue
        parts.append(_format_param(param))
    return " ".join(parts)


def _print_full_help(ctx: typer.Context):
    """Print comprehensive help showing all subcommands."""
    print("Nextcloud integration: files, calendar, and deck boards.\n")
    print("Usage: nextcloud <group> <command> [OPTIONS] [ARGS]\n")

    # Get the underlying Click group
    group = ctx.command

    subgroups = {
        "files": ("WebDAV file operations", files.app),
        "calendar": ("CalDAV calendar operations", calendar.app),
        "deck": ("Deck kanban board operations", deck.app),
        "instances": ("Manage Nextcloud instances", None),  # Defined inline
    }

    for group_name, (group_help, sub_app) in subgroups.items():
        print(f"## {group_name} - {group_help}\n")

        if sub_app is None:
            # Handle inline commands (instances)
            print(f"  nextcloud {group_name} list")
            print(f"      List configured Nextcloud instances.\n")
            continue

        # Get Click commands from the Typer app
        click_group = typer.main.get_command(sub_app)

        for cmd_name in sorted(click_group.commands.keys()):
            cmd = click_group.commands[cmd_name]
            sig = _get_command_signature(cmd_name, cmd)
            full_cmd = f"nextcloud {group_name} {sig}"

            # Print command with description
            print(f"  {full_cmd}")
            if cmd.help:
                print(f"      {cmd.help}")

            # Print non-trivial options
            for param in cmd.params:
                if isinstance(param, click.Option) and param.name != "help":
                    opts = "/".join(param.opts)
                    param_help = param.help or ""
                    default = ""
                    if param.default is not None and param.default != ():
                        default = f" (default: {param.default})"
                    print(f"        {opts}: {param_help}{default}")
            print()


def _help_callback(ctx: typer.Context, value: bool):
    """Custom help callback that shows all subcommands."""
    if value:
        _print_full_help(ctx)
        raise typer.Exit()


app = typer.Typer(
    name="nextcloud",
    help="Nextcloud integration: files, calendar, and deck boards.",
    no_args_is_help=False,
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    help: Optional[bool] = typer.Option(None, "--help", "-h", callback=_help_callback, is_eager=True),
):
    """Nextcloud integration: files, calendar, and deck boards."""
    if ctx.invoked_subcommand is None:
        _print_full_help(ctx)
        raise typer.Exit()


# Register command groups
app.add_typer(files.app, name="files", help="WebDAV file operations")
app.add_typer(calendar.app, name="calendar", help="CalDAV calendar operations")
app.add_typer(deck.app, name="deck", help="Deck kanban board operations")


# Instances command group
instances_app = typer.Typer(
    name="instances",
    help="Manage Nextcloud instances.",
    no_args_is_help=True,
)
app.add_typer(instances_app, name="instances", help="Manage Nextcloud instances")


@instances_app.command("list")
def list_instances():
    """List configured Nextcloud instances."""
    from skills.nextcloud.lib.client import list_instances

    instances = list_instances()

    if not instances:
        print("No Nextcloud instances configured.")
        print("Add instances in data/system/config.json under nextcloud.instances")
        return

    print("Configured Nextcloud instances:")
    for inst in instances:
        print(f"  {inst['id']}: {inst['name']} ({inst['url']})")


def main():
    """Entry point for the Nextcloud skill CLI."""
    app()


if __name__ == "__main__":
    main()
