"""
Autobot skill - Create, update, debug, and manage all skills.

Use this skill to:
- Generate new skill boilerplate with proper structure
- Write, append, and edit skill files
- Validate skill structure and conventions
- Delete skills or files within skills
- Read existing skill code for reference

This enables LLM agents to create and maintain fully functional skills on demand.
"""

import ast
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="autobot",
    help="Create, update, debug, and manage all skills",
    no_args_is_help=True,
)

# Get skills directory from environment or default
SKILLS_DIR = Path(os.environ.get("EUNO_SKILLS_DIR", Path(__file__).parent.parent))
PROJECT_ROOT = SKILLS_DIR.parent


@app.command("env")
def show_environment():
    """Show development environment and architecture information.

    Displays Python version, dependency management, project structure,
    and coding conventions. Use this before creating new skills to
    understand how to write code that fits the architecture.

    Example:
        autobot env
    """
    import subprocess

    print("=" * 60)
    print("EUNO DEVELOPMENT ENVIRONMENT")
    print("=" * 60)

    # Python version
    print(f"\nPython: {sys.version.split()[0]}")
    print(f"Executable: {sys.executable}")

    # uv version
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"uv: {result.stdout.strip()}")
    except FileNotFoundError:
        print("uv: not found")

    # Project paths
    print(f"\nProject root: {PROJECT_ROOT}")
    print(f"Skills directory: {SKILLS_DIR}")
    data_dir = PROJECT_ROOT / "data"
    print(f"Data directory: {data_dir}")

    # Architecture overview
    print("\n" + "-" * 60)
    print("PROJECT ARCHITECTURE")
    print("-" * 60)
    print("""
src/
├── core/           # Business logic (shared by web + skills)
│   ├── data/       # Topics, assets, memory, identity
│   ├── agents/     # Agent operations
│   └── system/     # Consolidation, notifications
├── skills/         # Skill infrastructure (discovery, executor, tools)
├── agent/          # Agent runtime (Identity + Cognition + Memory)
├── llms/           # LLM clients
└── web/            # FastAPI application

skills/             # Skill CLI interfaces (for LLM agents)
├── core/           # Core skill (wraps src/core/)
├── autobot/        # This skill - skill management
└── <your-skill>/   # Your new skills go here

data/
├── agents/         # Agent configs, state, memory
├── topics/         # SQLite database + assets
└── system/         # System config and logs
""")

    # Environment variables
    print("-" * 60)
    print("ENVIRONMENT VARIABLES (available in skills)")
    print("-" * 60)
    print("""
EUNO_DATA_DIR      - Path to data/ directory
EUNO_SKILLS_DIR    - Path to skills/ directory
EUNO_AGENT_ID      - Current agent ID (if running in agent context)
EUNO_TOPIC_ID      - Current topic ID (if processing a topic)
EUNO_SESSION_ID    - Current session ID (if in a chat session)
""")

    # Coding conventions
    print("-" * 60)
    print("SKILL CODING CONVENTIONS")
    print("-" * 60)
    print("""
1. STRUCTURE: Each skill is a directory with cli.py using Typer
   - cli.py must have main() function and if __name__ == "__main__" block
   - Use app = typer.Typer(name="skillname", help="description")

2. DEPENDENCIES: Use uv for package management
   - Add packages: autobot deps add <package>
   - All skills share project dependencies (no per-skill requirements)

3. CONTEXT: Access Euno context via environment variables
   ```python
   import os
   data_dir = os.environ.get("EUNO_DATA_DIR")
   agent_id = os.environ.get("EUNO_AGENT_ID")
   ```

4. IMPORTS: For accessing core functionality
   ```python
   # From skills, import src modules:
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent))
   from src.core.data.topics import list_topics, create_topic
   ```

5. OUTPUT: Print results to stdout, errors to stderr
   - Success: exit code 0
   - Failure: exit code non-zero with error message

6. COMMANDS: Use clear, verb-based names
   - list, get, create, update, delete, run, sync, etc.
""")

    # Current skills
    print("-" * 60)
    print("INSTALLED SKILLS")
    print("-" * 60)
    skills = []
    for path in sorted(SKILLS_DIR.iterdir()):
        if path.is_dir() and not path.name.startswith((".", "_")):
            cli_py = path / "cli.py"
            if cli_py.exists():
                skills.append(path.name)
    print(f"  {', '.join(skills)}")
    print()


