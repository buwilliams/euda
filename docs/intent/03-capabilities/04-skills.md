# Skills

## Key Ideas

- **Capabilities As CLIs**: a skill is a capability an agent can use, exposed as a command-line interface. Agents act by running commands.
- **Discover, Don't Hardcode**: agents find skills at runtime and read their usage, rather than depending on a fixed, baked-in tool list.
- **One Interface For All Actors**: the same skill commands serve people and agents. An agent acting and a person typing use the same surface.
- **Self-Contained Extensions**: integrations (calendar, files, social) are independent skills with their own logic, discovered automatically.
- **Power With Accountability**: skills give agents real reach into the world; topics, logs, and identity keep that reach visible and bounded.

## Purpose

Skills exist so agents can act on the world without the system having to predict, in advance, everything they might do. Rather than wiring dozens of bespoke tools into the agent runtime, Euda exposes capabilities as discoverable commands and lets agents compose them.

This keeps the action surface open and uniform. New capabilities arrive as new skills; agents discover and use them through the same small protocol; people can run the very same commands. The interface an agent uses to act is the interface a person uses to operate Euda.

## The Meta-Tool / Command Model

Across both eras, agents reach skills through a tiny, stable protocol rather than a sprawling tool list:

- **Discover** what capabilities exist.
- **Read** a capability's usage.
- **Execute** a command and get its output.

In `v1` these are three meta-tools—`list_skills`, `skill_usage(skill)`, and `execute_skill(skill, command)`—over skills auto-discovered from `skills/`, each a directory with a `cli.py` (Typer) entry point. Built-in skills include `core` (topics, memory, agents, identity, dates), `nextcloud` (files, calendar, deck), `speech` (text-to-speech), and `mastodon` (social).

On `main` the same idea is generalized: an agent's three tools become `list_apps`, `app_usage`, and `execute_command`, and *every* capability—core apps and skills alike—is reachable through them. The `core` capabilities that were skills in `v1` are now first-class CLI apps, and external integrations (such as `gcal`) live under `skills/` with the identical structure.

## Expected Role

Skills should be the accountable action layer beneath agents:

- agents discover and read skills at runtime, then execute commands;
- skill output is text or JSON, readable by people and agents alike;
- skills act on the world, but the *work* they serve is expressed as topics, so activity stays visible;
- agents can be restricted from specific skills when appropriate.

Current implementation details that matter to intent:

- `v1`'s `core` skill is special: its CLI commands are thin wrappers over shared business logic in `src/core/`, so the web UI and agents reach the same logic by different paths.
- On `main`, the distinction dissolves: capabilities are uniformly CLI apps composed via the router, and skills are simply apps under `skills/`. See [CLI](../04-surfaces/04-cli.md).
- Skills keep their own data and credentials separate from system config, so integrations can be added without touching the core.

Skills should not become a second product. They are adapters that let agents act; product meaning stays in identity, memory, topics, and workflow.

## Future Direction

As agents improve, the skill catalog should grow—more integrations, more reach—while the protocol for using them stays small and stable. The intent to preserve: capabilities are discoverable commands, the same for people and agents, and every powerful action remains visible through the topics and logs it touches.
