# Skills Specification

This document specifies the skill architecture for Euno.

## Overview

Skills extend Euno's capabilities through CLI-based commands. Agents interact with skills through three meta-tools rather than 80+ specialized tools:

- `list_skills` - Discover available skills
- `skill_usage(skill)` - Get help for a skill
- `execute_skill(skill, command)` - Run a skill command

## Directory Structure

```
src/core/                  # Business logic (shared by web UI + skills)
├── data/                  # Topics, assets, memory, identity
├── agents/                # Agent operations
├── system/                # Consolidation, notifications, dates
└── integration/           # File processing

skills/                    # Skill CLI interfaces (for LLM agents)
├── core/                  # Core skill (CLI wrappers only)
│   ├── cli.py             # Typer CLI entry point
│   └── commands/          # CLI wrappers (import from src/core/)
│       ├── topics.py      # → imports from src.core.data.topics
│       ├── assets.py      # → imports from src.core.data.assets
│       ├── memory.py      # → imports from src.core.data.memory
│       ├── identity.py    # → imports from src.core.data.identity
│       ├── agents.py      # → imports from src.core.agents
│       ├── consolidate.py # → imports from src.core.system.consolidation
│       ├── dates.py       # → imports from src.core.system.dates
│       ├── notifications.py
│       ├── quote.py
│       └── done.py
├── nextcloud/             # Self-contained external integration
│   ├── cli.py
│   └── commands/
├── speech/                # Self-contained external integration
│   └── cli.py
└── mastodon/              # Self-contained external integration
    └── cli.py

src/skills/                # Skill infrastructure
├── __init__.py            # Public API exports
├── discovery.py           # Scan skills/, validate
├── executor.py            # Run CLI via subprocess
├── usage.py               # Extract --help text
├── context.py             # Build env vars
├── exceptions.py          # Skill-specific errors
└── tools.py               # 3 meta-tools for LLM
```

### Architecture Note

The `core` skill is special: its CLI commands are thin wrappers that import business logic from `src/core/`. This allows:
- **Web UI**: Direct Python imports from `src/core/` (fast)
- **LLM Agents**: Skill CLI subprocess calls (flexible)

External skills (nextcloud, speech, mastodon) are self-contained with their own business logic.

## Skill Contract

### Entry Point

Each skill MUST have:
- A directory under `skills/{name}/`
- A `cli.py` file with a `main()` function
- The CLI should use Typer (recommended) or argparse

### Invocation

Skills are invoked via:
```bash
uv run euno skill <name> <command>
```

Or directly:
```bash
python skills/<name>/cli.py <command>
```

### Output Format

- Plain text output (LLM-friendly)
- Errors should print to stderr and exit with non-zero code
- Use exit code 0 for success

### Environment Variables

Skills receive context through environment variables:

| Variable | Description | When Set |
|----------|-------------|----------|
| `EUNO_DATA_DIR` | Path to data/ directory | Always |
| `EUNO_AGENT_ID` | Current agent ID | When agent context exists |
| `EUNO_TOPIC_ID` | Current topic being worked | When in work cycle |
| `EUNO_SESSION_ID` | Chat session ID | During chat |

## Agent Configuration

Agents configure skill access via `excluded_skills` in `config.json`:

```json
{
  "id": "myagent",
  "name": "My Agent",
  "excluded_skills": ["speech", "mastodon"]
}
```

An empty array (or omitting the key) gives access to all skills.

## Meta-Tools

### list_skills

Lists all available skills (filtered by agent's excluded_skills).

**Input:** None
**Output:**
```json
{
  "skills": [
    {"name": "core", "description": "..."},
    {"name": "nextcloud", "description": "..."}
  ],
  "count": 2
}
```

### skill_usage

Gets CLI help for a skill.

**Input:** `{"skill": "core"}`
**Output:**
```json
{
  "skill": "core",
  "usage": "Usage: cli.py [OPTIONS] COMMAND [ARGS]..."
}
```

### execute_skill

Executes a skill command.

**Input:** `{"skill": "core", "command": "topics list --status todo"}`
**Output:**
```json
{
  "success": true,
  "output": "[todo] My Topic (topic-abc123)...",
  "exit_code": 0
}
```

## Core Skill Commands

### Topics
- `topics list [--status] [--assignee] [--parent]`
- `topics get <id>`
- `topics create <name> [-d desc] [-p parent]`
- `topics update <id> [--name] [--status]`
- `topics complete <id>`
- `topics restore <id>`
- `topics archive <id>`
- `topics delete <id> [--children]`
- `topics log <id> <action>`
- `topics children <id>`
- `topics assign <id> <agent>`
- `topics unassign <id> <agent>`
- `topics claim <id>`
- `topics release <id>`
- `topics error <id> <message>`
- `topics handoff <id> <to> [--note]`

### Assets
- `assets list <topic_id>`
- `assets read <topic_id> <filename>`
- `assets write <topic_id> <filename> <content>`
- `assets delete <topic_id> <filename>`

### Memory
- `memory add <description> --type <type>`
- `memory list [--agent id]`
- `memory remove <id>`
- `memory graduate <id>`
- `memory write-long-term <content>`
- `memory recall <query>`
- `memory analyze <query>`

### Identity
- `identity show [--agent id]`
- `identity update <content>`

### Agents
- `agents list`
- `agents show <id>`
- `agents create <id> <name> <purpose>`
- `agents enable <id>`
- `agents disable <id>`
- `agents delete <id>`
- `agents tools`

### Store
- `store import <path> [--force] [--dry-run]`
- `store clear-manifest`

### Other
- `consolidate run [--phase]`
- `dates parse <text>`
- `dates current`
- `notify send <message>`
- `notify check`
- `quote generate`
- `done [summary]`

## Creating a New Skill

1. Create directory: `skills/{name}/`
2. Create `cli.py`:
   ```python
   """My skill description."""
   import typer

   app = typer.Typer(name="myskill", help="My skill help")

   @app.command()
   def mycommand():
       """Command description."""
       print("Output")

   def main():
       app()

   if __name__ == "__main__":
       main()
   ```
3. Skills are auto-discovered on next invocation

## Error Handling

```python
@dataclass
class SkillResult:
    exit_code: int
    stdout: str
    stderr: str
    success: bool
```

Meta-tool returns:
```python
# Success
{"success": True, "output": "...", "exit_code": 0}

# Failure
{"success": False, "output": "Error (exit 1): ...", "exit_code": 1}

# Skill not found
{"error": "Skill not found: xyz"}
```

## Timeout

Default timeout is 60 seconds per command execution.
