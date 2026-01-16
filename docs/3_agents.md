# Agents

## Our Bold Conjecture

Euno exists to test a hypothesis: that a personalized intelligence can help someone flourish—anticipating their needs, doing good work on their behalf, and supporting their path toward eudaimonia.

The bet is that this becomes possible through a **shared agent ontology**. Humans and AI agents aren't fundamentally different kinds of things. Both have identity that defines who they are, cognition that determines how they think, memory that provides context, and behavior that determines what they do. If we model them the same way, an AI agent can truly learn a person—not as a collection of preferences, but as a pattern of stable attractors that define who they are.

This architecture is the experiment. If the shared ontology holds, Euno can grow with you: learning what you want and fear, recognizing your stable patterns, adapting its behavior through the same reflection process you use. If it doesn't hold, we'll learn why humans and AI agents need different models.

Either way, we find out.

---

Euno is built on two core concepts: **Agents** and **Jobs**. Agents do the work; jobs are the work.

An agent is anything with the capacity to act—both people and AIs qualify. You, the user, are an agent too; you just have a different interface (the UI) than AI agents (autonomous loops). Every agent in Euno shares the same fundamental structure.

Jobs are how agents coordinate. Any agent can create a job, work on it directly, or hand it off to another agent. This creates a dynamic system where work flows based on who has the capacity and capability to act.

## The Agent Ontology

Every agent—human or AI—shares the same four-category structure:

```
Agent = Identity + Cognition + Memory + Behavior
```

| Category | Question | Stability |
|----------|----------|-----------|
| **Identity** | Who am I? | Most stable |
| **Cognition** | How do I think? | Stable patterns, evolving |
| **Memory** | What do I know? | Fluid, constantly updating |
| **Behavior** | What can I do? | Configured, can change |

### Identity (Who the agent is)

The stable self that grounds all agent activity.

- **Purpose** — Why the agent exists
- **Values** — What it pursues (Wants) and avoids (Fears)
- **Voice** — How it communicates
- **Stable Attractors** — Patterns it returns to under pressure
- **Context** — Biographical information, influences, notable events

Identity is the pattern of stable attractors over time. Agents act to pursue what they want and avoid what they fear. Through experience, they discover strategies that work—these get repeated and become stable patterns. Identity is discovered rather than configured, refined through reflection.

**Identity Schema** (all agents):
- **Purpose** — What drives them / why they exist
- **Behavioral Rules** — Learned must/must not constraints
- **Voice** — Communication style
- **Wants and Fears** — What they pursue and avoid
- **Stable Attractors** — Patterns they return to under stress
- **Notable Events** — Significant consistent or surprising actions
- **Influences** — People, places, experiences that shape them
- **Interests** — Current goals, projects, focus areas
- **Biographical Information** — Factual details

AI agents typically start with Purpose, Behavioral Rules, and Voice pre-filled. Users start empty. Over time, both can develop any section through reflection.

**Why one schema?** The same model of identity applies to both humans and AI agents. This means an AI agent can develop wants (goals it pursues), fears (outcomes it avoids), and stable attractors (behaviors it returns to). A user can have behavioral rules (learned constraints) and voice (communication style). The ontology is the same; only the starting state differs.

### Cognition (How the agent thinks)

The processing apparatus—both first-order and second-order thinking.

**Reasoning** — How the agent processes information and makes decisions
- System prompts define the agent's reasoning approach
- Prompt templates for different contexts (job assignment, exploration, reflection)
- Decision patterns emerge from reasoning combined with identity

**Metacognition** — Self-awareness and self-regulation
- How the agent monitors and regulates its own processes
- Inherent to all agents, not optional

| Capability | What It Does |
|------------|--------------|
| **Velocity Awareness** | Track call rate, pause if too fast |
| **Resource Awareness** | Track costs, enforce budgets |
| **Action Awareness** | Monitor tool calls per iteration |
| **Progress Awareness** | Detect stuck/thrashing patterns |
| **Strategic Planning** | Plan approach before complex tasks |
| **Efficiency Optimization** | Batch operations, defer reflection |

**Why group them together?** Both reasoning and metacognition are thinking. Reasoning is first-order (thinking about the world), metacognition is second-order (thinking about thinking). They form the agent's "mind."

**Key behaviors:**
- Agents automatically pause when runaway behavior is detected
- Tool call limits prevent infinite loops within a single chat
- Stuck detection breaks out of repeated identical tool calls
- Planning phase for exploration/reflection improves outcomes
- Batched reflection reduces LLM calls during work cycles

System-wide defaults in `data/system/config.json` under the `metacognition` key apply to all agents. Individual agents can override specific settings in their `config.json` if needed.

### Memory (What the agent knows)

Context that informs decisions. Without memory, every interaction starts from zero.

**Short-term memory** (90 days) captures what's currently on an agent's mind: people, places, things, goals, concerns, ideas, learnings, and behaviors. The last two enable self-improvement—agents can record what they've learned and behavioral patterns to refine over time. Memories are extracted automatically after conversations.

**Long-term memory** (permanent) is a chronological record of important events. When short-term memories expire, significant ones graduate to long-term storage. This archive becomes the source of truth for identity evolution.

The flow is: Conversations → Short-term Memory → Reflection → Long-term Memory → Identity updates.

### Behavior (What the agent does)

The action system—capabilities, activation, and balance.

**Tools** define what an agent can do. Each agent's config lists the tools it has access to—this is how you control capabilities and permissions. An agent that can't see a tool can't use it.

**Triggers** define when an agent acts. There are three types:

- **Job Assignment** — Work assigned by users or other agents. The agent executes and completes the job.
- **Exploration** — Scheduled discovery where agents research opportunities aligned with your interests. Configured via `exploration.trigger` in the agent's config.
- **Reflection** — Scheduled self-analysis where agents process memories and update identity. Configured via `reflection.trigger`.

**Modes** govern the balance between stability and growth:

- **Exploitation** (~90%) — Work within known patterns for stability
- **Exploration** (~10%) — Discover new options for growth

Flourishing requires this balance. Most activity exploits known strategies for stability, while reserving space for bounded exploration to discover new options. Euno respects this ratio for all agents.

Each trigger type has its own prompt template. System defaults live in `data/system/prompts/agent/`; individual agents can override with custom prompts in `data/agents/{id}/prompts/`.

## Jobs

Jobs are how all agents coordinate work. Any agent can spawn a job, work on it, or route it to others.

**Structure:**
- Jobs nest hierarchically via `parent_id`—top-level jobs organize related work
- Jobs have `assignees[]`—an agent only sees jobs assigned to it
- Status is `todo`, `completed`, or `archived`—only `todo` jobs are actionable

**Tags** provide context:
- `user:request` — User asked for this; hand findings back, don't auto-complete
- `trigger:exploration` — Scheduled discovery job
- `trigger:reflection` — Scheduled self-analysis job

**Flow patterns:**
- Agent creates job → works on it → completes it
- Agent creates job → hands off to another agent → receives result → completes
- Exploration creates suggestion → assigns to user for review
- Reflection generates insight → may spawn follow-up jobs

**Key tools:**
- `create_job(name, description, assignees)` — Create new work
- `handoff_job(job_id, to, note)` — Transfer to another agent
- `complete_job(job_id)` — Mark as done

The `pending_from` field tracks return routing so jobs find their way back after handoffs. Job logs preserve the full coordination history.

---

**Technical Details:** See `spec/1_agents.md` for implementation rules, `spec/2_data.md` for data schemas.
