# Surface Principles

## Key Ideas

- **Surfaces Are Adapters**: a surface exposes identity, memory, topics, and capabilities without owning their meaning.
- **A Platform, Not A UI**: Euda is the platform; any screen, voice, or agent interface is one surface over shared capability. The system must not depend on any single one surviving.
- **Two First-Class Bases**: for people, the base surface is *Focus*; for agents and composition, the base surface is the *CLI*. Both call the same capabilities.
- **Same Meaning Everywhere**: what a topic, an identity, or a pause means is identical across surfaces. Surfaces differ in ergonomics, not semantics.
- **Toward Ambient**: the long-term surfaces are ambient—HUDs, voice in wearables and smart devices, agents—where Euda lives wherever a person does.

## Purpose

Surfaces exist so different actors can use Euda well in their context. A person wants a calm, curated view and a place to say what's on their mind. An agent wants reliable, scriptable commands. A future wearable wants a glance or a sentence. Each is a different ergonomic over the same underlying intelligence.

The purpose of a surface is to make shared capability usable in a context—not to become a separate product. Euda was conceived as a platform: the screen is simply the most convenient surface today, not the end state.

## Expected Role

Every surface should preserve the same model and capability semantics:

- call into shared capabilities rather than reimplementing them;
- expose identity, memory, topics, and agent state clearly;
- make errors and pauses visible and recoverable;
- stay replaceable as better, more ambient interfaces arrive.

The surfaces Euda has built or intends:

- **Focus** — the first-class human surface: a curated view of what matters now. See [Focus](02-focus.md).
- **Chat** — a conversational input into the system, not the product itself. See [Chat](03-chat.md).
- **CLI** — the first-class agent and composition surface; the base of the `main` architecture. See [CLI](04-cli.md).
- **Web** — the packaging that delivers Focus and chat in a browser; on `main`, one capability among equals. See [Web](05-web.md).
- **API** — the contract surfaces share for product and runtime state. See [API](06-api.md).
- **Agent-Native** — agents operating Euda directly through the CLI. See [Agent](07-agent.md).

## Future Direction

Future surfaces may be voice, wearable HUDs, smart-device ambient displays, or fully agent-native. Euda should be ready by keeping meaning below the surface layer, so a new surface can appear without changing what work or identity means.

The intent to preserve: Euda is a platform whose surfaces are conveniences over shared capability. The dominant surface may eventually be no traditional screen at all—an agent or an ambient device serving a person in the flow of life—and the system should welcome that without losing its center.
