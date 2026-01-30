# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the Python application: core business logic in `src/core/`, agent runtime in `src/agent/`, FastAPI app in `src/web/`, and shared utilities in `src/llms/` and `src/sync/`.
- `skills/` holds CLI-based skills (thin wrappers around `src/core/` or self-contained integrations).
- `data/` stores local state (agents, topics DB, assets, system logs/config).
- `tests/` contains unit/integration tests plus `tests/e2e/` for Playwright UI runs.
- `docs/` and `specs/` are the source of truth for product intent and design rules.

## Build, Test, and Development Commands
- `uv sync` installs dependencies via uv.
- `euno web` runs the web server + agents locally.
- `euno chat` starts the CLI chat interface.
- `euno dev watch` streams system events for debugging.
- `uv run pytest` runs unit + integration tests (skips e2e by default).
- `uv run pytest tests/e2e/` runs Playwright e2e tests (server must be running).

## Coding Style & Naming Conventions
- Python code follows the existing conventions in `src/` (4-space indentation, explicit typing where already used).
- No formatter or linter is configured in `pyproject.toml`; keep changes consistent with nearby code and avoid style churn.
- Test files follow `test_*.py` naming, matching pytest config in `pyproject.toml`.

## Testing Guidelines
- Test framework: pytest with markers `unit`, `invariant`, and `e2e`.
- Default pytest options in `pyproject.toml` ignore `tests/e2e/`; run e2e explicitly when touching the UI or web routes.
- There is no documented coverage threshold; focus on drift-sensitive areas in `specs/`.

## Commit & Pull Request Guidelines
- Commit messages are short, imperative, and sentence-cased (e.g., “Add voice as first-class concept…”).
- Create feature branches from `main`, verify against `specs/*.md`, then open a PR.
- PRs should include a clear summary and note any spec/doc updates when behavior changes.

## Agent-Specific Notes
- See `CLAUDE.md` for dev CLI recipes and agent/skill conventions used by automation.
