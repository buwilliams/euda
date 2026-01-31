# Contributing

Build for yourself first. If it helps you flourish, it will help others too.

## Extension Hierarchy

When changing Euda, choose the lightest mechanism that achieves your goal:

### 1. Interface Changes

Modify how users interact with Euda.

#### Web UI
**Location:** `web/`

The browser-based interface—layouts, styles, interactions.

**Examples:**
- Change how topics are displayed
- Add a new view or tab
- Improve mobile responsiveness

#### CLI
**Location:** `router.py`, `src/cli/`

The command-line interface for terminal users.

**Examples:**
- Add a new command to `router.py`
- Modify the `chat` REPL experience
- Add dev CLI commands in `src/cli/`

#### Future Interfaces
**Location:** TBD

Other ways to interact with Euda (mobile apps, voice, APIs).

**Principle:** All interfaces share the same backend (AgentManager, skills, topics). Only the presentation layer differs.

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

**Example:** Create `data/agents/soul/prompts/research.md` for research task handling.

#### New Agents
**Location:** `data/agents/{new-agent}/`

Create a specialized agent for a new domain.

**When to use:** Need a new domain of expertise or different trigger/skill requirements.

**Example:** Create `data/agents/researcher/` with appropriate identity and config.

### 3. Skills
**Location:** `skills/{name}/`

Add new capabilities as CLI-based skills that agents can discover and execute.

**When to use:** Agents need to interact with external systems or perform new operations.

**Environment variables** available to skills:
- `EUNO_DATA_DIR` — Path to data directory (always set)
- `EUNO_AGENT_ID` — Current agent ID (set during agent execution)
- `EUNO_TOPIC_ID` — Current topic ID (set during topic work)
- `EUNO_SESSION_ID` — Current session ID (set during chat)

**Examples:**
- Create `skills/calendar/cli.py` for calendar integration
- Create `skills/obsidian/cli.py` for note-taking integration

See `specs/8_skills.md` for skill development guide.

### 4. Architecture Changes
**Location:** `src/`, `specs/`

Modify core systems—agent lifecycle, data schemas, APIs.

**When to use:** None of the above can achieve your goal.

**Rule of thumb:** If you're reaching for this level, ask in Discord first. There's often a lighter way.

## Your Arc

An Arc is your personal chapter of contribution. It answers: **What do I want Euda to do for me?**

**Good Arcs:**
- "I want Euda to anticipate my day so my energy feels good"
- "I want Euda to help me stay connected to people I care about"

**Too Technical:**
- "Calendar integration" (what value does it provide?)
- "Better memory system" (why do you need it?)

Stay in an Arc until it's delivering real value. Then pick another.

| Contributor | Arc |
|-------------|-----|
| Buddy | I want Euda to understand who I am and help me stay productive on what matters |
| *Your name* | *Your arc* |

## Source of Truth

Euda follows a top-down information hierarchy. When making changes, update higher levels first:

- **docs/** — most reliable understanding of Euda (what and why)
- **specs/** — technical details enforcing the docs (single-depth bullet rules)
- **tests/** — enforces the specs and docs, not the Python code
- **src/** — implementation produced from docs, specs, and tests

**Claude Code skills for maintaining consistency:**

- `/check-alignment` — Detect drift between docs, specs, tests, and code without making changes
- `/align` — After updating docs or specs, propagate changes downstream through specs, tests, and code

### Specs (Design Rules)

- [Agents](../specs/1_agents.md) — Agent behavior, triggers, work cycles
- [Data](../specs/2_data.md) — Entity schemas
- [Backend](../specs/3_backend.md) — Server, API, storage
- [UX & UI](../specs/4_ux_ui.md) — Interface patterns
- [CLI](../specs/5_cli.md) — Command-line interface
- [Skills](../specs/8_skills.md) — Skill architecture and development

## Submitting Changes

1. Create a feature branch from main
2. Make your changes
3. Review against `specs/*.md` for drift
4. Push and create PR:

```bash
git push -u origin feature/my-feature
gh pr create --title "Add my feature" --body "Description"
```

## Syncing Data

Keep local and remote in sync when developing on multiple machines or deploying to a server:

```bash
# Full sync (code + data, stops/restarts server)
euda sync                          # Deploy code + bidirectional data merge
euda sync --data-only              # Skip code sync, data only
euda sync --push                   # Local → remote only
euda sync --pull                   # Remote → local only
euda sync --dry-run                # Preview changes

# Conflict resolution
euda sync status                   # Show sync state
euda sync conflicts                # List unresolved conflicts
euda sync resolve <id> --keep-local
euda sync resolve <id> --keep-remote
```

By default, sync: (1) stops remote server, (2) syncs code, (3) syncs data, (4) restarts server.
Use `--data-only` to skip code deployment. Backups are created automatically before data sync.

**What syncs:** Source code (local → remote), topics, memory, agent configs/identities, assets

**What doesn't sync:** `.git/`, `.venv/`, `.env`, `data/system/logs/`, auth, sync state

## Community

**[Discord](https://discord.gg/5B9VdQ6vYP)** — where we meet, plan, and discuss. Come say hi!
