# Cognition

## Key Ideas

- **Two Orders Of Thought**: cognition is reasoning (first-order: how to do the work) plus metacognition (second-order: how the agent regulates and improves itself).
- **Plan Before Acting**: an agent forms a brief approach before executing—what tools, what sequence, what to delegate—so work is coherent rather than reactive.
- **Self-Awareness Is Inherent**: every agent watches its own resource use, notices when it is stuck, and can pause itself. Metacognition is not an add-on; it is part of being an agent.
- **Identity Shapes Cognition**: how an agent reasons and what it refuses come from its identity, not from hardcoded logic.
- **Operate Through The Shared Interface**: an agent acts by using skills and the CLI—the same interface a person uses—rather than through privileged internal calls.

## Purpose

Cognition is how an agent turns intent into action well. A capable actor must do two things: reason about the work in front of it, and regulate itself so it stays effective, bounded, and improving. Euda treats both as parts of one capability so agents are not just powerful but trustworthy.

## The Two Orders

### Reasoning (First-Order)

When an agent picks up a topic, it forms a brief plan—an approach, a tool sequence, what to delegate—before executing. Then it acts, using skills, until the work is done or handed off. Reasoning is shaped by the agent's identity and the topic's context, and on `main` it runs as a tool-use loop where the agent's actions are CLI commands.

### Metacognition (Second-Order)

Metacognition is the agent reflecting on its own operation. It has two aspects:

- **Self-Regulation** — token awareness, agent states, stuck detection, and incidents. This keeps an agent bounded and recoverable. See [Metacognition](02-metacognition.md).
- **Self-Improvement** — consolidation: processing memory and evolving identity. This is how an agent (and Euda's model of a person) grows. See [Consolidation](03-consolidation.md).

## Expected Role

Cognition should sit between an agent's identity and its actions:

- read identity, memory, and topic context to decide what to do;
- plan, then act through skills, leaving a trace;
- watch its own budget and progress, and pause rather than spin;
- after acting, feed observations into memory for later consolidation.

Current implementation details that matter to intent:

- `v1` separates reasoning (system prompts under `data/system/prompts/agent/`, with per-agent overrides) from metacognition (`agent/cognition/metacognition/`), and always runs a lightweight planning phase before execution.
- On `main`, the runner composes cognition from CLI calls: identity becomes the system prompt, the LLM app supplies the provider, and the agent's tools are `list_apps`, `app_usage`, and `execute_command`, bounded by `max_tool_rounds`.

Cognition should not become a place where product semantics are redefined. An agent reasons about *how* to advance work; it does not invent new meanings for identity, memory, or topics.

## Future Direction

As models improve, reasoning should become more capable while metacognition becomes more important, not less—stronger agents need stronger self-regulation. Euda should keep cognition observable: a person should be able to see what an agent planned, what it did, where it spent its budget, and when it chose to stop.

The intent to preserve: agents that are powerful and self-aware, whose reasoning is shaped by identity and whose regulation keeps them bounded, recoverable, and continually improving.
