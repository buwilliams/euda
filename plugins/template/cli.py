"""
Template plugin - Copy this directory to create a new plugin.

This is a minimal example showing the required structure for an Euno plugin.
Plugins are CLI applications that agents interact with via the execute_plugin tool.
"""

import os
import typer

app = typer.Typer(
    name="template",
    help="Template plugin - copy and modify for new plugins",
    no_args_is_help=True,
)


@app.command()
def hello(name: str = typer.Argument("world", help="Name to greet")):
    """Say hello - example command with an argument."""
    print(f"Hello, {name}!")


@app.command()
def echo(
    message: str = typer.Argument(..., help="Message to echo"),
    uppercase: bool = typer.Option(False, "--uppercase", "-u", help="Convert to uppercase"),
):
    """Echo a message - example command with options."""
    output = message.upper() if uppercase else message
    print(output)


@app.command()
def context():
    """Show environment context - demonstrates reading Euno environment variables."""
    data_dir = os.environ.get("EUNO_DATA_DIR", "(not set)")
    agent_id = os.environ.get("EUNO_AGENT_ID", "(not set)")
    topic_id = os.environ.get("EUNO_TOPIC_ID", "(not set)")
    session_id = os.environ.get("EUNO_SESSION_ID", "(not set)")

    print(f"EUNO_DATA_DIR: {data_dir}")
    print(f"EUNO_AGENT_ID: {agent_id}")
    print(f"EUNO_TOPIC_ID: {topic_id}")
    print(f"EUNO_SESSION_ID: {session_id}")


@app.command()
def fail():
    """Exit with error - example of error handling."""
    print("Something went wrong!", err=True)
    raise typer.Exit(1)


def main():
    """Entry point - required by Euno plugin system."""
    app()


if __name__ == "__main__":
    main()
