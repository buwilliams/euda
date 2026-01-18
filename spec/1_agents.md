# Agents

Rules for how agents work and coordinate through jobs.

## Core Principle

- Jobs are the only way agents do work — no other mechanism exists
- This creates visibility: users can see what agents are working on and what's queued

## Jobs

- A job is actionable when: assigned to an agent, status is `todo`, and due_date is NULL/today/past
- Jobs with `someday=true` are never actionable
- Jobs with future due_date are not actionable until that date
- Any user action that needs agent attention creates a job assigned to that agent

## Agents

- Agents poll for actionable jobs every 100ms (configurable via `poll_interval`)
- Job cache prevents database queries when no jobs are pending
- Cache is shared across all agent threads — when agent A assigns a job to agent B, the cache is notified immediately
- Agents work one job at a time — no polling during work cycle
- Disabled agents never process jobs
- Each agent runs in its own thread — one agent's work cannot block another
- When actionable jobs exist, the agent runs a work cycle until it calls `done_working`
- Agents can create jobs for themselves or other agents

## Triggers

- Triggers are configured per-agent in `config.json` under `triggers[]`
- Triggers create jobs, they do not wake agents directly
- Trigger job naming: `Trigger:{name}:{yyyy-mm-dd}`
- Trigger jobs have tag `trigger:{name}`
- Trigger types:
  - `system:start` — fires once at system startup
  - `time:{name}` — fires at scheduled times (morning, evening, hourly)

## Manager

- Loads agent configs from `data/agents/*/config.json`
- Starts each enabled agent in its own thread
- Maintains job cache per agent — cache is set when jobs are assigned
- Runs time scheduler that creates trigger jobs based on `schedules` in system config
- Creates startup trigger jobs for agents with `system:start`
- Detects missed `time:morning` and `time:evening` triggers at startup

## Work Cycle

- Agent receives ONE job per work cycle — prevents context overflow
- Agent works autonomously until calling `done_working` (max iterations configurable)
- After `done_working`, manager checks for more jobs and starts another cycle if needed
- Agent decides when any job is complete — including trigger jobs
- Jobs must be explicitly completed by the agent via `complete_job`

## Agent Creation & Management

- Users create agents through the Chat agent (via chat)
- Chat uses `list_available_tools` to determine appropriate tools for new agents
- Core agents are protected: chat, worker, user
- All agents get base tools: list_jobs, get_job, create_job, complete_job, add_job_log, done_working
- Changes to triggers require a restart to take effect
- Agent files: `config.json` (settings) and `identity.md` (identity/instructions)

## Writing Agent Identities

- Identities define the agent's purpose, voice, and approach — not rigid rules
- Write for spirit and intention, not exhaustive instructions
- The agent uses judgment to decide which tools and operations serve the user's intent
- Avoid rule-heavy identities that try to cover every scenario
- Trust the LLM to interpret the identity's spirit and apply it to novel situations
- Don't list available tools — they're included in the system prompt from config.json
- Good identity: "I help users track what matters to them"
- Bad identity: "When user says X, do Y. When user says Z, do W..."

## Design Philosophy

All agents (users and AI) share the same identity schema and evolve through the same reflection process. The only difference is starting state: AI agents start pre-filled, users start empty.

Identities reflect patterns of behavior, not rigid rules:
- Identity is the pattern of stable attractors over time
- Both users and AI agents can develop any identity section through reflection
- Both follow the 90/10 principle: 90% exploit known patterns, 10% explore new possibilities

See docs/3_agents.md for the cognitive foundations behind this design.

## Memory Append

- Each agent has an internal append process after conversations
- Lightweight extraction that adds noteworthy items to short-term memory
- Runs automatically when `reflection.enabled` is true
- This is automatic and invisible — no job created

## Behavioral Triggers

Agents respond to three types of behavioral triggers, each with its own prompt template:

- **Job Assignment** (`agent/job_assignment.md`): Regular job execution
  - Triggered when an agent receives a job to complete
  - Focus on executing the assigned work
  - Agent decides when work is complete
  - Jobs with `user:request` tag: write findings as asset, hand back to user

- **Exploration** (`agent/exploration.md`): Scheduled discovery
  - Configured per-agent in `config.json` under `exploration` key
  - `exploration.enabled`: Whether exploration is active (default false)
  - `exploration.trigger`: Which time trigger to use (e.g., `time:hour_04`)
  - Creates visible `Trigger:exploration:{date}` jobs
  - User-created agents can use this for autonomous discovery (see agent-lib/ for examples)
  - Apply 90/10 principle: 90% grounded in user's interests, 10% novel exposure

