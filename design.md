# Design

Technical architecture and implementation spec for Me and Us.

## Philosophy

Keep it simple. An agent is just:
- A context (list of strings)
- A loop (process input → call LLM → handle tools → repeat)
- Tools (JSON blobs describing functions)

As Thomas Ptacek notes: "Your wackiest idea will probably (1) work and (2) take 30 minutes to code."

## Core Agent Pattern

Every agent in the system follows this pattern:

```python
from anthropic import Anthropic

client = Anthropic()

def create_agent(identity_path, tools=[]):
    """Create an agent with identity loaded from file."""

    # Load core identity + agent-specific identity
    core = load_file("data/agents/identity/_core.identity.md")
    persona = load_file(identity_path)

    context = [{
        "role": "system",
        "content": f"{core}\n\n{persona}"
    }]

    def call():
        return client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8096,
            system=context[0]["content"],
            tools=tools,
            messages=context[1:]
        )

    def process(input_content):
        context.append({"role": "user", "content": input_content})
        response = call()

        # Handle tool calls in a loop
        while has_tool_calls(response):
            handle_tools(response, context)
            response = call()

        output = response.content[0].text
        context.append({"role": "assistant", "content": output})
        return output

    return process
```

## Agent Manager

Single Python process that spawns and monitors all agents.

```python
import asyncio
from watchdog.observers import Observer

class AgentManager:
    def __init__(self):
        self.agents = {}
        self.observers = []

    async def start(self):
        # Start each agent as an async task
        self.agents["ingestion"] = asyncio.create_task(
            run_ingestion_agent()
        )
        self.agents["summary"] = asyncio.create_task(
            run_summary_agent()
        )
        # ... etc

        # Monitor for hangs/failures
        while True:
            await self.health_check()
            await asyncio.sleep(60)

    async def health_check(self):
        for name, task in self.agents.items():
            if task.done():
                # Restart failed agent
                self.agents[name] = asyncio.create_task(
                    self.restart_agent(name)
                )
```

## Agents

### Ingestion Agent

Watches inbox, processes files, writes log entries.

```python
async def run_ingestion_agent():
    agent = create_agent(
        "data/agents/identity/ingestion.identity.md",
        tools=[process_file, extract_temporal, write_log_entry]
    )

    # Watch inbox directory
    observer = Observer()
    observer.schedule(InboxHandler(agent), "data/inbox/", recursive=True)
    observer.start()

    # Also check periodically
    while True:
        files = list_unprocessed_files("data/inbox/")
        for file in files:
            result = agent(f"Process this file: {file}")
            # Agent decides how to extract content, determine time, write entry

        await asyncio.sleep(300)  # Check every 5 minutes
```

### Summary Agent

Maintains yearly summaries, triggers on log changes.

```python
async def run_summary_agent():
    agent = create_agent(
        "data/agents/identity/summary.identity.md",
        tools=[read_log_files, read_manifest, write_summary, write_manifest]
    )

    while True:
        # Check each year's manifest for changes
        years = list_year_directories("data/log/")
        for year in years:
            manifest = read_manifest(year)
            if needs_reprocessing(manifest):
                result = agent(f"Reprocess summary for {year}. Manifest: {manifest}")

        await asyncio.sleep(3600)  # Check hourly
```

### Values Agent

Derives values from summaries.

```python
async def run_values_agent():
    agent = create_agent(
        "data/agents/identity/values.identity.md",
        tools=[read_summaries, read_current_values, write_values]
    )

    while True:
        # Watch for summary changes
        if summaries_changed():
            result = agent("""
                Analyze the yearly summaries and update values.
                Consider: current (rolling year), life phase, lifetime.
                Look for stated vs revealed tensions.
            """)

        await asyncio.sleep(3600)
```

### World Agent

Explores external sources for opportunities.

```python
async def run_world_agent():
    agent = create_agent(
        "data/agents/identity/world.identity.md",
        tools=[search_events, search_people, search_places,
               search_learning, read_values, write_opportunity]
    )

    while True:
        values = load_current_values()
        result = agent(f"""
            Given these values: {values}

            Search for opportunities. Remember:
            - 90% aligned with values
            - 10% expansive/surprising but still life-promoting
            - Respect location and resource constraints
            - Only public information unless value cards shared
        """)

        # Periodic sweep based on user's preferences
        await asyncio.sleep(get_sweep_interval())
```

### Attention Agent

Matches opportunities to values, manages surfacing.

```python
async def run_attention_agent():
    agent = create_agent(
        "data/agents/identity/attention.identity.md",
        tools=[read_opportunities, read_values, read_energy_signals,
               read_calendar, write_surfacing_queue, send_notification]
    )

    while True:
        now = datetime.now()

        # Morning attention
        if is_morning_time(now):
            result = agent("""
                Prepare morning attention. Consider:
                - Today's calendar
                - Current energy state
                - Relevant opportunities (integrate surprise naturally)
                - One thing to look forward to
                Keep it minimal - only what matters.
            """)
            send_morning_notification(result)

        # Evening journal prompt
        if is_evening_time(now):
            result = agent("""
                Prepare evening journal prompt.
                Be warm - user is likely tired.
                Guide reflection on the day.
            """)
            send_evening_notification(result)

        await asyncio.sleep(300)
```

### Interaction Agent

Handles user conversations.