@app.command("skill")
def create_skill(
    name: str = typer.Argument(..., help="Skill name (lowercase, no spaces)"),
    description: str = typer.Option(
        None, "--description", "-d",
        help="Skill description for --help output"
    ),
    with_commands: bool = typer.Option(
        False, "--with-commands", "-c",
        help="Create commands/ subdirectory structure"
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Overwrite existing skill"
    ),
):
    """Create a new skill with standard Euno conventions.

    Creates a skill directory with cli.py containing Typer boilerplate,
    environment variable handling, and example commands.

    Examples:
        autobot skill weather -d "Weather forecasts"
        autobot skill github -d "GitHub integration" --with-commands
    """
    # Validate name
    if not name.replace("_", "").replace("-", "").isalnum():
        print(f"Error: Invalid skill name '{name}'. Use lowercase letters, numbers, hyphens, or underscores.")
        raise typer.Exit(1)

    name = name.lower().replace("-", "_")
    skill_dir = SKILLS_DIR / name

    # Check if exists
    if skill_dir.exists() and not force:
        print(f"Error: Skill '{name}' already exists at {skill_dir}")
        print("Use --force to overwrite.")
        raise typer.Exit(1)

    # Create directory
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Generate description
    desc = description or f"{name.replace('_', ' ').title()} skill for Euno"

    if with_commands:
        _create_skill_with_commands(skill_dir, name, desc)
    else:
        _create_simple_skill(skill_dir, name, desc)

    print(f"Created skill: {name}")
    print(f"  Location: {skill_dir}")
    print()
    print("Next steps:")
    print(f"  1. Edit {skill_dir}/cli.py to add your commands")
    print(f"  2. Test with: euno skills {name} --help")
    print(f"  3. Use in chat: ask the agent to use the {name} skill")


@app.command("command")
def add_command(
    skill: str = typer.Argument(..., help="Skill name to add command to"),
    command: str = typer.Argument(..., help="Command name to add"),
    description: str = typer.Option(
        None, "--description", "-d",
        help="Command description"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be added without modifying files"
    ),
):
    """Add a new command to an existing skill.

    Inserts command boilerplate into the skill's cli.py file before the main() function.

    Examples:
        autobot command weather forecast -d "Get weather forecast"
        autobot command weather forecast -d "Get forecast" --dry-run
    """
    skill_dir = SKILLS_DIR / skill
    cli_path = skill_dir / "cli.py"

    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found at {skill_dir}")
        raise typer.Exit(1)

    if not cli_path.exists():
        print(f"Error: Skill '{skill}' is missing cli.py")
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

    if dry_run:
        print(f"Would add to {skill}/cli.py:")
        print()
        print(command_code)
        return

    # Read existing content and insert before main()
    content = cli_path.read_text()

    # Find the main() function definition
    main_match = re.search(r'\ndef main\(\):', content)
    if main_match:
        # Insert command before main()
        insert_pos = main_match.start()
        new_content = content[:insert_pos] + command_code + content[insert_pos:]
        cli_path.write_text(new_content)
        print(f"Added command '{command}' to {skill}/cli.py")
    else:
        # Fall back to appending before if __name__ block
        name_match = re.search(r'\nif __name__ == ["\']__main__["\']:', content)
        if name_match:
            insert_pos = name_match.start()
            new_content = content[:insert_pos] + command_code + content[insert_pos:]
            cli_path.write_text(new_content)
            print(f"Added command '{command}' to {skill}/cli.py")
        else:
            # Just append
            cli_path.write_text(content + command_code)
            print(f"Appended command '{command}' to {skill}/cli.py")


@app.command("append")
def append_file(
    skill: str = typer.Argument(..., help="Skill name"),
    file: str = typer.Argument(..., help="File to append to (e.g., cli.py)"),
    content: str = typer.Argument(..., help="Content to append"),
):
    """Append content to an existing skill file.

    Adds content to the end of the specified file.

    Examples:
        autobot append weather cli.py "# Additional code here"
        autobot append core commands/topics.py "def new_func(): pass"
    """
    skill_dir = SKILLS_DIR / skill

    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found")
        raise typer.Exit(1)

    file_path = skill_dir / file

    # Security: ensure file is within skill directory
    try:
        file_path.resolve().relative_to(skill_dir.resolve())
    except ValueError:
        print("Error: Invalid file path")
        raise typer.Exit(1)

    if not file_path.exists():
        print(f"Error: File '{file}' not found in skill '{skill}'")
        raise typer.Exit(1)

    # Append content
    existing = file_path.read_text()
    # Ensure newline before appended content if needed
    if existing and not existing.endswith('\n'):
        existing += '\n'
    file_path.write_text(existing + content)

    print(f"Appended {len(content)} bytes to {skill}/{file}")


