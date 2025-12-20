# Design

Technical architecture and implementation spec for me·and·us.

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

### Worker Agent

Executes tasks on behalf of the user with delegation logic and approval workflows.

```python
async def run_worker_agent():
    agent = create_agent(
        "data/agents/identity/worker.identity.md",
        tools=[create_task, get_tasks, update_task_status,
               create_pending_action, approve_action, reject_action,
               mark_action_executed, get_integration_status,
               create_project, store_result, prepare_learning_materials]
    )

    while True:
        # Check for pending tasks
        tasks = get_pending_tasks_for_worker()
        for task in tasks:
            # Delegation decision based on task type
            delegation = task.get('delegation', {})

            if delegation.get('strategy') == 'prepare_materials':
                # Learning task: prepare materials, notify user
                result = agent(f"Prepare learning materials for: {task}")
            elif delegation.get('strategy') == 'user_only':
                # Cannot execute, surface to user
                queue_notification(f"Task for you: {task['description']}")
            elif delegation.get('requires_approval'):
                # Create pending action for approval
                create_pending_action(task)
            else:
                # Execute autonomously, store result
                result = agent(f"Execute: {task}")
                store_result(task['id'], result)

        # Execute approved actions
        approved = get_approved_actions()
        for action in approved:
            result = agent(f"Execute approved action: {action}")
            mark_action_executed(action['id'], result)

        await asyncio.sleep(30)
```

### Introspection Agent

Analyzes and documents what the system can do. Maintains a living capabilities document.

```python
async def run_introspection_agent():
    agent = create_agent(
        "data/agents/identity/introspection.identity.md",
        tools=[list_agents, get_agent_identity, get_core_identity,
               analyze_agent_code, list_tools_modules, analyze_tools_module,
               get_system_overview, get_last_introspection, save_capabilities]
    )

    while True:
        # Check if capabilities doc needs refresh
        if capabilities_stale() or signal_received("identity_evolved"):
            result = agent("""
                Analyze the system comprehensively:
                1. Read all agent identities
                2. Analyze code for tools and triggers
                3. Generate user-friendly capabilities guide
                4. Save to data/agents/introspection/capabilities.md
            """)
            send_signal("introspection_updated")

        await asyncio.sleep(1800)  # 30 minutes
```

The capabilities document is accessible to the Interaction Agent, so users can ask "what can you do?" and get accurate, current information.

## Project and Task Management

The system includes a comprehensive project and task management system that spans the entire year.

### Philosophy

Tasks are not just to-do items—they're opportunities for the agent to either:
1. **Execute autonomously** (research, information gathering)
2. **Prepare materials** (learning tasks—user does the learning, agent curates)
3. **Request approval** (high-stakes actions)
4. **Surface to user** (user-only tasks like physical activity)

### Delegation Decision Tree

```
TASK → Is Learning? → YES → Prepare materials, surface to user
                  ↓ NO
       Is User-Only? → YES → Surface to user (cannot execute)
                  ↓ NO
       High Stakes? → YES → Create pending action (require approval)
                  ↓ NO
       Read-Only/Low-Risk? → YES → Execute autonomously, store result
                  ↓ NO
       Within Rate Limits? → YES → Execute autonomously
                  ↓ NO
       Pause & notify (rate limit hit)
```

### Data Structures

**Projects** (`data/tasks/projects/`):
```json
{
  "id": "project-xxx",
  "title": "Learn Spanish",
  "description": "Achieve conversational fluency",
  "type": "learning",
  "status": "active",
  "priority": "high",
  "deadline": "2025-06-01",
  "milestones": [],
  "values_alignment": ["growth", "adventure"],
  "meta": { "tasks_completed": 3, "total_tasks_created": 12 }
}
```

**Tasks** (`data/tasks/queue.json`):
```json
{
  "id": "task-xxx",
  "description": "Find Spanish conversation groups",
  "type": "research",
  "project_id": "project-xxx",
  "delegation": {
    "strategy": "agent_autonomous",
    "requires_approval": false,
    "learning_task": false
  },
  "scheduling": {
    "due_date": "2025-12-22",
    "energy_level": "medium",
    "best_window": "morning"
  },
  "rollover": {
    "times_rolled": 0,
    "original_date": null
  }
}
```

**Results** (`data/tasks/results/`):
```json
{
  "id": "result-xxx",
  "task_id": "task-xxx",
  "project_id": "project-xxx",
  "summary": "Found 3 Spanish conversation groups",
  "content": { "findings": [...], "recommendations": "..." },
  "surfaced_to_user": false
}
```

