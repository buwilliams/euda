# Agent

## Key Ideas

- **Agent = Identity + Cognition + Memory + Behavior**: every actor in Euda is composed of these four parts.
- **No Distinction Between Human And AI**: the user is an agent with the same structure as any AI agent. Only the interface differs.
- **All Agents Evolve Together**: not only does Euda's model of the user change over time, so do the agents serving the user. Each evolves uniquely, in relationship.
- **Concerns, Not Just Tasks**: agents are defined by what they care about—a curator's concern is your incoming feeds, an explorer's is your growth—not by a fixed job description.
- **Coordination Through Topics**: agents do not call each other directly. They coordinate by creating and handing off topics, which keeps their collaboration visible.

## Purpose

The agent is Euda's unit of actorhood. It exists so the system can have many distinct intelligences—some autonomous, some human—each with its own identity and memory, all able to act and coordinate.

The decision that makes Euda unusual is its refusal to distinguish human agents from AI agents. A person is `user`: an agent with identity, memory, cognition, and behavior. An AI persona is the same. This is not a gimmick. It means the modeling of the person and the modeling of their agents use the same mechanisms, so they can grow in parallel and understand one another through a shared structure.

## The Four Parts

- **Identity** — who the agent is: purpose, behavioral rules, voice, wants and fears, stable attractors. Discovered and evolving. See [Identity](01-identity.md).
- **Cognition** — how the agent thinks: first-order reasoning (planning and acting on work) and metacognition (self-regulation and self-improvement). See [Cognition](../03-capabilities/01-cognition.md).
- **Memory** — what the agent knows: short-term concerns and a long-term archive of lived experience. See [Memory](03-memory.md).
- **Behavior** — what the agent can do and when it acts: the skills it may use and the triggers that bring work to it. See [Skills](../03-capabilities/04-skills.md) and [Triggers](../03-capabilities/06-triggers.md).

## Expected Role

An agent should be a coherent, bounded actor that a person can understand and trust:

- It has a stable identity that shapes its judgment.
- It carries memory so it can anticipate rather than re-ask.
- It regulates itself—watching its own token budget, noticing when it is stuck, and pausing rather than spinning.
- It acts only through skills, and only on work expressed as topics, so its activity is visible and auditable.

Agent states make self-regulation legible:

- `enabled` — normal operation; the agent is available for work.
- `disabled` — explicitly turned off by the person.
- `paused` — automatically halted by the system (for example, a token budget breach) and requiring deliberate resumption.

Current implementation details that matter to intent:

- In `v1`, agents run autonomous work cycles as background threads inside the server, polling for actionable topics and working one at a time.
- On `main`, an agent is a small record (`agent.json`: name, type, state, linked identity) and is *run* through the CLI. The runner loads the agent's identity as its system prompt by calling the identity app, loads provider settings by calling the LLM app, and then operates Euda through the CLI itself.
- Agent types on `main` (`user`, `autonomous`, `subagent`) name the role, not a different kind of being—all share the same composition.

The point that must survive any refactor: an agent is the same thing whether a human or a model sits behind it. The system should never grow a privileged "human path" or a hidden "AI path."

## Future Direction

As capability grows, Euda should support a catalog of agents—personas tuned to facets of a person's wellbeing: mental health, fitness, education, relationships, work. Each carries its own identity and concern; together they form a personal team that evolves with the person it serves. See [Personas](../03-capabilities/05-personas/00-overview.md).

The long-term direction is many agents—human and AI—working in parallel on a person's behalf, coordinating through topics, each growing its own identity. The intent to preserve is parity and relationship: agents and the person they serve are modeled the same way and change together, and no agent's activity is hidden from the person it serves.
