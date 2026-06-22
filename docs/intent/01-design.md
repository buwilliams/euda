# Design

## Key Ideas

- **Personal Intelligence For Flourishing**: Euda exists to help a person grow into who they're meant to be, not to optimize their output. Productivity is a means; eudaimonia—human flourishing—is the end.
- **Identity Is The Magic**: the system's most important model is identity. Euda represents preferences, values, voice, and even ideology as a durable, evolving identity. Everything else serves the fidelity of that model.
- **No Distinction Between Agents**: Euda makes no categorical distinction between a human "agent" and an AI agent. All agents have identity, memory, cognition, and behavior. The user is an agent too, with a different interface. All agents evolve uniquely, together.
- **Agent = Identity + Cognition + Memory + Behavior**: this formula defines every actor in the system, human or AI.
- **Managed Attention Is Freedom**: the life problem Euda solves is cognitive overload, distraction, and algorithmic capture. Euda manages attention so people have freedom—freedom for what matters.
- **Focus Over Chat (Human Surface)**: for people, the first-class interface is *Focus*—a curated view of what matters now—not a chat box. Chat is one input, not the product.
- **CLI First (Agent Surface)**: for agents and composition, the first-class surface is the CLI. Every capability is a self-contained command an agent or person can call, and capabilities compose by calling each other.
- **Topics Coordinate Everyone**: a *topic* is the unit of work and the only coordination channel between agents. Agents assign work to AI agents or to human agents through topics, which makes the system a coordination hub rather than a chatbot.
- **Background Over Noise**: agents work in the background with distinct concerns. They curate, explore, and consolidate without interrupting. Euda guards attention by default.
- **Safety And Surprise**: 90% security, 10% surprise. Walls of safety ground a person in their values; bridges to the unfamiliar keep them out of an echo chamber.
- **Mitigation Greater Than Prevention**: power tools plus guardrails, audit trails, and reversibility—not capability denial—keep the system safe.
- **A Platform, Not A UI**: the screen is one surface. Euda is meant to live wherever a person does—HUDs, voice in wearables, smart devices, agents. The UI is a convenience over shared capability.

## System

Euda is built from three system levels. They map to the familiar concerns of interaction, action, and durable state, but Euda names them by product intent:

- **Foundation** is the durable conceptual base: identity, agent, memory, and topic. These are the concepts every surface and capability must preserve.
- **Capabilities** are the active powers: cognition (reasoning and metacognition), consolidation (how Euda learns a person), skills, personas, and triggers.
- **Surfaces** are the ways people and agents interact with those capabilities: Focus, chat, CLI, web, API, and agent-native.

State and storage belong to the foundation because flat files, versioned identities, JSONL logs, and a small topic database are not incidental—they protect local ownership, inspectability, evolution, and agent readability.

### Surfaces Are Plural

A system can have many interfaces: web, desktop, CLI, API, voice, agent-native, and more arriving every month. Euda should not depend on any one of them. The base surface for agents and composition is the CLI; the base surface for people today is Focus in the browser. Both call into the same capabilities.

## Foundation, Capabilities, And Surfaces

- The **foundation** should remain small and stable. It defines the concepts future agents must preserve: identity, agent, memory, topic, and the lifecycle that connects them. These should be simple enough for a person to explain and structured enough for an agent to operate on without guessing.
- The **capabilities** should be shared. Cognition, consolidation, skills, personas, and triggers are durable powers, not properties of one screen or command. Every surface should call into them rather than reimplementing them.
- The **surfaces** should be replaceable. Focus, chat, web, CLI, voice, and agent-native interfaces will evolve quickly. Euda treats them as adapters over the same model and capabilities so a new surface can appear without changing what work or identity means.

## Intended Outcome

Euda should become the personal intelligence layer through which a person interacts with technology in daily life. It should learn who someone is, manage their attention so logistics fall away, and create space for meaning, discovery, and growth.

If future AI systems find better internal designs, they should still preserve the product intent:

- a person is modeled as an agent, with the same dignity and structure as any AI agent;
- identity is discovered from lived evidence, not configured, and is allowed to evolve;
- attention is guarded—curated, batched, and quiet by default;
- work and coordination flow through understandable topics;
- state is durable, inspectable, and owned by the person;
- surfaces are conveniences over shared capability;
- safety comes from mitigation, reversibility, and audit trails rather than capability denial.

## Design Pressure

Euda should resist becoming a productivity tool by default. Inbox-zero and optimized calendars are table stakes; the deeper question is *now that the logistics are handled, what do you actually want to do with your life?* The first design pressure is flourishing, not throughput.

Euda should also resist becoming a UI-shaped system. The browser and Focus matter because they make the product accessible, but the core should be understandable and operable by agents directly. As AI improves, the highest-value surface may be an agent reading the intent docs, inspecting the flat files, and operating the CLI—no human-style screen required.

Finally, Euda should resist a categorical split between human and machine. The moment the system treats the user as "the human" and everything else as "the AI," it loses its central idea: that both are modeled the same way, learn through the same mechanisms, and grow together.

## Architecture Direction

Euda has two named architectural eras, both preserved in the documentation because each protects a different part of the intent.

### Version 1 (the `v1` branch, originally named "Euno")

Version 1 is a single FastAPI web application. Business logic lives in `src/core/`; the browser and API import it directly, and skills are CLI wrappers that shell into the same logic. The agent runtime (`src/agent/`) runs autonomous work cycles as background threads inside the server. The first-class surface is *Focus*: a curated, mobile-first browser view that a person opens to see what matters now. Skills are reached through three meta-tools (`list_skills`, `skill_usage`, `execute_skill`).

Version 1's gift to the project is the conceptual core: identity modeling, the non-distinction between agents, Focus as managed attention, background personas, topics as the coordination hub, and consolidation as the engine that learns a person.

### The Port To CLI-First (the `main` branch)

The `main` branch is a deliberate rewrite that makes the **CLI a first-class surface**. The intent did not change; the substrate did. Instead of one server owning all logic, every capability becomes a small, self-contained CLI application:

- Each capability—`agents`, `chat`, `identity`, `llm`, `logs`, `memory`, `topics`, `web`—is an independent app under `core/`, with its own `pyproject.toml`, dependencies, config, and tests.
- A dynamic router (`router.py`, exposed as the `euda` command) discovers apps and dispatches to them with `uv run --project <app>`. It also provides `list`, `help`, `info`, `search`, and `last`.
- Apps compose by calling each other as subprocesses through `shared-router.py` (`run_core`, `run_cli`, `run_cli_json`). For example, the agent runner builds its system prompt by calling `identity id read <name>` and loads provider settings by calling `llm config cat-full`.
- Agents operate Euda *through the same CLI a person would use*. Their entire tool surface is three commands—`list_apps`, `app_usage`, `execute_command`—so an agent acting and a person typing share one interface.
- The web app becomes one capability among equals (`core/web`) rather than the system's center.

This is a Unix-philosophy, composition-first design (similar in spirit to OpenClaw): small programs that do one thing, speak text and JSON, and call one another. It serves the intent directly:

- a single CLI surface for both people and agents removes the special "AI-only" path;
- self-contained apps keep capabilities inspectable, independently testable, and replaceable;
- subprocess composition keeps coordination explicit and observable;
- text and JSON keep state readable by humans and agents alike;
- versioned identities and JSONL logs keep evolution and audit durable.

These choices are not sacred on their own. They matter because they protect local ownership, surface independence, agent readability, and the freedom to swap any single program without rewriting the system. The intent—personal intelligence for human flourishing, identity at the center, no distinction between agents—must survive any future substrate.
