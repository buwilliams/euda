# LLM Architecture

Rules for how agents interact with LLMs, including prompts, tools, and work cycles.

## System Prompts

System prompts follow a consistent structure defined in `data/system/prompts/system_prompt.md`:

1. **Agent Profile** - The agent's identity, purpose, and behavioral rules
2. **Available Tools** - Tools grouped by type with usage guidance

### What's NOT Included

User profile, user memory, and conversation history are NOT included automatically in system prompts. This:
- Reduces token usage for agents that don't need user context
- Makes context access explicit and auditable
- Lets agents decide when to fetch user data based on the task

Agents should use `get_profile` and `list_memory` tools when needed.

## Tool Organization

Tools are organized into four categories in `src/tools/{type}/`:

### Data Tools (`src/tools/data/`)
User and job data operations:
- **jobs.py** - Job CRUD, assignment, batch operations, system containers
- **assets.py** - File attachments per job
- **profile.py** - Profile access for any agent
- **memory.py** - Short-term and long-term memory for any agent

### Agent Tools (`src/tools/agents/`)
Agent management and introspection:
- **agents.py** - List, create, update, enable/disable agents

### System Tools (`src/tools/system/`)
System operations and control:
- **system.py** - Config, done_working, notifications batch
- **dates.py** - Current date, date parsing
- **notifications.py** - Chat messages, connection check

### Integration Tools (`src/tools/integration/`)
External knowledge and documentation:
- **knowledge.py** - List and read docs/specs, read agent logs

## Tool Descriptions

Every tool description includes two parts:
1. What the tool does
2. When to use it (specific scenarios)

Format: `"What it does. Use when: specific scenarios."`

Example:
```python
@tool("list_jobs",
      "List all jobs, optionally filtered. Use when: reviewing work queue, finding assigned jobs.",
      tool_type="data")
```

## Tool Registration

Tools are registered with the `@tool` decorator in each module:

```python
from .. import tool

@tool("tool_name", "Description. Use when: ...", tool_type="data")
def tool_name(...):
    ...
```

Parameters:
- `name` - Tool name (used in agent configs and API)
- `description` - What it does and when to use it
- `input_schema` - Optional explicit schema for complex types
- `tool_type` - One of: data, agents, system, integration

## Prompt Templates

Templates are stored in `data/system/prompts/` as markdown files:

| Template | Purpose |
|----------|---------|
| `system_prompt.md` | System prompt structure |
| `job_prompt.md` | Job assignment format |
| `continue_prompt.md` | Work cycle continuation |

Templates use Python format string syntax: `{variable_name}`

### Template Loader

Load and render templates via `src/prompts.py`:

```python
from .prompts import load_template, render_template

# Load raw template
template = load_template("job_prompt")

# Render with variables
prompt = render_template("job_prompt",
    job_name="My Task",
    job_description="Do something",
    job_due_date="2024-01-15",
    job_attachments="No attachments",
    remaining_jobs_notice=""
)
```

## Job Prompts

When an agent is assigned a job, the prompt format is defined in `data/system/prompts/job_prompt.md`:

```
You have been assigned a job:
- **Name**: {job name}
- **Description**: {description or "None provided"}
- **Due**: {due date or "No deadline"}
- **Context**: {attachment count and names, or "No attachments"}

Work on this job according to your role. Use available tools to:
1. Get user profile/memory if you need user context
2. Read/write job assets as needed
3. Create sub-jobs if work needs breakdown
4. Call done_working() when finished
```

## Work Cycle Flow

1. Agent polls for actionable jobs assigned to it
2. Takes first job (one at a time to prevent context overflow)
3. Formats job using `job_prompt.md` template
4. Enters autonomous loop:
   - Sends prompt to LLM
   - Executes any tool calls
   - Checks if `done_working()` was called
   - If not done, sends `continue_prompt.md`
5. Exits when agent calls `done_working()` or max iterations reached

## Context Access Patterns

| Context | How to Access |
|---------|---------------|
| User Profile | `get_profile("user")` tool |
| Agent Profile | `get_profile(agent_id)` tool |
| Short-term Memory | `list_memory(agent_id)` tool |
| Long-term Memory | `read_long_term_memory(date, agent_id)` tool |
| Job Assets | `list_assets`, `read_asset` tools |
| Conversation | Auto-included in system prompt |

## Memory Tools

Short-term memory (90-day rolling):
- `add_memory(short_description, type, date_expected, agent_id)` - Add item
- `list_memory(agent_id)` - List all items
- `remove_memory(entry_id, agent_id)` - Remove item

Long-term memory (indefinite archive):
- `write_long_term_memory(content, date, agent_id)` - Write to archive
- `read_long_term_memory(date, agent_id)` - Read from archive
- `list_long_term_memory_dates(agent_id)` - List available dates

All functions default to `agent_id="user"` for backward compatibility.

## Prompt Logging

Prompts are logged to `data/system/logs/prompts/{date}.jsonl` for debugging.

Each entry includes:
- Timestamp
- Agent ID
- Model name
- System prompt and length
- Messages
- Tools used

## Token Efficiency

The architecture improves token efficiency:

- Profile/memory not auto-included saves ~1000+ tokens per call
- Tools grouped by type helps LLM understand capabilities
- Standardized job format is more parseable than raw JSON
- Conversation history limited to last 100 lines
- Templates are cached after first load
