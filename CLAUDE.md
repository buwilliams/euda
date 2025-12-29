# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Euno is a personal intelligence that learns to anticipate you: doing tasks for you, curating what helps you thrive, and expanding your horizons.

## Current State

6 agents implemented with web UI and API. Key files:
- `README.md` - Product specification
- `docs/3_architecture.md` - Technical architecture and implementation spec
- `docs/2_profile.md` - Profile system and agent personas
- `docs/4_user-experience.md` - UI/UX vision and philosophy
- `docs/5_user-interface.md` - Current UI components and layout reference
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

4. Run Euno:
   ```
   python main.py
   ```

## Project Structure

```
euno/
├── main.py                 # Entry point
├── src/
│   ├── agents/             # 6 agent modules
│   │   └── base.py         # Core agent pattern
│   ├── tools/              # Organized by agent concern
│   │   ├── shared/         # Cross-agent (log, agent identity, signals)
│   │   ├── archivist/      # File processing, queue, budget, iPhone backup tools
│   │   ├── profiler/       # User profile synthesis (epistemic, values, behaviors)
│   │   ├── curator/        # Energy + attention queue + context
│   │   ├── friend/         # Conversations + cards
│   │   ├── worker/         # Tasks + projects
│   │   └── adaptor/        # System analysis and identity evolution
│   └── web/
│       └── app.py          # FastAPI server
└── data/                   # Agent-oriented data
    │                       # Standard pattern: config/, logs/, prompts/, state/
    ├── shared/             # Cross-agent resources
    │   └── state/          # agents/, profile/, lifelog/, signals/
    ├── archivist/          # state/inbox/, state/digests/
    ├── profiler/           # state/values/, state/behaviors/, state/profile/, etc.
    ├── curator/            # state/queue/
    ├── friend/             # state/conversations/, state/cards/
    ├── worker/             # state/tasks/, state/projects/, state/actions/
    └── adaptor/            # state/output/
```

See `docs/3_architecture.md` for full directory structure details.

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

Six agents communicate via shared flat files, all inheriting from a shared Core identity:
1. **Archivist** - Preserves irreversible human signal with high fidelity; memory, not meaning
2. **Profiler** - Constructs the Profile from raw Lifelog data; extracts patterns from behavior
3. **Curator** - Explores integrable opportunities; allocates scarce attention; respects capacity
4. **Friend** - Supports thinking without threatening identity coherence
5. **Worker** - Executes tasks without undermining agency; checks Profile before irreversible actions
6. **Adaptor** - Refines agent identities to serve this specific user; proposes, never forces

Each agent has:
- Core identity (shared ontology and operating principles)
- Persona identity (role-specific purpose, constraints, output contract)
- Tools (functions it can call)
- Context (conversation history)

## Batch Archival

The Archivist uses batch processing to minimize API calls:

```bash
python main.py ingest                      # Process inbox (default batch size: 5)
python main.py ingest --batch-size 10      # Custom batch size
python main.py ingest ~/Documents -r       # External directory
```

Batch processing groups files together and requests structured JSON output instead of tool calls, significantly reducing API round trips.

## iPhone Backup Extraction

Standalone tools for extracting data from iOS device backups, located in `src/tools/archivist/iphone/`:

```bash
# Auto-find backup and export messages + media
python src/tools/archivist/iphone/iphone_backup.py

# Export messages only
python src/tools/archivist/iphone/iphone_backup.py --messages

# Export media only (photos/videos)
python src/tools/archivist/iphone/iphone_backup.py --media

# Specify custom paths
python src/tools/archivist/iphone/iphone_backup.py --backup /path/to/backup --output ./export

# Find available backups and databases
python src/tools/archivist/iphone/find_backup_db.py

# Export directly from sms.db (without contact name lookup)
python src/tools/archivist/iphone/iphone_messages_export.py /path/to/sms.db --output ./export
```

Key details:
- Requires unencrypted iPhone backup (created via iTunes/Finder)
- Auto-detects backup location on macOS, Windows, and WSL
- Exports messages as markdown files named by contact
- Preserves DCIM folder structure for photos/videos

## Adding New Agents

1. Create agent file: `data/shared/state/agents/[number]_[name].agent.md`
2. Create agent module: `src/agents/[name].py`
3. Add tools if needed: `src/tools/[agent]/[tool].py`
4. Create data directory: `data/[name]/` with `state/` subdirectory
5. Register in `main.py`