### Rollover Logic

Incomplete tasks are processed each evening:
1. **High priority** → Always migrate to tomorrow
2. **Has future deadline** → Reschedule before deadline
3. **Rolled 3+ times** → Mark stale, queue for user review
4. **Low priority, no deadline** → Archive
5. **Default** → Migrate to tomorrow, increment count

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
    worker.py
  tools/
    log.py                # Log read/write tools
    files.py              # File processing tools
    search.py             # External search tools
    notifications.py      # Push notification tools
    worker.py             # Task and action management
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
        worker.identity.md
        ...
      state/
      signals/
      evolution/          # Identity evolution proposals
    tasks/                # Project and task management
      queue.json          # Master task queue
      projects/           # Project definitions
        _index.json       # Quick lookup
        project-xxx.json
      daily/              # Daily task views
        2024-12-20.json
      results/            # Completed work output
        2024/12/
          result-xxx.json
      learning/           # Prepared learning materials
        project-xxx/
      archive/            # Completed/archived projects
      config/
        delegation.json   # Delegation rules
        rollover.json     # Rollover policies
    worker/               # Worker agent data (legacy)
      actions/            # Pending and completed actions
      config/             # Integration settings
    notifications/        # Agent-to-user messages
      timestamp.json
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

## Notification System

Agents proactively notify users through a unified notification system.

### Architecture

```
Agent completes work
    ↓
Calls queue_notification()
    ↓
Notification saved to data/notifications/{id}.json
    ↓
Frontend polls /api/notifications
    ↓
User sees notification in activity feed
    ↓
Click triggers action_prompt in chat
```

### Notification Schema

```json
{
  "id": "20251220_093000_123456",
  "agent_name": "attention",
  "title": "Good morning",
  "message": "Here's what to focus on today...",
  "type": "info",
  "action_prompt": "Tell me more about what I should focus on today",
  "priority": "normal",
  "created_at": "2025-12-20T09:30:00",
  "status": "pending",
  "seen": false
}
```

### Notification Types

| Type | Purpose | Example |
|------|---------|---------|
| `info` | FYI, no action needed | "Morning attention ready" |
| `approval` | Needs user decision | "Identity evolution proposal" |
| `question` | Needs user input | "How are you feeling today?" |
| `alert` | Important, time-sensitive | "Project deadline tomorrow" |

### Agent Integration

Each autonomous agent calls `queue_notification()` after completing work:

```python
from ..tools.notifications import queue_notification

def do_work(self):
    result = run_discovery_sweep()

    # Notify user about new discoveries
    queue_notification(
        agent_name="world",
        title="New opportunities discovered",
        message="Found opportunities matching your values",
        notification_type="info",
        action_prompt="Show me the opportunities you discovered",
        priority="normal"
    )
```

## Conversation History

All conversations are persisted for later retrieval and analysis.

### Storage Structure

```
data/conversations/
  sessions/
    {session_id}.json      # Full conversation for a session
  daily/
    {yyyy-mm-dd}.json      # Index of sessions by date
```

### Session Schema

```json
{
  "session_id": "abc123",
  "created": "2025-12-20T09:00:00",
  "updated": "2025-12-20T10:30:00",
  "messages": [
    {
      "timestamp": "2025-12-20T09:00:00",
      "user": "What should I focus on today?",
      "assistant": "Based on your values..."
    }
  ]
}
```

### Capabilities

- **Auto-save**: Every exchange saved automatically
- **Search**: Find conversations by keyword/topic
- **Load by date**: Retrieve all conversations from a specific day
- **Theme analysis**: Identify patterns and themes over time
- **Restore**: Load previous conversations into current chat

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
# Start web server with background agents (recommended for daily use)
python main.py serve

# Start full agent manager (all agents + file watchers + web server)
python main.py start

# Interactive chat only (no background agents)
python main.py chat

