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

- Tools organized by type in `src/tools/{type}/`:
  - `data/` — jobs, assets, identity, memory
  - `agents/` — agent management
  - `system/` — config, dates, notifications, done_working
  - `integration/` — docs, specs, logs
- Every tool description has two parts: what it does, when to use it
- Format: `"What it does. Use when: specific scenarios."`
- All agents get base tools: list_jobs, get_job, create_job, complete_job, add_job_log, done_working

## Context Access

- Agent identity: included in system prompt (who the agent is)
- User identity: included in system prompt (who the agent serves)
- User short-term memory: `list_memory("user")` tool (what's on their mind)
- User long-term memory: `read_long_term_memory(date, "user")` tool (their history)
- Job assets: `list_assets`, `read_asset` tools
- Conversation history: included in messages array (not system prompt)

## Prompt Logging

- All prompts logged to `data/system/logs/prompts/{date}.jsonl`
- Entries include: timestamp, agent_id, model, system prompt, messages, tools
