# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the CLI entry point and wires the Typer app.
- `src/` contains implementation modules (`cli.py`, `config.py`).
- `config.default.json` holds default configuration values.
- `tests/` contains unit and placeholder e2e tests (`tests/unit`, `tests/e2e`).

## Build, Test, and Development Commands
- `uv run python main.py --help` runs the CLI directly from source.
- `uv run python -m pytest` runs the test suite (uses the default pytest discovery).
- `uv pip install -e .` installs the CLI in editable mode; afterwards, run `logs --help`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, PEP 8 naming (`snake_case` for functions/vars).
- Keep modules small and focused; prefer adding new commands in `src/cli.py`.
- No formatter or linter is configured; keep imports sorted and avoid unused imports.

## Testing Guidelines
- Tests are Python-based and should be placed under `tests/`.
- Name tests `test_*.py` and functions `test_*` to match pytest discovery.
- Add unit tests alongside CLI changes (see `tests/unit/test_smoke.py` for pattern).

## Commit & Pull Request Guidelines
- Recent commits are short, imperative descriptions (e.g., “Standardize app scaffolds…”).
- Keep commits focused and descriptive; include context in the PR description.
- If changes affect CLI behavior, include example commands/output in the PR.

## Configuration & Runtime Notes
- Config overrides are stored in `config.json` next to `config.default.json`.
- Set `LOGS_CONFIG_DIR` to point the CLI at an alternate config directory.
- Use `logs config get/set/cat/cat-full/write` to manage configuration.
