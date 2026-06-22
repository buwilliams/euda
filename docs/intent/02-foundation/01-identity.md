# Identity

## Key Ideas

- **Identity Is The Center**: identity is the single most important model in Euda. It captures who an agent is—preferences, values, voice, and ideology—and everything else exists to serve its fidelity.
- **Every Agent Has Identity**: humans and AI agents are modeled identically. There is no "user profile" on one side and "AI persona" on the other—there is identity, the same structure for both.
- **Discovered, Not Configured**: identity is learned from lived evidence. It is not a list of settings or `if X then Y` rules; it is a description of patterns that recur.
- **Evolving, Not Fixed**: identity changes as a person changes and as an agent grows. Both the user's identity and the agents serving the user evolve uniquely, together.
- **Spirit Over Rules**: identity describes intention and pattern so an agent can apply judgment to novel situations, rather than enumerating commands that break the moment reality differs.
- **Held Lightly**: conclusions about identity should be earned by evidence and held with stated confidence. Empty is better than speculative.

## Purpose

Identity exists so Euda can act as *this person's* intelligence rather than a generic assistant. To do tasks someone's way, to curate toward their values, and to anticipate their needs, the system must model who they are with depth and honesty.

Identity is also the reason agents can serve a person over years. A person is not static; their patterns shift, their interests turn, their voice matures. An identity that is discovered and continually revised lets the relationship deepen instead of decay.

Because the same model describes AI agents, identity is also how Euda gives its own actors coherence. An agent with a clear purpose, voice, and set of attractors behaves consistently under pressure and can be reasoned about, corrected, and trusted.

## The Identity Model

Euda has articulated the identity model in two compatible forms. Both are preserved because each captures something true.

### The Original Articulation (v1)

Version 1 framed identity as a small set of human-legible sections written in an agent's `identity.md`:

- **Purpose** — what the agent exists to do; what drives it.
- **Behavioral Rules** — learned must / must-not constraints, written as principles rather than an exhaustive rulebook.
- **Voice** — communication style: tone, word choice, sentence patterns, and how register shifts across contexts.
- **Wants And Fears** — what the agent pursues and what it avoids.
- **Stable Attractors** — the patterns it returns to under stress; what it is when everything else is stripped away.

Plus optional sections that accrue over time:

- **Notable Events** — significant, consistent, or surprising actions.
- **Influences** — people, places, and experiences that shaped the agent.
- **Interests** — current goals, projects, and areas of focus.
- **Biographical Information** — factual details about the agent's life or existence.

For AI agents, Purpose, Behavioral Rules, and Voice are seeded so the agent can act from the start; the remaining sections evolve. For the user agent, identity often starts nearly empty and is discovered almost entirely through observation and consolidation.

### The Evolved Schema (main)

The `main` branch refined the model into a schema built around *learned patterns*. Its framing: "Identity is learned patterns—how someone pursues wants, avoids fears, regulates emotion, and communicates. These patterns are domain-specific, context-activated, and relationally maintained. They operate on a substrate (temperament, neurobiology) that is given, not learned." The schema has seven sections, all optional, written as plain prose:

- **Substrate** — what is given, not learned: disclosed neurodivergence, health, temperament. Populated only when explicit.
- **Patterns** — the core of the file: domain-specific behavioral attractors (work, relationships, conflict, creativity, money, health, friendship), each noted with its trigger, whether it is adaptive, a confidence level, and the evidence behind it.
- **Regulation** — emotional regulation: default state, stress markers, strategies, and tolerance window.
- **Values** — constraints on strategy selection: what is stated, what is demonstrated in behavior, and what is refused even when effective.
- **Self-Model** — how the person sees themselves versus how they behave, including where the two diverge.
- **Voice** — communication patterns: register, density, directness, emotional expression, epistemic style, humor, conflict style, narrative tendency, and listening shape.
- **Meta** — plasticity and current state: metacognitive capacity and current phase (stability, transition, crisis, exploration).

The two forms agree on the essentials: identity is purpose, constraint, voice, motivation, and the stable core a person or agent returns to. The evolved schema makes the *evidence discipline* explicit—distinguish what is said from what is revealed, weight sources differently, and hold conclusions until they are earned.

## Expected Role

Identity should sit beneath every other capability:

- **Cognition** reads identity to decide how to act and what to refuse.
- **Consolidation** is the process that writes identity—observing memory and conversation, detecting patterns, and updating the file with small, earned diffs.
- **Skills and topics** are filtered through identity: what to curate, what to surface, what counts as care versus busywork.
- **Voice** lets agents mirror the person's natural language; for the user this is discovered, for AI agents it is seeded and refined.

Current implementation details that matter to intent:

- Identity is plain markdown so people and agents can read and edit it directly.
- On `main`, identities are **versioned and append-only** (`identity-{n}.md` with a `.json` sidecar). Consolidation produces a new version, records the change ratio against a cap, and never silently rewrites history.
- A separate **guide** (also versioned) instructs the consolidation process on how to extract patterns from data—identity and the method for evolving it are both first-class.
- New identities start from a template so structure is consistent and emptiness is acceptable.

Identity should never collapse into a settings panel. The moment it becomes `when the user says X, do Y`, it stops being identity and starts being brittle automation.

## Future Direction

As agents improve, identity should become richer without becoming more obscure. It may grow to represent dependencies between patterns, contested values, evidence provenance, and the trajectory of change over time—while still reading as something a person recognizes as themselves.

The long-term direction is an identity that a far more capable future system can use to serve a person faithfully across every surface—HUD, voice, wearable, agent—without losing the person's freedom. The central question this document protects is: *does Euda model who someone is honestly enough to help them flourish, and does that model stay theirs as both they and their agents evolve?*
