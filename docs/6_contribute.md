# Contributing

Build for yourself first. If it helps you flourish, it will help others too.

## Extension Hierarchy

When changing Euno, choose the lightest mechanism that achieves your goal:

### 1. UI Changes
**Location:** `web/`

Modify the web interface—layouts, styles, interactions.

**Examples:**
- Change how topics are displayed
- Add a new view or tab
- Improve mobile responsiveness

### 2. Agent Changes

Agent behavior changes, from lightest to heaviest:

#### Identity Changes
**Location:** `data/agents/{id}/identity.md`

Change an agent's persona, values, or behavioral rules.

**When to use:** Agent responds in a way you don't like, should prioritize differently, or needs new constraints.

**Example:** Add to identity: "I must not: Turn every musing into an action item."

#### Prompt Changes
**Location:** `data/agents/{id}/prompts/` or `data/system/prompts/`

Change how agents handle specific situations.

**When to use:** Specific workflow needs different handling or detailed instructions.

**Example:** Create `data/agents/worker/prompts/research.md` for research task handling.

#### Tool Additions
**Location:** `src/tools/`

Add new capabilities agents can invoke.

**When to use:** Agents need to interact with external systems or perform new operations.

**Example:** Create `src/tools/integration/calendar.py` with `@tool` decorator.

#### New Agents
**Location:** `data/agents/{new-agent}/`

Create a specialized agent for a new domain.

**When to use:** Need a new domain of expertise or different trigger/tool requirements.

**Example:** Create `data/agents/researcher/` with appropriate identity and config.

### 3. Integrations
**Location:** `src/tools/integration/`

Connect Euno to external services—calendars, task managers, APIs, MCP servers.

**Examples:**
- Calendar sync (Google, Apple, Nextcloud)
- Note-taking apps (Obsidian, Notion)
- Communication tools (email, Slack)

### 4. Architecture Changes
**Location:** `src/`, `specs/`

Modify core systems—agent lifecycle, data schemas, APIs.

**When to use:** None of the above can achieve your goal.

**Rule of thumb:** If you're reaching for this level, ask in Discord first. There's often a lighter way.

## Your Arc

An Arc is your personal chapter of contribution. It answers: **What do I want Euno to do for me?**

**Good Arcs:**
- "I want Euno to anticipate my day so my energy feels good"
- "I want Euno to help me stay connected to people I care about"

**Too Technical:**
- "Calendar integration" (what value does it provide?)
- "Better memory system" (why do you need it?)

Stay in an Arc until it's delivering real value. Then pick another.

| Contributor | Arc |
|-------------|-----|
| Buddy | I want Euno to understand who I am and help me stay productive on what matters |
| *Your name* | *Your arc* |

## Submitting Changes

1. Create a feature branch from main
2. Make your changes
3. Review against `specs/*.md` for drift
4. Push and create PR:

```bash
git push -u origin feature/my-feature
gh pr create --title "Add my feature" --body "Description"
```

### Specs (Design Rules)

The `specs/` directory defines how Euno works. Before merging, check for implementation drift:

- [Agents](../specs/1_agents.md) — Agent behavior, triggers, work cycles
- [Data](../specs/2_data.md) — Entity schemas
- [Backend](../specs/3_backend.md) — Server, API, storage
- [UX & UI](../specs/4_ux_ui.md) — Interface patterns
- [CLI](../specs/5_cli.md) — Command-line interface

## Community

**[Discord](https://discord.gg/5B9VdQ6vYP)** — where we meet, plan, and discuss. Come say hi!
