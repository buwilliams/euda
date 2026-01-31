# Repository Guidelines

## Project Structure & Module Organization
- `main.py` contains the Typer-based CLI entrypoint and commands (currently `ping`).
- `src/` contains implementation modules (`cli.py`, `config.py`).
- `config.default.json` holds default configuration values.
- `tests/` contains unit and placeholder e2e tests.

## Build, Test, and Development Commands
- `uv run {{script_name}} ping` — run the CLI entrypoint via the installed script to confirm wiring.
- `uv run python main.py --help` — run the CLI directly during local development.
- `uv run python -m pytest` — execute the test suite (ensure `pytest` is available).

## Coding Style & Naming Conventions
- Python with 4-space indentation; keep functions and variables in `snake_case`.
- CLI commands are defined as Typer commands on the shared `app` instance in `src/cli.py`.
- Test files follow `tests/**/test_*.py` naming; test functions are `test_*`.
- No formatter or linter is configured in this package; keep changes small and consistent.

## Testing Guidelines
- Tests use `pytest` and Typer’s `CliRunner` for CLI invocation.
- Add unit tests for new commands under `tests/unit/` and e2e coverage under `tests/e2e/` when appropriate.
- Prefer asserting exit codes and stdout for CLI behavior (see `tests/unit/test_smoke.py`).

## Commit & Pull Request Guidelines
- Commit messages in history use short, imperative summaries (e.g., “Fix …”, “Standardize …”).
- Pull requests should include: a concise description, the commands you ran, and any behavior changes.
- Attach relevant test output or screenshots when changes affect CLI output or UX.

## Agent-Specific Notes
- Keep repository changes minimal and focused; avoid adding unused dependencies.
- If introducing new commands, update `tests/unit/` with a smoke test and document usage here.
