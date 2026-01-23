# Design

The design of Euno anthropomorphizes AI [attributing human characteristics/behavior]. In Euno, we treat people and AI basically the same and call them Agents. Agents, like people, grow and change over time, so we've built a system that supports that type of growth. When a person eats, they grow, AIs grow when fed them with data. Here's what makes up an Agent:
- Cognition: the ability to reason and have self-awareness (consolidation/regulation)
- Memory: form new short and long-term memories
- Behavior: (triggers, events, schedules)
- Identity: purpose based on psychological concepts of a 'cognitive core', these are beliefs about the 'self'

We call what makes up Euno the 'Ontology' or 'the nature of being'. This raises questions: How does the Euno system work? How is it wired together? How do Agents collaborate? We call these category of questions 'Euno Lifecycle', here are the parts of it:
- Jobs: agents take action when they receive a job, these jobs can be nested and change hands, and an Agent works one job at a time.
- Manager: in charge of starting agents, assigning them scheduled jobs, and monitoring their health
- Agent Lifecycle: enabled, disabled, paused—and transitions between them

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

- Reasoning is first-order thinking about the world—how the agent approaches problems and communicates. This includes job planning: when an agent begins work on a job, it first creates a brief plan (tool sequence, delegation decisions, approach) then executes that plan. Planning reduces wasted effort and enables efficient batching.
- Metacognition is second-order thinking, or thinking about thinking. It includes token awareness for budget enforcement, progress awareness for stuck detection, and consolidation for memory processing and identity evolution.

### Memory

Memory is the context that informs decisions.

- Short-term memory holds current concerns: people, goals, ideas, learnings. It's a rolling window that informs immediate behavior.
- Long-term memory is a permanent chronological archive. It's the source material for identity evolution.

### RLM (Recursive Language Model)

RLM provides intelligent access to long-term memory through iterative exploration. Rather than simple keyword search, RLM uses an LLM to semantically navigate and analyze memory archives. Methods include `analyze()` for open-ended exploration, `recall()` for finding specific facts, and `extract_identity()` for discovering patterns that update identity. RLM is used during consolidation to evolve identity based on observed patterns.

### Behavior

Behavior is what enables action. It has two parts.

- Tools are capabilities that agents use to act in the world. Each tool is a function with a name, description, and parameters. Each agent has access to a configured subset of available tools.
- Triggers determine when agents act—job assignment, scheduled times, or system events.

---

## Euno Lifecycle

### Jobs

Jobs are the unit of work and how agents coordinate. Any agent can create, work on, or route jobs to others. A job has a name, description, hierarchy, assignment, status, and assets. Jobs can be handed off between agents, enabling collaboration patterns like request-response and delegation.

### Manager

The Manager orchestrates the system—it starts agents, runs the scheduler, and monitors health. At startup, it loads agent configurations and starts each agent in its own thread. A background scheduler creates trigger jobs at configured times. Agents discover these jobs through polling; the Manager doesn't wake agents directly.

### Agent Lifecycle

Here's how agents operate:

1. Manager instantiates agents and monitors their health (handling reloads and shutdown)
2. Each agent has a state: enabled, disabled, or paused
3. Enabled agents poll for assigned jobs
4. When a job is found, the agent runs a work cycle: claim → plan → execute → complete
5. Jobs progress through states: todo → working → done (or error)
6. Metacognition regulates all LLM calls—if a breach is detected (e.g., budget exceeded), the agent is paused
7. Between jobs, consolidation reviews memory and evolves identity

#### Agent States

Agents transition between three states:
- Enabled: normal operation, polling for jobs and working on them
- Disabled: user explicitly turned it off, no work happens
- Paused: system auto-paused (usually budget exceeded), requires manual resume

#### Polling

Enabled agents poll for assigned jobs. They're not pushed—this keeps them decoupled and resilient to failures. When an agent finds an actionable job, it begins a work cycle.

#### Job States

Jobs progress through states based on assignment and work:
- todo + no assignee: unassigned, waiting to be picked up
- todo + assignee: queued, assigned but not yet being worked
- working + assignee: agent is actively working on the job
- done: completed successfully
- error: something went wrong
- archived: soft-deleted, no longer active

An agent can have multiple jobs assigned (queued), but only works one at a time.

#### Job Routing

Jobs move between agents (and users) through reassignment. When an agent needs input or wants to delegate, it reassigns the job and sets status back to `todo`. The recipient picks it up when they poll for work.

**Handoff**: An agent can hand off a job to another agent or the user. This updates the assignee and records who sent it (`pending_from`), so the job can be returned after review. Example: an agent needs user approval, so it hands off to `user` with a note explaining what's needed.

**Blocking**: Jobs can be marked as blocked using tags:
- `waiting:*` — waiting for external input (e.g., `waiting:user-response`)
- `blocked:*` — blocked by a dependency (e.g., `blocked:api-access`)

Blocked jobs are excluded from actionable queries—agents won't pick them up until unblocked. When a user interacts with a blocked job (views it, adds an asset), the blocking tags are automatically removed and the job returns to the agent's queue.

**The user as agent**: The user participates in job routing like any other agent. Jobs can be assigned to `user`, handed off to `user`, or created by `user`. The difference is interface—users work through the UI, agents work through polling and tool calls.

#### Work Cycle

When an agent starts working a job, it sets the status to `working`, creates a brief plan (tool sequence, delegation decisions, approach), then executes that plan until complete. Finally it marks the job `done` and returns to polling.

Planning is part of Reasoning—it reduces wasted effort and enables efficient batching (e.g., deferring consolidation to end of work cycle). All LLM calls go through metacognition for budget tracking and stuck detection.

#### Regulation

Metacognition monitors all LLM calls for self-awareness. It tracks token usage against budgets, detects stuck patterns (like repeated tool calls), and enforces limits. When a threshold is breached, the agent is automatically paused and requires manual intervention to resume.

#### Consolidation

Agents run scheduled reviews of their memory to update their identity. This is how identity is discovered, not configured—agents evolve through consolidation.