@app.command("edit")
def edit_file(
    skill: str = typer.Argument(..., help="Skill name"),
    file: str = typer.Argument(..., help="File to edit (e.g., cli.py)"),
    find: str = typer.Option(..., "--find", "-f", help="Text to find"),
    replace: str = typer.Option(..., "--replace", "-r", help="Text to replace with"),
    all_occurrences: bool = typer.Option(
        False, "--all", "-a",
        help="Replace all occurrences (default: first only)"
    ),
):
    """Replace content in a skill file (find/replace).

    By default replaces only the first occurrence.
    Use --all to replace all occurrences.

    Examples:
        autobot edit weather cli.py --find "Test" --replace "Demo"
        autobot edit core cli.py -f "old_func" -r "new_func" --all
    """
    skill_dir = SKILLS_DIR / skill

    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found")
        raise typer.Exit(1)

    file_path = skill_dir / file

    # Security: ensure file is within skill directory
    try:
        file_path.resolve().relative_to(skill_dir.resolve())
    except ValueError:
        print("Error: Invalid file path")
        raise typer.Exit(1)

    if not file_path.exists():
        print(f"Error: File '{file}' not found in skill '{skill}'")
        raise typer.Exit(1)

    content = file_path.read_text()

    if find not in content:
        print(f"Error: Text '{find}' not found in {skill}/{file}")
        raise typer.Exit(1)

    if all_occurrences:
        count = content.count(find)
        new_content = content.replace(find, replace)
        file_path.write_text(new_content)
        print(f"Replaced {count} occurrence(s) in {skill}/{file}")
    else:
        new_content = content.replace(find, replace, 1)
        file_path.write_text(new_content)
        print(f"Replaced 1 occurrence in {skill}/{file}")


@app.command("delete")
def delete_item(
    skill: str = typer.Argument(..., help="Skill name"),
    file: Optional[str] = typer.Argument(None, help="File to delete (omit to delete entire skill)"),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Delete without confirmation"
    ),
):
    """Delete a skill or a file within a skill.

    If no file is specified, deletes the entire skill directory.
    Use --force to skip confirmation.

    Examples:
        autobot delete weather                    # Delete entire skill
        autobot delete weather commands/old.py   # Delete specific file
        autobot delete testskill --force         # Delete without confirmation
    """
    skill_dir = SKILLS_DIR / skill

    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found")
        raise typer.Exit(1)

    if file:
        # Delete specific file
        file_path = skill_dir / file

        # Security: ensure file is within skill directory
        try:
            file_path.resolve().relative_to(skill_dir.resolve())
        except ValueError:
            print("Error: Invalid file path")
            raise typer.Exit(1)

        if not file_path.exists():
            print(f"Error: File '{file}' not found in skill '{skill}'")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Delete {skill}/{file}?")
            if not confirm:
                print("Cancelled")
                raise typer.Exit(0)

        file_path.unlink()
        print(f"Deleted {skill}/{file}")
    else:
        # Delete entire skill
        if not force:
            confirm = typer.confirm(f"Delete entire skill '{skill}'?")
            if not confirm:
                print("Cancelled")
                raise typer.Exit(0)

        shutil.rmtree(skill_dir)
        print(f"Deleted skill '{skill}'")


