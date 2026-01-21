# System

Euno exists to be a personalized intelligence to help us flourish. The shape of the Euno system (architecture) should that make that vision that the most likely outcome. Understanding Euno's shape requires two perspectives:
- **Ontology** [the nature of being]: defines the essence of each entity in Euno
- **Lifecycle** [series of changes]: defines how entities behave over time, their states, how they transition between states, and how they interact with other entities.

Together, these perspectives explain the complete system. The sections below cover each core entity from both angles.

---

## Manager

The orchestrator for Agents.

### Ontology

The Manager is a singleton that owns the runtime:

- **Agent Registry** — All loaded agent instances
- **Thread Pool** — One thread per agent
- **Event Bus** — Trigger distribution system
- **Time Scheduler** — Cron-like job creation for scheduled triggers
- **Job Cache** — Tracks which agents have pending work

### Lifecycle

```
Startup → Load Configs → Start Agents → Run Scheduler → [Wait] → Shutdown
```

| Phase | What Happens |
|-------|--------------|
| **Startup** | Initialize event bus, start time scheduler thread |
| **Load Configs** | Scan `data/agents/*/config.json` |
| **Start Agents** | Create Agent instance per config, start each in own thread |
| **Run Scheduler** | Background thread creates trigger jobs at scheduled times |
| **Wait** | Main thread waits; agents poll and work independently |
| **Shutdown** | Set `running=False`, emit shutdown events for agents and threads |

The Manager creates **jobs** (not direct wake-ups) for time-based events. Agents discover these jobs through normal polling.

---

## Agents

Agents are entities with the capacity to act. Both humans and AIs are agents—they share the same structure but have different interfaces (UI vs autonomous loop).

### Ontology

Every agent shares:

- **Identity**: Who am I? Based on cognitive core.
- **Cognition**: How do I think? Reasoning and metacognition (regulation, consolidation)
- **Memory**: What do I know? Fluid, constantly updating.
- **Behavior**: What can I do? Complete jobs by using tools. Triggered by job assignment.

#### Identity

All agents share a **cognitive core**, the same identity schema:

- **Purpose** — Why the agent exists
- **Behavioral Rules** — Learned must/must not constraints
- **Voice** — How it communicates
- **Wants and Fears** — What it pursues and avoids
- **Stable Attractors** — Patterns it returns to under pressure
- **Notable Events** — Significant actions (consistent or surprising)
- **Influences** — People, places, experiences that shape them
- **Interests** — Current goals, projects, focus areas
- **Biographical Information** — Factual details

Identity is discovered, not configured. It evolves as patterns emerge.

#### Cognition

The thinking apparatus—both first-order and second-order.

**Reasoning** — First-order thinking about the world
- System prompts define reasoning approach
- Prompt templates for job types (assignment, exploration, reflection)

**Metacognition** — Second-order thinking about thinking
- Token awareness (budget enforcement, auto-pause)
- Progress awareness (stuck detection)
- Strategic planning (approach before complex tasks)
- Consolidation (memory processing, identity evolution)

#### Memory

Context that informs decisions.

- **Short-term** (90 days) — Current concerns: people, goals, ideas, learnings. Built via append phase after Conversations or Jobs. Falls off after 90 days.
- **Long-term** (permanent) — Chronological archive. Built from Conversations, Jobs, and Integrations.

Consolidation uses RLM on both memory types to evolve identity.

#### Behavior

The action system.

- **Tools** — What the agent can do (configured per-agent)
- **Triggers** — When the agent acts (job assignment, scheduled times)
- **Modes** — Balance between exploitation (~90%) and exploration (~10%)

### Lifecycle

```
Stopped → Enabled → [Polling/Working] → Paused/Disabled → Stopped
```

| State | Description | Can Work? |
|-------|-------------|-----------|
| **Enabled** | Normal operation | Yes |
| **Disabled** | User explicitly disabled | No |
| **Paused** | Token budget exceeded (requires manual resume) | No |

**Agent Loop** (while enabled):

```
Poll for jobs → Claim job → Set context → Work cycle → Release job → Repeat
```

1. Poll `data/jobs/` for actionable jobs assigned to this agent
2. Claim job (prevents other agents from taking it)
3. Execute work cycle: chat loop with tools until `done_working`
4. Release job (marks complete or returns to queue)
5. Check for more jobs; repeat or sleep

All LLM calls go through metacognition for token tracking and budget enforcement.