- **Reflection** (`agent/reflection.md`): Scheduled self-analysis
  - Triggered by consolidate trigger (e.g., `time:evening`)
  - Creates visible `Trigger:reflection:{date}` jobs
  - Agent reviews memories, identifies patterns, evolves identity
  - Uses tools: list_memory, read_long_term_memory, graduate_memory, update_own_identity
  - Consolidate includes recent completed jobs (last 20) for context on work patterns

## Prompt Templates

- Base templates in `data/system/prompts/agent/`
- Agent-specific overrides in `data/agents/{agent}/prompts/`
- System checks agent-specific first, falls back to base
- Template selection based on job type:
  - `Trigger:reflection:*` jobs or `trigger:reflection` tag → reflection.md
  - `Trigger:exploration:*` jobs or `trigger:exploration` tag → exploration.md
  - Other `Trigger:*` jobs → exploration.md (legacy support)
  - All other jobs → job_assignment.md

## Job Coordination

Jobs can flow between agents and users via `handoff_job`:

- **handoff_job(job_id, to, note)**: Pass a job to another agent or user
  - Sets `pending_from` to track who handed it off
  - Enables return routing — recipient knows who to send it back to
  - Logs the handoff with optional note

**User → Agent → User (Request-Response)**
1. User asks Chat for something
2. Chat creates job with `user:request` tag, assigns to appropriate agent
3. Agent works, writes findings as asset
4. Agent calls `handoff_job(job_id, "user", "Ready for review")`
5. User reviews, provides feedback or completes

**User → Agent → User (Feedback Loop)**
1. Same as above, but user has feedback
2. User sends feedback via job context (UI routes to appropriate agent)
3. Agent revises, hands back to user
4. Loop continues until user completes

**Agent → Agent → Agent (Collaboration)**
1. Agent A is working on something
2. A needs Agent B's expertise: `handoff_job(job_id, "B", "need your input")`
3. B works, hands back: `handoff_job(job_id, "A", "here's my analysis")`
4. A continues, may involve more agents
5. Eventually returns to user or completes

**Rules:**
- Only call `complete_job` when work is truly done
- Use `handoff_job` for transfers, not `update_job`
- `pending_from` tracks return routing
- Job logs show full coordination history

## Agent Routing

- `list_agents_for_routing`: Get minimal agent info for routing decisions
  - Returns id, name, purpose (first line of identity), enabled status
  - Use when deciding which agent should handle a job

## Chat Agent Role

- Primary interface for user interaction
- Routes user requests to appropriate agents with `user:request` tag
- Can create and manage other agents
- Can answer questions about Euno by reading docs/specs
- Has access to user identity and memory for personalized responses

## Agent Ontology

Every agent shares the same four-category structure:

```
Agent = Identity + Cognition + Memory + Behavior
```

| Category | Question | What It Contains |
|----------|----------|------------------|
| **Identity** | Who am I? | Purpose, values, voice, attractors, context |
| **Cognition** | How do I think? | Reasoning (prompts) + Metacognition (self-regulation, reflection) |
| **Memory** | What do I know? | Short-term (90 days) + Long-term (permanent) |
| **Behavior** | What can I do? | Tools + Triggers + Modes |

### Identity

- Stored in `identity.md` as markdown sections
- Contains: Purpose, Behavioral Rules, Voice, Wants/Fears, Stable Attractors, Notable Events, Influences, Interests, Biographical Info
- Evolves through reflection—discovered, not configured
- AI agents start pre-filled; users start empty
- Historical snapshots: `identity.{yyyy}.md`

### Memory

- **Short-term**: `memory/short-term.jsonl` — Rolling 90-day window of noteworthy items
- **Long-term**: `memory/long-term/{yyyy}/{yyyy-mm-dd}.md` — Permanent chronological archive
- Types: person, place, thing, goal, concern, idea, learning, behavior
- Flow: Conversations → Append phase → Short-term → Consolidate phase → Long-term
- Cross-pollination: Chat agent's user-relevant items flow to user's memory
- See `spec/2_data.md` for detailed memory schemas and flow

### Cognition

Cognition has two aspects:

**Reasoning** — First-order thinking (about the world)
- Defined by system prompts in `data/system/prompts/agent/`
- Agent-specific overrides in `data/agents/{id}/prompts/`
- Template selection based on job type (job_assignment, exploration, reflection)

