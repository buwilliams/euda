# Euno Plugin Implementation Plan

## Summary

This document outlines the complete implementation plan for replacing Euno's current tool and integration system with a unified plugin architecture. The new system simplifies the LLM interface from 82+ specialized tools to just 3 meta-tools while enabling clone-and-go extensibility.

---

## Current State

### Tools Today
- **82+ Python functions** with `@tool()` decorators in a global registry
- **In-process execution** (fast, direct memory access)
- **Tightly coupled** to agent internals (`set_agent_context()`, direct state modification)
- **Static imports** at startup, no dynamic discovery
- LLM receives tool schemas, calls them, gets results in conversation loop

### Pain Points
- Schema maintenance burden for every tool
- Adding capabilities requires Python code changes in `src/tools/`, imports, and registry updates
- No language flexibility for plugin authors
- Tight coupling makes testing difficult

---

## Target Architecture

### Core Entities
| Entity | Description |
|--------|-------------|
| **Agents** | Autonomous actors that use plugins via CLI |
| **Topics** | Work items and goals being tracked |
| **Plugins** | Self-contained capabilities with CLI interfaces |

### The Big Simplification

**Before:** LLM needs schemas for 82 specialized tools

**After:** LLM operates like a human at a terminal with 3 tools:

```python
@tool("list_plugins")
def list_plugins() -> list[str]:
    """Returns available plugin names"""

@tool("plugin_usage")
def plugin_usage(plugin: str) -> str:
    """Returns CLI help/usage for a plugin"""

@tool("execute_plugin")
def execute_plugin(plugin: str, command: str) -> str:
    """Executes a plugin command with arguments"""
```

### LLM Workflow
1. "What plugins do I have?" → `list_plugins()`
2. "How do I use nextcloud?" → `plugin_usage("nextcloud")`
3. "List my calendar events" → `execute_plugin("nextcloud", "calendar list --calendar personal")`

---

## Design Decisions

### 1. Command Structure
**Decision:** Unified entry point

```bash
euno plugin <plugin_name> <command> [args]
euno plugin core topics list --status todo
euno plugin nextcloud calendar list --calendar personal
```

### 2. execute_plugin Signature
**Decision:** Raw string (LLM builds CLI string)

```python
execute_plugin("nextcloud", "calendar list --calendar personal --limit 10")
```

Rationale: Simpler for the LLM—it just writes a command like a human would.

### 3. Plugin Usage Format
**Decision:** Raw `--help` text (simpler for plugin authors)

```
Usage: euno plugin nextcloud calendar <command>

Commands:
  list      List calendar events
  create    Create a new event
  delete    Delete an event

Options:
  --calendar TEXT   Calendar name [default: personal]
  --limit INT       Max events to return
```

### 4. Core Plugin Scope
**Decision:** Core plugin encompasses entire current `src/tools/data/` + `src/tools/system/`

| Current Tool | Proposed Location |
|-------------|-------------------|
| create_topic, list_topics | Core plugin |
| get_memory, add_memory | Core plugin |
| nc_list_files, nc_create_event | Nextcloud plugin |
| speak_aloud | Speech plugin |
| get_mastodon_posts | Mastodon plugin |

### 5. Sync vs Async
**Decision:** Blocking execution (leverage multiple agents for parallelism)

### 6. CLI Framework
**Decision:** Typer for core plugin; external plugins can use whatever they want (as long as `--help` works)

### 7. Plugin Entry Point Convention
**Decision:** `plugins/<name>/cli.py` with `main()`

```python
# Euno executes:
subprocess.run(["python", "plugins/<name>/cli.py", ...])
```

### 8. Output Format
**Decision:** Plain text (default) — good for LLM consumption

```
ID: abc123
Title: Fix the bug
Status: todo
```

### 9. Integration with euno CLI
**Decision:** Integrated into existing CLI (move old commands to `plugins/core`)

```bash
uv run euno plugin core topics list
uv run euno plugin nextcloud calendar list
```

