import importlib.util
import os
import subprocess
from pathlib import Path
import sys
from typing import Dict
from typing import List

import typer

app = typer.Typer(
    help="Euda CLI router.",
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)

ROOT = Path(__file__).parent
EUDA_DIR = ROOT / "euda"
SKILLS_DIR = ROOT / "skills"
TEMPLATES_DIR = ROOT / "templates" / "scaffold"


def _load_shared_cli() -> None:
    if "shared_cli" in sys.modules:
        return
    shared_path = Path(__file__).with_name("shared-cli.py")
    if not shared_path.exists():
        return
    spec = importlib.util.spec_from_file_location("shared_cli", shared_path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules["shared_cli"] = module
    spec.loader.exec_module(module)


_load_shared_cli()
del _load_shared_cli


def _list_apps(base: Path) -> List[str]:
    if not base.exists():
        return []
    apps = []
    for item in sorted(base.iterdir()):
        if item.is_dir() and (item / "main.py").exists():
            apps.append(item.name)
    return apps


def _run_app(base: Path, name: str, args: List[str]) -> int:
    app_dir = base / name
    if not app_dir.exists():
        typer.echo(f"Unknown app: {name}")
        return 2
    if not (app_dir / "main.py").exists():
        typer.echo(f"Missing main.py in {app_dir}")
        return 2

    cmd = [
        "uv",
        "run",
        "--project",
        str(app_dir),
        "python",
        "main.py",
        *args,
    ]
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run(cmd, cwd=str(app_dir), env=env)
    return result.returncode


def _slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _validate_name(name: str) -> str:
    slug = _slugify(name)
    if not slug or not all(ch.isalnum() or ch in "-_" for ch in slug):
        typer.echo("Name must be lowercase letters, numbers, hyphens, or underscores.", err=True)
        raise typer.Exit(code=2)
    return slug


def _template_replacements(name: str, app_label: str, project_name: str, description: str) -> Dict[str, str]:
    env_name = name.upper().replace("-", "_")
    return {
        "name": name,
        "app_label": app_label,
        "project_name": project_name,
        "description": description,
        "script_name": name,
        "config_env_var": f"{env_name}_CONFIG_DIR",
    }


def _render_template(template_root: Path, target_root: Path, replacements: Dict[str, str]) -> None:
    for path in template_root.rglob("*"):
        relative = path.relative_to(template_root)
        target_path = target_root / relative
        if path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        content = path.read_text(encoding="utf-8")
        for key, value in replacements.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")


@app.command(help="Scaffold a new CLI app.")
def scaffold(
    name: str = typer.Argument(..., help="New app name."),
    dest: str = typer.Option(
        "topic",
        "--dest",
        help="Destination: topic (skills/) or euda (euda/).",
        show_default=True,
    ),
) -> None:
    name_slug = _validate_name(name)
    normalized_dest = dest.strip().lower()
    if normalized_dest == "topic":
        base_dir = SKILLS_DIR
        template_dir = TEMPLATES_DIR / "skill"
        project_name = f"euda-skill-{name_slug}"
        description = f"Skills {name_slug} CLI"
        app_label = "Skills"
    elif normalized_dest == "euda":
        base_dir = EUDA_DIR
        template_dir = TEMPLATES_DIR / "euda"
        project_name = f"euda-{name_slug}"
        description = f"Euda {name_slug} CLI"
        app_label = "Euda"
    else:
        typer.echo("Invalid --dest. Use 'topic' or 'euda'.", err=True)
        raise typer.Exit(code=2)

    target_dir = base_dir / name_slug
    if target_dir.exists():
        typer.echo(f"Target already exists: {target_dir}", err=True)
        raise typer.Exit(code=2)
    if not template_dir.exists():
        typer.echo(f"Missing scaffold template: {template_dir}", err=True)
        raise typer.Exit(code=2)

    replacements = _template_replacements(name_slug, app_label, project_name, description)
    _render_template(template_dir, target_dir, replacements)
    typer.echo(f"Scaffolded {name_slug} in {target_dir}")


skills_app = typer.Typer(
    help="Manage skills CLI apps.",
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)


@app.callback()
def app_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None and ctx.args:
        name, *args = ctx.args
        raise typer.Exit(_run_app(EUDA_DIR, name, args))


@skills_app.callback()
def skills_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None and ctx.args:
        name, *args = ctx.args
        raise typer.Exit(_run_app(SKILLS_DIR, name, args))


def _register_commands(router: typer.Typer, base: Path, label: str) -> None:
    @router.command("list")
    def _list():
        """List apps."""
        for name in _list_apps(base):
            typer.echo(name)

    @router.command("usage")
    def _usage(name: str):
        """Show usage for an app."""
        raise typer.Exit(_run_app(base, name, ["--help"]))

    @router.command("run")
    def _run(name: str, args: List[str] = typer.Argument(None)):
        """Run an app."""
        raise typer.Exit(_run_app(base, name, args or []))


_register_commands(app, EUDA_DIR, "euda")
_register_commands(skills_app, SKILLS_DIR, "skills")


app.add_typer(skills_app, name="skills")


if __name__ == "__main__":
    app()
