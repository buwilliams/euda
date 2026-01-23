# Dev CLI

Rules for the developer experience CLI (`python main.py dev`).

## Purpose

- Debugging and improving agent internals from the command line
- Bypassing typical workflow to run specific phases in isolation
- Streaming output for real-time visibility into agent execution
- Machine-readable output for integration with Claude Code

## Entry Point

- `python main.py dev <subcommand> [args]`
- Global `--json` flag outputs JSON lines instead of human-readable text
- Unknown subcommands show help and exit with code 1

## Output Modes

- **Human-readable (default)**: Colored, timestamped, scannable terminal output
- **JSON mode (`--json`)**: One JSON object per line, suitable for piping and parsing
- All commands support both modes

## Event Streaming

- Execution commands stream events in real-time as they happen
- Events include: chat_start, llm_response, tool_call, tool_result, work_cycle_end, append_complete, etc.
- Agent class accepts optional `event_sink` callback for streaming
- Events are emitted in addition to normal logging (not instead of)

## Job Execution

- `dev job <agent> <task>` — Create job assigned to agent, run immediately
- `dev run <agent> <job_id>` — Run existing job
- Creates standalone Agent instance (not managed by AgentManager)
- Runs `work_cycle_sync()` directly, bypassing polling
- Flags:
  - `--no-reflect` — Skip reflection append after execution
  - `--dry-run` — Show prompt without executing
  - `--max-iterations N` — Override work cycle iteration limit

## Reflection

- `dev reflect <agent>` — Run full reflection (append + consolidate)
- `--append` — Run only append phase (extract from recent conversation)
- `--consolidate` — Run only consolidate phase (graduate memories, update identity)
- Append phase requires recent conversation; reads from session file
- Consolidate phase can run independently anytime

## Memory Commands

- `dev memory <agent>` — Show all memory (short-term + recent long-term)
- `--short` — Show only short-term memory
- `--long` — Show only long-term memory (last 7 days)
- `--add <type> <description>` — Manually add memory entry
- `--graduate <id>` — Manually graduate memory to long-term
- Valid types: person, place, thing, goal, concern, idea, learning, behavior

## Identity Commands

- `dev identity <agent>` — Show agent's current identity
- `--history` — Show historical identity snapshots if they exist

## Tool Commands

- `dev tool <name> [json_input]` — Execute tool directly with JSON input
- `dev tools` — List all available tools with their schemas
- Executes in isolation without agent context
- Useful for testing tool behavior

## Prompt Commands

- `dev prompt <agent> job <job_id>` — Show prompt that would be generated for job
- `dev prompt <agent> reflect` — Show reflection prompt
- `dev prompt <agent> system` — Show system prompt (identity + tools)
- Read-only inspection, no LLM calls

## Chat Command

- `dev chat <agent> <message>` — Single LLM turn without work cycle
- `--no-tools` — Disable tool execution
- `--no-reflect` — Skip reflection append
- Useful for testing agent responses in isolation

## Upload Command

- `dev upload <target> <file>` — Upload file to agent inbox or job
- Target is agent_id (creates job with asset) or job-xxx (adds to existing job)
- Supports any file type

## Watch Command

- `dev watch` — Live stream of all system events
- `--agent <id>` — Filter to specific agent
- `--event <type>` — Filter to specific event type
- Uses EventBus dev subscribers for real-time events
- Ctrl+C to stop

## Trace Command

- `dev trace <job_id>` — Show full execution trace of a job
- Aggregates events from job logs, agent logs, and reflection logs
- Shows chronological sequence of what happened

## Module Structure

- Dev CLI code lives in `src/cli/`
- Main dispatcher: `src/cli/dev.py`
- Individual commands: `src/cli/commands/*.py`
- Output formatting: `src/cli/formatters.py`
- Event streaming: `src/cli/stream.py`

## Design Principles

- Minimal changes to existing Agent/Reflection classes
- Event sink is additive (doesn't replace logging)
- Commands are independent — each handles its own setup/teardown
- Fail gracefully with clear error messages
- No side effects from read-only commands (memory, identity, prompt, tools)