### 10. Plugin Dependencies
**Decision:** Shared environment — external plugins list deps in `requirements.txt` installed into main env

### 11. Plugin Discovery
**Decision:** Replace `tools[]` with `excluded_plugins[]` in agent configs — all plugins available by default

---

## Environment Contract

Euno sets these environment variables before plugin execution:

```bash
EUNO_DATA_DIR=/path/to/data
EUNO_AGENT_ID=chat
EUNO_PLUGINS_DIR=/path/to/plugins
EUNO_TOPICS_DB=/path/to/data/topics/db.sqlite
```

Plugins read from environment to get context without CLI argument pollution.

---

## Directory Structure

### Final State

```
euno/
├── src/
│   ├── manager.py           # Boots agents, event bus, discovers plugins
│   ├── agent/
│   │   └── agent.py         # Uses simplified tool interface
│   ├── plugins/             # Plugin execution layer (NEW)
│   │   ├── __init__.py
│   │   ├── discovery.py     # list_plugins() - scans plugins/
│   │   ├── executor.py      # execute_plugin() - runs CLI, captures output
│   │   ├── usage.py         # plugin_usage() - runs --help, returns text
│   │   └── tools.py         # The 3 LLM meta-tools
│   ├── eventbus/
│   ├── llms/
│   └── topics/
│
├── plugins/                 # Plugin directory (NEW)
│   ├── core/                # Euno's built-in capabilities
│   │   ├── cli.py           # Main entry point (Typer)
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── topics.py
│   │       ├── assets.py
│   │       ├── memory.py
│   │       ├── identity.py
│   │       ├── agents.py
│   │       ├── consolidate.py
│   │       ├── notifications.py
│   │       ├── dates.py
│   │       └── quote.py
│   ├── nextcloud/
│   │   ├── cli.py
│   │   └── commands/
│   ├── speech/
│   │   └── cli.py
│   └── mastodon/
│       └── cli.py
│
├── data/
│   └── agents/
│       └── {agent}/
│           └── config.json  # Now uses excluded_plugins[]
└── docs/
```

---

## Core Plugin Commands

```bash
# Topics
euno plugin core topics list [--status STATUS] [--parent PARENT_ID]
euno plugin core topics create --title TITLE [--description DESC]
euno plugin core topics update ID [--status STATUS] [--title TITLE]
euno plugin core topics complete ID

# Memory
euno plugin core memory list [--type TYPE] [--agent AGENT]
euno plugin core memory add --type TYPE --content CONTENT
euno plugin core memory delete ID

# Identity
euno plugin core identity show [--agent AGENT]
euno plugin core identity update --section SECTION --content CONTENT

# Assets
euno plugin core assets list [--path PATH]
euno plugin core assets read PATH
euno plugin core assets write PATH --content CONTENT
euno plugin core assets delete PATH

# Consolidation
euno plugin core consolidate [--phase append|consolidate|both]

# Agents
euno plugin core agents list
euno plugin core agents show AGENT_ID

# Utilities
euno plugin core dates now [--format FORMAT]
euno plugin core dates relative DESCRIPTION
euno plugin core quote random
euno plugin core notifications send --message MESSAGE
```

---

## Implementation Phases

### Phase 1: Foundation
**Goal:** Create plugin infrastructure and prove the concept

#### 1.1 Create Plugin Infrastructure in src/

```
src/plugins/
├── __init__.py
├── discovery.py    # Scan plugins/, return names
├── executor.py     # Run CLI, capture output
├── usage.py        # Run --help, return text
└── tools.py        # The 3 LLM tools
```

**Tasks:**
- [ ] Create `src/plugins/__init__.py`
- [ ] Implement `src/plugins/discovery.py`
  - [ ] `list_plugins()` function that scans `plugins/` directory
  - [ ] Filter out `__pycache__`, hidden directories
  - [ ] Return list of plugin names
