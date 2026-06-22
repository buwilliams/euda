# Triggers

## Key Ideas

- **Background Over Noise**: agents work on their own schedule, quietly. Triggers are how autonomous work begins without a person initiating it.
- **Triggers Create Topics**: a trigger does not wake an agent directly—it creates a topic. All work, even scheduled work, flows through the visible board.
- **Time And Event**: triggers fire on schedules (morning, evening, hourly), on intervals (daily, weekly, and far beyond), and on system events.
- **Recurrence Without Clutter**: a trigger can reuse a single topic instead of piling up duplicates, so a recurring concern stays one living item.

## Purpose

Triggers exist so Euda can act in the background, on its own initiative, without interrupting. The whole premise of managed attention is that agents do their work quietly—curating, exploring, consolidating—and surface only what matters. Triggers are the clockwork that sets that background activity in motion.

Crucially, triggers preserve visibility. Rather than silently waking an agent, a trigger creates a topic. So even autonomous, scheduled work appears on the same board a person already watches, and nothing the system does on its own is hidden.

## Expected Role

Triggers should turn the passage of time and the occurrence of events into visible work:

- a trigger names an event, a topic to create, and instructions for that topic;
- on firing, it creates (or reopens) the topic, which the assigned agent then claims and works;
- recurring triggers can reuse one topic so a standing concern does not multiply.

Event kinds include:

- **Schedule events** — named times of day such as `morning`, `evening`, and hourly marks, mapped to a person's configured schedule.
- **Interval events** — fixed cadences from `minute` and `hourly` through `daily`, `weekly`, `monthly`, and onward to spans like `generational` and `centennial`, with state tracked per trigger.
- **System events** — occurrences such as startup, a received message, or a topic's creation or completion.

Current implementation details that matter to intent:

- `v1` configures triggers per agent in `config.json` under `triggers[]`, with `event`, `topic_name`, `instructions`, and an optional `only_one` to reuse a single topic.
- Internal system topics (named like `euno:consolidate`) can run directly rather than through a full reasoning loop, so routine maintenance such as consolidation is cheap and reliable.
- A manager process loads agents, watches for config changes, and creates scheduled topics at trigger times.

Triggers should not become a general-purpose scheduler or a way to bypass the board. Their purpose is to begin background work *as visible topics*, on a cadence that fits a person's life.

## Future Direction

As Euda spreads across surfaces—wearables, smart devices, voice—triggers should grow richer event sources while keeping the same discipline: scheduled and event-driven work always becomes a visible topic. The intent to preserve: agents act in the background on their own initiative, quietly, and never invisibly.
