# Repository Guidelines

## Project Structure & Module Organization
- `src/` holds the application code (`cli.py` for Typer commands, `config.py` for config loading/merging).
- `main.py` is the CLI entrypoint (wired to the `topics` console script).
- `config.default.json` provides the baseline config; `config.json` stores local overrides.
- `tests/unit/` contains fast unit tests; `tests/e2e/` is reserved for end-to-end coverage.

## Build, Test, and Development Commands
- `uv pip install -e .` installs the CLI in editable mode.
- `uv run pytest` runs the test suite (unit and e2e).
- `uv run python -m build` creates a wheel/sdist (Hatchling build backend).

## Coding Style & Naming Conventions
- Python, 4-space indentation; keep modules small and focused.
- Use type hints for public functions where helpful (see `src/config.py`).
- Naming: `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants.
- Prefer simple, explicit control flow over cleverness; keep CLI outputs user-friendly.

## Testing Guidelines
- Framework: `pytest` with `typer.testing.CliRunner` for CLI behavior.
- Test names should be descriptive and prefixed with `test_` (e.g., `test_ping`).
- Keep unit tests fast; place slower, workflow-style tests under `tests/e2e/`.

## Commit & Pull Request Guidelines
- Commit messages are short, imperative, and sentence-style (e.g., “Standardize app scaffolds…”).
- PRs should include: a clear description, the commands run (tests/build), and any config changes.
- If you add CLI flags or config keys, update `config.default.json` and include an example.

## Configuration Notes
- Config is resolved as: defaults from `config.default.json` + overrides from `config.json`.
- You can set `TOPICS_CONFIG_DIR` to point to an alternate config directory.