@app.command("validate")
def validate_skill(
    skill: str = typer.Argument(..., help="Skill name to validate"),
    fix: bool = typer.Option(
        False, "--fix",
        help="Attempt to fix common issues"
    ),
):
    """Validate skill structure and conventions.

    Checks:
    - Directory exists
    - cli.py exists and has main() function
    - Commands have docstrings
    - No syntax errors

    Examples:
        autobot validate weather
        autobot validate weather --fix
    """
    skill_dir = SKILLS_DIR / skill
    issues = []
    fixed = []

    # Check directory exists
    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found at {skill_dir}")
        raise typer.Exit(1)

    # Check cli.py exists
    cli_path = skill_dir / "cli.py"
    if not cli_path.exists():
        issues.append("Missing cli.py")
        if fix:
            # Create minimal cli.py
            _create_simple_skill(skill_dir, skill, f"{skill.title()} skill")
            fixed.append("Created cli.py with boilerplate")
    else:
        content = cli_path.read_text()

        # Check for syntax errors
        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append(f"Syntax error in cli.py: {e}")

        # Check for main() function
        if "def main():" not in content and "def main(" not in content:
            issues.append("Missing main() function in cli.py")
            if fix:
                # Add main function
                main_code = '''

def main():
    """Entry point for the skill CLI."""
    app()


if __name__ == "__main__":
    main()
'''
                cli_path.write_text(content + main_code)
                fixed.append("Added main() function")

        # Check if __name__ == "__main__" block exists
        if 'if __name__ ==' not in content:
            issues.append("Missing if __name__ == '__main__' block")

        # Check for module docstring
        if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
            issues.append("Missing module docstring")

    # Check for __init__.py (recommended but not required)
    init_path = skill_dir / "__init__.py"
    if not init_path.exists():
        issues.append("Missing __init__.py (recommended)")
        if fix:
            init_path.write_text(f'"""{skill.title()} skill."""\n')
            fixed.append("Created __init__.py")

    # Report results
    if issues:
        print(f"Validation issues for '{skill}':")
        for issue in issues:
            print(f"  - {issue}")
        if fixed:
            print()
            print("Fixed:")
            for f in fixed:
                print(f"  + {f}")
        if not fix and any("Missing" in i for i in issues):
            print()
            print("Run with --fix to attempt automatic fixes")
        raise typer.Exit(1 if not fix else 0)
    else:
        print(f"Skill '{skill}' is valid")


@app.command("list")
def list_skills():
    """List all available skills."""
    if not SKILLS_DIR.exists():
        print("No skills directory found.")
        raise typer.Exit(1)

    skills = []
    for path in sorted(SKILLS_DIR.iterdir()):
        if path.is_dir() and not path.name.startswith((".", "_")):
            cli_py = path / "cli.py"
            if cli_py.exists():
                # Extract description from docstring
                desc = _extract_description(cli_py)
                skills.append((path.name, desc))

    if not skills:
        print("No skills found.")
        return

    print("Available skills:")
    print()
    for name, desc in skills:
        if desc:
            print(f"  {name}: {desc}")
        else:
            print(f"  {name}")


@app.command("read")
def read_file(
    skill: str = typer.Argument(..., help="Skill name"),
    file: str = typer.Argument("cli.py", help="File to read (default: cli.py)"),
):
    """Read a skill file.

    Use this to examine existing skill code for reference or modification.

    Examples:
        autobot read core cli.py
        autobot read weather commands/forecast.py
    """
    skill_dir = SKILLS_DIR / skill

    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found")
        raise typer.Exit(1)

    file_path = skill_dir / file

    if not file_path.exists():
        print(f"Error: File '{file}' not found in skill '{skill}'")
        print()
        print("Available files:")
        for f in _list_skill_files(skill_dir):
            print(f"  {f}")
        raise typer.Exit(1)

    # Security: ensure file is within skill directory
    try:
        file_path.resolve().relative_to(skill_dir.resolve())
    except ValueError:
        print("Error: Invalid file path")
        raise typer.Exit(1)

    print(file_path.read_text())


@app.command("write")
def write_file(
    skill: str = typer.Argument(..., help="Skill name"),
    file: str = typer.Argument(..., help="File to write (e.g., cli.py)"),
    content: str = typer.Argument(..., help="File content to write"),
):
    """Write content to a skill file.

    Use this to create or update skill code. The skill directory must exist
    (use 'autobot skill <name>' first).

    Examples:
        autobot write weather cli.py "import typer..."
        autobot write weather commands/forecast.py "def get_forecast():..."
    """
    skill_dir = SKILLS_DIR / skill

    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found. Create it first with:")
        print(f"  autobot skill {skill}")
        raise typer.Exit(1)

    file_path = skill_dir / file

    # Security: ensure file is within skill directory
    try:
        file_path.resolve().relative_to(skill_dir.resolve())
    except ValueError:
        print("Error: Invalid file path")
        raise typer.Exit(1)

    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    file_path.write_text(content)

    print(f"Wrote {len(content)} bytes to {skill}/{file}")


@app.command("files")
def list_files(
    skill: str = typer.Argument(..., help="Skill name"),
):
    """List files in a skill directory.

    Shows all Python files and other relevant files in the skill.

    Example:
        autobot files core
    """
    skill_dir = SKILLS_DIR / skill

    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found")
        raise typer.Exit(1)

    files = _list_skill_files(skill_dir)

    if not files:
        print(f"No files found in skill '{skill}'")
        return

    print(f"Files in {skill}/:")
    for f in files:
        print(f"  {f}")


