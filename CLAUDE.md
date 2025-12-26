# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Euno is a personal intelligence that learns to anticipate you: doing tasks for you, curating what helps you thrive, and expanding your horizons.

## Current State

All 8 agents implemented with web UI and API. Key files:
- `README.md` - Product specification
- `design.md` - Technical architecture and implementation spec
- `main.py` - Entry point for running agents

## Setup

1. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```

2. Add your Anthropic API key to `.env`:
   ```
   ANTHROPIC_API_KEY=your-actual-key
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the Ingestion Agent:
   ```
   python main.py
   ```

## Project Structure

```
euno/
├── main.py                 # Entry point
├── src/
│   ├── agents/             # 8 agent modules (ingestion, summary, identity, etc.)
│   │   └── base.py         # Core agent pattern
│   ├── tools/              # Organized by agent concern
│   │   ├── shared/         # Cross-agent (log, agent identity, notifications)
│   │   ├── ingestion/      # File processing, queue, budget, iPhone backup tools
│   │   ├── identity/       # User identity (values at core, behaviors, context)
│   │   ├── world/          # Opportunities + fetch
│   │   ├── attention/      # Energy + surfacing queue
│   │   ├── interaction/    # Conversations + cards
│   │   ├── worker/         # Tasks + projects
│   │   └── introspection/  # Self-analysis
│   └── web/
│       └── app.py          # FastAPI server
└── data/                   # Agent-oriented data
    ├── shared/             # Cross-agent (log, signals, identity, notifications)
    ├── ingestion/          # inbox/, queue/, digests/
    ├── identity/           # values/, behaviors/, context/, derived/
    ├── world/              # opportunities/
    ├── attention/          # energy + surfacing queue
    ├── interaction/        # conversations/
    ├── worker/             # tasks/, projects/, actions/
    └── introspection/      # capabilities
```

See `design.md` for full directory structure details.

## Development Philosophy

Build for yourself first, not "other people." This is not a solution looking for a problem.

- Build the best agent for the creator's own daily use
- Refine through lived experience, not hypothetical users
- Features get prioritized by real need, rough edges smoothed by real annoyance
- The agent is its own first user study

### Information Flow

When adding features or content, don't add directly. First examine the system's architecture and capabilities, then design the addition to align with them. If a capability is missing, consider carefully how to organize it alongside existing capabilities.

```
Architecture → Organization → Capabilities → Features
```

This hierarchy ensures coherent growth. Features serve capabilities, capabilities fit the organization, organization reflects architecture.

## Philosophy

The system is grounded in Popperian epistemology: all knowledge is conjecture. Values are not absolute truths but useful generalizations about what promotes life (motion, growth, pleasure, joy, peace, awe). Values are testable and can be refined or discarded.

## Agent Architecture

Eight agents communicate via shared flat files:
1. **Ingestion Agent (The Archivist)** - Transforms messy data into clean log entries
2. **Summary Agent (The Historian)** - Distills patterns from the life log
3. **Identity Agent (The Keeper)** - Maintains user identity (values at core, behaviors, context)
4. **World Agent (The Scout)** - Explores external opportunities
5. **Attention Agent (The Curator)** - Orchestrates what surfaces when
6. **Interaction Agent (The Caring Friend)** - User-facing conversations
7. **Worker Agent (The Executor)** - Executes tasks with smart delegation
8. **Introspection Agent (The Mirror)** - Documents system capabilities

### Identity Hierarchy

The Identity Agent maintains a comprehensive model of who the user is:
1. **Values & Beliefs** (core) - Who you ARE
2. **Behaviors** (derived) - How you actually act
3. **Relationships** (context) - Who matters to you
4. **Biographical facts** (context) - Background information

Values are the PRIMARY definition of identity. Biographical facts and relationships are supporting context that helps agents anticipate the user, but do not define identity.

Each agent has:
- Core identity (shared beliefs and behaviors)
- Persona identity (role-specific traits)
- Tools (functions it can call)
- Context (conversation history)

## iPhone Backup Extraction

Standalone tools for extracting data from iOS device backups, located in `src/tools/ingestion/iphone/`:

```bash
# Auto-find backup and export messages + media
python src/tools/ingestion/iphone/iphone_backup.py

# Export messages only
python src/tools/ingestion/iphone/iphone_backup.py --messages

# Export media only (photos/videos)
python src/tools/ingestion/iphone/iphone_backup.py --media

# Specify custom paths
python src/tools/ingestion/iphone/iphone_backup.py --backup /path/to/backup --output ./export

# Find available backups and databases
python src/tools/ingestion/iphone/find_backup_db.py

# Export directly from sms.db (without contact name lookup)
python src/tools/ingestion/iphone/iphone_messages_export.py /path/to/sms.db --output ./export
```

Key details:
- Requires unencrypted iPhone backup (created via iTunes/Finder)
- Auto-detects backup location on macOS, Windows, and WSL
- Exports messages as markdown files named by contact
- Preserves DCIM folder structure for photos/videos

## Adding New Agents

1. Create identity file: `data/shared/identity/[name].identity.md`
2. Create agent module: `src/agents/[name].py`
3. Add tools if needed: `src/tools/[agent]/[tool].py`
4. Create data directory: `data/[name]/` with `state/` subdirectory
5. Register in `main.py`
