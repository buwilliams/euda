import os
import subprocess
from pathlib import Path
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
    result = subprocess.run(cmd, cwd=str(app_dir))
    return result.returncode


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
