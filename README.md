<p align="center">
  <img src="static/images/euno-logo-with-subtitle.png" alt="Euno" width="50%">
</p>

_Euno (you-know), from Eudaimonia (you-dye-MOH-nee-ah)—ancient Greek for "human flourishing." A deep sense of fulfillment achieved through virtuous living, developing one's potential, and engaging in meaningful activities._

Today's AI remembers facts about you, but it doesn't know you. Euno understands who you are—your values, your patterns, your rhythms. **Euno is a personal intelligence that learns to anticipate you.** It understands who you are, proactively does tasks for you, and curates what deserves your attention.

## Contributing

1. **Get access** — Request access to the [repo](https://github.com/buwilliams/Euno) and [GitHub Projects](https://github.com/users/buwilliams/projects/1)
2. **Read the docs** — Start with [Pitch](docs/1_pitch.md) and [Business Plan](docs/2_business-plan.md)
3. **Set up locally** — See [Contributing Guide](docs/4_contribute.md) for setup and deployment
4. **Work on your first feature** — Pick a task from [GitHub Projects](https://github.com/users/buwilliams/projects/1)
5. **Review against spec** — Check your changes against [spec/](spec/) for drift
6. **Submit your PR** — Repository administrators approve merges into main

**Time & cost expectations:** See [Affordable Loss](docs/2_business-plan.md#vision) in the Business Plan. See the [Operating Agreement](docs/6_operating-agreement.md) for contributor rewards.

## Documentation

- [Pitch](docs/1_pitch.md) — Introduction and vision
- [Business Plan](docs/2_business-plan.md) — Vision and growth gates
- [Anticipate](docs/3_anticipate.md) — Profile + Memory = Anticipation
- [Contributing](docs/4_contribute.md) — Setup, PR process, deployment
- [Points](docs/5_points.md) — Contribution tracking and rewards
- [Operating Agreement](docs/6_operating-agreement.md) — Ownership and governance

## Spec (Design Rules)

The [spec/](spec/) directory is the best place to understand how Euno works. Each file is intentionally scannable—designed for both humans and AI to quickly grasp the system's rules.

**Why specs matter:** Specs are our AI-first alternative to unit tests. They maintain system consistency across the entire platform. Before merging any PR, ask a coding agent to review the specs and check for implementation drift. This ensures changes align with the system's design.

- [Orchestration](spec/1_orchestration.md) — Agent/job coordination, triggers, work cycles
- [Data](spec/2_data.md) — Entity schemas (lifelog, profile, memory, agent, job, config)
- [Backend](spec/3_backend.md) — Server, API, authentication, storage
- [UX & UI](spec/4_ux_ui.md) — User experience and interface patterns
- [CLI](spec/5_cli.md) — Command-line interface commands and behavior

## License

This project is proprietary software. See [LICENSE](LICENSE) for terms. By contributing, you agree to assign your contributions to the project.
