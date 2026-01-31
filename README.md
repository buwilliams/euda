# Euda

Scaffold for a multi-CLI workspace using Typer and uv. Each CLI app is isolated
in its own directory with its own `pyproject.toml` and tests.

## Usage (examples)
- `uv run euda list`
- `uv run euda skills list`
- `uv run euda memory ping`
- `uv run euda skills gcal ping`

## Layout
- `main.py` — router CLI that dispatches to euda/skills apps via `uv run`
- `euda/<app>/main.py` — euda apps (llm, memory, agents, logs, topics, chat, web)
- `skills/<app>/main.py` — skills apps (gcal is scaffolded)
