"""
Scaffold plugin - Create and author new plugins.

Use this plugin to:
- Generate new plugin boilerplate with proper structure
- Write custom code to plugin files
- Read existing plugin code for reference

This enables LLM agents to create fully functional plugins on demand.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="scaffold",
    help="Create and author new plugins",
    no_args_is_help=True,
)

# Get plugins directory from environment or default
PLUGINS_DIR = Path(os.environ.get("EUNO_PLUGINS_DIR", Path(__file__).parent.parent))


@app.command("plugin")
def create_plugin(
    name: str = typer.Argument(..., help="Plugin name (lowercase, no spaces)"),
    description: str = typer.Option(
        None, "--description", "-d",
        help="Plugin description for --help output"
    ),
    with_commands: bool = typer.Option(
        False, "--with-commands", "-c",
        help="Create commands/ subdirectory structure"
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Overwrite existing plugin"
    ),
):
    """Create a new plugin with standard Euno conventions.

    Creates a plugin directory with cli.py containing Typer boilerplate,
    environment variable handling, and example commands.

    Examples:
        scaffold plugin weather -d "Weather forecasts"
        scaffold plugin github -d "GitHub integration" --with-commands
    """
    # Validate name
    if not name.replace("_", "").replace("-", "").isalnum():
        print(f"Error: Invalid plugin name '{name}'. Use lowercase letters, numbers, hyphens, or underscores.")
        raise typer.Exit(1)

    name = name.lower().replace("-", "_")
    plugin_dir = PLUGINS_DIR / name

    # Check if exists
    if plugin_dir.exists() and not force:
        print(f"Error: Plugin '{name}' already exists at {plugin_dir}")
        print("Use --force to overwrite.")
        raise typer.Exit(1)

    # Create directory
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Generate description
    desc = description or f"{name.replace('_', ' ').title()} plugin for Euno"

    if with_commands:
        _create_plugin_with_commands(plugin_dir, name, desc)
    else:
        _create_simple_plugin(plugin_dir, name, desc)

    print(f"Created plugin: {name}")
    print(f"  Location: {plugin_dir}")
    print()
    print("Next steps:")
    print(f"  1. Edit {plugin_dir}/cli.py to add your commands")
    print(f"  2. Test with: uv run euno plugin {name} --help")
    print(f"  3. Use in chat: ask the agent to use the {name} plugin")


@app.command("command")
def add_command(
    plugin: str = typer.Argument(..., help="Plugin name to add command to"),
    command: str = typer.Argument(..., help="Command name to add"),
    description: str = typer.Option(
        None, "--description", "-d",
        help="Command description"
    ),
):
    """Add a new command to an existing plugin.

    Generates command boilerplate and prints instructions for integration.

    Example:
        scaffold command weather forecast -d "Get weather forecast"
    """
    plugin_dir = PLUGINS_DIR / plugin

    if not plugin_dir.exists():
        print(f"Error: Plugin '{plugin}' not found at {plugin_dir}")
        raise typer.Exit(1)

    desc = description or f"{command.replace('_', ' ').title()} command"

    # Generate command code
    command_code = f'''
@app.command("{command}")
def {command.replace("-", "_")}_cmd(
    # Add your arguments here
    # arg: str = typer.Argument(..., help="Description"),
    # option: str = typer.Option(None, "--option", "-o", help="Description"),
):
    """{desc}."""
    # Get context from environment
    agent_id = os.environ.get("EUNO_AGENT_ID")

    # TODO: Implement {command} logic
    print(f"Running {command}...")
'''

    print(f"Add this to {plugin_dir}/cli.py:")
    print()
    print(command_code)


@app.command("list")
def list_plugins():
    """List all available plugins."""
    if not PLUGINS_DIR.exists():
        print("No plugins directory found.")
        raise typer.Exit(1)

    plugins = []
    for path in sorted(PLUGINS_DIR.iterdir()):
        if path.is_dir() and not path.name.startswith((".", "_")):
            cli_py = path / "cli.py"
            if cli_py.exists():
                # Extract description from docstring
                desc = _extract_description(cli_py)
                plugins.append((path.name, desc))

    if not plugins:
        print("No plugins found.")
        return

    print("Available plugins:")
    print()
    for name, desc in plugins:
        if desc:
            print(f"  {name}: {desc}")
        else:
            print(f"  {name}")


@app.command("read")
def read_file(
    plugin: str = typer.Argument(..., help="Plugin name"),
    file: str = typer.Argument("cli.py", help="File to read (default: cli.py)"),
):
    """Read a plugin file.

    Use this to examine existing plugin code for reference or modification.

    Examples:
        scaffold read core cli.py
        scaffold read weather commands/forecast.py
    """
    plugin_dir = PLUGINS_DIR / plugin

    if not plugin_dir.exists():
        print(f"Error: Plugin '{plugin}' not found")
        raise typer.Exit(1)

    file_path = plugin_dir / file

    if not file_path.exists():
        print(f"Error: File '{file}' not found in plugin '{plugin}'")
        print()
        print("Available files:")
        for f in _list_plugin_files(plugin_dir):
            print(f"  {f}")
        raise typer.Exit(1)

    # Security: ensure file is within plugin directory
    try:
        file_path.resolve().relative_to(plugin_dir.resolve())
    except ValueError:
        print(f"Error: Invalid file path")
        raise typer.Exit(1)

    print(file_path.read_text())


@app.command("write")
def write_file(
    plugin: str = typer.Argument(..., help="Plugin name"),
    file: str = typer.Argument(..., help="File to write (e.g., cli.py)"),
    content: str = typer.Argument(..., help="File content to write"),
):
    """Write content to a plugin file.

    Use this to create or update plugin code. The plugin directory must exist
    (use 'scaffold plugin <name>' first).

    Examples:
        scaffold write weather cli.py "import typer..."
        scaffold write weather commands/forecast.py "def get_forecast():..."
    """
    plugin_dir = PLUGINS_DIR / plugin

    if not plugin_dir.exists():
        print(f"Error: Plugin '{plugin}' not found. Create it first with:")
        print(f"  scaffold plugin {plugin}")
        raise typer.Exit(1)

    file_path = plugin_dir / file

    # Security: ensure file is within plugin directory
    try:
        file_path.resolve().relative_to(plugin_dir.resolve())
    except ValueError:
        print(f"Error: Invalid file path")
        raise typer.Exit(1)

    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    file_path.write_text(content)

    print(f"Wrote {len(content)} bytes to {plugin}/{file}")


@app.command("files")
def list_files(
    plugin: str = typer.Argument(..., help="Plugin name"),
):
    """List files in a plugin directory.

    Shows all Python files and other relevant files in the plugin.

    Example:
        scaffold files core
    """
    plugin_dir = PLUGINS_DIR / plugin

    if not plugin_dir.exists():
        print(f"Error: Plugin '{plugin}' not found")
        raise typer.Exit(1)

    files = _list_plugin_files(plugin_dir)

    if not files:
        print(f"No files found in plugin '{plugin}'")
        return

    print(f"Files in {plugin}/:")
    for f in files:
        print(f"  {f}")


@app.command("test")
def test_plugin(
    plugin: str = typer.Argument(..., help="Plugin name to test"),
):
    """Test a plugin by running its --help command.

    Verifies the plugin can be loaded and executed.

    Example:
        scaffold test weather
    """
    import subprocess

    plugin_dir = PLUGINS_DIR / plugin
    cli_path = plugin_dir / "cli.py"

    if not cli_path.exists():
        print(f"Error: Plugin '{plugin}' not found or missing cli.py")
        raise typer.Exit(1)

    try:
        result = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(plugin_dir)
        )

        if result.returncode == 0:
            print(f"Plugin '{plugin}' is working!")
            print()
            print(result.stdout)
        else:
            print(f"Plugin '{plugin}' has errors:")
            print(result.stderr or result.stdout)
            raise typer.Exit(1)

    except subprocess.TimeoutExpired:
        print(f"Error: Plugin '{plugin}' timed out")
        raise typer.Exit(1)
    except Exception as e:
        print(f"Error testing plugin: {e}")
        raise typer.Exit(1)


def _list_plugin_files(plugin_dir: Path) -> list[str]:
    """List relevant files in a plugin directory."""
    files = []
    for path in sorted(plugin_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(plugin_dir)
            # Skip __pycache__ and hidden files
            if "__pycache__" not in str(rel) and not str(rel).startswith("."):
                files.append(str(rel))
    return files


def _create_simple_plugin(plugin_dir: Path, name: str, description: str):
    """Create a simple plugin with all commands in cli.py."""
    cli_content = f'''"""
{description}