**Metacognition** — Second-order thinking (about thinking)
- Self-awareness, self-regulation, and self-improvement
- Inherent to all agents, not optional
- Configuration in `data/system/config.json` under `metacognition`

## Metacognition (Cognition Subsystem)

Metacognition is the self-regulation and self-improvement component of Cognition:
- **Self-regulation** — Velocity, resources, progress, planning (keeping the agent healthy)
- **Self-improvement** — Reflection (helping the agent grow)

### Velocity Awareness

- Tracks API call frequency globally across all agents
- Rolling window rate limiting (default: 30 calls per 60 seconds)
- Runaway detection pauses agents making too many calls too fast
- Paused agents auto-resume after cooldown period
- Configuration in `metacognition.velocity`

### Background Job Pacing

- Jobs tagged `background` are paced based on API utilization
- Regular jobs process immediately — only `background` jobs get delays
- Delay scales with load: none at <50%, 1-3s at 50-80%, 3-10s at >80%
- Use for uploads, integrations, batch processing

### Resource Awareness

- Tracks API costs per agent and per job
- Enforces budget limits with warnings at 80% and 95%
- Logs all LLM usage to daily cost files
- Configuration in `metacognition.resources`

### Progress Awareness

- Counts tool calls per iteration (max_tool_calls_per_iteration)
- Detects stuck patterns: same tool called repeatedly with identical inputs
- Breaks work cycle when stuck detected
- Configuration in `metacognition.progress`

### Strategic Planning

- Planning phase for complex operations (exploration, reflection)
- Creates a brief approach plan before execution
- Plan is injected into the working prompt for context
- Configuration in `metacognition.planning.enabled_for`

### Efficiency Optimization

- Batches reflection at end of work cycle instead of per-iteration
- Reduces LLM calls during autonomous work
- Configuration in `metacognition.efficiency.defer_reflection_in_work_cycles`

### Reflection (Self-Improvement)

Reflection is the metacognitive process of self-analysis and growth:

- **Append phase** (automatic after conversations)
  - Lightweight extraction of noteworthy items to short-term memory
  - Runs automatically after each chat() call
  - No job created — invisible to user

- **Consolidate phase** (triggered, creates visible jobs)
  - Heavy analysis triggered by `reflection.trigger` config
  - Creates `Trigger:reflection:{date}` jobs
  - Reviews short-term memory, graduates items to long-term
  - Updates identity based on patterns

Note: `reflection.trigger` in config.json defines WHEN reflection runs (Behavior).
The reflection process itself is Metacognition (Cognition).

### Configuration

System-wide defaults in `data/system/config.json`:
```json
{
  "metacognition": {
    "velocity": { "enabled": true, "max_calls_per_window": 30 },
    "resources": { "budget_limit": 10.0 },
    "progress": { "max_tool_calls_per_iteration": 50 },
    "planning": { "enabled_for": ["exploration", "reflection"] },
    "efficiency": { "defer_reflection_in_work_cycles": true },
    "reflection": {
      "append_max_tokens": 500,
      "append_batch_max_tokens": 1000,
      "consolidate_max_tokens": 2000,
      "upload_analysis_max_tokens": 1000
    }
  }
}
```

Individual agents can override specific settings in their `config.json` but rarely need to.

## Behavior

Behavior defines what agents can do and when they activate.

### Tools

- Capabilities defined by `tools[]` in agent's config.json
- All agents get base tools: list_jobs, get_job, create_job, complete_job, add_job_log, done_working
- Additional tools granted per-agent based on role
- An agent cannot use tools not in its config

### Triggers

- Configured per-agent in `config.json` under `triggers[]`
- Triggers create jobs, they do not wake agents directly
- Trigger job naming: `Trigger:{name}:{yyyy-mm-dd}`
- Trigger types:
  - `system:start` — fires once at system startup
  - `time:{name}` — fires at scheduled times (morning, evening, hourly)
  - `job:assigned` — fires when job assigned to agent

### Modes

- **Exploitation** (~90%): Regular job execution, working within known patterns
- **Exploration** (~10%): Scheduled discovery, finding new opportunities
- Exploration configured per-agent: `exploration.enabled`, `exploration.trigger`

### Triggers vs Processes

Behavior defines *when* things activate via triggers. The processes themselves may belong to other categories:

| Trigger Config | Activates | Process Lives In |
|---------------|-----------|------------------|
| `triggers[]` | Job assignment | Behavior (tool execution) |
| `exploration.trigger` | Discovery mode | Behavior (exploration mode) |
| `reflection.trigger` | Self-analysis | Cognition (metacognition) |
