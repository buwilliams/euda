# LLM

Rules for how agents interact with language models.

## System Prompts

- Structure: agent profile, then available tools grouped by type
- User profile and memory are NOT auto-included — reduces tokens, makes access explicit
- Agents fetch user context explicitly via `get_profile` and `list_memory` tools
- Templates stored in `data/system/prompts/` as markdown files
- Templates use Python format string syntax: `{variable_name}`

## Tools

- Tools organized by type in `src/tools/{type}/`:
  - `data/` — jobs, assets, profile, memory
  - `agents/` — agent management
  - `system/` — config, dates, notifications, done_working
  - `integration/` — docs, specs, logs
- Every tool description has two parts: what it does, when to use it
- Format: `"What it does. Use when: specific scenarios."`
- All agents get base tools: list_jobs, get_job, create_job, complete_job, add_job_log, done_working

## Context Access

- Agent profile: included in system prompt
- User profile: `get_profile("user")` tool
- Short-term memory: `list_memory(agent_id)` tool
- Long-term memory: `read_long_term_memory(date, agent_id)` tool
- Job assets: `list_assets`, `read_asset` tools
- Conversation history: included in messages array (not system prompt)

## Rate Limiting

- Global rate limiter controls LLM API call frequency
- Rolling window: max calls per time window (default 30/minute)
- Optional throttle queue for controlled pacing
- Runaway detection pauses agents making excessive calls
- Config in `data/system/config.json` under `llm.rate_limiting`
- API endpoints at `/api/rate-limiting` for monitoring and control

## Prompt Logging

- All prompts logged to `data/system/logs/prompts/{date}.jsonl`
- Entries include: timestamp, agent_id, model, system prompt, messages, tools
