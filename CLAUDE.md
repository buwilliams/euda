# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

me·an·dus is an AI personal assistant that manages user attention to maximize life enjoyment through learning, growth, and contribution. The agent builds an understanding of the user and their world to surface personalized activities and recommendations.

## Current State

Initial implementation with working Ingestion Agent. Key files:
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
meandus/
├── main.py                 # Entry point
├── src/
│   ├── agents/
│   │   ├── base.py         # Core agent pattern
│   │   └── ingestion.py    # Ingestion Agent (The Archivist)
│   └── tools/
│       └── log.py          # Log read/write tools
└── data/
    ├── agents/identity/    # Agent identity files
    │   ├── _core.identity.md
    │   ├── ingestion.identity.md
    │   └── ... (8 agent personas)
    └── log/                # Life log entries
        └── [yyyy]/[yyyy-mm-dd].md
```

## Development Philosophy

Build for yourself first, not "other people." This is not a solution looking for a problem.

- Build the best agent for the creator's own daily use
- Refine through lived experience, not hypothetical users
- Features get prioritized by real need, rough edges smoothed by real annoyance
- The agent is its own first user study

## Philosophy

The system is grounded in Popperian epistemology: all knowledge is conjecture. Values are not absolute truths but useful generalizations about what promotes life (motion, growth, pleasure, joy, peace, awe). Values are testable and can be refined or discarded.

## Agent Architecture

Eight agents communicate via shared flat files:
1. **Ingestion Agent (The Archivist)** - Transforms messy data into clean log entries
2. **Summary Agent (The Historian)** - Distills patterns from the life log
3. **Values Agent (The Philosopher)** - Derives and refines user values
4. **World Agent (The Scout)** - Explores external opportunities
5. **Attention Agent (The Curator)** - Orchestrates what surfaces when
6. **Interaction Agent (The Caring Friend)** - User-facing conversations
7. **Worker Agent (The Executor)** - Executes tasks with smart delegation
8. **Introspection Agent (The Mirror)** - Documents system capabilities

Each agent has:
- Core identity (shared beliefs and behaviors)
- Persona identity (role-specific traits)
- Tools (functions it can call)
- Context (conversation history)

## Adding New Agents

1. Create identity file: `data/agents/identity/[name].identity.md`
2. Create agent module: `src/agents/[name].py`
3. Add tools if needed: `src/tools/[name].py`
4. Register in `main.py`
