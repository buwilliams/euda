# Plugins Specification

This document specifies the plugin architecture for Euno.

## Overview

Plugins extend Euno's capabilities through CLI-based commands. Agents interact with plugins through three meta-tools rather than 80+ specialized tools:

- `list_plugins` - Discover available plugins
- `plugin_usage(plugin)` - Get help for a plugin
- `execute_plugin(plugin, command)` - Run a plugin command

## Directory Structure

```
plugins/                    # Plugin directory (project root)
├── core/                   # Core Euno functionality
│   ├── cli.py              # Typer CLI entry point
│   ├── __init__.py
│   └── commands/           # Command modules
│       ├── topics.py       # Topic management
│       ├── assets.py       # Asset operations
│       ├── memory.py       # Memory operations
│       ├── identity.py     # Identity management
│       ├── agents.py       # Agent management
│       ├── consolidate.py  # Consolidation
│       ├── dates.py        # Date utilities
│       ├── notifications.py
│       ├── quote.py
│       └── done.py
├── nextcloud/              # Nextcloud integration
│   ├── cli.py
│   └── commands/
│       ├── files.py
│       ├── calendar.py
│       └── deck.py
├── speech/                 # Text-to-speech
│   └── cli.py
└── mastodon/              # Mastodon integration
    └── cli.py

src/plugins/               # Plugin infrastructure
├── __init__.py            # Public API exports
├── discovery.py           # Scan plugins/, validate
├── executor.py            # Run CLI via subprocess
├── usage.py               # Extract --help text
├── context.py             # Build env vars
├── exceptions.py          # Plugin-specific errors
└── tools.py               # 3 meta-tools for LLM
```

## Plugin Contract

### Entry Point

Each plugin MUST have:
- A directory under `plugins/{name}/`
- A `cli.py` file with a `main()` function
- The CLI should use Typer (recommended) or argparse

### Invocation

Plugins are invoked via:
```bash
uv run euno plugin <name> <command>
```

Or directly:
```bash
python plugins/<name>/cli.py <command>
```

### Output Format

- Plain text output (LLM-friendly)
- Errors should print to stderr and exit with non-zero code
- Use exit code 0 for success

### Environment Variables

Plugins receive context through environment variables:

| Variable | Description | When Set |
|----------|-------------|----------|
| `EUNO_DATA_DIR` | Path to data/ directory | Always |
| `EUNO_AGENT_ID` | Current agent ID | When agent context exists |
| `EUNO_TOPIC_ID` | Current topic being worked | When in work cycle |
| `EUNO_SESSION_ID` | Chat session ID | During chat |

## Agent Configuration

Agents configure plugin access via `excluded_plugins` in `config.json`:

```json
{
  "id": "myagent",
  "name": "My Agent",
  "excluded_plugins": ["speech", "mastodon"]
}
```

An empty array (or omitting the key) gives access to all plugins.

## Meta-Tools

### list_plugins

Lists all available plugins (filtered by agent's excluded_plugins).

**Input:** None
**Output:**
```json
{
  "plugins": [
    {"name": "core", "description": "..."},
    {"name": "nextcloud", "description": "..."}
  ],
  "count": 2
}
```

### plugin_usage

Gets CLI help for a plugin.

**Input:** `{"plugin": "core"}`
**Output:**
```json
{
  "plugin": "core",
  "usage": "Usage: cli.py [OPTIONS] COMMAND [ARGS]..."
}
```

### execute_plugin

Executes a plugin command.

**Input:** `{"plugin": "core", "command": "topics list --status todo"}`
**Output:**
```json
{
  "success": true,
  "output": "[todo] My Topic (topic-abc123)...",
  "exit_code": 0
}
```

## Core Plugin Commands

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

### Other
- `consolidate run [--phase]`
- `dates parse <text>`
- `dates current`
- `notify send <message>`
- `notify check`
- `quote generate`
- `done [summary]`

## Creating a New Plugin

1. Create directory: `plugins/{name}/`
2. Create `cli.py`:
   ```python
   """My plugin description."""
   import typer

   app = typer.Typer(name="myplugin", help="My plugin help")

   @app.command()
   def mycommand():
       """Command description."""
       print("Output")

   def main():
       app()

   if __name__ == "__main__":
       main()
   ```
3. Plugins are auto-discovered on next invocation

## Error Handling

```python
@dataclass
class PluginResult:
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

# Plugin not found
{"error": "Plugin not found: xyz"}
```

## Timeout

Default timeout is 60 seconds per command execution.