---

## Jobs

Jobs are the unit of work. They're how agents coordinate—any agent can create, work on, or route jobs to others.

### Ontology

A job is a work item with:

- **Identity** — `id`, `name`, `description`
- **Hierarchy** — `parent_id` for nesting related work
- **Assignment** — `assignees[]` (who should work on it)
- **Status** — `todo`, `completed`, `archived`
- **Scheduling** — `due_date`, `someday` flag
- **Context** — `tags[]`, `pending_from` (return routing)
- **Assets** — Attached files in `data/jobs/assets/{id}/`

**Tags** provide semantic context:
- `user:request` — User asked for this; hand findings back
- `trigger:exploration` — Scheduled discovery job
- `trigger:reflection` — Scheduled self-analysis job

### Lifecycle

```
pending → working → done/error
```

| State | Description |
|-------|-------------|
| **pending** | Waiting to be processed (`status=todo`) |
| **working** | Claimed by an agent, in progress |
| **done** | Completed successfully (`status=completed`) |
| **error** | Failed (may retry or escalate) |

**Job Flow Patterns:**

| Pattern | Flow |
|---------|------|
| **Direct** | Agent creates → works → completes |
| **Handoff** | Agent A creates → hands to B → B works → hands back → A completes |
| **Exploration** | System creates trigger → Agent explores → Creates suggestions for user |
| **Escalation** | Agent fails 3x → Auto-handoff to user |

Key operations (via `tools/data/jobs.py`):
- `create_job()` — Create new work
- `claim_job()` / `release_job()` — Exclusive access during work
- `handoff_job()` — Transfer to another agent
- `complete_job()` — Mark as done

---

## Tools

Tools are capabilities that agents use to act in the world.

### Ontology

A tool is a function with:

- **Name** — Unique identifier (e.g., `create_job`)
- **Description** — What it does (shown to LLM)
- **Parameters** — JSON schema of inputs
- **Category** — Organizational grouping

**Categories:**

| Category | Purpose | Examples |
|----------|---------|----------|
| **data** | Job and memory operations | `create_job`, `list_memory`, `read_asset` |
| **agents** | Agent introspection | `list_agents`, `update_own_identity` |
| **system** | Runtime control | `done_working`, `web_search` |
| **integration** | External services | `send_email`, `import_file` |

Tools are registered with the `@tool` decorator and live in `src/tools/`.

### Lifecycle

Tools don't have states—they're stateless functions. Their lifecycle is per-invocation:

```
Agent requests tool → Execute → Return result
```

**Access Control:**
- Each agent's `config.json` lists allowed tools
- Base tools are always available: `list_jobs`, `get_job`, `create_job`, `complete_job`, `done_working`
- An agent cannot use tools not in its config

**Execution Context:**
- Tools execute synchronously within the agent's work cycle
- Agent context is set before execution (for tools that need agent info)
- Results are returned to the LLM for next reasoning step

---

## How It All Connects

```
┌─────────────────────────────────────────────────────────────┐
│                         MANAGER                              │
│  - Loads agent configs                                       │
│  - Starts agent threads                                      │
│  - Runs time scheduler (creates trigger jobs)                │
└─────────────────────────────────────────────────────────────┘
                              │
                    starts/stops agents
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         AGENTS                               │
│  - Poll for assigned jobs                                    │
│  - Execute work cycles (LLM + tools)                         │
│  - All LLM calls go through metacognition                    │
└─────────────────────────────────────────────────────────────┘
                              │
                    claim/complete jobs
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          JOBS                                │
│  - Stored in SQLite (data/jobs/db.sqlite)                    │
│  - Agents discover work through polling                      │
│  - Jobs coordinate work between agents                       │
└─────────────────────────────────────────────────────────────┘
                              │
                    agents use tools to act
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         TOOLS                                │
│  - Stateless functions agents invoke                         │
│  - Access controlled per-agent                               │
│  - Categories: data, agents, system, integration             │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles:**

1. **Jobs are the only work mechanism** — No hidden channels; all work is visible
2. **Agents poll, they're not pushed** — Decoupled, resilient to failures
3. **All LLM calls go through metacognition** — Budget enforcement, cost tracking
4. **Tools are shared infrastructure** — Same tools available to agents, API, and CLI

---

**Technical Details:** See `spec/1_agents.md` for implementation rules, `spec/2_data.md` for data schemas.