This plugin was scaffolded by the Euno scaffold plugin.
"""

import os
from typing import Optional

import typer

app = typer.Typer(
    name="{name}",
    help="{description}",
    no_args_is_help=True,
)


@app.command("run")
def run_cmd(
    arg: str = typer.Argument(..., help="Input argument"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run the main command.

    This is an example command. Replace with your implementation.
    """
    # Access Euno context from environment variables
    data_dir = os.environ.get("EUNO_DATA_DIR")
    agent_id = os.environ.get("EUNO_AGENT_ID")
    topic_id = os.environ.get("EUNO_TOPIC_ID")

    if verbose:
        print(f"Data dir: {{data_dir}}")
        print(f"Agent: {{agent_id}}")
        print(f"Topic: {{topic_id}}")

    # TODO: Implement your logic here
    print(f"Running with arg: {{arg}}")


@app.command("status")
def status_cmd():
    """Show plugin status.

    Example command that shows environment context.
    """
    print("{name} plugin")
    print()
    print("Environment:")
    print(f"  EUNO_DATA_DIR: {{os.environ.get('EUNO_DATA_DIR', '(not set)')}}")
    print(f"  EUNO_AGENT_ID: {{os.environ.get('EUNO_AGENT_ID', '(not set)')}}")
    print(f"  EUNO_TOPIC_ID: {{os.environ.get('EUNO_TOPIC_ID', '(not set)')}}")


