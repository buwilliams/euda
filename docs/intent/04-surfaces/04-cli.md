# CLI

## Key Ideas

- **CLI First**: on the `main` branch, the CLI is the first-class surface. Every capability is a command, and the command line is the base on which all other surfaces rest.
- **Capabilities Are Programs**: each capability—`agents`, `chat`, `identity`, `llm`, `logs`, `memory`, `topics`, `web`—is a small, self-contained CLI application with its own dependencies, config, and tests.
- **Composition By Subprocess**: capabilities compose by calling one another as commands, passing text and JSON. This is the Unix philosophy applied to a personal intelligence.
- **One Interface For People And Agents**: an agent operates Euda through the same CLI a person uses. There is no privileged internal path.
- **The Port's Purpose**: the rewrite from `v1` to `main` changed the substrate, not the intent. Making the CLI first-class removes the special "AI-only" path and keeps every capability inspectable, testable, and replaceable.

## Purpose

The CLI exists to make Euda's capabilities reliable, composable, and equally available to people and agents. A surface built on a stateful server can be lost or refreshed; a surface built on small, explicit commands is dependable, scriptable, and close to the host. As AI agents become the primary actors, the most direct and robust interface for them is exactly the one a careful person would also choose: clear commands with readable output.

This is why `main` made the CLI first-class. Euda's intent—personal intelligence, identity at the center, no distinction between agents—is better served when the action surface is one shared command line rather than a web server with agents bolted inside it.

## The Architecture (The Port From v1 To main)

### What v1 Was

Version 1 is a single FastAPI application. Business logic lives in `src/core/`; the browser and API import it directly; the agent runtime runs work cycles as background threads inside the server; and skills are CLI wrappers that shell into the same logic. *Focus* is the first-class surface, and the CLI exists mainly to launch the server and run developer tools.

### What main Is

The `main` branch turns every capability into an independent CLI application and makes composition explicit:

- **Apps as programs.** Each capability under `core/` (and each integration under `skills/`) is its own `uv` project: `main.py`, `pyproject.toml`, `src/cli.py` (Typer), `src/config.py`, and `tests/`. It can be developed, tested, and run on its own.
- **A dynamic router.** `router.py`, exposed as the `euda` command, discovers apps and dispatches to them. `euda core <app> …` and `euda skills <app> …` run the target app with `uv run --project <app>`. The router also offers `list`, `help`, `info`, `search`, and `last` (replaying the previous invocation recorded in `.euda_history.json`).
- **Composition by subprocess.** `shared-router.py` provides `run_core`, `run_cli`, and `run_cli_json`, so one capability can call another and parse its output. The agent runner, for example, builds its system prompt by calling `identity id read <name>` and loads provider settings by calling `llm config cat-full`.
- **Uniform config.** Every app reads a tracked `config.default.json` and deep-merges an optional, gitignored `config.json`, and every app exposes the same `config get|set|cat|cat-full|write` commands. Defaults are shared; overrides stay local.
- **Web as one app.** The browser experience becomes `core/web`, one capability among equals rather than the system's center.

This is a composition-first design in the spirit of small Unix programs (and similar in shape to OpenClaw): each program does one thing, speaks text and JSON, and calls its neighbors.

### Why It Serves The Intent

- A single CLI surface for people and agents removes the special AI-only path, honoring the non-distinction between agents at the level of the interface itself.
- Self-contained apps keep capabilities inspectable, independently testable, and replaceable—any single program can be swapped without rewriting the system.
- Subprocess composition keeps coordination explicit and observable.
- Text and JSON keep state readable by humans and agents alike.

## Expected Role

The CLI should be the most stable and composable surface:

- expose every capability as a command with readable output;
- let capabilities call one another rather than sharing hidden internal state;
- serve as the foundation that Focus, web, and agent-native surfaces build upon;
- remain conservative in surface area—commands should express real capabilities, not mirror a screen.

The CLI should not become a second implementation of Euda. It *is* the implementation surface; other surfaces are adapters over it.

## Future Direction

As agents become the main actors, the CLI should remain their primary interface—high-signal commands and machine-readable output, no human-style screen required. New capabilities should arrive as new apps that compose with the existing ones.

The intent to preserve: a single, reliable, composable command surface that people and agents share equally, so that whatever substrate Euda runs on next, its capabilities stay small, explicit, inspectable, and replaceable.
