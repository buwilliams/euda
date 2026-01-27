# Design

There are two main concepts in Euno: Agents and Topics. Agents are actors. Topics are containers of work.

---

## Entities

This section defines the core entities, their properties, and relationships. This is the source of truth for what exists in the system.

### Agent

An agent is an actor in the system (AI or human).

**Properties:**
- `id` - unique identifier
- `name` - display name
- `state` - operational state
  - `enabled` - normal operation, polling for topics
  - `disabled` - user explicitly turned off
  - `paused` - system auto-paused (e.g., budget exceeded)
- `order` - execution priority (lower runs first)

**Files:**
- `identity.md` - current identity (purpose, values, voice, rules)
- `identity.{year}.md` - archived identity snapshots (e.g., `identity.2025.md`)
- `config.json` - behavior configuration

**Memory:**
- `short-term[]` - rolling 90-day concerns (`.jsonl`)
- `long-term[]` - permanent archive by date (`{yyyy}/{yyyy-mm-dd}.md`)

**Cognition:**
- `system_prompts[]` - base reasoning prompts
- `prompts[]` - dynamic prompts (identity, memory, context)
- `regulation` - metacognition (token tracking, progress detection)

**Behavior:**
- `excluded_plugins[]` - plugins to exclude (empty = all plugins available)
- `triggers[]` - when agent acts (schedules, events)

**Consolidation:**
- `enabled` - whether consolidation runs
- `trigger` - when to run (e.g., `time:evening`)

### Topic

A topic is a unit of work and coordination between agents.

**Properties:**
- `id` - unique identifier (14-char)
- `name` - title
- `description` - details
- `state` - workflow state
  - `todo` - waiting to be worked
  - `working` - agent actively working
  - `done` - completed successfully
  - `error` - something went wrong
  - `archived` - soft-deleted
- `due_date` - optional deadline (`YYYY-MM-DD`)
- `assignee` - agent_id or `user`
- `parent_id` - parent topic (hierarchy)
- `created_by` - who created it
- `pending_from` - who handed it off (for returns)
- `tags[]` - metadata tags (e.g., `waiting:user-response`)

**Related Data:**
- `assets[]` - files attached to topic (`data/topics/assets/{topic-id}/`)
- `topic_logs[]` - execution history (`data/topics/logs/{topic-id}.jsonl`)
- `llm_calls[]` - LLM API calls made while working topic (`data/topics/llm/{topic-id}.jsonl`)
- `topics[]` - child topics (hierarchy)

### Manager

The manager orchestrates the system lifecycle.

**Responsibilities:**
- Loads agents from `data/agents/*`
- Watches for agent config changes
- Reloads agents on config change
- Runs time scheduler for triggers
- Creates scheduled topics at trigger times
- Monitors agent health

---

## Agency

The design of Euno anthropomorphizes AI [attributing human characteristics/behavior]. In Euno, we treat people and AI basically the same and call them Agents. Agents, like people, grow and change over time, so we've built a system that supports that type of growth. When a person eats, they grow, AIs grow when fed them with data. Here's what makes up an Agent:
- Cognition: the ability to reason and have self-awareness (consolidation/regulation)
- Memory: form new short and long-term memories
- Behavior: (triggers, schedules)
- Identity: purpose based on psychological concepts of a 'cognitive core', these are beliefs about the 'self'

We call what makes up Euno the 'Ontology' or 'the nature of being'. This raises questions: How does the Euno system work? How is it wired together? How do Agents collaborate? We call these category of questions 'Euno Lifecycle', here are the parts of it:
- Topics: agents take action when they receive a topic, these topics can be nested and change hands, and an Agent works one topic at a time.
- Manager: in charge of starting agents, assigning them scheduled topics, and monitoring their health
- Agent State: enabled, disabled, paused—and transitions between them

---

## Ontology

### Identity

Identity is rooted in a cognitive core—a schema that all agents share. It defines who they are:
- Purpose: why the agent exists
- Behavioral Rules: learned must/must not constraints
- Voice: how it communicates
- Wants and Fears: what it pursues and avoids
- Stable Attractors: patterns it returns to under pressure
- Notable Events: significant actions, consistent or surprising
- Influences: people/agents, places, experiences that shape them
- Interests: current goals, projects, focus areas
- Biographical Information: factual details

Identity is discovered, not configured. It evolves as patterns emerge through consolidation.

### Cognition

Cognition is the ability to think. It has two layers:

- Reasoning is first-order thinking about the world—how the agent approaches problems and communicates. This includes topic planning: when an agent begins work on a topic, it first creates a brief plan (tool sequence, delegation decisions, approach) then executes that plan. Planning reduces wasted effort and enables efficient batching.
- Metacognition is second-order thinking, or thinking about thinking. It includes token awareness for budget enforcement, progress awareness for stuck detection, and consolidation for memory processing and identity evolution.

### Memory

Memory is the context that informs decisions.

- Short-term memory holds current concerns: people, goals, ideas, learnings. It's a rolling window that informs immediate behavior.
- Long-term memory is a permanent chronological archive. It's the source material for identity evolution.

### RLM (Recursive Language Model)

RLM provides intelligent access to long-term memory through iterative exploration. Rather than simple keyword search, RLM uses an LLM to semantically navigate and analyze memory archives. Methods include `analyze()` for open-ended exploration, `recall()` for finding specific facts, and `extract_identity()` for discovering patterns that update identity. RLM is used during consolidation to evolve identity based on observed patterns.

### Behavior

Behavior is what enables action. It has two parts.

