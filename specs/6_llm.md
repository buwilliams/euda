# LLM

Rules for how agents interact with language models.

## System Prompts

- Structure: agent identity, user identity, then available tools grouped by type
- Agent's identity (from `identity.md`) defines who the agent is
- User's identity (from `data/agents/user/identity.md`) is auto-included so agents can anticipate needs
- User memory is NOT auto-included — agents fetch specifics via `list_memory` tool when needed
- Templates stored in `data/system/prompts/` as markdown files
- Templates use Python format string syntax: `{variable_name}`

## Tools

Agents interact with Euno through **plugins** using three meta-tools:
- `list_plugins` — Discover available plugins
- `plugin_usage(plugin)` — Get help for a plugin
- `execute_plugin(plugin, command)` — Run a plugin command

Business logic is organized in `src/core/`:
  - `data/` — topics, assets, identity, memory
  - `agents/` — agent management
  - `system/` — config, dates, notifications, consolidation
  - `integration/` — file processing

Plugin CLI commands in `plugins/core/commands/` are thin wrappers that import from `src/core/`.

See `specs/8_plugins.md` for full plugin documentation.

## Context Access

- Agent identity: included in system prompt (who the agent is)
- User identity: included in system prompt (who the agent serves)
- User short-term memory: `list_memory("user")` tool (what's on their mind)
- User long-term memory: `read_long_term_memory(date, "user")` tool (their history)
- Topic assets: `list_assets`, `read_asset` tools
- Conversation history: included in messages array (not system prompt)

## Prompt Logging

- All prompts logged to `data/system/logs/prompts/{date}.jsonl`
- Entries include: timestamp, agent_id, model, system prompt, messages, tools
