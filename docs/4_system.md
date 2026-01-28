# System

There are three core concepts in Euno: **Agents**, **Skills**, and **Topics**.

- **Agents** are actors (AI or human) that do work
- **Skills** are capabilities that agents use to act
- **Topics** are units of work that agents coordinate around

---

## Agents

An agent is an actor in the system. Agents can be AI or human—the user is also an agent, just with a different interface.

**What makes up an agent:**
- **Identity** — purpose, values, voice, behavioral rules
- **Memory** — short-term (90 days rolling) and long-term (permanent archive)
- **Cognition** — reasoning + metacognition (self-regulation)
- **Behavior** — skills they can use, triggers that activate them

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

Skills are CLI-based extensions that give agents capabilities. Agents don't call tools directly—they use three meta-tools to discover and execute skills:

- `list_skills` — see what's available
- `skill_usage(skill)` — get help for a skill
- `execute_skill(skill, command)` — run a command

**Built-in skills:**
- `core` — topics, memory, agents, identity, dates
- `nextcloud` — files, calendar, deck
- `speech` — text-to-speech
- `mastodon` — social media

Skills are auto-discovered from `skills/`. Each skill is a directory with a `cli.py` entry point using Typer. Agents can be configured to exclude specific skills.

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

## Learn More

- `specs/1_agents.md` — agent behavior, triggers, work cycles
- `specs/2_data.md` — data structures, schemas, file paths
- `specs/8_skills.md` — skill architecture and commands
