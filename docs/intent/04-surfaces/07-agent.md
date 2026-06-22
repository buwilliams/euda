# Agent

## Key Ideas

- **Agents Operate Euda Directly**: an AI agent uses Euda through the same CLI a person would, not through a privileged internal API.
- **Three Commands Are Enough**: an agent's entire action surface is discover, read-usage, and execute. Everything else is composition.
- **The Same Interface As People**: because agents act through the CLI, there is no separate machinery for AI—honoring the non-distinction between agents at the level of operation.
- **Future Dominance**: over time, agent-native operation may become the most important surface. The system is built to welcome that.

## Purpose

The agent surface exists because Euda is designed for AI-assisted and eventually AI-led operation. An agent needs a reliable way to understand the system, inspect state, take action, and leave a trace. Euda's answer is to let agents operate through the CLI—the same explicit, scriptable, low-state surface a careful person would use.

This is a direct expression of Euda's central idea. If the user is an agent and an AI persona is an agent, then both should act through the same interface. The agent surface is not a special integration; it is the shared CLI, used by a non-human actor.

## How Agents Operate

On `main`, the agent runner gives a model a tiny, stable tool surface:

- **`list_apps`** — discover what capabilities exist (the combined `core` and `skills` listings).
- **`app_usage`** — read the usage for a capability, e.g. `core topics` or `skills gcal`.
- **`execute_command`** — run an Euda command, e.g. `core topics list --state todo`, and receive its output.

The runner assembles the agent from CLI calls: it loads the agent's identity as the system prompt by calling the identity app, loads the provider and model by calling the LLM app, then runs a bounded tool-use loop where the agent's "tools" are these three commands. The agent thinks, runs a command, reads the result, and continues—operating Euda exactly as a person typing commands would, within a `max_tool_rounds` budget.

## Expected Role

Agents should be first-class operators of Euda:

- understand the system by listing apps and reading their usage, not by reverse-engineering internals;
- act by executing commands, so their actions are the same operations available to anyone;
- leave durable evidence—topics, logs, memory—rather than disappearing into a provider transcript;
- stay bounded by self-regulation: budgets, round limits, and pause states.

Current implementation details that matter to intent:

- the runner supports multiple providers (such as Anthropic, OpenAI, and xAI) through a single tool-use loop, so the action surface is provider-independent;
- provider and model are configuration read from the LLM app, not hardcoded behavior;
- identity is the system prompt, so an agent's behavior flows from who it is.

Agents should not gain a hidden, more powerful path than people have. Their power comes from the same commands, used well.

## Future Direction

The agent surface should grow toward fleets of agents operating Euda on a person's behalf—planning, curating, exploring, consolidating, and coordinating through topics. As models strengthen, more of the system's operation may move here.

The intent to preserve: agents and people share one operating surface; agents act through the same commands, leave the same durable evidence, and remain bounded by the same self-regulation—so that an AI-led Euda is still legible, accountable, and the person's own.