@app.command("test")
def test_skill(
    skill: str = typer.Argument(..., help="Skill name to test"),
):
    """Test a skill by running its --help command.

    Verifies the skill can be loaded and executed.

    Example:
        autobot test weather
    """
    import subprocess

    skill_dir = SKILLS_DIR / skill
    cli_path = skill_dir / "cli.py"

    if not cli_path.exists():
        print(f"Error: Skill '{skill}' not found or missing cli.py")
        raise typer.Exit(1)

    try:
        result = subprocess.run(
            [sys.executable, str(cli_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(skill_dir)
        )

        if result.returncode == 0:
            print(f"Skill '{skill}' is working!")
            print()
            print(result.stdout)
        else:
            print(f"Skill '{skill}' has errors:")
            print(result.stderr or result.stdout)
            raise typer.Exit(1)

    except subprocess.TimeoutExpired:
        print(f"Error: Skill '{skill}' timed out")
        raise typer.Exit(1)
    except Exception as e:
        print(f"Error testing skill: {e}")
        raise typer.Exit(1)


@app.command("shell")
def shell_command(
    skill: str = typer.Argument(..., help="Skill name (determines working directory)"),
    command: str = typer.Argument(..., help="Shell command to execute"),
    timeout: int = typer.Option(
        60, "--timeout", "-t",
        help="Timeout in seconds (default: 60)"
    ),
):
    """Execute a shell command in the skill's directory.

    Use this for development tasks like checking imports, running tests,
    or any terminal operation needed while building a skill.

    Examples:
        autobot shell weather "python -c 'import requests; print(requests.__version__)'"
        autobot shell weather "python cli.py forecast --city NYC"
        autobot shell weather "ls -la"
        autobot shell weather "python -m py_compile cli.py"
    """
    import shlex
    import subprocess

    skill_dir = SKILLS_DIR / skill

    if not skill_dir.exists():
        print(f"Error: Skill '{skill}' not found")
        raise typer.Exit(1)

    print(f"$ {command}")
    print("-" * 40)

    try:
        # Run command through shell for full shell features
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(skill_dir)
        )

        # Show output
        if result.stdout:
            print(result.stdout, end="")

        if result.stderr:
            if result.stdout and not result.stdout.endswith('\n'):
                print()
            print("STDERR:", file=sys.stderr)
            print(result.stderr, end="", file=sys.stderr)

        # Show exit code
        print("-" * 40)
        if result.returncode == 0:
            print(f"Exit code: 0 (success)")
        else:
            print(f"Exit code: {result.returncode} (error)")
            raise typer.Exit(result.returncode)

    except subprocess.TimeoutExpired:
        print("-" * 40)
        print(f"Error: Command timed out after {timeout} seconds")
        raise typer.Exit(124)
    except Exception as e:
        print(f"Error running command: {e}")
        raise typer.Exit(1)


@app.command("deps")
def manage_deps(
    action: str = typer.Argument(..., help="Action: add, remove, list, check"),
    package: Optional[str] = typer.Argument(None, help="Package name (for add/remove)"),
):
    """Manage project dependencies using uv.

    Actions:
      add <package>    - Add a package (e.g., 'requests', 'httpx>=0.25')
      remove <package> - Remove a package
      list             - List installed packages
      check <skill>    - Check if a skill's imports are available

    Examples:
        autobot deps add requests
        autobot deps add "httpx>=0.25"
        autobot deps remove requests
        autobot deps list
        autobot deps check weather
    """
    import subprocess

    # Get project root (parent of skills/)
    project_root = SKILLS_DIR.parent

    if action == "add":
        if not package:
            print("Error: Package name required for 'add'")
            raise typer.Exit(1)

        print(f"Adding package: {package}")
        result = subprocess.run(
            ["uv", "add", package],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        if result.returncode == 0:
            print(result.stdout or f"Added {package}")
        else:
            print(f"Error: {result.stderr or result.stdout}")
            raise typer.Exit(1)

    elif action == "remove":
        if not package:
            print("Error: Package name required for 'remove'")
            raise typer.Exit(1)

        print(f"Removing package: {package}")
        result = subprocess.run(
            ["uv", "remove", package],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        if result.returncode == 0:
            print(result.stdout or f"Removed {package}")
        else:
            print(f"Error: {result.stderr or result.stdout}")
            raise typer.Exit(1)

    elif action == "list":
        result = subprocess.run(
            ["uv", "pip", "list"],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error: {result.stderr or result.stdout}")
            raise typer.Exit(1)

    elif action == "check":
        if not package:
            print("Error: Skill name required for 'check'")
            raise typer.Exit(1)

        skill = package  # In check mode, 'package' is actually the skill name
        skill_dir = SKILLS_DIR / skill

        if not skill_dir.exists():
            print(f"Error: Skill '{skill}' not found")
            raise typer.Exit(1)

        # Find all imports in the skill
        imports = set()
        for py_file in skill_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text()
                # Simple import detection
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('import '):
                        # import foo, bar
                        parts = line[7:].split(',')
                        for p in parts:
                            mod = p.strip().split('.')[0].split(' ')[0]
                            if mod:
                                imports.add(mod)
                    elif line.startswith('from ') and ' import ' in line:
                        # from foo import bar
                        mod = line[5:].split(' import ')[0].split('.')[0].strip()
                        if mod:
                            imports.add(mod)
            except Exception:
                pass

        # Filter out standard library and local imports
        stdlib = {'os', 'sys', 'typing', 'pathlib', 'json', 'datetime', 're',
                  'shutil', 'subprocess', 'ast', 'collections', 'functools',
                  'itertools', 'dataclasses', 'enum', 'abc', 'contextlib',
                  'threading', 'time', 'hashlib', 'base64', 'urllib', 'http'}

        external = {i for i in imports if i not in stdlib and not i.startswith('skills') and not i.startswith('src')}

        if not external:
            print(f"Skill '{skill}' has no external dependencies detected")
            return

        print(f"External imports in '{skill}':")
        missing = []
        for imp in sorted(external):
            # Try to import it
            result = subprocess.run(
                [sys.executable, "-c", f"import {imp}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  {imp}: OK")
            else:
                print(f"  {imp}: MISSING")
                missing.append(imp)

        if missing:
            print()
            print(f"Missing packages: {', '.join(missing)}")
            print(f"Install with: autobot deps add <package>")
            raise typer.Exit(1)

    else:
        print(f"Error: Unknown action '{action}'")
        print("Valid actions: add, remove, list, check")
        raise typer.Exit(1)


def _list_skill_files(skill_dir: Path) -> list[str]:
    """List relevant files in a skill directory."""
    files = []
    for path in sorted(skill_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(skill_dir)
            # Skip __pycache__ and hidden files
            if "__pycache__" not in str(rel) and not str(rel).startswith("."):
                files.append(str(rel))
    return files


def _create_simple_skill(skill_dir: Path, name: str, description: str):
    """Create a simple skill with all commands in cli.py."""
    cli_content = f'''"""
{description}

This skill was created by the Euno autobot skill.
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
    """Show skill status.

    Example command that shows environment context.
    """
    print("{name} skill")
    print()
    print("Environment:")
    print(f"  EUNO_DATA_DIR: {{os.environ.get('EUNO_DATA_DIR', '(not set)')}}")
    print(f"  EUNO_AGENT_ID: {{os.environ.get('EUNO_AGENT_ID', '(not set)')}}")
    print(f"  EUNO_TOPIC_ID: {{os.environ.get('EUNO_TOPIC_ID', '(not set)')}}")


def main():
    """Entry point for the skill CLI."""
    app()


if __name__ == "__main__":
    main()
'''

    (skill_dir / "cli.py").write_text(cli_content)
    (skill_dir / "__init__.py").write_text(f'"""{description}"""\n')


def _create_skill_with_commands(skill_dir: Path, name: str, description: str):
    """Create a skill with commands/ subdirectory structure."""
    commands_dir = skill_dir / "commands"
    commands_dir.mkdir(exist_ok=True)

    # Create cli.py
    cli_content = f'''"""
{description}

This skill was created by the Euno autobot skill.
"""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.{name}.commands import example

app = typer.Typer(
    name="{name}",
    help="{description}",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(example.app, name="example", help="Example commands")


def main():
    """Entry point for the skill CLI."""
    app()


if __name__ == "__main__":
    main()
'''

    # Create commands/__init__.py
    commands_init = f'''"""{name} skill commands."""
'''

    # Create commands/example.py
    example_content = f'''"""Example commands for {name} skill."""

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

    (skill_dir / "cli.py").write_text(cli_content)
    (skill_dir / "__init__.py").write_text(f'"""{description}"""\n')
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
    """Entry point for the autobot skill CLI."""
    app()


if __name__ == "__main__":
    main()
