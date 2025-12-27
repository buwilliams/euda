# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Euno is a personal intelligence that learns to anticipate you: doing tasks for you, curating what helps you thrive, and expanding your horizons.

## Current State

All 8 agents implemented with web UI and API. Key files:
- `README.md` - Product specification
- `docs/architecture.md` - Technical architecture and implementation spec
- `docs/vision.md` - Vision for what Euno should become
- `docs/user-experience.md` - UI/UX vision and comparison to current state
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
│   ├── agents/             # 8 agent modules (ingestion, summary, synthesis, etc.)
│   │   └── base.py         # Core agent pattern
│   ├── tools/              # Organized by agent concern
│   │   ├── shared/         # Cross-agent (log, agent identity, notifications)
│   │   ├── ingestion/      # File processing, queue, budget, iPhone backup tools
│   │   ├── synthesis/      # User synthesis (epistemic, values, behaviors, context)
│   │   ├── world/          # Opportunities + fetch
│   │   ├── attention/      # Energy + surfacing queue
│   │   ├── interaction/    # Conversations + cards
│   │   ├── worker/         # Tasks + projects
│   │   └── evolution/      # System analysis and identity evolution
│   └── web/
│       └── app.py          # FastAPI server
└── data/                   # Agent-oriented data
    │                       # Standard pattern: config/, logs/, prompts/, state/
    ├── shared/             # Cross-agent resources
    │   └── state/          # identity/, profile/, lifelog/, signals/, notifications/
    ├── ingestion/          # state/inbox/, state/digests/
    ├── summary/            # state/
    ├── synthesis/          # state/values/, state/behaviors/, state/profile/, etc.
    ├── world/              # state/opportunities/
    ├── attention/          # state/queue/
    ├── interaction/        # state/conversations/, state/cards/
    ├── worker/             # state/tasks/, state/projects/, state/actions/
    └── evolution/          # state/output/
```

See `docs/architecture.md` for full directory structure details.

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
1. **Ingestion Agent (The Archivist)** - Preserves irreversible human signal with high fidelity; memory, not meaning
2. **Summary Agent (The Historian)** - Compresses time without collapsing structure; preserves patterns, tensions, change signals
3. **Synthesis Agent (The Keeper)** - Constructs predictive identity model; anticipates behavior, not aspirations
4. **World Agent (The Scout)** - Explores integrable external opportunities; filters through identity constraints
5. **Attention Agent (The Curator)** - Allocates scarce attention; respects capacity, introduces surprise safely
6. **Interaction Agent (The Caring Friend)** - Supports thinking without threatening identity coherence
7. **Worker Agent (The Executor)** - Executes tasks without undermining agency; checks constraints before irreversible actions
8. **Evolution Agent (The Evolver)** - Refines agent identities to serve this specific user; proposes, never forces

### Identity Stack (Ordered by Predictive Power)

The Synthesis Agent maintains a predictive model of who the user is:
1. **Identity Constraints** (primary) - Non-negotiable rules revealed by sacrifice and refusal; rarely change
2. **Failure Modes** (primary) - Predictable breakdowns under stress; strongest behavior predictors
3. **Behavioral Attractors** - Stable patterns the user returns to across contexts
4. **Utility Tradeoff Curves** - What they sacrifice first when goals conflict (truth vs belonging, comfort vs dignity)
5. **Epistemic Style** (supporting) - How they handle uncertainty, revision, authority
6. **Narrative Identity** (supporting) - Self-concept and aspirational framing; useful for alignment, unreliable for prediction

The prime question: *What would this person rather suffer than violate?*

Each agent has:
- Core identity (shared ontology and operating principles)
- Persona identity (role-specific purpose, constraints, output contract)
- Tools (functions it can call)
- Context (conversation history)

## Batch Ingestion

Ingestion uses batch processing to minimize API calls:

```bash
python main.py ingest                      # Process inbox (default batch size: 5)
python main.py ingest --batch-size 10      # Custom batch size
python main.py ingest ~/Documents -r       # External directory
```

Batch processing groups files together and requests structured JSON output instead of tool calls, significantly reducing API round trips.

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

1. Create identity file: `data/shared/state/identity/[name].identity.md`
2. Create agent module: `src/agents/[name].py`
3. Add tools if needed: `src/tools/[agent]/[tool].py`
4. Create data directory: `data/[name]/` with `state/` subdirectory
5. Register in `main.py`