- [ ] Implement `src/plugins/executor.py`
  - [ ] `execute_plugin(plugin: str, command: str) -> str`
  - [ ] Set environment variables (EUNO_DATA_DIR, EUNO_AGENT_ID, etc.)
  - [ ] Run subprocess with `python plugins/<name>/cli.py <command>`
  - [ ] Capture stdout/stderr
  - [ ] Handle timeouts and errors gracefully
- [ ] Implement `src/plugins/usage.py`
  - [ ] `plugin_usage(plugin: str) -> str`
  - [ ] Run `python plugins/<name>/cli.py --help`
  - [ ] Return help text
- [ ] Implement `src/plugins/tools.py`
  - [ ] `@tool("list_plugins")` wrapper
  - [ ] `@tool("plugin_usage")` wrapper
  - [ ] `@tool("execute_plugin")` wrapper

#### 1.2 Create Core Plugin Skeleton

```
plugins/
└── core/
    ├── cli.py
    └── commands/
        └── __init__.py
```

**Tasks:**
- [ ] Create `plugins/` directory at project root
- [ ] Create `plugins/core/` directory
- [ ] Create `plugins/core/cli.py` with Typer app
  - [ ] Set up main Typer app
  - [ ] Add subcommand groups (topics, memory, identity, etc.)
  - [ ] Implement `--help` at all levels
- [ ] Create `plugins/core/commands/__init__.py`

#### 1.3 Implement Proof of Concept (Topics)

**Tasks:**
- [ ] Create `plugins/core/commands/topics.py`
  - [ ] `list` command with `--status` and `--parent` options
  - [ ] `create` command with `--title` and `--description`
  - [ ] `update` command
  - [ ] `complete` command
- [ ] Wire topics commands into `cli.py`
- [ ] Test end-to-end: `uv run euno plugin core topics list`

#### 1.4 Integrate into Main CLI

**Tasks:**
- [ ] Add `plugin` subcommand to `main.py`
- [ ] Route to appropriate plugin CLI
- [ ] Test: `uv run euno plugin core topics list`

---

### Phase 2: Core Plugin (Full Migration)
**Goal:** Migrate all data and system tools to core plugin

#### 2.1 Migrate src/tools/data/

| Source File | Target | Commands |
|-------------|--------|----------|
| `topics.py` (22 tools) | `commands/topics.py` | list, create, update, complete, delete, etc. |
| `assets.py` (4 tools) | `commands/assets.py` | list, read, write, delete |
| `memory.py` (7 tools) | `commands/memory.py` | list, add, delete |
| `identity.py` (4 tools) | `commands/identity.py` | show, update |

**Tasks:**
- [ ] Complete `plugins/core/commands/topics.py`
  - [ ] Migrate all 22 topic-related tools
  - [ ] Ensure output format is LLM-friendly plain text
- [ ] Create `plugins/core/commands/assets.py`
  - [ ] `list [--path PATH]`
  - [ ] `read PATH`
  - [ ] `write PATH --content CONTENT`
  - [ ] `delete PATH`
- [ ] Create `plugins/core/commands/memory.py`
  - [ ] `list [--type TYPE] [--agent AGENT]`
  - [ ] `add --type TYPE --content CONTENT`
  - [ ] `delete ID`
- [ ] Create `plugins/core/commands/identity.py`
  - [ ] `show [--agent AGENT]`
  - [ ] `update --section SECTION --content CONTENT`

#### 2.2 Migrate src/tools/system/

| Source File | Target | Commands |
|-------------|--------|----------|
| `system.py` | `commands/agents.py` | list, show |
| `system.py` | `commands/notifications.py` | send |
| `dates.py` | `commands/dates.py` | now, relative |
| `quote.py` | `commands/quote.py` | random |
| `consolidation/` | `commands/consolidate.py` | (phases) |

**Tasks:**
- [ ] Create `plugins/core/commands/agents.py`
  - [ ] `list`
  - [ ] `show AGENT_ID`
- [ ] Create `plugins/core/commands/notifications.py`
  - [ ] `send --message MESSAGE`