- Plugins are capabilities that agents use to act in the world. Each plugin provides CLI commands for a domain (topics, memory, integrations). Agents interact with plugins through three meta-tools: `list_plugins`, `plugin_usage`, and `execute_plugin`.
- Triggers determine when agents act—topic assignment, scheduled times, or system events.

### Plugins

Plugins are CLI-based extensions that provide capabilities to agents. The system uses a plugin architecture where agents don't call individual tools directly—instead, they use three meta-tools to discover and execute plugin commands.

**Meta-Tools:**
- `list_plugins` - Discover available plugins
- `plugin_usage(plugin)` - Get CLI help for a plugin
- `execute_plugin(plugin, command)` - Run a plugin command

**Built-in Plugins:**
- `core` - Topics, memory, agents, identity, consolidation, dates
- `nextcloud` - Files, calendar, deck integration
- `speech` - Text-to-speech
- `mastodon` - Social media posts

**Plugin Structure:**
Each plugin is a directory under `plugins/` with a `cli.py` entry point that implements a Typer CLI. Plugins are auto-discovered at runtime.

**Agent Configuration:**
Agents configure plugin access via `excluded_plugins[]` in their config. An empty list gives access to all plugins.

---

## Euno Lifecycle

### System Flow

```
Manager:
  1. Loads agents from data/agents/*
  2. Watches data/agents/* for changes
  3. Reloads agents on config change
  4. Creates scheduled topics at trigger times

Agent (work cycle):
  1. Agent polls for one assigned topic (status=todo, assignee=self)
  2. Agent sets topic to 'working'
  3. Agent calls LLM with system prompts + context
  4. LLM uses tools to act
  5. Regulation monitors all LLM calls (tokens, progress)
  6. Agent updates topic:
     - Creates assets as needed
     - Sets state to 'done' or 'error'
     - Or reassigns to another agent
  7. (repeat)
```

### Topics

Topics are the unit of work and how agents coordinate. Any agent can create, work on, or route topics to others. A topic has a name, description, hierarchy, assignment, status, and assets. Topics can be handed off between agents, enabling collaboration patterns like request-response and delegation.

Think of topics as a filesystem: topics are directories, assets are files. Topics can contain child topics (subdirectories), and any topic can be assigned to an agent. Some topics are permanent containers—"Projects" holds user projects, "Agents" holds agent inboxes. These never close; they organize other topics.

### Manager

The Manager orchestrates the system—it starts agents, runs the scheduler to manage triggers, and monitors health. At startup, it loads agent configurations and starts each agent in its own thread. A background scheduler creates trigger topics at configured times. Agents discover these topics through polling; the Manager doesn't wake agents directly.

### Agent Lifecycle

Here's how agents operate:

1. Manager instantiates agents and monitors their health (handling reloads and shutdown)
2. Each agent has a state: enabled, disabled, or paused
3. Enabled agents poll for assigned topics
4. When a topic is found, the agent runs a work cycle: claim → plan → execute → complete
5. Topics progress through states: todo → working → done (or error)
6. Metacognition regulates all LLM calls—if a breach is detected (e.g., budget exceeded), the agent is paused
7. Between topics, consolidation reviews memory and evolves identity

#### Agent States

Agents transition between three states:
- Enabled: normal operation, polling for topics and working on them
- Disabled: user explicitly turned it off, no work happens
- Paused: system auto-paused (usually budget exceeded), requires manual resume

#### Polling

Enabled agents poll for assigned topics. They're not pushed—this keeps them decoupled and resilient to failures. When an agent finds an actionable topic, it begins a work cycle.

#### Topic States

Topics progress through states based on assignment and work:
- todo + no assignee: unassigned, waiting to be picked up
- todo + assignee: queued, assigned but not yet being worked
- working + assignee: agent is actively working on the topic
- done: completed successfully
- error: something went wrong
- archived: soft-deleted, no longer active

An agent can have multiple topics assigned (queued), but only works one at a time.

#### Topic Routing

Topics move between agents (and users) through reassignment. When an agent needs input or wants to delegate, it reassigns the topic and sets status back to `todo`. The recipient picks it up when they poll for work.

**Handoff**: An agent can hand off a topic to another agent or the user. This updates the assignee and records who sent it (`pending_from`), so the topic can be returned after review. Example: an agent needs user approval, so it hands off to `user` with a note explaining what's needed.

**Blocking**: Topics can be marked as blocked using tags:
- `waiting:*` — waiting for external input (e.g., `waiting:user-response`)
- `blocked:*` — blocked by a dependency (e.g., `blocked:api-access`)

Blocked topics are excluded from actionable queries—agents won't pick them up until unblocked. When a user interacts with a blocked topic (views it, adds an asset), the blocking tags are automatically removed and the topic returns to the agent's queue.

**The user as agent**: The user participates in topic routing like any other agent. Topics can be assigned to `user`, handed off to `user`, or created by `user`. The difference is interface—users work through the UI, agents work through polling and tool calls.

#### Work Cycle

When an agent starts working a topic, it sets the status to `working`, creates a brief plan (tool sequence, delegation decisions, approach), then executes that plan until complete. Finally it marks the topic `done` and returns to polling.

Planning is part of Reasoning—it reduces wasted effort and enables efficient batching (e.g., deferring consolidation to end of work cycle). All LLM calls go through metacognition for budget tracking and stuck detection.

#### Regulation

Metacognition monitors all LLM calls for self-awareness. It tracks token usage against budgets, detects stuck patterns (like repeated tool calls), and enforces limits. When a threshold is breached, the agent is automatically paused and requires manual intervention to resume.

#### Consolidation

Agents run scheduled reviews of their memory to update their identity. This is how identity is discovered, not configured—agents evolve through consolidation.
