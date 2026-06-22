# API

## Key Ideas

- **The Shared Contract**: the API is how surfaces reach product and runtime state without duplicating logic.
- **Same Meaning As Everywhere**: the API exposes identity, memory, topics, and agent state with the same semantics the CLI and Focus use.
- **Local By Default**: the API is a local contract for a single person's instance, not a multi-tenant cloud service.
- **Real-Time Where It Helps**: the API can stream changes so surfaces stay current—topic updates, agent activity, consolidation progress.

## Purpose

The API exists so the human-facing surfaces have a consistent way to read and change state. Focus and the browser should not each invent their own notion of what a topic is or how an agent pauses; they call the same contract. The API keeps surfaces aligned with the shared model.

In keeping with Euda's design, the API is a *local* contract. Each instance serves one person on their own infrastructure; there is no shared database or multi-tenant backend. The API's job is to let a person's surfaces talk to a person's capabilities, not to centralize anyone's data.

## Expected Role

The API should be the alignment layer for surfaces:

- expose topics, agents, identity, memory, user data, settings, and events;
- preserve the same semantics as the CLI and Focus, so no surface can do something the others cannot;
- stream real-time updates where surfaces benefit—topic changes, agent messages, and consolidation progress.

Current implementation details that matter to intent:

- `v1` provides a FastAPI surface over `src/core/` (topics and assets, agents and their identity/memory/monitoring, chat, user identity and memory, settings, backups) plus a Server-Sent Events channel for live updates.
- On `main`, the same product meaning is reachable through the CLI capabilities; an HTTP API is the web capability's contract rather than the system's core.

The API should not become a second source of truth or a place where product rules diverge. It is a contract over shared capability.

## Future Direction

As surfaces multiply—voice, wearable, agent-native—the API's role is to keep them all speaking the same model while remaining local and owned by the person. The intent to preserve: one consistent contract over shared capability, never a centralized service that takes a person's data out of their hands.
