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

Cognition is the abililty to think. It has two layers:

- Reasoning is first-order thinking about the world—how the agent approaches problems and communicates.
- Metacognition is second-order thinking, or thinking about thinking. It includes token awareness for budget enforcement, progress awareness for stuck detection, and consolidation for memory processing and identity evolution.

### Memory

Memory is the context that informs decisions.

- Short-term memory holds current concerns: people, goals, ideas, learnings. It's a rolling window that informs immediate behavior.
- Long-term memory is a permanent chronological archive. It's the source material for identity evolution.

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
4. When a job is found, the agent runs a work cycle: claim → reason with tools → complete
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

An agent can have multiple jobs assigned (queued), but only works one at a time.

#### Work Cycle

When an agent starts working a job, it sets the status to `working`, executes a reasoning loop with tools until complete, then marks the job `done` and returns to polling.

All LLM calls go through metacognition for budget tracking and stuck detection.

#### Regulation

Metacognition monitors all LLM calls for self-awareness. It tracks token usage against budgets, detects stuck patterns (like repeated tool calls), and enforces limits. When a threshold is breached, the agent is automatically paused and requires manual intervention to resume.

#### Consolidation

Agents run scheduled reviews of their memory to update their identity. This is how identity is discovered, not configured—agents evolve through consolidation.
