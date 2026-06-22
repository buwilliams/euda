# Metacognition (Self-Regulation)

## Key Ideas

- **Bounded Power**: agents are given real capability and kept safe by guardrails, not by denial. Self-regulation is the primary guardrail.
- **Token Awareness**: agents estimate cost before acting, record it after, and live within a budget. Money and attention are finite.
- **Auto-Pause Over Runaway**: when an agent breaches its budget, it pauses and waits for a person, rather than continuing to spend.
- **Stuck Detection**: an agent that repeats the same action without progress should notice and break the loop.
- **Incidents Are Visible**: threshold breaches and warnings are recorded and surfaced, not swallowed.

## Purpose

Self-regulation exists so that autonomous agents are safe to run unattended. A fleet of background agents acting on a person's behalf must not quietly burn budget, spin in loops, or hide failures. Metacognition gives each agent the awareness to govern itself and the honesty to report when it cannot.

This is Euda's expression of *mitigation greater than prevention*: rather than restricting what agents may attempt, Euda makes their resource use measurable, their loops detectable, their failures visible, and their pauses deliberate.

## Expected Role

Self-regulation should wrap every agent's operation:

- **Token Awareness** — pre-call estimation, post-call recording, and per-agent budgets. A global budget can be divided among enabled agents, with separate input and output allowances and configurable frequency (daily, hourly, and so on).
- **Agent States** — `enabled`, `disabled`, and `paused`. A `paused` agent has hit a limit or an incident and requires manual intervention; it does not resume itself.
- **Progress / Stuck Detection** — counting tool calls per iteration and noticing when the same action repeats with identical inputs, then breaking the cycle.
- **Incidents** — recording threshold breaches and warnings so a person can see why an agent paused and what happened.

Current implementation details that matter to intent:

- `v1` implements these under `agent/cognition/metacognition/regulation/`, with system-wide defaults in `data/system/config.json` under `metacognition`, and surfaces pauses, monitoring, and incidents in the Focus UI.
- On `main`, the LLM app carries budget and pause state in its config (hourly token and cost windows, a `paused` flag), so cost governance lives with the capability that spends.
- The Focus surface shows a paused agent plainly—for example, "Agent paused due to token budget"—with the path to resume.

Self-regulation should never become a wall that prevents useful work. Its job is to make power *accountable*, so that an agent can be trusted to run on its own.

## Future Direction

As agent fleets grow, self-regulation should evolve toward orchestration-aware budgeting: priorities across agents, smarter detection of unproductive loops, and richer incident reporting. Stronger agents will attempt more ambitious work, which makes honest accounting and clean pausing more important, not less.

The intent to preserve: every agent watches itself, spends within bounds, stops when stuck, pauses rather than runs away, and tells the person the truth about what happened.
