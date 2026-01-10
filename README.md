<p align="center">
  <img src="static/images/euno-logo-with-subtitle.png" alt="Euno" width="50%">
</p>

_Euno (you-know), from Eudaimonia (you-dye-MOH-nee-ah)—ancient Greek for "human flourishing." A deep sense of fulfillment achieved through virtuous living, developing one's potential, and engaging in meaningful activities._

Today's AI remembers facts about you, but it doesn't know you. Euno understands who you are—your values, your patterns, your rhythms. **Euno is a personal intelligence that learns to anticipate you.** It understands who you are, proactively does tasks for you, and curates what deserves your attention.

## Getting Started

The best way to get started is to understand the mental model behind Euno.

**Suggested reading:**
1. [Pitch](docs/1_pitch.md) — What Euno is and why it exists
2. [Business Plan](docs/2_business-plan.md) — Vision, affordable loss, crazy quilt, and gates
3. [Agents](docs/3_agents.md) — How agents work and think
4. [Contributing](docs/4_contribute.md) — Setup, assignments, and PR process

The [Contributing Guide](docs/4_contribute.md) provides three hands-on assignments to help you learn by doing.

## Community

Join our [Discord](https://discord.gg/5B9VdQ6vYP) — where we meet, plan, and discuss Euno updates and what's happening.

## Documentation

- [Pitch](docs/1_pitch.md) — Introduction and vision
- [Business Plan](docs/2_business-plan.md) — Vision and growth gates
- [Agents](docs/3_agents.md) — What agents are and how they work
- [Contributing](docs/4_contribute.md) — Setup, PR process, deployment
- [Points](docs/5_points.md) — Contribution tracking and rewards
- [Operating Agreement](docs/6_operating-agreement.md) — Ownership and governance
- [Privacy](docs/7_privacy.md) — Privacy philosophy and current state

## Spec (Design Rules)

The [spec/](spec/) directory is the best place to understand how Euno works. Each file is intentionally scannable—designed for both humans and AI to quickly grasp the system's rules.

**Why specs matter:** Specs are our AI-first alternative to unit tests. They maintain system consistency across the entire platform. Before merging any PR, ask a coding agent to review the specs and check for implementation drift. This ensures changes align with the system's design.

- [Agents](spec/1_agents.md) — Agent behavior, job coordination, triggers, work cycles
- [Data](spec/2_data.md) — Entity schemas (memory, profile, agent, job, config)
- [Backend](spec/3_backend.md) — Server, API, authentication, storage
- [UX & UI](spec/4_ux_ui.md) — User experience and interface patterns
- [CLI](spec/5_cli.md) — Command-line interface commands and behavior

## License

This project is proprietary software. See [LICENSE](LICENSE) for terms. By contributing, you agree to assign your contributions to the project.
