# System

There are three core concepts in Euda: **Agents**, **Skills**, and **Topics**.

- **Agents** are actors (AI or human) that do work
- **Skills** are capabilities that agents use to act
- **Topics** are units of work that agents coordinate around

---

## Agents

An agent is an actor in the system. Agents can be AI or human—the user is also an agent, just with a different interface.

**What makes up an agent:**
- **Identity** — purpose, values, behavioral rules
- **Voice** — communication style, tone, word choices, sentence patterns
- **Memory** — short-term (90 days rolling) and long-term (permanent archive)
- **Cognition** — reasoning + metacognition (self-regulation)
- **Behavior** — skills they can use, triggers that activate them

**Voice** is how an agent communicates — their formality level, sentence structure, characteristic phrases, tone, and register shifts across contexts. For AI agents, voice is configured in identity and refined through consolidation. For users, voice is *discovered* — consolidation observes how they write in conversations, documents, and notes, then builds a style profile so agents can mirror their natural language.

**Agent states:**
- `enabled` — normal operation, polling for topics
- `disabled` — explicitly turned off by user
- `paused` — auto-paused by system (e.g., budget exceeded)

**Key files:**
- `identity.md` — who the agent is
- `config.json` — behavior configuration
- `memory/short-term.jsonl` — recent concerns
- `memory/long-term/{year}/` — archived memories

Agents grow through **consolidation**—a scheduled process that reviews memory and evolves identity. Identity is discovered, not configured.

---

## Skills

Skills are CLI apps that give agents capabilities. The primary interface is bash: agents (and users) run CLI apps to take action.

Skills are auto-discovered from `skills/`. Each skill is a self-contained CLI app with its own `main.py` and `pyproject.toml`. Use the router to list and run them:

- `euda skills list`
- `euda skills <app> --help`
- `euda skills <app> [args...]`

---

## Topics

A topic is a unit of work. Topics have a name, description, state, and optional assets (files). They can be nested (hierarchy) and assigned to agents.

**Topic states:**
- `todo` — waiting to be worked
- `working` — agent actively working
- `done` — completed successfully
- `error` — something went wrong
- `archived` — soft-deleted

**How topics flow:**
1. Topic is created (by user or agent)
2. Topic is assigned to an agent
3. Agent claims it, sets state to `working`
4. Agent does the work using skills
5. Agent completes it (`done`) or hands it off

Topics can be **handed off** between agents. When an agent needs input, it reassigns the topic and records who sent it, so it can be returned later.

**The user as agent:** Topics can be assigned to `user`. The difference is interface—users work through the UI, agents work through polling.

---

## System Flow

```
Manager:
  - Loads agents from data/agents/
  - Watches for config changes
  - Creates scheduled topics at trigger times

Agent (work cycle):
  1. Poll for assigned topic (status=todo)
  2. Set topic to 'working'
  3. Plan approach, execute using skills
  4. Complete topic ('done' or 'error') or hand off
  5. Repeat
```

**Metacognition** monitors all agent activity—tracking token usage, detecting stuck patterns, and auto-pausing if limits are breached.

---

## CLI App Architecture

Every app is a self-contained CLI project in either `core/` or `skills/`, with `main.py` as its entry point. `router.py` is the single CLI router that dispatches `euda core <app>` or `euda skills <app>` to the appropriate project (via `uv run --project`). `shared-router.py` provides helper functions for calling these CLI apps from Python and capturing structured output.
This design is LLM-friendly: text-first CLI commands make it straightforward for agents to act through bash and record results.

---

## Learn More

- `specs/1_agents.md` — agent behavior, triggers, work cycles
- `specs/2_data.md` — data structures, schemas, file paths
- `specs/8_skills.md` — skill architecture and commands
