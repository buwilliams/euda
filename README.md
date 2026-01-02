<p align="center">
  <img src="static/images/euno-logo-with-subtitle.png" alt="Euno" width="50%">
</p>

_Euno [you-know], from Eudaimonia—ancient Greek for "human flourishing." A deep sense of fulfillment achieved through virtuous living, developing one's potential, and engaging in meaningful activities._

**Euno is a personal intelligence that learns to anticipate you.** It understands who you are, proactively does tasks for you, and curates what deserves your attention.

Today's AI remembers facts about you. Euno understands who you are—your values, your patterns, your rhythms.

## How It Works

1. **Learns** from your data and behaviors
2. **Understands** who you really are—values, patterns, rhythms
3. **Anticipates** what you need before you ask

## What It Does

- **Reads your life data** — photos, documents, exports from any platform
- **Maintains a life log** — one unified record of everything, searchable and private
- **Learns who you are** — values, patterns, rhythms—discovered from behavior, not just what you say
- **Surfaces what matters** — the right thing at the right moment, respecting your energy
- **Guards your attention** — reads your feeds, shields you from engagement algorithms, less screen time without losing touch
- **Executes tasks** — handles work autonomously, asks before acting on anything important
- **Talks like a friend** — not a chatbot, not an assistant—a caring collaborator who knows you and goes deep when you need it

## Core Ideas

**Promotion of Life** — The foundation: promote life. Not fatalistic, not nihilistic. A life that is safe AND surprising.

**90/10 Balance** — ~90% grounded in your values; ~10% novelty that challenges and expands. Too much surprise → anxiety. Too little → stagnation.

**Stated vs Revealed** — What you say matters vs what your behavior shows. The gap isn't hypocrisy—it's tension to understand.

**Energy Awareness** — Models your energy (physical, mental, emotional, social). Adjusts what it surfaces based on your capacity.

## Agents

Seven agents work together, each defined by config + persona + tools:

| Agent | Role | Mode |
|-------|------|------|
| **Archivist** | Preserves high-fidelity human data before interpretation | Scheduled (5 min) |
| **Profiler** | Constructs the Profile from raw Lifelog data | Scheduled (30 min) |
| **Curator** | Explores opportunities; guards attention; delivers what counts | Scheduled (15 min) |
| **Friend** | Supports thinking without threatening identity coherence | Interactive |
| **Worker** | Executes tasks without undermining agency | Scheduled (2 min) |
| **Adaptor** | Refines agent identities to serve this specific user | Scheduled (60 min) |
| **Assistant** | General purpose helper for direct requests | Interactive |

Adding a new agent requires only a `config.json` and persona markdown file—no Python code.

## Quick Start

```bash
# Setup
cp .env.example .env      # Add your ANTHROPIC_API_KEY
pip install -r requirements.txt

# Run
python main.py serve      # Web server + background agents
python main.py chat       # Interactive chat with assistant
python main.py chat friend  # Chat with The Friend
python main.py agents     # List all agents
python main.py jobs       # List all jobs
python main.py start      # Run agents only (no web)
```

## Architecture

Everything is either an **Agent** or a **Job**.

```
data/
├── agents/           # Agent configs and personas (code)
│   └── {agent}/
│       ├── config.json
│       └── {agent}-persona.md
├── jobs/             # SQLite database for jobs
├── assets/           # Files attached to jobs
├── user/             # Profile and lifelog
└── system/           # Global config

src/
├── agent.py          # Generic agent: config + persona + tools + loop
├── manager.py        # Starts/stops all agents
├── tools/            # All tools with @tool decorator
└── web/              # FastAPI + routes
```

## Documentation

- **[Pitch](docs/1_pitch.md)** — Introduction and vision overview
- **[Profile](docs/2_profile.md)** — Profile system and agent personas
- **[Architecture](docs/3_architecture.md)** — Technical design and implementation
- **[User Experience](docs/4_user-experience.md)** — UI/UX philosophy and vision
- **[User Interface](docs/5_user-interface.md)** — Current UI components and layout
- **[DevOps](docs/6_devops.md)** — Deployment and operations

## Privacy

Your data stays local. Processing uses AI APIs (requires trusting those providers). The tradeoff: you get a personal intelligence working for *your* interests, not an algorithm optimizing for engagement.