def main():
    """Entry point for the plugin CLI."""
    app()


if __name__ == "__main__":
    main()
'''

    (plugin_dir / "cli.py").write_text(cli_content)
    (plugin_dir / "__init__.py").write_text(f'"""{description}"""\n')


def _create_plugin_with_commands(plugin_dir: Path, name: str, description: str):
    """Create a plugin with commands/ subdirectory structure."""
    commands_dir = plugin_dir / "commands"
    commands_dir.mkdir(exist_ok=True)

    # Create cli.py
    cli_content = f'''"""
{description}

This plugin was scaffolded by the Euno scaffold plugin.
"""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from plugins.{name}.commands import example

app = typer.Typer(
    name="{name}",
    help="{description}",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(example.app, name="example", help="Example commands")


def main():
    """Entry point for the plugin CLI."""
    app()


if __name__ == "__main__":
    main()
'''

    # Create commands/__init__.py
    commands_init = f'''"""{name} plugin commands."""
'''

    # Create commands/example.py
    example_content = f'''"""Example commands for {name} plugin."""

import os
from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


@app.command("run")
def run_cmd(
    arg: str = typer.Argument(..., help="Input argument"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run the example command.

    Replace this with your implementation.
    """
    # Access Euno context from environment variables
    data_dir = os.environ.get("EUNO_DATA_DIR")
    agent_id = os.environ.get("EUNO_AGENT_ID")

    if verbose:
        print(f"Data dir: {{data_dir}}")
        print(f"Agent: {{agent_id}}")

    print(f"Running with arg: {{arg}}")


@app.command("list")
def list_cmd():
    """List items.

    Example list command.
    """
    print("No items yet.")
'''

    (plugin_dir / "cli.py").write_text(cli_content)
    (plugin_dir / "__init__.py").write_text(f'"""{description}"""\n')
    (commands_dir / "__init__.py").write_text(commands_init)
    (commands_dir / "example.py").write_text(example_content)


def _extract_description(cli_py: Path) -> Optional[str]:
    """Extract description from cli.py docstring."""
    try:
        content = cli_py.read_text()
        # Look for module docstring
        if content.startswith('"""'):
            end = content.find('"""', 3)
            if end > 0:
                docstring = content[3:end].strip()
                # Return first line
                return docstring.split("\n")[0].strip()
        elif content.startswith("'''"):
            end = content.find("'''", 3)
            if end > 0:
                docstring = content[3:end].strip()
                return docstring.split("\n")[0].strip()
    except Exception:
        pass
    return None


def main():
    """Entry point for the scaffold plugin CLI."""
    app()


if __name__ == "__main__":
    main()
