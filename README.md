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

Six specialized agents work together, all inheriting from a shared Core identity:

| Agent | Role |
|-------|------|
| **Archivist** | Preserves high-fidelity human data before interpretation |
| **Profiler** | Constructs the Profile from raw Lifelog data |
| **Curator** | Explores opportunities; guards attention; delivers what counts |
| **Friend** | Supports thinking without threatening identity coherence |
| **Worker** | Executes tasks without undermining agency |
| **Adaptor** | Refines agent identities to serve this specific user |

## Documentation

- **[Pitch](docs/1_pitch.md)** — Introduction and vision overview
- **[Profile](docs/2_profile.md)** — Profile system and agent personas
- **[Architecture](docs/3_architecture.md)** — Technical design and implementation
- **[User Experience](docs/4_user-experience.md)** — UI/UX philosophy and vision
- **[User Interface](docs/5_user-interface.md)** — Current UI components and layout
- **[DevOps](docs/6_devops.md)** — Deployment and operations

## Development

Build for yourself first. This is not a solution looking for a problem.

```bash
# Setup
cp .env.example .env  # Add your ANTHROPIC_API_KEY
pip install -r requirements.txt

# Run
python main.py        # Start the web UI and agents
```

## Privacy

Your data stays local. Processing uses AI APIs (requires trusting those providers). The tradeoff: you get a personal intelligence working for *your* interests, not an algorithm optimizing for engagement.