```python
async def run_interaction_agent():
    agent = create_agent(
        "data/agents/identity/interaction.identity.md",
        tools=[read_values, read_log, read_energy, write_log_entry,
               schedule_reminder, search_log]
    )

    # This agent responds to user input via API
    # Runs as a web server endpoint

    @app.post("/chat")
    async def chat(message: str, session_id: str):
        # Load or create session context
        context = get_session_context(session_id)

        # Detect intent and adapt
        response = agent(f"""
            User message: {message}

            Detect their intent:
            - Exploring an idea? → participate, challenge, expand
            - Venting? → listen, reflect, empathize
            - Capturing for later? → confirm, schedule, link
            - Making a decision? → surface values, pros/cons
            - Brainstorming? → generate, connect, be playful

            Respond appropriately. Log the conversation.
        """)

        return response
```

## Tools

Tools are just functions with JSON schema descriptions.

```python
tools = [
    {
        "name": "write_log_entry",
        "description": "Write an entry to the life log",
        "input_schema": {
            "type": "object",
            "properties": {
                "timestamp": {"type": "string", "description": "ISO timestamp"},
                "source": {"type": "string", "description": "Data source"},
                "locality": {"type": "string", "description": "Location"},
                "entry_type": {"type": "string", "description": "Type of entry"},
                "content": {"type": "string", "description": "Entry content"},
                "temporal_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "temporal_source": {"type": "string", "description": "How time was determined"}
            },
            "required": ["timestamp", "source", "content"]
        }
    },
    # ... more tools
]

def write_log_entry(timestamp, source, content, locality="", entry_type="",
                    temporal_confidence="medium", temporal_source=""):
    date = parse_date(timestamp)
    year_dir = f"data/log/{date.year}"
    ensure_dir(year_dir)

    entry = f"""---
{timestamp}
source: {source}
locality: {locality}
type: {entry_type}
temporal_confidence: {temporal_confidence}
temporal_source: {temporal_source}
content: {content}
---
"""

    log_file = f"{year_dir}/{date.strftime('%Y-%m-%d')}.md"
    append_to_file(log_file, entry)
    update_manifest(year_dir, date, source)

    return f"Entry written to {log_file}"
```

## File Structure

```
meandus/
  main.py                 # Agent manager entry point
  agents/
    base.py               # Core agent pattern
    ingestion.py
    summary.py
    values.py
    world.py
    attention.py
    interaction.py
  tools/
    log.py                # Log read/write tools
    files.py              # File processing tools
    search.py             # External search tools
    notifications.py      # Push notification tools
  web/
    app.py                # FastAPI app
    routes/
      chat.py
      cards.py
      logs.py
      agents.py

  data/                   # All data lives here
    inbox/                # Drop files here
    log/
      2024/
        2024-01-01.md
        _manifest.md
        _summary.md
    agents/
      identity/
        _core.identity.md
        ingestion.identity.md
        ...
      state/
      signals/
      queues/
    cards/
      internal.card.md
      public.card.md
      exchanges/
    values/
      current.values.md
      phase.values.md
      lifetime.values.md
    ui/
      layout.md
      evolution.md
```

## Context Engineering

Key insight from Ptacek: context engineering is a real programming problem.

### Managing Token Budget

- Each agent has focused context (not everything at once)
- Load only relevant files for current task
- Summarize before context gets too large
- Sub-agents for specific tasks (fresh context)

### Sub-Agent Pattern

When an agent needs to do something complex, spawn a sub-agent:

```python
def analyze_photo(photo_path):
    """Sub-agent with fresh context just for this photo."""
    sub_agent = create_agent(
        "data/agents/identity/ingestion.identity.md",
        tools=[extract_exif, ocr_image, describe_image]
    )

    result = sub_agent(f"Analyze this photo completely: {photo_path}")
    return result  # Returns to parent agent's context
```

### Agent Communication

Agents communicate through files, not direct calls:
- Write to queues (opportunities.queue.md)
- Write signals (values_updated.signal)
- Read shared state (current.values.md)

This keeps agents decoupled and debuggable.

## API

Simple REST API via FastAPI.

```python
from fastapi import FastAPI

app = FastAPI()

# Chat
@app.post("/chat")
async def chat(message: str, session_id: str): ...

# Cards
@app.get("/cards/public")
async def get_public_card(): ...

@app.put("/cards/public")
async def update_public_card(card: Card): ...

@app.post("/cards/exchange")
async def exchange_cards(agent_url: str): ...

# Logs
@app.get("/logs/{year}/{date}")
async def get_log(year: int, date: str): ...

@app.get("/logs/search")
async def search_logs(query: str): ...

# Agents
@app.get("/agents/status")
async def get_agent_status(): ...

# Values
@app.get("/values/current")
async def get_current_values(): ...
```

## Running

```bash
# Start all agents
python main.py

# Web UI (separate process)
uvicorn web.app:app --reload
```

## Development Approach

### Bootstrapping with Claude Code

Before building any agents, use Claude Code itself as an interactive Ingestion Agent:
- Drop files and ask Claude to process them into log entries
- Ask Claude to read blogs/articles and log interesting content
- Dictate conversations, ideas, reflections for Claude to capture
- Have Claude write directly to `data/log/` and `data/inbox/`

This builds real data to work with while developing the actual agents.

### Build Order

1. Start with Ingestion Agent alone - get file processing working
2. Add Interaction Agent - get chat working
3. Add Summary Agent - get yearly summaries working
4. Add Values Agent - get values derivation working
5. Add Attention Agent - get morning/evening flow working
6. Add World Agent - get external discovery working
7. Refine and tune based on actual use

Build for yourself. Use daily. Refine through lived experience.
