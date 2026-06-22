# Table of Contents

- [Design](01-design.md)
- Foundation
  - [Identity](02-foundation/01-identity.md)
  - [Agent](02-foundation/02-agent.md)
  - [Memory](02-foundation/03-memory.md)
  - [Topic](02-foundation/04-topic.md)
- Capabilities
  - [Cognition](03-capabilities/01-cognition.md)
  - [Metacognition (Self-Regulation)](03-capabilities/02-metacognition.md)
  - [Consolidation (Self-Improvement)](03-capabilities/03-consolidation.md)
  - [Skills](03-capabilities/04-skills.md)
  - Personas
    - [Overview](03-capabilities/05-personas/00-overview.md)
    - [Soul](03-capabilities/05-personas/01-soul.md)
    - [Curator](03-capabilities/05-personas/02-curator.md)
    - [Explorer](03-capabilities/05-personas/03-explorer.md)
  - [Triggers](03-capabilities/06-triggers.md)
- Surfaces
  - [Surface Principles](04-surfaces/01-surface-principles.md)
  - [Focus](04-surfaces/02-focus.md)
  - [Chat](04-surfaces/03-chat.md)
  - [CLI](04-surfaces/04-cli.md)
  - [Web](04-surfaces/05-web.md)
  - [API](04-surfaces/06-api.md)
  - [Agent](04-surfaces/07-agent.md)

## Key Ideas

- **Intent Over Implementation**: these documents explain why Euda exists, why each part exists, and what outcomes each part must preserve.
- **Table Of Contents As Design**: the file layout should make the system understandable before any file is opened.
- **Consistent Vocabulary**: use the same words for the same concepts across every document—identity, agent, memory, topic, persona, surface.
- **Purpose First**: describe each part by its purpose, expected role, and future direction before naming implementation details.
- **Implementation As Evidence**: include technical detail only when it explains or protects intent.
- **Future AI Readers**: write so that stronger future agents can preserve the design even when they change the code.

## Purpose

The intent folder is the durable explanation of Euda's design. It is not a changelog, an implementation manual, or marketing. It is where the system states what it is trying to become and what must remain true as the implementation changes.

Euda is a personal intelligence for human flourishing—*eudaimonia*. It learns who a person is and manages their attention so the logistics of life fall away, creating space for meaning, discovery, and growth. These documents should help people and agents understand the product from the inside out:

- what Euda believes about a person and their flourishing,
- what each system area is responsible for,
- why each feature exists,
- what outcomes the feature should create,
- what future versions should preserve or improve.

## Two Branches, One Intent

These documents intentionally draw on both branches of Euda's history, because each protects a different part of the design:

- **`v1`** (originally named *Euno*) carries the conceptual core: identity modeling, the non-distinction between human and AI agents, *Focus* as managed attention, background personas, topics as the coordination hub, and consolidation as the engine that learns a person.
- **`main`** carries the architectural rewrite that makes the **CLI a first-class surface**: every capability becomes a small, self-contained command, and capabilities compose by calling one another.

The intent did not change between them; the substrate did. Where the two eras differ, the documents say so and explain why the change serves the same purpose.

## Document Shape

Each feature document generally uses this shape:

- **Key Ideas**: the small set of principles that define the part.
- **Purpose**: why it exists.
- **Expected Role**: how it contributes to the whole system.
- **Future Direction**: how it should evolve as Euda and AI agents improve.

Sections may be adapted when a topic needs a different shape, but the document should still answer the same questions.

## Organization

The root document, `01-design.md`, explains the whole-system design and the architectural port from `v1` to `main`.

The remaining documents are organized by system level:

- **Foundation**: the durable concepts Euda depends on—identity, agent, memory, topic.
- **Capabilities**: the active powers—cognition, consolidation, skills, personas, triggers.
- **Surfaces**: the ways people and agents interact—Focus, chat, CLI, web, API, and agent-native.

Each section should be discrete enough to read on its own and connected enough to make the whole system easier to understand.

## Writing Rules

- Lead with key ideas.
- Use consistent vocabulary.
- Explain features by purpose, expected role, and future direction.
- Avoid implementation detail unless it matters to the intent.
- Prefer plain language over framework language.
- Keep the writing compact enough that the structure stays visible.
- Preserve the product philosophy even when describing technical tradeoffs.

## Implementation Detail

Implementation details belong in these documents when they explain a product decision. Flat files, versioned identities, JSONL logs, a small topic database, and the CLI-first composition on `main` matter because they serve the intent: local ownership, inspectability, honest evolution of identity, surface independence, and agent readability.

Implementation details do not belong here when they only describe how the current code happens to be arranged. Those details should live closer to the code unless they protect an intentional design choice.
