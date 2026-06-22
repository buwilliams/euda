# Topic

## Key Ideas

- **The Unit Of Work**: a topic is the primary unit of work in Euda. Tasks, projects, ideas, references, and goals are all topics.
- **The Coordination Hub**: topics are the *only* channel through which agents coordinate. An agent assigns work to another agent—AI or human—by creating or handing off a topic.
- **Visibility By Design**: because all coordination flows through topics, a person can always see what every agent is working on and what is queued. There is no hidden inter-agent protocol.
- **Human And AI On The Same Board**: a topic can be assigned to an AI agent or to the user. The difference is only the interface used to work it.
- **Stateful Lifecycle**: topics move through explicit states so progress is legible and recoverable.

## Purpose

Topics exist so that work and collaboration are never invisible. In a system full of autonomous agents, the danger is a swarm of activity a person cannot see or steer. Euda answers this by routing *all* work and *all* coordination through one durable object: the topic.

This makes Euda a coordination hub rather than a chatbot. An agent that notices an opportunity does not act in secret; it creates a topic. An agent that needs a person's judgment does not block; it hands the topic off. The person, themselves an agent, receives topics the same way an AI agent does.

## The Lifecycle

Topics carry a name, description, state, optional assets (files), and can be nested into a hierarchy and assigned to an agent. They move through explicit states:

- `todo` — waiting to be worked.
- `working` — an agent is actively working it.
- `done` — completed successfully.
- `error` — something went wrong.
- `archived` — soft-deleted, history preserved.

A topic becomes actionable when it is assigned to an agent, is in `todo`, and is due now or has no due date. Future-dated and "someday" topics wait; blocked or waiting topics are held out of the actionable set until the dependency clears. An agent claims an actionable topic, sets it to `working`, plans, acts through skills, and then completes it—or **hands it off**, recording who sent it so the work can be routed back later.

## Expected Role

Topics should be the shared board that keeps a fleet of agents legible:

- Any action that needs an agent's attention becomes a topic assigned to that agent.
- Agents create topics for themselves or for others, including the user.
- Handoff carries provenance (`pending_from`) so collaboration can round-trip.
- Assets, logs, and execution traces attach to topics so the full story of a piece of work is inspectable.

Current implementation details that matter to intent:

- Topics live in a small SQLite database because they need indexing and querying; almost everything else in Euda is flat files. The database is an implementation choice in service of fast, reliable querying, not a departure from local ownership.
- On `main`, topics are their own CLI app (`euda core topics`) with `create`, `get`, `list`, `update`, `delete`, `search`, and hierarchy commands (`tree`, `parent`, `children`).
- Topic state and assignment are the same whether a human or an AI agent works the topic.

Topics should not become a generic project-management database. Their purpose is coordination and visibility for an agent fleet serving one person.

## Future Direction

As agent fleets grow, topics should support richer coordination—dependencies, ordering, and clearer handoff semantics—without losing their defining property: that a person can look at the board and understand what their agents are doing and why.

The intent to preserve: work is always representable as an understandable topic, coordination always flows through topics, and no agent—human or AI—works in a way the person cannot see.