- [ ] Create `plugins/core/commands/dates.py`
  - [ ] `now [--format FORMAT]`
  - [ ] `relative DESCRIPTION`
- [ ] Create `plugins/core/commands/quote.py`
  - [ ] `random`
- [ ] Create `plugins/core/commands/consolidate.py`
  - [ ] `run [--phase append|consolidate|both]`
  - [ ] Migrate consolidation logic

---

### Phase 3: Integration Plugins
**Goal:** Extract integrations into standalone plugins

#### 3.1 Nextcloud Plugin

```
plugins/nextcloud/
├── cli.py
└── commands/
    ├── files.py
    ├── calendar.py
    └── tasks.py
```

**Tasks:**
- [ ] Create `plugins/nextcloud/` directory
- [ ] Create `plugins/nextcloud/cli.py` with Typer app
- [ ] Create `plugins/nextcloud/commands/files.py`
  - [ ] `list PATH`
  - [ ] `read PATH`
  - [ ] `write PATH --content CONTENT`
  - [ ] `delete PATH`
  - [ ] `search QUERY`
- [ ] Create `plugins/nextcloud/commands/calendar.py`
  - [ ] `list [--calendar NAME] [--limit N]`
  - [ ] `create --title TITLE --start START [--end END]`
  - [ ] `delete EVENT_ID`
- [ ] Create `plugins/nextcloud/commands/tasks.py`
  - [ ] Migrate task-related functionality
- [ ] Migrate authentication/connection logic

#### 3.2 Speech Plugin

```
plugins/speech/
└── cli.py
```

**Tasks:**
- [ ] Create `plugins/speech/` directory
- [ ] Create `plugins/speech/cli.py`
  - [ ] `speak TEXT [--voice VOICE]`
  - [ ] `voices` (list available voices)
- [ ] Migrate TTS logic

#### 3.3 Mastodon Plugin

```
plugins/mastodon/
└── cli.py
```

**Tasks:**
- [ ] Create `plugins/mastodon/` directory
- [ ] Create `plugins/mastodon/cli.py`
  - [ ] `timeline [--limit N]`
  - [ ] `post --content CONTENT`
  - [ ] `notifications`
- [ ] Migrate Mastodon API logic

---

### Phase 4: Agent Updates
**Goal:** Update agents to use new plugin system

#### 4.1 Update Agent Configs

**Before:**
```json
{
  "name": "chat",
  "tools": ["list_topics", "create_topic", "nc_list_files"]
}
```

**After:**
```json
{
  "name": "chat",
  "excluded_plugins": []
}
```

**Tasks:**
- [ ] Update all agent configs in `data/agents/*/config.json`
  - [ ] Replace `tools[]` with `excluded_plugins[]`
  - [ ] Default to empty array (all plugins available)
- [ ] Create JSON schema for new config format
- [ ] Update config validation logic

#### 4.2 Update Agent Implementation

**Tasks:**
- [ ] Modify `src/agent/agent.py`
  - [ ] Remove old tool loading logic
  - [ ] Import new tools from `src/plugins/tools.py`
  - [ ] Update tool execution to use plugin system
- [ ] Update LLM tool schema generation
  - [ ] Only include the 3 meta-tools
- [ ] Handle `excluded_plugins` filtering in `list_plugins()`

#### 4.3 Update Manager

**Tasks:**
- [ ] Modify `src/manager.py`
  - [ ] Add plugin discovery at startup
  - [ ] Validate plugin directory structure
  - [ ] Log available plugins
- [ ] Consider plugin health checks (optional)

---

### Phase 5: Cleanup
**Goal:** Remove legacy code and update documentation

#### 5.1 Remove Old Tools Infrastructure

**Tasks:**
- [ ] Archive `src/tools/` to `src/tools_legacy/` (temporary)
- [ ] Remove `@tool` decorator system from `src/llms/tools/`
- [ ] Remove tool registry code
- [ ] Remove `set_agent_context()` and related coupling
- [ ] After validation period, delete `src/tools_legacy/`

#### 5.2 Update Documentation

