<p align="center">
  <img src="static/images/euno-logo-with-subtitle.png" alt="Euno" width="50%">
</p>

_Euno [U-no], from Eudaimonia—ancient Greek for "human flourishing." A deep sense of fulfillment achieved through virtuous living, developing one's potential, and engaging in meaningful activities._

**Euno is a personal intelligence that learns to anticipate you.** It proactively does tasks for you, curates what helps you thrive, and expands your horizons.

## How It Works

1. **Learns** from your data and behaviors
2. **Understands** who you really are—values, patterns, rhythms
3. **Anticipates** what you need before you ask

## What It Does

- **Reads your life data** — photos, documents, exports from any platform
- **Maintains a life log** — one unified record of everything, searchable and private
- **Learns your values** — discovers what matters from patterns, not just what you say
- **Surfaces what matters** — the right thing at the right moment, respecting your energy
- **Executes tasks** — handles work autonomously, asks before acting on anything important
- **Talks like a friend** — not a chatbot, not an assistant—a caring collaborator who knows you

## Core Ideas

**Promotion of Life** — The foundation: promote life. Not fatalistic, not nihilistic. A life that is safe AND surprising.

**90/10 Balance** — ~90% grounded in your values; ~10% novelty that challenges and expands. Too much surprise → anxiety. Too little → stagnation.

**Stated vs Revealed** — What you say matters vs what your behavior shows. The gap isn't hypocrisy—it's tension to understand.

**Energy Awareness** — Models your energy (physical, mental, emotional, social). Adjusts what it surfaces based on your capacity.

## Agents

Eight specialized agents work together:

| Agent | Role |
|-------|------|
| **Ingestion** | Transforms messy data into clean log entries |
| **Summary** | Distills daily logs into narratives |
| **Synthesis** | Builds understanding of who you are |
| **World** | Explores opportunities matching your values |
| **Attention** | Surfaces the right thing at the right time |
| **Interaction** | Your interface—converses, listens, adapts |
| **Worker** | Handles tasks autonomously or escalates |
| **Evolution** | Evolves agent identities, steers the system |

## Documentation

- **[Vision](docs/vision.md)** — What Euno should become
- **[Architecture](docs/architecture.md)** — Technical design and implementation
- **[User Experience](docs/user-experience.md)** — UI/UX philosophy
- **[Todo](docs/todo.md)** — Implementation roadmap

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
