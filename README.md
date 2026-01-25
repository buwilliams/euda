<p align="center">
  <img src="src/web/frontend/images/euno-logo-with-subtitle.png" alt="Euno" width="50%">
</p>

_Euno (you-know), from Eudaimonia (you-dye-MOH-nee-ah)—ancient Greek for "human flourishing." A deep sense of fulfillment achieved through virtuous living, developing one's potential, and engaging in meaningful activities._

Today's AI remembers facts about you, but it doesn't know you. Euno understands who you are—your values, your patterns, your rhythms. **Euno is a personal intelligence that learns to anticipate you.** It understands who you are, proactively does tasks for you, and curates what deserves your attention.

## Getting Started

The best way to get started is to understand the mental model behind Euno.

**Suggested reading:**
1. [Pitch](docs/1_pitch.md) — What Euno is and why it exists
2. [Euno for People](docs/2_euno_for_people.md) — Personas and how Euno helps them flourish
3. [Business Plan](docs/3_business-plan.md) — Vision, affordable loss, crazy quilt, and gates
4. [System](docs/4_system.md) — Entities, ontology, and lifecycle

The [Contributing Guide](docs/5_contribute.md) provides three hands-on assignments to help you learn by doing.

## Usage

```bash
# Install dependencies (requires uv: https://docs.astral.sh/uv/)
uv sync
playwright install chromium  # for e2e tests

# Start Euno (web server + agents)
uv run euno start

# Run tests
uv run pytest                      # unit + integration tests (default)
uv run pytest tests/e2e/           # e2e UI tests (requires running server)

# CLI commands
uv run euno chat                   # interactive chat with agent
uv run euno dev watch              # stream all system events
uv run euno dev memory chat        # view agent's memory
```

## Community

Join our [Discord](https://discord.gg/5B9VdQ6vYP) — where we meet, plan, and discuss Euno updates and what's happening. Merged PRs are automatically posted to #updates so everyone stays in sync.

## Source of Truth

Euno follows a top-down information hierarchy. When making changes, update higher levels first:

- **docs/** — most reliable understanding of Euno (what and why)
- **specs/** — technical details enforcing the docs (single-depth bullet rules)
- **tests/** — enforces the specs and docs, not the Python code
- **src/** — implementation produced from docs, specs, and tests

**Claude Code skills for maintaining consistency:**

- `/check-alignment` — Detect drift between docs, specs, tests, and code without making changes
- `/align` — After updating docs or specs, propagate changes downstream through specs, tests, and code

## Documentation

- [Pitch](docs/1_pitch.md) — Introduction and vision
- [Euno for People](docs/2_euno_for_people.md) — Personas and how Euno helps them flourish
- [Business Plan](docs/3_business-plan.md) — Vision and growth gates
- [System](docs/4_system.md) — Entities, ontology, and lifecycle
- [Contributing](docs/5_contribute.md) — Setup, PR process, deployment
- [Points](docs/6_points.md) — Contribution tracking and rewards
- [Operating Agreement](docs/7_operating-agreement.md) — Ownership and governance
- [Privacy](docs/8_privacy.md) — Privacy philosophy and current state

## License

This project is proprietary software. See [LICENSE](LICENSE) for terms. By contributing, you agree to assign your contributions to the project.