**Tasks:**
- [ ] Update `CLAUDE.md` with new architecture
- [ ] Update `docs/4_system.md`
  - [ ] New plugin system overview
  - [ ] How plugins work
  - [ ] How to create a plugin
- [ ] Update `specs/1_agents.md`
  - [ ] New config format
  - [ ] How agents use plugins
- [ ] Update `specs/2_data.md`
  - [ ] Remove tools documentation
  - [ ] Add plugin documentation
- [ ] Create `specs/X_plugins.md` (new)
  - [ ] Plugin architecture
  - [ ] Creating a plugin guide
  - [ ] CLI conventions
  - [ ] Environment variables
  - [ ] Best practices

#### 5.3 Create Plugin Development Guide

**Tasks:**
- [ ] Write `plugins/README.md`
  - [ ] How to create a new plugin
  - [ ] Required file structure
  - [ ] CLI conventions
  - [ ] How to test plugins
- [ ] Create `plugins/template/` example plugin
  - [ ] Minimal working plugin
  - [ ] Example commands
  - [ ] Comments explaining structure

---

## Testing Strategy

### Unit Tests

- [ ] `test_discovery.py` - Plugin discovery
- [ ] `test_executor.py` - CLI execution, error handling
- [ ] `test_usage.py` - Help text retrieval
- [ ] `test_tools.py` - LLM tool wrappers

### Integration Tests

- [ ] Test full flow: list → usage → execute
- [ ] Test environment variable passing
- [ ] Test error scenarios (missing plugin, CLI crash, timeout)
- [ ] Test excluded_plugins filtering

### Plugin Tests

- [ ] Each plugin should have its own test suite
- [ ] Test CLI commands directly
- [ ] Test output format consistency

---

## Migration Checklist

### Pre-Migration
- [ ] Document all current tools and their usage patterns
- [ ] Identify any tools with special requirements
- [ ] Create rollback plan

### During Migration
- [ ] Keep old system operational during transition
- [ ] Migrate one plugin category at a time
- [ ] Test each migration thoroughly before proceeding

### Post-Migration
- [ ] Monitor for issues in production
- [ ] Gather feedback on new system
- [ ] Archive and remove legacy code

---

## Benefits Recap

| Benefit | Description |
|---------|-------------|
| **Clone-and-go extensibility** | `git clone <plugin-repo> plugins/myplugin` — done |
| **Language agnostic** | Plugins can be written in any language |
| **Clear boundaries** | CLI forces clean interfaces |
| **Testable isolation** | Each plugin testable independently |
| **Self-documenting** | CLI `--help` as documentation |
| **Simplified LLM interface** | 82 tools → 3 meta-tools |
| **Reduced maintenance** | No schema maintenance burden |

---

## Open Questions / Future Considerations

1. **Plugin versioning** - How to handle plugin updates?
2. **Plugin marketplace** - Central registry of available plugins?
3. **Plugin configuration** - Per-plugin config files?
4. **Async execution** - If needed later, how to add?
5. **Plugin sandboxing** - Security for untrusted plugins?

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Foundation | 2-3 days | None |
| Phase 2: Core Plugin | 3-5 days | Phase 1 |
| Phase 3: Integration Plugins | 2-3 days | Phase 1 |
| Phase 4: Agent Updates | 1-2 days | Phases 2, 3 |
| Phase 5: Cleanup | 1-2 days | Phase 4 |

**Total: ~10-15 days**

---

## Getting Started

Begin with Phase 1.1:

```bash
# Create plugin infrastructure
mkdir -p src/plugins
touch src/plugins/__init__.py
touch src/plugins/discovery.py
touch src/plugins/executor.py
touch src/plugins/usage.py
touch src/plugins/tools.py

# Create core plugin skeleton
mkdir -p plugins/core/commands
touch plugins/core/cli.py
touch plugins/core/commands/__init__.py
touch plugins/core/commands/topics.py
```

Then implement discovery → executor → tools → proof of concept with topics.