# Individual agent commands
python main.py morning      # Generate morning attention
python main.py evening      # Generate evening reflection
python main.py discover     # Run world discovery sweep
python main.py tasks        # Process task queue
python main.py introspect   # Run system analysis
```

The `serve` command automatically starts background agents (Worker, Attention, World, Ingestion) so you get proactive functionality out of the box.

---

## User Interface Design

### Philosophy

The UI must embody the project's core value: **attention is sacred**. Every element competes for attention. Therefore:

- **Empty is good.** If the system has nothing to say, the screen should communicate peace, not emptiness. A nearly-blank screen means "you're free, go live."
- **Push, don't pull.** The user shouldn't come here to check on things. The system reaches out when there's something worth their attention.
- **Less is more.** Each element must earn its place. No decoration, no "nice to have" info.
- **The friend, not the dashboard.** The primary relationship is conversational, not informational.

### Anti-Patterns to Avoid

These patterns optimize for engagement, not wellbeing:

- **Cards and containers** - Visual boxes create the illusion of "content to consume"
- **Grids of options** - Decision fatigue disguised as choice
- **Tabs demanding attention** - Every tab is a question: "What about me?"
- **Stats and counts** - Gamification that creates compulsion
- **Notification badges** - Anxiety triggers
- **Dense information** - Information overload defeats attention management

### Visual Principles

**Typography-first:**
- Black text on white background
- Let words breathe with generous spacing
- No visual noise competing with content
- The logo is the only graphical anchor

**Minimal structure:**
- Plain HTML with light CSS
- No containers, borders, boxes (except navigation)
- No shadows, gradients, or decorative elements
- Whitespace communicates importance through absence

**Progressive disclosure:**
- Primary: What matters right now (dashboard)
- Secondary: Chat (always available)
- Tertiary: Everything else (hidden in navigation)

### Information Architecture

**Single Screen Design**

There is one screen with three persistent elements:

1. **Header** - Logo + title, always present
2. **Activity Feed** - Real-time agent status, shows what the system is doing
3. **Chat** - The Caring Friend, primary interface for everything

**Activity Feed:**

Shows what agents are doing in real-time:
- "All quiet. Your attention is free." when nothing is happening
- "Ingestion working..." when processing new data
- "Summary finished" when agents complete work
- Pulsing dot indicates active work, green dot shows completion

This keeps the user informed without leaving them in limbo.

**Chat as Primary Interface:**

Everything happens through conversation:
- Ask "what are my values" → Friend fetches and explains your values
- Ask "any discoveries" → Friend shows relevant opportunities
- Ask "what did I log today" → Friend reads your log
- Share information → Friend captures it to the log

No separate screens needed. The friend knows you and can access everything.

**Chat Bubbles:**

Messages display as conversation bubbles:
- User messages: Black background, white text, right-aligned, rounded corners with tail on right
- Friend messages: Light gray background, black text, left-aligned, rounded corners with tail on left
- Messages fade in smoothly with subtle slide-up animation
- Auto-focus returns to input after each response

**Loading States:**

Never leave the user wondering:
- "Thinking..." with animated dots while waiting for response
- Input disabled during processing
- Agent activity visible in the feed

**Subtle Hints:**

Below the chat input, gentle suggestions:
- "what did I log today"
- "what are my values"
- "any discoveries"

These are not buttons - they're conversation starters. Clicking fills the input.

### Layout Structure

```
┌─────────────────────────────────────┐
│  [logo] me·an·dus                   │
├─────────────────────────────────────┤
│  All quiet. Your attention is free. │  ← Activity feed
│  (or: Ingestion working...)         │
├─────────────────────────────────────┤
│                                     │
│  Hey. I'm here when you need me.    │  ← Chat messages
│  What's on your mind?               │
│                                     │
│  [user message]                     │
│                                     │
│  Thinking...                        │  ← Loading state
│                                     │
│  [Talk to me...              ] Send │  ← Input
│                                     │
│  Try: "what are my values" ·        │  ← Hints
│       "any discoveries"             │
└─────────────────────────────────────┘
```

### No Separate Screens

Everything happens through chat:
- Ask about logs → Friend reads and summarizes
- Ask about values → Friend explains your values
- Ask about discoveries → Friend shares opportunities
- Share something → Friend captures to log

No navigation needed. The friend knows you and has access to everything.

### Logo Usage

The logo (`static/images/meandus.png`) serves as:
- Visual anchor at the top
- The "face" of the friend
- A moment of recognition, not branding

Place it simply. Don't make it a "header" or wrap it in navigation chrome.

### What Success Looks Like

A user opens the app and sees: their best friend waiting quietly.

"All quiet. Your attention is free." - and they feel relieved.

When they want to know something, they just ask. "What are my values?" "Any discoveries?" The friend knows them and has the answers.

When agents are working, they see it: "Ingestion working..." No limbo. No wondering.

The UI feels like talking to a brilliant, caring friend who happens to know everything about you and the world.

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
